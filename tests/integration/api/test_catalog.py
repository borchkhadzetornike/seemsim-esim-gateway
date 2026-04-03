"""Integration tests for catalog endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.deps import get_provider
from app.providers.base import BaseEsimProvider, ProviderPackageData


@pytest.fixture
def mock_provider_with_data() -> AsyncMock:
    mock = AsyncMock(spec=BaseEsimProvider)
    mock.provider_name = "esim_access"
    mock.sync_products.return_value = [
        ProviderPackageData(
            package_code="US_1_7",
            name="USA 1GB 7 Days",
            type="BASE",
            data_volume_mb=1024,
            duration_days=7,
            price=4.5,
            currency="USD",
            countries=["US"],
            location_code="US",
            raw={},
        ),
    ]
    return mock


@pytest.mark.asyncio
async def test_sync_catalog_endpoint(
    app,
    client: AsyncClient,
    mock_provider_with_data: AsyncMock,  # type: ignore[no-untyped-def]
) -> None:
    app.dependency_overrides[get_provider] = lambda: mock_provider_with_data

    response = await client.post("/v1/catalog/sync")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["packages_synced"] == 1


@pytest.mark.asyncio
async def test_list_products_empty(client: AsyncClient) -> None:
    response = await client.get("/v1/catalog/products")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"] == []


@pytest.mark.asyncio
async def test_get_product_not_found(client: AsyncClient) -> None:
    response = await client.get("/v1/catalog/products/nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["error_code"] == "RESOURCE_NOT_FOUND"
