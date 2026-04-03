from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from app.api.deps import WebhookServiceDep
from app.schemas.common import ApiResponse
from app.schemas.webhook import WebhookResponse

router = APIRouter(prefix="/provider/webhooks", tags=["Webhooks"])


@router.post(
    "/esim-access",
    response_model=ApiResponse[WebhookResponse],
    summary="eSIM Access webhook ingestion endpoint",
    description=(
        "Receives webhook notifications from eSIM Access. "
        "Supports events: ORDER_STATUS, ESIM_STATUS, DATA_USAGE, VALIDITY_USAGE."
    ),
)
async def esim_access_webhook(
    request: Request,
    service: WebhookServiceDep,
) -> ApiResponse[WebhookResponse]:
    payload: dict[str, Any] = await request.json()

    event_id = await service.process_webhook(payload)

    return ApiResponse(data=WebhookResponse(received=True, event_id=event_id))
