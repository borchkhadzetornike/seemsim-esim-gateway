from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import ProviderPackage, ProviderProduct


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_all_products(self, active_only: bool = True) -> list[ProviderProduct]:
        stmt = select(ProviderProduct)
        if active_only:
            stmt = stmt.where(ProviderProduct.is_active.is_(True))
        stmt = stmt.order_by(ProviderProduct.name)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_product_by_id(self, product_id: str) -> ProviderProduct | None:
        return await self._session.get(ProviderProduct, product_id)

    async def upsert_product(self, product: ProviderProduct) -> ProviderProduct:
        existing = await self._session.get(ProviderProduct, product.id)
        if existing:
            existing.name = product.name
            existing.description = product.description
            existing.location_code = product.location_code
            existing.is_active = product.is_active
            return existing
        self._session.add(product)
        return product

    async def get_package_by_code(self, package_code: str) -> ProviderPackage | None:
        stmt = select(ProviderPackage).where(ProviderPackage.package_code == package_code)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_package(self, package: ProviderPackage) -> ProviderPackage:
        existing = await self.get_package_by_code(package.package_code)
        if existing:
            existing.name = package.name
            existing.type = package.type
            existing.data_volume_mb = package.data_volume_mb
            existing.duration_days = package.duration_days
            existing.price = package.price
            existing.currency = package.currency
            existing.countries = package.countries
            existing.support_topup_type = package.support_topup_type
            existing.is_active = package.is_active
            existing.raw_provider_data = package.raw_provider_data
            return existing
        self._session.add(package)
        return package

    async def deactivate_missing_packages(self, active_codes: set[str], provider_name: str) -> int:
        stmt = select(ProviderPackage).where(
            ProviderPackage.provider_name == provider_name,
            ProviderPackage.is_active.is_(True),
            ProviderPackage.package_code.notin_(active_codes),
        )
        result = await self._session.execute(stmt)
        deactivated = 0
        for pkg in result.scalars().all():
            pkg.is_active = False
            deactivated += 1
        return deactivated
