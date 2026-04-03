from __future__ import annotations

from datetime import datetime

from app.schemas.common import BaseSchema


class PackageOut(BaseSchema):
    id: str
    product_id: str
    package_code: str
    name: str
    type: str
    data_volume_mb: int | None = None
    duration_days: int | None = None
    price: float
    currency: str
    countries: list[str] | None = None
    is_active: bool


class ProductOut(BaseSchema):
    id: str
    name: str
    description: str | None = None
    location_code: str | None = None
    is_active: bool
    packages: list[PackageOut] = []
    created_at: datetime
    updated_at: datetime


class ProductListOut(BaseSchema):
    id: str
    name: str
    location_code: str | None = None
    is_active: bool
    package_count: int = 0


class CatalogSyncResponse(BaseSchema):
    products_synced: int
    packages_synced: int
    provider: str
