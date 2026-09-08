from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from gestion_boutiques.api.dependencies import CurrentUser, SessionDependency, require_roles
from gestion_boutiques.api.stores import get_accessible_store
from gestion_boutiques.models.catalog import Category, Product, ProductUnit, StoreProduct
from gestion_boutiques.models.inventory import InventoryBalance
from gestion_boutiques.models.store import StoreOwnership
from gestion_boutiques.models.user import User, UserRole
from gestion_boutiques.schemas.catalog import (
    CategoryCreate,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdate,
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
    StoreProductConfigure,
    StoreProductListResponse,
    StoreProductResponse,
)
from gestion_boutiques.services.audit import record_audit_event

router = APIRouter(prefix="/catalog", tags=["catalog"])
ManagerUser = Annotated[User, Depends(require_roles(UserRole.MANAGER))]


def accessible_products_query(current_user: User):
    query = select(Product).where(Product.organization_id == current_user.organization_id)
    if current_user.role is UserRole.OWNER:
        query = (
            query.join(StoreProduct, StoreProduct.product_id == Product.id)
            .join(StoreOwnership, StoreOwnership.store_id == StoreProduct.store_id)
            .where(StoreOwnership.owner_id == current_user.id)
            .distinct()
        )
    return query


async def get_category(
    session: AsyncSession,
    organization_id: UUID,
    category_id: UUID,
) -> Category:
    category = await session.scalar(
        select(Category).where(
            Category.id == category_id,
            Category.organization_id == organization_id,
        )
    )
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Catégorie introuvable",
        )
    return category


async def get_product(
    session: AsyncSession,
    organization_id: UUID,
    product_id: UUID,
) -> Product:
    product = await session.scalar(
        select(Product).where(
            Product.id == product_id,
            Product.organization_id == organization_id,
        )
    )
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produit introuvable",
        )
    return product


async def ensure_category_exists(
    session: AsyncSession,
    organization_id: UUID,
    category_id: UUID | None,
) -> None:
    if category_id is not None:
        await get_category(session, organization_id, category_id)


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    request: CategoryCreate,
    session: SessionDependency,
    manager: ManagerUser,
) -> Category:
    category = Category(organization_id=manager.organization_id, name=request.name)
    session.add(category)
    try:
        await session.flush()
        record_audit_event(
            session,
            organization_id=manager.organization_id,
            actor_user_id=manager.id,
            action="category.created",
            entity_type="category",
            entity_id=category.id,
        )
        await session.refresh(category)
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette catégorie existe déjà",
        ) from error
    return category


@router.get("/categories", response_model=CategoryListResponse)
async def list_categories(
    session: SessionDependency,
    current_user: CurrentUser,
    is_active: bool | None = None,
) -> CategoryListResponse:
    query = select(Category).where(Category.organization_id == current_user.organization_id)
    if is_active is not None:
        query = query.where(Category.is_active.is_(is_active))
    categories = (await session.scalars(query.order_by(Category.name, Category.id))).all()
    return CategoryListResponse(
        items=[CategoryResponse.model_validate(category) for category in categories],
        total=len(categories),
    )


@router.patch("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID,
    request: CategoryUpdate,
    session: SessionDependency,
    manager: ManagerUser,
) -> Category:
    category = await get_category(session, manager.organization_id, category_id)
    changes = request.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(category, field, value)
    try:
        record_audit_event(
            session,
            organization_id=manager.organization_id,
            actor_user_id=manager.id,
            action="category.updated",
            entity_type="category",
            entity_id=category.id,
            details={"changed_fields": sorted(changes)},
        )
        await session.flush()
        await session.refresh(category)
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette catégorie existe déjà",
        ) from error
    return category


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    request: ProductCreate,
    session: SessionDependency,
    manager: ManagerUser,
) -> Product:
    await ensure_category_exists(session, manager.organization_id, request.category_id)
    product = Product(
        organization_id=manager.organization_id,
        category_id=request.category_id,
        name=request.name,
        sku=request.sku,
        description=request.description,
        unit=request.unit,
    )
    session.add(product)
    try:
        await session.flush()
        record_audit_event(
            session,
            organization_id=manager.organization_id,
            actor_user_id=manager.id,
            action="product.created",
            entity_type="product",
            entity_id=product.id,
            details={"sku": product.sku},
        )
        await session.refresh(product)
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce SKU existe déjà",
        ) from error
    return product


@router.get("/products", response_model=ProductListResponse)
async def list_products(
    session: SessionDependency,
    current_user: CurrentUser,
    search: Annotated[str | None, Query(max_length=160)] = None,
    category_id: UUID | None = None,
    unit: ProductUnit | None = None,
    is_active: bool | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ProductListResponse:
    query = accessible_products_query(current_user)
    if search:
        term = f"%{search.strip()}%"
        query = query.where(or_(Product.name.ilike(term), Product.sku.ilike(term)))
    if category_id is not None:
        query = query.where(Product.category_id == category_id)
    if unit is not None:
        query = query.where(Product.unit == unit)
    if is_active is not None:
        query = query.where(Product.is_active.is_(is_active))
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    products = (
        await session.scalars(
            query.order_by(Product.name, Product.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return ProductListResponse(
        items=[ProductResponse.model_validate(product) for product in products],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/products/{product_id}", response_model=ProductResponse)
async def read_product(
    product_id: UUID,
    session: SessionDependency,
    current_user: CurrentUser,
) -> Product:
    product = await session.scalar(
        accessible_products_query(current_user).where(Product.id == product_id)
    )
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produit introuvable",
        )
    return product


@router.patch("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    request: ProductUpdate,
    session: SessionDependency,
    manager: ManagerUser,
) -> Product:
    product = await get_product(session, manager.organization_id, product_id)
    changes = request.model_dump(exclude_unset=True)
    await ensure_category_exists(session, manager.organization_id, changes.get("category_id"))
    for field, value in changes.items():
        setattr(product, field, value)
    try:
        record_audit_event(
            session,
            organization_id=manager.organization_id,
            actor_user_id=manager.id,
            action="product.updated",
            entity_type="product",
            entity_id=product.id,
            details={"changed_fields": sorted(changes)},
        )
        await session.flush()
        await session.refresh(product)
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce SKU existe déjà",
        ) from error
    return product


@router.put("/stores/{store_id}/products/{product_id}", response_model=StoreProductResponse)
async def configure_store_product(
    store_id: UUID,
    product_id: UUID,
    request: StoreProductConfigure,
    session: SessionDependency,
    manager: ManagerUser,
) -> StoreProduct:
    await get_accessible_store(session, manager, store_id)
    await get_product(session, manager.organization_id, product_id)
    key = {
        "organization_id": manager.organization_id,
        "store_id": store_id,
        "product_id": product_id,
    }
    store_product = await session.get(StoreProduct, key)
    action = "store_product.updated"
    if store_product is None:
        store_product = StoreProduct(**key)
        session.add(store_product)
        session.add(InventoryBalance(**key, quantity=Decimal(0)))
        action = "store_product.created"
    store_product.unit_price = request.unit_price
    store_product.low_stock_threshold = request.low_stock_threshold
    store_product.is_active = request.is_active
    record_audit_event(
        session,
        organization_id=manager.organization_id,
        actor_user_id=manager.id,
        action=action,
        entity_type="store_product",
        entity_id=product_id,
        details={"store_id": str(store_id)},
    )
    await session.flush()
    await session.refresh(store_product)
    await session.commit()
    return store_product


@router.get("/stores/{store_id}/products", response_model=StoreProductListResponse)
async def list_store_products(
    store_id: UUID,
    session: SessionDependency,
    current_user: CurrentUser,
    is_active: bool | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> StoreProductListResponse:
    await get_accessible_store(session, current_user, store_id)
    query = select(StoreProduct).where(
        StoreProduct.organization_id == current_user.organization_id,
        StoreProduct.store_id == store_id,
    )
    if is_active is not None:
        query = query.where(StoreProduct.is_active.is_(is_active))
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    configurations = (
        await session.scalars(
            query.order_by(StoreProduct.product_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return StoreProductListResponse(
        items=[StoreProductResponse.model_validate(item) for item in configurations],
        total=total or 0,
        page=page,
        page_size=page_size,
    )