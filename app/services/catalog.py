from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import ProviderPackage, ProviderProduct
from app.providers.base import BaseEsimProvider
from app.repositories.product import ProductRepository
from app.schemas.product import CatalogSyncResponse

logger = structlog.get_logger(__name__)


class CatalogService:
    def __init__(self, provider: BaseEsimProvider, session: AsyncSession) -> None:
        self._provider = provider
        self._repo = ProductRepository(session)
        self._session = session

    async def sync_catalog(self) -> CatalogSyncResponse:
        logger.info("catalog_sync_start", provider=self._provider.provider_name)

        packages_data = await self._provider.sync_products()

        products_by_location: dict[str, ProviderProduct] = {}
        active_codes: set[str] = set()
        packages_synced = 0

        for pkg_data in packages_data:
            loc = pkg_data.location_code or "GLOBAL"
            product_id = f"{self._provider.provider_name}_{loc}"

            if loc not in products_by_location:
                product = ProviderProduct(
                    id=product_id,
                    provider_name=self._provider.provider_name,
                    name=f"eSIM - {loc}",
                    location_code=pkg_data.location_code,
                    is_active=True,
                )
                await self._repo.upsert_product(product)
                products_by_location[loc] = product

            package_id = f"{self._provider.provider_name}_{pkg_data.package_code}"
            package = ProviderPackage(
                id=package_id,
                product_id=product_id,
                provider_name=self._provider.provider_name,
                package_code=pkg_data.package_code,
                name=pkg_data.name,
                type=pkg_data.type,
                data_volume_mb=pkg_data.data_volume_mb,
                duration_days=pkg_data.duration_days,
                price=pkg_data.price,
                currency=pkg_data.currency,
                countries=pkg_data.countries,
                support_topup_type=pkg_data.support_topup_type,
                is_active=True,
                raw_provider_data=pkg_data.raw,
            )
            await self._repo.upsert_package(package)
            active_codes.add(pkg_data.package_code)
            packages_synced += 1

        deactivated = await self._repo.deactivate_missing_packages(
            active_codes, self._provider.provider_name
        )

        await self._session.flush()

        logger.info(
            "catalog_sync_complete",
            products=len(products_by_location),
            packages=packages_synced,
            deactivated=deactivated,
        )

        return CatalogSyncResponse(
            products_synced=len(products_by_location),
            packages_synced=packages_synced,
            provider=self._provider.provider_name,
        )

    async def get_products(self, active_only: bool = True) -> list[ProviderProduct]:
        return await self._repo.get_all_products(active_only=active_only)

    async def get_product(self, product_id: str) -> ProviderProduct | None:
        return await self._repo.get_product_by_id(product_id)
