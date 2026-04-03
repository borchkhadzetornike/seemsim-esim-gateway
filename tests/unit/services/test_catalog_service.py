"""Unit tests for CatalogService."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.providers.base import ProviderPackageData
from app.services.catalog import CatalogService


@pytest.mark.asyncio
async def test_sync_catalog_persists_products(
    db_session: AsyncSession, mock_provider: AsyncMock
) -> None:
    mock_provider.provider_name = "esim_access"
    mock_provider.sync_products.return_value = [
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
        ProviderPackageData(
            package_code="UK_2_14",
            name="UK 2GB 14 Days",
            type="BASE",
            data_volume_mb=2048,
            duration_days=14,
            price=8.0,
            currency="USD",
            countries=["GB"],
            location_code="GB",
            raw={},
        ),
    ]

    service = CatalogService(provider=mock_provider, session=db_session)
    result = await service.sync_catalog()

    assert result.products_synced == 2
    assert result.packages_synced == 2
    assert result.provider == "esim_access"

    products = await service.get_products()
    assert len(products) == 2


@pytest.mark.asyncio
async def test_sync_catalog_empty_list(db_session: AsyncSession, mock_provider: AsyncMock) -> None:
    mock_provider.provider_name = "esim_access"
    mock_provider.sync_products.return_value = []

    service = CatalogService(provider=mock_provider, session=db_session)
    result = await service.sync_catalog()

    assert result.packages_synced == 0
