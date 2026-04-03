"""Integration tests for order endpoints.

Order creation now returns status="pending" with iccid=None (ICCID
arrives via webhook per verified contract).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.deps import get_provider
from app.providers.base import BaseEsimProvider, ProviderOrderResult


@pytest.fixture
def mock_order_provider() -> AsyncMock:
    mock = AsyncMock(spec=BaseEsimProvider)
    mock.provider_name = "esim_access"
    mock.create_order.return_value = ProviderOrderResult(
        order_no="ORD-001",
        transaction_id="txn-test",
        status="pending",
        iccid=None,
        raw={"orderNo": "ORD-001"},
    )
    return mock


@pytest.mark.asyncio
async def test_create_order_success(
    app,
    client: AsyncClient,
    mock_order_provider: AsyncMock,  # type: ignore[no-untyped-def]
) -> None:
    app.dependency_overrides[get_provider] = lambda: mock_order_provider

    response = await client.post(
        "/v1/orders",
        json={"package_code": "US_1_7", "quantity": 1},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["provider_order_no"] == "ORD-001"
    assert data["data"]["status"] == "pending"


@pytest.mark.asyncio
async def test_create_order_with_idempotency_key(
    app,
    client: AsyncClient,
    mock_order_provider: AsyncMock,
    mock_redis: AsyncMock,  # type: ignore[no-untyped-def]
) -> None:
    app.dependency_overrides[get_provider] = lambda: mock_order_provider

    store: dict[str, str] = {}

    async def fake_get(key: str) -> str | None:
        return store.get(key)

    async def fake_set(key: str, value: str, **kwargs: object) -> bool:
        store[key] = value
        return True

    async def fake_delete(key: str) -> int:
        store.pop(key, None)
        return 1

    mock_redis.get = fake_get  # type: ignore[assignment]
    mock_redis.set = fake_set  # type: ignore[assignment]
    mock_redis.delete = fake_delete  # type: ignore[assignment]

    headers = {"Idempotency-Key": "test-idem-key-001"}
    body = {"package_code": "US_1_7", "quantity": 1}

    response1 = await client.post("/v1/orders", json=body, headers=headers)
    assert response1.status_code == 201

    response2 = await client.post("/v1/orders", json=body, headers=headers)
    assert response2.status_code == 201

    assert response1.json()["data"]["id"] == response2.json()["data"]["id"]
    assert mock_order_provider.create_order.call_count == 1


@pytest.mark.asyncio
async def test_get_order_not_found(client: AsyncClient) -> None:
    response = await client.get("/v1/orders/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_order_validation_error(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/orders",
        json={"package_code": "US_1_7", "quantity": 0},
    )
    assert response.status_code == 422
