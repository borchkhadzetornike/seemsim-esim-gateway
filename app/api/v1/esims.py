from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter

from app.api.deps import EsimServiceDep, ProviderDep
from app.core.auth import RequireEsimsRead
from app.schemas.common import ApiResponse
from app.schemas.esim import EsimOut, EsimStatusHistoryOut, EsimStatusOut, TopupPackageOut

router = APIRouter(prefix="/esims", tags=["eSIMs"])


@router.get(
    "/{esim_id}",
    response_model=ApiResponse[EsimOut],
    summary="Get eSIM details",
)
async def get_esim(esim_id: str, service: EsimServiceDep, _caller: RequireEsimsRead) -> ApiResponse[EsimOut]:
    esim = await service.get_esim(esim_id)
    return ApiResponse(data=EsimOut.model_validate(esim))


@router.get(
    "/{esim_id}/status",
    response_model=ApiResponse[EsimStatusOut],
    summary="Get live eSIM status from provider",
    description="Fetches the current status and data usage from the provider in real time.",
)
async def get_esim_status(esim_id: str, service: EsimServiceDep, _caller: RequireEsimsRead) -> ApiResponse[EsimStatusOut]:
    status = await service.get_esim_status(esim_id)
    return ApiResponse(
        data=EsimStatusOut(
            iccid=status.iccid,
            status=status.status,
            data_usage_remaining_mb=status.data_usage_remaining_mb,
            days_remaining=status.days_remaining,
            last_updated=datetime.now(UTC),
        )
    )


@router.get(
    "/{esim_id}/topup-packages",
    response_model=ApiResponse[list[TopupPackageOut]],
    summary="Get available top-up packages for an eSIM",
    description="Queries the provider for TOPUP-eligible packages using the eSIM's ICCID.",
)
async def get_topup_packages(
    esim_id: str, service: EsimServiceDep, provider: ProviderDep, _caller: RequireEsimsRead,
) -> ApiResponse[list[TopupPackageOut]]:
    esim = await service.get_esim(esim_id)
    if not esim.iccid:
        return ApiResponse(data=[])

    packages = await provider.get_topup_packages(esim.iccid)
    items = [
        TopupPackageOut(
            package_code=p.package_code,
            name=p.name,
            data_volume_mb=p.data_volume_mb,
            duration_days=p.duration_days,
            price=p.price,
            currency=p.currency,
            countries=p.countries,
        )
        for p in packages
    ]
    return ApiResponse(data=items)


@router.get(
    "/{esim_id}/history",
    response_model=ApiResponse[list[EsimStatusHistoryOut]],
    summary="Get eSIM status change history",
)
async def get_esim_history(
    esim_id: str, service: EsimServiceDep, _caller: RequireEsimsRead,
) -> ApiResponse[list[EsimStatusHistoryOut]]:
    history = await service.get_status_history(esim_id)
    items = [EsimStatusHistoryOut.model_validate(h) for h in history]
    return ApiResponse(data=items)
