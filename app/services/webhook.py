from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils import utc_now
from app.models.esim import EsimStatusHistory
from app.models.webhook_event import ProviderWebhookEvent
from app.providers.base import BaseEsimProvider
from app.repositories.esim import EsimRepository
from app.repositories.order import OrderRepository
from app.repositories.webhook import WebhookRepository
from app.services.state_sync import ProviderStateSyncer

logger = structlog.get_logger(__name__)


def _payload_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


class WebhookService:
    """Processes incoming provider webhooks.

    Deduplication strategy: hash the raw payload to detect exact
    duplicate deliveries.  Different status updates for the same order
    are *not* considered duplicates and are processed normally.

    After applying any inline updates, every webhook with an order_no
    triggers a full provider query refresh so the internal state is
    always reconciled with the provider source of truth.
    """

    def __init__(self, provider: BaseEsimProvider, session: AsyncSession) -> None:
        self._provider = provider
        self._webhook_repo = WebhookRepository(session)
        self._order_repo = OrderRepository(session)
        self._esim_repo = EsimRepository(session)
        self._state_syncer = ProviderStateSyncer(provider, session)

    async def process_webhook(self, raw_payload: dict[str, Any]) -> str:
        normalized = await self._provider.handle_webhook(raw_payload)
        p_hash = _payload_hash(raw_payload)

        event_id = str(uuid.uuid4())
        event = ProviderWebhookEvent(
            id=event_id,
            provider_name=self._provider.provider_name,
            event_type=normalized.get("event_type", "UNKNOWN"),
            order_no=normalized.get("order_no"),
            iccid=normalized.get("iccid"),
            transaction_id=normalized.get("transaction_id"),
            payload_hash=p_hash,
            payload=raw_payload,
            processed=False,
            processing_status="pending",
        )
        await self._webhook_repo.create(event)

        existing = await self._webhook_repo.find_duplicate_by_hash(p_hash)
        if existing:
            logger.info(
                "webhook_exact_duplicate_detected",
                event_id=event_id,
                existing_event_id=existing.id,
                payload_hash=p_hash,
            )
            await self._webhook_repo.mark_processed(event_id)
            return event_id

        try:
            await self._handle_event(normalized)
            await self._trigger_provider_refresh(normalized)
            await self._webhook_repo.mark_processed(event_id)
            logger.info(
                "webhook_processed",
                event_id=event_id,
                event_type=normalized.get("event_type"),
                order_no=normalized.get("order_no"),
            )
        except Exception as exc:
            logger.error("webhook_processing_failed", event_id=event_id, error=str(exc))
            await self._webhook_repo.mark_processed(event_id, error=str(exc))

        return event_id

    async def _handle_event(self, normalized: dict[str, Any]) -> None:
        event_type = normalized.get("event_type", "")

        if event_type == "ORDER_STATUS":
            await self._handle_order_status(normalized)
        elif event_type == "ESIM_STATUS":
            await self._handle_esim_status(normalized)
        elif event_type == "SMDP_EVENT":
            await self._handle_smdp_event(normalized)
        elif event_type == "DATA_USAGE":
            await self._handle_data_usage(normalized)
        elif event_type == "VALIDITY_USAGE":
            await self._handle_validity_usage(normalized)
        elif event_type == "CHECK_HEALTH":
            logger.info("webhook_health_check_received")
        else:
            logger.warning("webhook_unknown_event_type", event_type=event_type)

    async def _trigger_provider_refresh(self, normalized: dict[str, Any]) -> None:
        """After webhook processing, query provider for full state update."""
        order_no = normalized.get("order_no")
        if not order_no:
            return

        order = await self._order_repo.get_by_provider_order_no(order_no)
        if not order:
            logger.warning("webhook_refresh_order_not_found", order_no=order_no)
            return

        try:
            await self._state_syncer.sync_order(order, "webhook")
            logger.info("webhook_triggered_refresh_complete", order_no=order_no)
        except Exception as exc:
            logger.warning(
                "webhook_triggered_refresh_failed",
                order_no=order_no,
                error=str(exc),
            )

    async def _handle_order_status(self, data: dict[str, Any]) -> None:
        order_no = data.get("order_no")
        if not order_no:
            return

        order = await self._order_repo.get_by_provider_order_no(order_no)
        if not order:
            logger.warning("webhook_order_not_found", order_no=order_no)
            return

        new_status = data.get("status", "completed")
        old_status = order.status

        terminal = frozenset({"consumed", "cancelled", "failed"})
        if old_status not in terminal:
            order.status = new_status

        iccid = data.get("iccid")
        if iccid and not order.iccid:
            order.iccid = iccid

        logger.info(
            "webhook_order_status_updated",
            order_id=order.id,
            order_no=order_no,
            old_status=old_status,
            new_status=new_status,
            applied=old_status not in terminal,
        )

    async def _handle_esim_status(self, data: dict[str, Any]) -> None:
        iccid = data.get("iccid")
        if not iccid:
            return

        esim = await self._esim_repo.get_by_iccid(iccid)
        if not esim:
            logger.warning("webhook_esim_not_found", iccid=iccid)
            return

        new_esim_status = data.get("esim_status")
        if new_esim_status and new_esim_status.upper() != (esim.esim_status or ""):
            esim.esim_status = new_esim_status.upper()

        new_smdp = data.get("smdp_status")
        if new_smdp and new_smdp != esim.smdp_status:
            esim.smdp_status = new_smdp

        new_status = data.get("status", esim.status)
        if new_status != esim.status:
            previous = esim.status
            esim.status = new_status

            history = EsimStatusHistory(
                id=str(uuid.uuid4()),
                esim_id=esim.id,
                iccid=iccid,
                previous_status=previous,
                new_status=new_status,
                source="webhook",
                recorded_at=utc_now(),
            )
            await self._esim_repo.add_status_history(history)

            logger.info(
                "webhook_esim_status_updated",
                iccid=iccid,
                from_status=previous,
                to_status=new_status,
                esim_status=new_esim_status,
                smdp_status=new_smdp,
            )

    async def _handle_smdp_event(self, data: dict[str, Any]) -> None:
        iccid = data.get("iccid")
        if not iccid:
            return

        esim = await self._esim_repo.get_by_iccid(iccid)
        if not esim:
            logger.warning("webhook_smdp_esim_not_found", iccid=iccid)
            return

        new_smdp = data.get("smdp_status")
        if new_smdp and new_smdp != esim.smdp_status:
            previous_smdp = esim.smdp_status
            esim.smdp_status = new_smdp

            history = EsimStatusHistory(
                id=str(uuid.uuid4()),
                esim_id=esim.id,
                iccid=iccid,
                previous_status=previous_smdp,
                new_status=f"smdp:{new_smdp}",
                source="webhook_smdp",
                recorded_at=utc_now(),
            )
            await self._esim_repo.add_status_history(history)

            logger.info(
                "webhook_smdp_status_updated",
                iccid=iccid,
                from_smdp=previous_smdp,
                to_smdp=new_smdp,
            )

    async def _handle_data_usage(self, data: dict[str, Any]) -> None:
        iccid = data.get("iccid")
        if not iccid:
            return

        esim = await self._esim_repo.get_by_iccid(iccid)
        if not esim:
            logger.warning("webhook_data_usage_esim_not_found", iccid=iccid)
            return

        total_volume = data.get("total_volume")
        order_usage = data.get("order_usage")
        threshold = data.get("remain_threshold")

        if total_volume is not None:
            esim.total_volume = int(total_volume)
        if order_usage is not None:
            esim.order_usage = int(order_usage)

        logger.info(
            "webhook_data_usage_updated",
            iccid=iccid,
            total_volume=total_volume,
            order_usage=order_usage,
            threshold=threshold,
        )

    async def _handle_validity_usage(self, data: dict[str, Any]) -> None:
        iccid = data.get("iccid")
        if not iccid:
            return

        esim = await self._esim_repo.get_by_iccid(iccid)
        if not esim:
            logger.warning("webhook_validity_esim_not_found", iccid=iccid)
            return

        expired_time = data.get("expired_time")
        if expired_time:
            from datetime import datetime
            try:
                esim.expired_time = datetime.fromisoformat(expired_time.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                logger.warning("webhook_validity_bad_timestamp", expired_time=expired_time)

        logger.info(
            "webhook_validity_usage",
            iccid=iccid,
            expired_time=expired_time,
            remain=data.get("remain"),
        )
