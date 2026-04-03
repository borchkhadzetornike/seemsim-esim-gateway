from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CatalogServiceDep
from app.core.auth import RequireCatalogRead, RequireCatalogSync
from app.core.errors import ResourceNotFoundError
from app.schemas.common import ApiResponse
from app.schemas.product import CatalogSyncResponse, PackageOut, ProductListOut, ProductOut

router = APIRouter(prefix="/catalog", tags=["Catalog"])


@router.post(
    "/sync",
    response_model=ApiResponse[CatalogSyncResponse],
    summary="Sync product catalog from provider",
    description="Fetches all packages from eSIM Access provider and persists them locally.",
)
async def sync_catalog(
    service: CatalogServiceDep,
    _caller: RequireCatalogSync,
) -> ApiResponse[CatalogSyncResponse]:
    result = await service.sync_catalog()
    return ApiResponse(data=result)


@router.get(
    "/products",
    response_model=ApiResponse[list[ProductListOut]],
    summary="List all products",
)
async def list_products(
    service: CatalogServiceDep,
    _caller: RequireCatalogRead,
) -> ApiResponse[list[ProductListOut]]:
    products = await service.get_products()
    items = [
        ProductListOut(
            id=p.id,
            name=p.name,
            location_code=p.location_code,
            is_active=p.is_active,
            package_count=len(p.packages) if p.packages else 0,
        )
        for p in products
    ]
    return ApiResponse(data=items)


@router.get(
    "/packages",
    response_model=ApiResponse[list[PackageOut]],
    summary="List all active packages (flat)",
    description="Returns every active package across all products in a single response.",
)
async def list_all_packages(
    service: CatalogServiceDep,
    _caller: RequireCatalogRead,
) -> ApiResponse[list[PackageOut]]:
    products = await service.get_products()
    packages = [
        PackageOut.model_validate(pkg)
        for product in products
        for pkg in (product.packages or [])
        if pkg.is_active
    ]
    return ApiResponse(data=packages)


@router.get(
    "/products/{product_id}",
    response_model=ApiResponse[ProductOut],
    summary="Get product details with packages",
)
async def get_product(
    product_id: str,
    service: CatalogServiceDep,
    _caller: RequireCatalogRead,
) -> ApiResponse[ProductOut]:
    product = await service.get_product(product_id)
    if not product:
        raise ResourceNotFoundError(detail=f"Product {product_id} not found")
    return ApiResponse(data=ProductOut.model_validate(product))
