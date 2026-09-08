from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from gestion_boutiques.api.dependencies import CurrentUser, SessionDependency, require_roles
from gestion_boutiques.api.stores import get_accessible_store
from gestion_boutiques.models.catalog import StoreProduct
from gestion_boutiques.models.inventory import (
    InventoryBalance,
    StockAlert,
    StockAlertType,
    StockMovement,
    StockMovementType,
)
from gestion_boutiques.models.store import StoreOwnership
from gestion_boutiques.models.user import User, UserRole
from gestion_boutiques.schemas.inventory import (
    InventoryBalanceListResponse,
    InventoryBalanceResponse,
    StockAlertListResponse,
    StockAlertResponse,
    StockMovementCreate,
    StockMovementListResponse,
    StockMovementResponse,
    StockMovementResultResponse,
)
from gestion_boutiques.services.audit import record_audit_event

router = APIRouter(prefix="/inventory", tags=["inventory"])
ManagerUser = Annotated[User, Depends(require_roles(UserRole.MANAGER))]
INCREASE_TYPES = {StockMovementType.ENTRY, StockMovementType.ADJUSTMENT_IN}


async def get_store_product_configuration(
    session: AsyncSession,
    organization_id: UUID,
    store_id: UUID,
    product_id: UUID,
) -> StoreProduct:
    configuration = await session.scalar(
        select(StoreProduct).where(
            StoreProduct.organization_id == organization_id,
            StoreProduct.store_id == store_id,
            StoreProduct.product_id == product_id,
        )
    )
    if configuration is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produit non configuré pour cette boutique",
        )
    if not configuration.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce produit est inactif dans cette boutique",
        )
    return configuration


async def reconcile_stock_alert(
    session: AsyncSession,
    *,
    organization_id: UUID,
    store_id: UUID,
    product_id: UUID,
    quantity: Decimal,
    threshold: Decimal,
) -> StockAlert | None:
    open_alert = await session.scalar(
        select(StockAlert)
        .where(
            StockAlert.organization_id == organization_id,
            StockAlert.store_id == store_id,
            StockAlert.product_id == product_id,
            StockAlert.resolved_at.is_(None),
        )
        .with_for_update()
    )
    target_type = None
    if quantity == 0:
        target_type = StockAlertType.OUT_OF_STOCK
    elif quantity <= threshold:
        target_type = StockAlertType.LOW_STOCK

    if target_type is None:
        if open_alert is not None:
            open_alert.resolved_at = datetime.now(UTC)
        return None

    if open_alert is not None and open_alert.alert_type is target_type:
        open_alert.observed_quantity = quantity
        open_alert.threshold = threshold
        return open_alert

    if open_alert is not None:
        open_alert.resolved_at = datetime.now(UTC)
        await session.flush()

    new_alert = StockAlert(
        organization_id=organization_id,
        store_id=store_id,
        product_id=product_id,
        alert_type=target_type,
        observed_quantity=quantity,
        threshold=threshold,
    )
    session.add(new_alert)
    return new_alert


@router.post(
    "/stores/{store_id}/movements",
    response_model=StockMovementResultResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_stock_movement(
    store_id: UUID,
    request: StockMovementCreate,
    session: SessionDependency,
    manager: ManagerUser,
) -> StockMovementResultResponse:
    await get_accessible_store(session, manager, store_id)
    configuration = await get_store_product_configuration(
        session,
        manager.organization_id,
        store_id,
        request.product_id,
    )
    balance = await session.scalar(
        select(InventoryBalance)
        .where(
            InventoryBalance.organization_id == manager.organization_id,
            InventoryBalance.store_id == store_id,
            InventoryBalance.product_id == request.product_id,
        )
        .with_for_update()
    )
    if balance is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Le solde de stock n'est pas initialisé",
        )

    previous_quantity = balance.quantity
    delta = request.quantity if request.movement_type in INCREASE_TYPES else -request.quantity
    new_quantity = previous_quantity + delta
    if new_quantity < 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stock insuffisant pour cette sortie",
        )

    balance.quantity = new_quantity
    movement = StockMovement(
        organization_id=manager.organization_id,
        store_id=store_id,
        product_id=request.product_id,
        actor_user_id=manager.id,
        movement_type=request.movement_type,
        quantity=request.quantity,
        previous_quantity=previous_quantity,
        new_quantity=new_quantity,
        reason=request.reason,
    )
    session.add(movement)
    alert = await reconcile_stock_alert(
        session,
        organization_id=manager.organization_id,
        store_id=store_id,
        product_id=request.product_id,
        quantity=new_quantity,
        threshold=configuration.low_stock_threshold,
    )
    await session.flush()
    record_audit_event(
        session,
        organization_id=manager.organization_id,
        actor_user_id=manager.id,
        action="stock.movement_recorded",
        entity_type="stock_movement",
        entity_id=movement.id,
        details={
            "store_id": str(store_id),
            "product_id": str(request.product_id),
            "movement_type": request.movement_type.value,
            "quantity": str(request.quantity),
            "new_quantity": str(new_quantity),
        },
    )
    await session.refresh(movement)
    await session.refresh(balance)
    if alert is not None:
        await session.refresh(alert)
    await session.commit()
    return StockMovementResultResponse(
        movement=StockMovementResponse.model_validate(movement),
        balance=InventoryBalanceResponse.model_validate(balance),
        alert=StockAlertResponse.model_validate(alert) if alert is not None else None,
    )


@router.get(
    "/stores/{store_id}/balances",
    response_model=InventoryBalanceListResponse,
)
async def list_inventory_balances(
    store_id: UUID,
    session: SessionDependency,
    current_user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> InventoryBalanceListResponse:
    await get_accessible_store(session, current_user, store_id)
    query = select(InventoryBalance).where(
        InventoryBalance.organization_id == current_user.organization_id,
        InventoryBalance.store_id == store_id,
    )
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    balances = (
        await session.scalars(
            query.order_by(InventoryBalance.product_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return InventoryBalanceListResponse(
        items=[InventoryBalanceResponse.model_validate(balance) for balance in balances],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/stores/{store_id}/movements",
    response_model=StockMovementListResponse,
)
async def list_stock_movements(
    store_id: UUID,
    session: SessionDependency,
    current_user: CurrentUser,
    product_id: UUID | None = None,
    movement_type: StockMovementType | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> StockMovementListResponse:
    await get_accessible_store(session, current_user, store_id)
    query = select(StockMovement).where(
        StockMovement.organization_id == current_user.organization_id,
        StockMovement.store_id == store_id,
    )
    if product_id is not None:
        query = query.where(StockMovement.product_id == product_id)
    if movement_type is not None:
        query = query.where(StockMovement.movement_type == movement_type)
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    movements = (
        await session.scalars(
            query.order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return StockMovementListResponse(
        items=[StockMovementResponse.model_validate(movement) for movement in movements],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/alerts", response_model=StockAlertListResponse)
async def list_stock_alerts(
    session: SessionDependency,
    current_user: CurrentUser,
    store_id: UUID | None = None,
    open_only: bool = True,
    alert_type: StockAlertType | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> StockAlertListResponse:
    query = select(StockAlert).where(
        StockAlert.organization_id == current_user.organization_id
    )
    if current_user.role is UserRole.OWNER:
        query = query.join(
            StoreOwnership,
            StoreOwnership.store_id == StockAlert.store_id,
        ).where(StoreOwnership.owner_id == current_user.id)
    if store_id is not None:
        await get_accessible_store(session, current_user, store_id)
        query = query.where(StockAlert.store_id == store_id)
    if open_only:
        query = query.where(StockAlert.resolved_at.is_(None))
    if alert_type is not None:
        query = query.where(StockAlert.alert_type == alert_type)
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    alerts = (
        await session.scalars(
            query.order_by(StockAlert.created_at.desc(), StockAlert.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return StockAlertListResponse(
        items=[StockAlertResponse.model_validate(alert) for alert in alerts],
        total=total or 0,
        page=page,
        page_size=page_size,
    )