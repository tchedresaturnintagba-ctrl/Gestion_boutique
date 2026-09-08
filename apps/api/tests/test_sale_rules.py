from uuid import UUID

import pytest

from gestion_boutiques.domain.sales import (
    InsufficientStockError,
    SaleLine,
    SalePermissionError,
    UserRole,
    validate_sale,
)

PRODUCT_A = UUID("00000000-0000-0000-0000-000000000001")
PRODUCT_B = UUID("00000000-0000-0000-0000-000000000002")


def test_manager_can_validate_sale_when_stock_is_sufficient() -> None:
    validate_sale(
        actor_role=UserRole.MANAGER,
        lines=[SaleLine(product_id=PRODUCT_A, quantity=2)],
        available_stock={PRODUCT_A: 3},
    )


def test_owner_cannot_enter_sale_in_mvp() -> None:
    with pytest.raises(SalePermissionError):
        validate_sale(
            actor_role=UserRole.OWNER,
            lines=[SaleLine(product_id=PRODUCT_A, quantity=1)],
            available_stock={PRODUCT_A: 3},
        )


def test_sale_reports_every_insufficient_product() -> None:
    with pytest.raises(InsufficientStockError) as error:
        validate_sale(
            actor_role=UserRole.MANAGER,
            lines=[
                SaleLine(product_id=PRODUCT_A, quantity=4),
                SaleLine(product_id=PRODUCT_B, quantity=2),
            ],
            available_stock={PRODUCT_A: 3},
        )

    actual_shortages = [
        (item.product_id, item.available_quantity, item.requested_quantity)
        for item in error.value.shortages
    ]
    assert actual_shortages == [
        (PRODUCT_A, 3, 4),
        (PRODUCT_B, 0, 2),
    ]