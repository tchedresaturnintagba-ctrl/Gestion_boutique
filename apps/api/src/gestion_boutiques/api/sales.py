from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from gestion_boutiques.api.dependencies import CurrentUser, SessionDependency, require_roles
from gestion_boutiques.api.inventory import reconcile_stock_alert
from gestion_boutiques.api.stores import get_accessible_store
from gestion_boutiques.domain.sales import (
    InsufficientStockError,
    validate_sale,
)
from gestion_boutiques.domain.sales import (
    SaleLine as DomainSaleLine,
)
from gestion_boutiques.domain.sales import (
    UserRole as DomainUserRole,
)
from gestion_boutiques.models.catalog import StoreProduct
from gestion_boutiques.models.inventory import (
    InventoryBalance,
    StockMovement,
    StockMovementType,
)
from gestion_boutiques.models.sale import Sale, SaleLine
from gestion_boutiques.models.store import StoreOwnership
from gestion_boutiques.models.user import User, UserRole
from gestion_boutiques.schemas.sales import SaleCreate, SaleListResponse, SaleResponse
from gestion_boutiques.services.audit import record_audit_event

router = APIRouter(prefix="/sales", tags=["sales"])
ManagerUser = Annotated[User, Depends(require_roles(UserRole.MANAGER))]
MONEY_QUANTUM = Decimal("0.01")


def accessible_sales_query(current_user: User):
    query = select(Sale).where(Sale.organization_id == current_user.organization_id)
    if current_user.role is UserRole.OWNER:
        query = query.join(
            StoreOwnership,
            StoreOwnership.store_id == Sale.store_id,
        ).where(StoreOwnership.owner_id == current_user.id)
    return query


def consolidate_lines(request: SaleCreate) -> dict[UUID, Decimal]:
    requested_by_product: dict[UUID, Decimal] = {}
    for line in request.lines:
        requested_by_product[line.product_id] = (
            requested_by_product.get(line.product_id, Decimal(0)) + line.quantity
        )
    return requested_by_product


@router.post("", response_model=SaleResponse, status_code=status.HTTP_201_CREATED)
async def create_sale(
    request: SaleCreate,
    session: SessionDependency,
    manager: ManagerUser,
) -> SaleResponse:
    store = await get_accessible_store(session, manager, request.store_id)
    if not store.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La boutique est suspendue",
        )

    requested_by_product = consolidate_lines(request)
    product_ids = sorted(requested_by_product, key=str)
    configurations = (
        await session.scalars(
            select(StoreProduct)
            .where(
                StoreProduct.organization_id == manager.organization_id,
                StoreProduct.store_id == request.store_id,
                StoreProduct.product_id.in_(product_ids),
            )
            .order_by(StoreProduct.product_id)
            .with_for_update()
        )
    ).all()
    configuration_by_product = {
        configuration.product_id: configuration for configuration in configurations
    }
    unavailable_product_ids = [
        product_id
        for product_id in product_ids
        if product_id not in configuration_by_product
        or not configuration_by_product[product_id].is_active
    ]
    if unavailable_product_ids:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Produits indisponibles dans cette boutique",
                "product_ids": [str(product_id) for product_id in unavailable_product_ids],
            },
        )

    balances = (
        await session.scalars(
            select(InventoryBalance)
            .where(
                InventoryBalance.organization_id == manager.organization_id,
                InventoryBalance.store_id == request.store_id,
                InventoryBalance.product_id.in_(product_ids),
            )
            .order_by(InventoryBalance.product_id)
            .with_for_update()
        )
    ).all()
    balance_by_product = {balance.product_id: balance for balance in balances}
    if len(balance_by_product) != len(product_ids):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Le stock de certains produits n'est pas initialisé",
        )

    try:
        validate_sale(
            actor_role=DomainUserRole(manager.role.value),
            lines=[
                DomainSaleLine(product_id=product_id, quantity=quantity)
                for product_id, quantity in requested_by_product.items()
            ],
            available_stock={
                product_id: balance_by_product[product_id].quantity
                for product_id in product_ids
            },
        )
    except InsufficientStockError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(error),
                "shortages": [
                    {
                        "product_id": str(shortage.product_id),
                        "available_quantity": str(shortage.available_quantity),
                        "requested_quantity": str(shortage.requested_quantity),
                    }
                    for shortage in error.shortages
                ],
            },
        ) from error

    line_totals = {
        product_id: (
            Decimal(configuration_by_product[product_id].unit_price) * quantity
        ).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
        for product_id, quantity in requested_by_product.items()
    }
    sale = Sale(
        id=uuid4(),
        organization_id=manager.organization_id,
        store_id=request.store_id,
        actor_user_id=manager.id,
        total_amount=sum(line_totals.values(), start=Decimal(0)),
        lines=[],
    )
    session.add(sale)
    await session.flush()

    for product_id in product_ids:
        quantity = requested_by_product[product_id]
        configuration = configuration_by_product[product_id]
        balance = balance_by_product[product_id]
        previous_quantity = balance.quantity
        new_quantity = previous_quantity - quantity
        balance.quantity = new_quantity
        sale.lines.append(
            SaleLine(
                id=uuid4(),
                sale_id=sale.id,
                organization_id=manager.organization_id,
                store_id=request.store_id,
                product_id=product_id,
                quantity=quantity,
                unit_price=configuration.unit_price,
                line_total=line_totals[product_id],
            )
        )
        session.add(
            StockMovement(
                organization_id=manager.organization_id,
                store_id=request.store_id,
                product_id=product_id,
                actor_user_id=manager.id,
                sale_id=sale.id,
                movement_type=StockMovementType.SALE,
                quantity=quantity,
                previous_quantity=previous_quantity,
                new_quantity=new_quantity,
                reason=f"Vente {sale.id}",
            )
        )
        await reconcile_stock_alert(
            session,
            organization_id=manager.organization_id,
            store_id=request.store_id,
            product_id=product_id,
            quantity=new_quantity,
            threshold=configuration.low_stock_threshold,
        )

    await session.flush()
    record_audit_event(
        session,
        organization_id=manager.organization_id,
        actor_user_id=manager.id,
        action="sale.created",
        entity_type="sale",
        entity_id=sale.id,
        details={
            "store_id": str(request.store_id),
            "line_count": len(sale.lines),
            "total_amount": str(sale.total_amount),
        },
    )
    await session.commit()
    return SaleResponse.model_validate(sale)


@router.get("", response_model=SaleListResponse)
async def list_sales(
    session: SessionDependency,
    current_user: CurrentUser,
    store_id: UUID | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> SaleListResponse:
    query = accessible_sales_query(current_user)
    if store_id is not None:
        await get_accessible_store(session, current_user, store_id)
        query = query.where(Sale.store_id == store_id)
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    sales = (
        await session.scalars(
            query.options(selectinload(Sale.lines))
            .order_by(Sale.created_at.desc(), Sale.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return SaleListResponse(
        items=[SaleResponse.model_validate(sale) for sale in sales],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/{sale_id}", response_model=SaleResponse)
async def read_sale(
    sale_id: UUID,
    session: SessionDependency,
    current_user: CurrentUser,
) -> SaleResponse:
    sale = await session.scalar(
        accessible_sales_query(current_user)
        .where(Sale.id == sale_id)
        .options(selectinload(Sale.lines))
    )
    if sale is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vente introuvable")
    return SaleResponse.model_validate(sale)