"""eSIM Access provider adapter.

Implements the BaseEsimProvider interface by mapping eSIM Access API
operations to normalized internal data structures.

Verified endpoints (live-tested against api.esimaccess.com 2026-03-31):
  /api/v1/open/package/list    — package catalog
  /api/v1/open/esim/order      — create order
  /api/v1/open/esim/query      — query orders/eSIMs (paginated)
  /api/v1/open/esim/topup      — top up existing eSIM
  /api/v1/open/esim/cancel     — cancel unused eSIM
  /api/v1/open/balance/query   — merchant balance

Response envelope: {success, errorCode, errorMsg, obj}

Source of truth: docs.esimaccess.com + CONTRACT_REVALIDATION.md
"""

from __future__ import annotations

from typing import Any

import structlog

from app.core.errors import ProviderCapabilityUnavailableError
from app.providers.base import (
    BaseEsimProvider,
    ProviderCancelResult,
    ProviderEsimProfile,
    ProviderEsimStatus,
    ProviderOrderResult,
    ProviderPackageData,
    ProviderTopupResult,
)
from app.providers.esim_access.client import EsimAccessClient

logger = structlog.get_logger(__name__)

ENDPOINT_PACKAGE_LIST = "/api/v1/open/package/list"
ENDPOINT_ORDER = "/api/v1/open/esim/order"
ENDPOINT_QUERY = "/api/v1/open/esim/query"
ENDPOINT_TOPUP = "/api/v1/open/esim/topup"
ENDPOINT_CANCEL = "/api/v1/open/esim/cancel"
ENDPOINT_BALANCE = "/api/v1/open/balance/query"

PRICE_DIVISOR = 10_000


class EsimAccessProvider(BaseEsimProvider):
    provider_name = "esim_access"

    def __init__(self, client: EsimAccessClient) -> None:
        self._client = client

    # ------------------------------------------------------------------
    # Package list
    # ------------------------------------------------------------------

    async def sync_products(self) -> list[ProviderPackageData]:
        data = await self._client.request(ENDPOINT_PACKAGE_LIST, {})
        obj = data.get("obj") or {}
        packages_raw = obj.get("packageList", [])

        if not isinstance(packages_raw, list):
            packages_raw = []

        result: list[ProviderPackageData] = []
        for pkg in packages_raw:
            result.append(self._map_package(pkg))

        logger.info("sync_products_complete", count=len(result))
        return result

    # ------------------------------------------------------------------
    # Order creation
    # ------------------------------------------------------------------

    async def create_order(
        self, package_code: str, quantity: int, transaction_id: str
    ) -> ProviderOrderResult:
        payload: dict[str, Any] = {
            "transactionId": transaction_id,
            "packageInfoList": [
                {"packageCode": package_code, "count": quantity},
            ],
        }

        data = await self._client.request(ENDPOINT_ORDER, payload)
        obj = data.get("obj") or {}

        return ProviderOrderResult(
            order_no=obj.get("orderNo", ""),
            transaction_id=transaction_id,
            status="pending",
            iccid=None,
            raw=obj,
        )

    # ------------------------------------------------------------------
    # Order/eSIM query (paginated)
    # ------------------------------------------------------------------

    async def get_order_status(self, order_no: str) -> ProviderOrderResult:
        payload: dict[str, Any] = {
            "orderNo": order_no,
            "pager": {"pageNum": 1, "pageSize": 5},
        }
        data = await self._client.request(ENDPOINT_QUERY, payload)
        obj = data.get("obj") or {}
        esim_list = obj.get("esimList", [])

        if not esim_list:
            return ProviderOrderResult(
                order_no=order_no,
                transaction_id="",
                status="unknown",
                raw=obj,
            )

        record = esim_list[0]
        return self._map_esim_to_order_result(record, order_no)

    # ------------------------------------------------------------------
    # eSIM profile lookup
    # ------------------------------------------------------------------

    async def get_esim(self, iccid: str) -> ProviderEsimProfile:
        payload: dict[str, Any] = {
            "iccid": iccid,
            "pager": {"pageNum": 1, "pageSize": 5},
        }
        data = await self._client.request(ENDPOINT_QUERY, payload)
        obj = data.get("obj") or {}
        esim_list = obj.get("esimList", [])

        if not esim_list:
            return ProviderEsimProfile(iccid=iccid, status="unknown", raw={})

        record = esim_list[0]
        return ProviderEsimProfile(
            iccid=record.get("iccid", iccid),
            smdp_address=record.get("smdpAddress"),
            matching_id=record.get("matchingId"),
            activation_code=record.get("ac"),
            status=self._effective_status(record),
            msisdn=record.get("msisdn"),
            raw=record,
        )

    # ------------------------------------------------------------------
    # eSIM status (usage is inferred from query, not a separate endpoint)
    # ------------------------------------------------------------------

    async def get_esim_status(self, iccid: str) -> ProviderEsimStatus:
        payload: dict[str, Any] = {
            "iccid": iccid,
            "pager": {"pageNum": 1, "pageSize": 5},
        }
        data = await self._client.request(ENDPOINT_QUERY, payload)
        obj = data.get("obj") or {}
        esim_list = obj.get("esimList", [])

        if not esim_list:
            return ProviderEsimStatus(iccid=iccid, status="unknown", raw={})

        record = esim_list[0]
        remaining_mb: float | None = None
        days_remaining: int | None = None

        total_volume = record.get("totalVolume")
        order_usage = record.get("orderUsage")
        if total_volume is not None and order_usage is not None:
            try:
                remaining_bytes = int(total_volume) - int(order_usage)
                remaining_mb = remaining_bytes / (1024 * 1024)
            except (ValueError, TypeError):
                pass

        expired_time = record.get("expiredTime")

        return ProviderEsimStatus(
            iccid=iccid,
            status=self._effective_status(record),
            data_usage_remaining_mb=remaining_mb,
            days_remaining=days_remaining,
            raw=record,
        )

    # ------------------------------------------------------------------
    # Top-up package discovery
    # ------------------------------------------------------------------

    async def get_topup_packages(self, iccid: str) -> list[ProviderPackageData]:
        """Query the provider for top-up eligible packages for a specific eSIM."""
        payload: dict[str, Any] = {
            "type": "TOPUP",
            "iccid": iccid,
        }
        data = await self._client.request(ENDPOINT_PACKAGE_LIST, payload)
        obj = data.get("obj") or {}
        packages_raw = obj.get("packageList", [])

        if not isinstance(packages_raw, list):
            packages_raw = []

        result: list[ProviderPackageData] = []
        for pkg in packages_raw:
            result.append(self._map_package(pkg))

        logger.info("topup_packages_fetched", iccid=iccid, count=len(result))
        return result

    # ------------------------------------------------------------------
    # Top-up (documented and verified)
    # ------------------------------------------------------------------

    async def topup_esim(
        self, iccid: str, package_code: str, transaction_id: str
    ) -> ProviderTopupResult:
        payload: dict[str, Any] = {
            "iccid": iccid,
            "packageCode": package_code,
            "transactionId": transaction_id,
        }
        data = await self._client.request(ENDPOINT_TOPUP, payload)
        obj = data.get("obj") or {}

        return ProviderTopupResult(
            order_no=obj.get("orderNo", ""),
            iccid=obj.get("iccid", iccid),
            package_code=package_code,
            status="completed" if data.get("success") else "failed",
            raw=obj,
        )

    # ------------------------------------------------------------------
    # Cancel (documented and verified)
    # ------------------------------------------------------------------

    async def cancel_order(self, order_no: str) -> ProviderCancelResult:
        """Cancel an unused eSIM. The eSIM Access cancel endpoint uses iccid,
        so order_no is treated as an iccid for this provider."""
        payload: dict[str, Any] = {"iccid": order_no}
        data = await self._client.request(ENDPOINT_CANCEL, payload)

        return ProviderCancelResult(
            order_no=order_no,
            status="cancelled" if data.get("success") else "failed",
            message=str(data.get("errorMsg") or ""),
            raw=data.get("obj") or {},
        )

    # ------------------------------------------------------------------
    # Suspend — NOT documented, remains disabled
    # ------------------------------------------------------------------

    async def suspend_esim(self, iccid: str) -> ProviderCancelResult:
        raise ProviderCapabilityUnavailableError(
            detail="eSIM suspension is not documented in the eSIM Access API."
        )

    # ------------------------------------------------------------------
    # Balance
    # ------------------------------------------------------------------

    async def get_balance(self) -> dict[str, Any]:
        data = await self._client.request(ENDPOINT_BALANCE, {})
        obj = data.get("obj") or {}
        raw_balance = obj.get("balance", 0)
        return {
            "balance_raw": raw_balance,
            "balance_usd": raw_balance / PRICE_DIVISOR if isinstance(raw_balance, (int, float)) else 0.0,
            "raw": obj,
        }

    # ------------------------------------------------------------------
    # Webhook normalization
    # ------------------------------------------------------------------

    async def handle_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Normalize eSIM Access webhook payload.

        Documented webhook types: ORDER_STATUS, ESIM_STATUS, DATA_USAGE,
        VALIDITY_USAGE, SMDP_EVENT.

        Payload structure: top-level has notifyType, notifyId,
        eventGenerateTime. Actual data lives in nested "content" object.
        """
        notify_type = payload.get("notifyType", "ORDER_STATUS")
        content = payload.get("content") or {}

        order_no = content.get("orderNo") or payload.get("orderNo")
        iccid = content.get("iccid") or content.get("ICCID") or payload.get("ICCID") or payload.get("iccid")
        transaction_id = content.get("transactionId") or payload.get("transactionId")

        result_value = content.get("result") or payload.get("result", "")
        status = "unknown"
        if result_value == "COMPLETED":
            status = "completed"
        elif result_value == "FAILED":
            status = "failed"

        esim_status = content.get("esimStatus") or content.get("orderStatus")
        smdp_status = content.get("smdpStatus")

        if notify_type == "ESIM_STATUS" and esim_status:
            status = str(esim_status).lower()
        elif notify_type == "ORDER_STATUS" and esim_status:
            status = str(esim_status).lower()
        elif notify_type == "SMDP_EVENT" and smdp_status:
            status = f"smdp_{smdp_status.lower()}"

        return {
            "event_type": notify_type,
            "order_no": order_no,
            "iccid": iccid,
            "transaction_id": transaction_id,
            "esim_status": str(esim_status).lower() if esim_status else None,
            "smdp_status": smdp_status,
            "lpa": content.get("lpa") or payload.get("lpa"),
            "package_code": content.get("packageCode") or payload.get("packageCode"),
            "package_name": content.get("packageName") or payload.get("packageName"),
            "price": content.get("price") or payload.get("price"),
            "currency": content.get("currency") or payload.get("currency"),
            "status": status,
            # DATA_USAGE fields
            "total_volume": content.get("totalVolume"),
            "order_usage": content.get("orderUsage"),
            "remain": content.get("remain"),
            "remain_threshold": content.get("remainThreshold"),
            # VALIDITY_USAGE fields
            "duration_unit": content.get("durationUnit"),
            "expired_time": content.get("expiredTime"),
            "total_duration": content.get("totalDuration"),
            "raw": payload,
        }

    # ------------------------------------------------------------------
    # Full query for state sync
    # ------------------------------------------------------------------

    async def query_order_full(self, order_no: str) -> dict[str, Any]:
        """Return the full provider query response obj including all esimList entries."""
        payload: dict[str, Any] = {
            "orderNo": order_no,
            "pager": {"pageNum": 1, "pageSize": 500},
        }
        data = await self._client.request(ENDPOINT_QUERY, payload)
        return data.get("obj") or {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _effective_status(record: dict[str, Any]) -> str:
        """Derive a single effective status from esimStatus + smdpStatus.

        The provider keeps esimStatus as GOT_RESOURCE even after the profile
        is downloaded/installed. The real lifecycle state comes from combining
        both fields per the eSIM Access webhook documentation.

        smdpStatus semantics (SM-DP+ server states):
          RELEASED     – profile available for download, customer hasn't touched it
          DOWNLOAD     – device is downloading the profile
          INSTALLATION – device is installing the profile
          ENABLED      – profile is installed and active on device
          DISABLED     – profile suspended
          DELETED      – profile removed
        """
        esim_status = str(record.get("esimStatus", "unknown")).lower()
        smdp_status = str(record.get("smdpStatus", "")).upper()

        if smdp_status == "DELETED":
            return "deleted"
        if smdp_status == "DISABLED":
            return "suspended"

        if esim_status == "got_resource":
            if smdp_status == "RELEASED":
                return "ready"
            if smdp_status in ("DOWNLOAD", "INSTALLATION"):
                return "installing"
            if smdp_status == "ENABLED":
                return "installed"

        return esim_status

    @staticmethod
    def _map_package(pkg: dict[str, Any]) -> ProviderPackageData:
        price_raw = pkg.get("price", 0)
        price_usd = 0.0
        if isinstance(price_raw, (int, float)):
            price_usd = price_raw / PRICE_DIVISOR

        volume_bytes = pkg.get("volume", 0)
        data_volume_mb: int | None = None
        if isinstance(volume_bytes, (int, float)) and volume_bytes > 0:
            data_volume_mb = int(volume_bytes / (1024 * 1024))

        duration_days = pkg.get("duration")
        if duration_days is not None:
            try:
                duration_days = int(duration_days)
            except (ValueError, TypeError):
                duration_days = None

        location = pkg.get("location", "")
        countries: list[str] = [c.strip() for c in location.split(",") if c.strip()] if location else []

        topup_raw = pkg.get("supportTopUpType")
        support_topup_type: int | None = None
        if isinstance(topup_raw, int):
            support_topup_type = topup_raw
        elif isinstance(topup_raw, str) and topup_raw.isdigit():
            support_topup_type = int(topup_raw)

        return ProviderPackageData(
            package_code=pkg.get("packageCode", ""),
            name=pkg.get("name", ""),
            type=str(pkg.get("activeType", "")),
            data_volume_mb=data_volume_mb,
            duration_days=duration_days,
            price=price_usd,
            currency=pkg.get("currencyCode", "USD"),
            countries=countries,
            location_code=pkg.get("locationCode"),
            support_topup_type=support_topup_type,
            raw=pkg,
        )

    @classmethod
    def _map_esim_to_order_result(cls, record: dict[str, Any], fallback_order_no: str) -> ProviderOrderResult:
        effective = cls._effective_status(record)
        status_map = {
            "got_resource": "completed",
            "ready": "completed",
            "installing": "completed",
            "installed": "completed",
            "in_use": "active",
            "used_up": "expired",
            "used_expired": "expired",
            "unused_expired": "expired",
            "deleted": "cancelled",
            "cancel": "cancelled",
            "revoked": "cancelled",
            "suspended": "suspended",
        }
        status = status_map.get(effective, effective)

        return ProviderOrderResult(
            order_no=record.get("orderNo", fallback_order_no),
            transaction_id=record.get("transactionId", ""),
            status=status,
            iccid=record.get("iccid"),
            raw=record,
        )
