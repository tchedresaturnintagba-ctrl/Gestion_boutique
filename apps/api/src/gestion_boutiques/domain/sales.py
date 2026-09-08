from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class UserRole(StrEnum):
    MANAGER = "manager"
    OWNER = "owner"


@dataclass(frozen=True, slots=True)
class SaleLine:
    product_id: UUID
    quantity: Decimal


@dataclass(frozen=True, slots=True)
class StockShortage:
    product_id: UUID
    available_quantity: Decimal
    requested_quantity: Decimal


class SaleValidationError(ValueError):
    """Base error for a sale rejected before persistence."""


class SalePermissionError(SaleValidationError):
    pass


class InvalidSaleQuantityError(SaleValidationError):
    pass


class InsufficientStockError(SaleValidationError):
    def __init__(self, shortages: Sequence[StockShortage]) -> None:
        self.shortages = tuple(shortages)
        super().__init__("Stock insuffisant pour valider la vente")


def validate_sale(
    *,
    actor_role: UserRole,
    lines: Sequence[SaleLine],
    available_stock: Mapping[UUID, Decimal],
) -> None:
    if actor_role is not UserRole.MANAGER:
        raise SalePermissionError("Seul un gestionnaire peut saisir une vente dans le MVP")

    if not lines:
        raise InvalidSaleQuantityError("Une vente doit contenir au moins un produit")

    requested_by_product: dict[UUID, Decimal] = {}
    for line in lines:
        if line.quantity <= 0:
            raise InvalidSaleQuantityError("La quantité vendue doit être strictement positive")
        requested_by_product[line.product_id] = (
            requested_by_product.get(line.product_id, 0) + line.quantity
        )

    shortages = [
        StockShortage(
            product_id=product_id,
            available_quantity=available_stock.get(product_id, 0),
            requested_quantity=requested_quantity,
        )
        for product_id, requested_quantity in requested_by_product.items()
        if requested_quantity > available_stock.get(product_id, 0)
    ]
    if shortages:
        raise InsufficientStockError(shortages)