"""Provider state → internal state synchronization service.

Maps verified eSIM Access query responses into internal order/eSIM records.
Source of truth: docs.esimaccess.com + SANDBOX_EVIDENCE.md verified live shapes.

Update precedence rules:
  1. Provider query is the richest fulfillment source
  2. Never overwrite non-null internal values with null provider values
  3. Never downgrade terminal statuses (consumed, cancelled, failed)
  4. Record history for every meaningful state transition
  5. Store raw provider payloads for audit
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, ClassVar

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.esim import Esim, EsimStatusHistory
from app.models.order import ProviderOrder
from app.models.order_state_history import OrderStateHistory
from app.providers.base import BaseEsimProvider
from app.repositories.esim import EsimRepository
from app.repositories.order import OrderRepository
from app.repositories.order_state_history import OrderStateHistoryRepository

logger = structlog.get_logger(__name__)


@dataclass
class SyncResult:
    order: ProviderOrder
    esims: list[Esim] = field(default_factory=list)
    state_changed: bool = False


class ProviderStateSyncer:
    """Merges provider query responses into internal state."""

    ESIM_STATUS_MAP: ClassVar[dict[str, str]] = {
        "GOT_RESOURCE": "ready",
        "IN_USE": "active",
        "USED_UP": "consumed",
        "DELETED": "cancelled",
    }

    TERMINAL_STATUSES: ClassVar[frozenset[str]] = frozenset({
        "consumed", "cancelled", "failed",
    })

    def __init__(self, provider: BaseEsimProvider, session: AsyncSession) -> None:
        self._provider = provider
        self._session = session
        self._order_repo = OrderRepository(session)
        self._esim_repo = EsimRepository(session)
        self._history_repo = OrderStateHistoryRepository(session)

    async def sync_order(
        self,
        order: ProviderOrder,
        source: str,
    ) -> SyncResult:
        """Query provider and merge state into internal order + eSIM records."""
        if not order.provider_order_no:
            return SyncResult(order=order)

        try:
            query_obj = await self._provider.query_order_full(order.provider_order_no)
        except Exception as exc:
            logger.warning(
                "provider_query_failed_during_sync",
                order_id=order.id,
                source=source,
                error=str(exc),
            )
            return SyncResult(order=order)

        esim_list: list[dict[str, Any]] = query_obj.get("esimList") or []

        now = _utc_now()
        order.last_provider_sync_at = now
        order.last_provider_payload = query_obj

        if not esim_list:
            return SyncResult(order=order)

        old_status = order.status
        old_provider_status = order.provider_status

        primary = esim_list[0]
        raw_esim_status = str(primary.get("esimStatus") or "")
        new_provider_status = raw_esim_status
        new_internal_status = self.map_status(raw_esim_status)

        if old_status in self.TERMINAL_STATUSES:
            new_internal_status = old_status

        order.status = new_internal_status
        order.provider_status = new_provider_status

        iccid = primary.get("iccid")
        if iccid and not order.iccid:
            order.iccid = str(iccid)

        state_changed = (
            old_status != new_internal_status
            or old_provider_status != new_provider_status
        )

        if state_changed:
            await self._history_repo.create(
                OrderStateHistory(
                    id=str(uuid.uuid4()),
                    order_id=order.id,
                    old_status=old_status,
                    new_status=new_internal_status,
                    old_provider_status=old_provider_status,
                    new_provider_status=new_provider_status,
                    source=source,
                    payload_json=query_obj,
                )
            )

        esims: list[Esim] = []
        for record in esim_list:
            record_iccid = record.get("iccid")
            if not record_iccid:
                continue
            esim = await self._merge_esim_record(order, record, source)
            esims.append(esim)

        logger.info(
            "order_state_synced",
            order_id=order.id,
            source=source,
            state_changed=state_changed,
            old_status=old_status,
            new_status=order.status,
            esim_count=len(esims),
        )

        return SyncResult(order=order, esims=esims, state_changed=state_changed)

    async def _merge_esim_record(
        self,
        order: ProviderOrder,
        record: dict[str, Any],
        source: str,
    ) -> Esim:
        """Create or update an eSIM record from a provider esimList entry."""
        iccid = str(record["iccid"])

        esim = await self._esim_repo.get_by_iccid(iccid)
        is_new = esim is None

        if is_new:
            esim = Esim(
                id=str(uuid.uuid4()),
                iccid=iccid,
                provider_name=self._provider.provider_name,
                order_id=order.id,
                status="allocated",
            )
            self._session.add(esim)
            await self._session.flush()

        old_status = esim.status

        _set_if_present(esim, "provider_esim_tran_no", record.get("esimTranNo"))
        _set_if_present(esim, "imsi", record.get("imsi"))
        _set_if_present(esim, "msisdn", record.get("msisdn"))
        _set_if_present(esim, "activation_code", record.get("ac"))
        _set_if_present(esim, "qr_code_url", record.get("qrCodeUrl"))
        _set_if_present(esim, "short_url", record.get("shortUrl"))
        _set_if_present(esim, "smdp_status", record.get("smdpStatus"))
        _set_if_present(esim, "pin", record.get("pin"))
        _set_if_present(esim, "puk", record.get("puk"))
        _set_if_present(esim, "apn", record.get("apn"))
        _set_if_present(esim, "fup_policy", record.get("fupPolicy"))
        _set_if_present(esim, "duration_unit", record.get("durationUnit"))
        _set_if_present(esim, "esim_status", record.get("esimStatus"))

        # Parse LPA activation code -> smdp_address + matching_id
        ac = record.get("ac") or ""
        if ac.startswith("LPA:"):
            parts = ac.split("$")
            if len(parts) >= 3:
                _set_if_present(esim, "smdp_address", parts[1])
                _set_if_present(esim, "matching_id", parts[2])

        # Numeric fields (always update when provider sends a value)
        _set_int_if_present(esim, "total_volume", record.get("totalVolume"))
        _set_int_if_present(esim, "total_duration", record.get("totalDuration"))
        _set_int_if_present(esim, "order_usage", record.get("orderUsage"))
        _set_int_if_present(esim, "support_topup_type", record.get("supportTopUpType"))

        # Provider datetime fields
        esim.activate_time = (
            _parse_provider_dt(record.get("activateTime")) or esim.activate_time
        )
        esim.installation_time = (
            _parse_provider_dt(record.get("installationTime")) or esim.installation_time
        )
        esim.expired_time = (
            _parse_provider_dt(record.get("expiredTime")) or esim.expired_time
        )

        # Map provider esimStatus -> internal status
        raw_esim_status = str(record.get("esimStatus") or "")
        if raw_esim_status:
            new_status = self.map_status(raw_esim_status)
            if old_status not in self.TERMINAL_STATUSES:
                esim.status = new_status

        # Raw payload for audit
        esim.raw_provider_payload = record
        esim.raw_provider_data = record

        if old_status != esim.status:
            await self._esim_repo.add_status_history(
                EsimStatusHistory(
                    id=str(uuid.uuid4()),
                    esim_id=esim.id,
                    iccid=esim.iccid,
                    previous_status=old_status,
                    new_status=esim.status,
                    source=source,
                    recorded_at=_utc_now(),
                )
            )

        return esim

    @classmethod
    def map_status(cls, raw: str) -> str:
        """Map raw provider esimStatus to internal status."""
        return cls.ESIM_STATUS_MAP.get(raw, "unknown_provider_state")


# ---------------------------------------------------------------------------
# Helpers — never overwrite good values with null/empty
# ---------------------------------------------------------------------------


def _set_if_present(obj: object, attr: str, value: Any) -> None:
    """Set a string field only if the new value is non-null and non-empty."""
    if value is not None and str(value).strip():
        setattr(obj, attr, str(value))


def _set_int_if_present(obj: object, attr: str, value: Any) -> None:
    """Set an integer field only if the new value is a valid number."""
    if value is not None:
        try:
            setattr(obj, attr, int(value))
        except (ValueError, TypeError):
            pass


def _parse_provider_dt(value: str | None) -> datetime | None:
    """Parse eSIM Access datetime format: ``2026-09-27T19:29:36+0000``."""
    if not value:
        return None
    try:
        cleaned = value.replace("+0000", "+00:00").replace("-0000", "+00:00")
        return datetime.fromisoformat(cleaned)
    except (ValueError, AttributeError):
        return None


def _utc_now() -> datetime:
    return datetime.now(UTC)
