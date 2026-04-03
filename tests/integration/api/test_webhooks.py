"""Integration tests for webhook endpoint.

Webhook payload shape matches verified docs:
  {orderNo, currency, iccid, lpa, packageCode, packageName, price, result}
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.deps import get_provider
from app.providers.base import BaseEsimProvider


@pytest.fixture
def webhook_provider() -> AsyncMock:
    mock = AsyncMock(spec=BaseEsimProvider)
    mock.provider_name = "esim_access"
    mock.handle_webhook.return_value = {
        "event_type": "ORDER_STATUS",
        "order_no": "ORD-1",
        "iccid": "ICC-001",
        "lpa": "LPA:1$rsp.demo$MATCH",
        "package_code": "YN123",
        "package_name": "Test Package",
        "price": "9.99",
        "currency": "4",
        "status": "completed",
        "raw": {},
    }
    return mock


@pytest.mark.asyncio
async def test_webhook_ingestion(
    app,
    client: AsyncClient,
    webhook_provider: AsyncMock,  # type: ignore[no-untyped-def]
) -> None:
    app.dependency_overrides[get_provider] = lambda: webhook_provider

    response = await client.post(
        "/v1/provider/webhooks/esim-access",
        json={
            "orderNo": "ORD-1",
            "currency": "4",
            "iccid": "ICC-001",
            "lpa": "LPA:1$rsp.demo$MATCH",
            "packageCode": "YN123",
            "packageName": "Test Package",
            "price": "9.99",
            "result": "COMPLETED",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["received"] is True
    assert data["data"]["event_id"] is not None
