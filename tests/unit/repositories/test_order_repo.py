"""Unit tests for OrderRepository."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import ProviderOrder
from app.repositories.order import OrderRepository


@pytest.mark.asyncio
async def test_create_and_get_order(db_session: AsyncSession) -> None:
    repo = OrderRepository(db_session)

    order = ProviderOrder(
        id=str(uuid.uuid4()),
        transaction_id="txn-1",
        package_code="US_1_7",
        quantity=1,
        status="pending",
    )
    created = await repo.create(order)
    assert created.id == order.id

    fetched = await repo.get_by_id(order.id)
    assert fetched is not None
    assert fetched.transaction_id == "txn-1"


@pytest.mark.asyncio
async def test_get_by_transaction_id(db_session: AsyncSession) -> None:
    repo = OrderRepository(db_session)

    order = ProviderOrder(
        id=str(uuid.uuid4()),
        transaction_id="unique-txn",
        package_code="PKG_1",
        quantity=1,
        status="pending",
    )
    await repo.create(order)

    found = await repo.get_by_transaction_id("unique-txn")
    assert found is not None
    assert found.id == order.id


@pytest.mark.asyncio
async def test_update_status(db_session: AsyncSession) -> None:
    repo = OrderRepository(db_session)
    oid = str(uuid.uuid4())

    order = ProviderOrder(
        id=oid,
        transaction_id=str(uuid.uuid4()),
        package_code="PKG_1",
        quantity=1,
        status="pending",
    )
    await repo.create(order)

    updated = await repo.update_status(oid, "completed", provider_order_no="ORD-1")
    assert updated is not None
    assert updated.status == "completed"
    assert updated.provider_order_no == "ORD-1"


@pytest.mark.asyncio
async def test_get_pending_orders(db_session: AsyncSession) -> None:
    repo = OrderRepository(db_session)

    for status in ["pending", "processing", "completed"]:
        await repo.create(
            ProviderOrder(
                id=str(uuid.uuid4()),
                transaction_id=str(uuid.uuid4()),
                package_code="PKG",
                quantity=1,
                status=status,
            )
        )

    pending = await repo.get_pending_orders()
    assert len(pending) == 2
    assert all(o.status in ("pending", "processing") for o in pending)
