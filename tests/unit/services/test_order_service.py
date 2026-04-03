"""Unit tests for OrderService.

Reflects the verified contract where create_order returns status="pending"
and iccid=None. ICCID is delivered asynchronously via webhook.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    ProviderCapabilityUnavailableError,
    ProviderValidationError,
    ResourceNotFoundError,
)
from app.providers.base import ProviderOrderResult
from app.services.order import OrderService


@pytest.fixture
def provider() -> AsyncMock:
    mock = AsyncMock()
    mock.provider_name = "esim_access"
    return mock


@pytest.mark.asyncio
async def test_create_order_success_pending(db_session: AsyncSession, provider: AsyncMock) -> None:
    """Order creation returns pending status with no ICCID."""
    provider.create_order.return_value = ProviderOrderResult(
        order_no="ORD-1",
        transaction_id="txn-1",
        status="pending",
        iccid=None,
        raw={"orderNo": "ORD-1"},
    )

    service = OrderService(provider=provider, session=db_session)
    order = await service.create_order("US_1_7", 1, "idem-key-1")

    assert order.provider_order_no == "ORD-1"
    assert order.status == "pending"
    assert order.iccid is None
    provider.create_order.assert_called_once()


@pytest.mark.asyncio
async def test_create_order_provider_failure(db_session: AsyncSession, provider: AsyncMock) -> None:
    provider.create_order.side_effect = ProviderValidationError("Package not found")

    service = OrderService(provider=provider, session=db_session)

    with pytest.raises(ProviderValidationError):
        await service.create_order("INVALID_PKG", 1)


@pytest.mark.asyncio
async def test_get_order_not_found(db_session: AsyncSession, provider: AsyncMock) -> None:
    service = OrderService(provider=provider, session=db_session)

    with pytest.raises(ResourceNotFoundError):
        await service.get_order("nonexistent-id")


@pytest.mark.asyncio
async def test_cancel_order_raises_capability_unavailable(
    db_session: AsyncSession, provider: AsyncMock
) -> None:
    """Cancel is not documented — adapter raises ProviderCapabilityUnavailableError."""
    provider.create_order.return_value = ProviderOrderResult(
        order_no="ORD-1",
        transaction_id="txn-1",
        status="pending",
        iccid=None,
        raw={},
    )
    provider.cancel_order.side_effect = ProviderCapabilityUnavailableError(
        "Not supported"
    )

    service = OrderService(provider=provider, session=db_session)
    order = await service.create_order("PKG_1", 1)

    with pytest.raises(ProviderCapabilityUnavailableError):
        await service.cancel_order(order.id)
