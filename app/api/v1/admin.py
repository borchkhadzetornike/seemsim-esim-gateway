"""Admin/ops endpoints for internal tooling.

All endpoints require internal service auth with appropriate scopes.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ProviderDep, SessionDep
from app.core.auth import RequireAdminOps, RequireBalanceRead, RequireReconciliationRun
from app.models.webhook_event import ProviderWebhookEvent
from app.schemas.common import ApiResponse
from app.tasks.reconciliation import reconcile_pending_orders

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/balance",
    response_model=ApiResponse[dict[str, Any]],
    summary="Query provider account balance",
)
async def get_balance(
    provider: ProviderDep,
    _caller: RequireBalanceRead,
) -> ApiResponse[dict[str, Any]]:
    balance = await provider.get_balance()
    return ApiResponse(data=balance)


@router.post(
    "/reconciliation/trigger",
    response_model=ApiResponse[dict[str, int]],
    summary="Manually trigger order reconciliation",
    description="Runs the reconciliation job for stale/incomplete orders.",
)
async def trigger_reconciliation(
    _caller: RequireReconciliationRun,
) -> ApiResponse[dict[str, int]]:
    reconciled = await reconcile_pending_orders()
    return ApiResponse(data={"reconciled_count": reconciled})


@router.get(
    "/webhook-events",
    response_model=ApiResponse[list[dict[str, Any]]],
    summary="List recent webhook events",
)
async def list_webhook_events(
    session: SessionDep,
    _caller: RequireAdminOps,
    limit: int = 50,
) -> ApiResponse[list[dict[str, Any]]]:
    stmt = (
        select(ProviderWebhookEvent)
        .order_by(ProviderWebhookEvent.created_at.desc())
        .limit(min(limit, 200))
    )
    result = await session.execute(stmt)
    events = result.scalars().all()

    items = [
        {
            "id": e.id,
            "event_type": e.event_type,
            "order_no": e.order_no,
            "iccid": e.iccid,
            "processing_status": e.processing_status,
            "processing_error": e.processing_error,
            "received_at": e.received_at.isoformat() if e.received_at else None,
            "processed_at": e.processed_at.isoformat() if e.processed_at else None,
        }
        for e in events
    ]
    return ApiResponse(data=items)
