"""Unit tests for eSIM Access adapter response normalization.

All test data shapes match the verified eSIM Access contract from
docs.esimaccess.com and live API probes on 2026-03-31.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.errors import ProviderCapabilityUnavailableError
from app.providers.esim_access.adapter import (
    ENDPOINT_BALANCE,
    ENDPOINT_CANCEL,
    ENDPOINT_ORDER,
    ENDPOINT_PACKAGE_LIST,
    ENDPOINT_QUERY,
    ENDPOINT_TOPUP,
    EsimAccessProvider,
)


@pytest.fixture
def mock_client() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def adapter(mock_client: AsyncMock) -> EsimAccessProvider:
    return EsimAccessProvider(client=mock_client)


# ------------------------------------------------------------------
# Package list
# ------------------------------------------------------------------


class TestSyncProducts:
    @pytest.mark.asyncio
    async def test_calls_correct_endpoint(
        self, adapter: EsimAccessProvider, mock_client: AsyncMock
    ) -> None:
        mock_client.request.return_value = {
            "success": True, "obj": {"packageList": []}
        }
        await adapter.sync_products()
        mock_client.request.assert_called_once_with(ENDPOINT_PACKAGE_LIST, {})

    @pytest.mark.asyncio
    async def test_parses_obj_package_list(
        self, adapter: EsimAccessProvider, mock_client: AsyncMock
    ) -> None:
        """Packages are under obj.packageList[], not a flat data array."""
        mock_client.request.return_value = {
            "success": True,
            "obj": {
                "packageList": [
                    {
                        "packageCode": "CKH511",
                        "name": "Georgia 1GB 7Days",
                        "price": 15000,
                        "currencyCode": "USD",
                        "volume": 1073741824,
                        "duration": 7,
                        "durationUnit": "DAY",
                        "location": "GE",
                        "locationCode": "GE",
                        "description": "Georgia 1GB 7Days",
                        "activeType": 2,
                    }
                ]
            },
        }

        result = await adapter.sync_products()
        assert len(result) == 1
        pkg = result[0]
        assert pkg.package_code == "CKH511"
        assert pkg.name == "Georgia 1GB 7Days"
        assert pkg.price == 1.5
        assert pkg.currency == "USD"
        assert pkg.data_volume_mb == 1024
        assert pkg.duration_days == 7
        assert "GE" in pkg.countries
        assert pkg.location_code == "GE"

    @pytest.mark.asyncio
    async def test_price_conversion_from_10000ths(
        self, adapter: EsimAccessProvider, mock_client: AsyncMock
    ) -> None:
        mock_client.request.return_value = {
            "success": True,
            "obj": {
                "packageList": [
                    {"packageCode": "X", "name": "Test", "price": 70000, "volume": 0, "duration": 1}
                ]
            },
        }
        result = await adapter.sync_products()
        assert result[0].price == 7.0

    @pytest.mark.asyncio
    async def test_volume_conversion_from_bytes(
        self, adapter: EsimAccessProvider, mock_client: AsyncMock
    ) -> None:
        mock_client.request.return_value = {
            "success": True,
            "obj": {
                "packageList": [
                    {"packageCode": "X", "name": "Test", "price": 0, "volume": 3221225472, "duration": 30}
                ]
            },
        }
        result = await adapter.sync_products()
        assert result[0].data_volume_mb == 3072

    @pytest.mark.asyncio
    async def test_handles_empty_package_list(
        self, adapter: EsimAccessProvider, mock_client: AsyncMock
    ) -> None:
        mock_client.request.return_value = {"success": True, "obj": {"packageList": []}}
        result = await adapter.sync_products()
        assert result == []


# ------------------------------------------------------------------
# Order creation
# ------------------------------------------------------------------


class TestCreateOrder:
    @pytest.mark.asyncio
    async def test_calls_correct_endpoint(
        self, adapter: EsimAccessProvider, mock_client: AsyncMock
    ) -> None:
        mock_client.request.return_value = {
            "success": True, "obj": {"orderNo": "ORD1"},
        }
        await adapter.create_order("PKG_1", 1, "txn-123")
        call_args = mock_client.request.call_args
        assert call_args[0][0] == ENDPOINT_ORDER

    @pytest.mark.asyncio
    async def test_sends_transaction_id_and_package_info_list(
        self, adapter: EsimAccessProvider, mock_client: AsyncMock
    ) -> None:
        mock_client.request.return_value = {
            "success": True, "obj": {"orderNo": "ORD1"},
        }
        await adapter.create_order("CKH511", 1, "txn-123")

        payload = mock_client.request.call_args[0][1]
        assert payload["transactionId"] == "txn-123"
        assert payload["packageInfoList"] == [{"packageCode": "CKH511", "count": 1}]

    @pytest.mark.asyncio
    async def test_batch_order_with_quantity(
        self, adapter: EsimAccessProvider, mock_client: AsyncMock
    ) -> None:
        mock_client.request.return_value = {
            "success": True, "obj": {"orderNo": "ORD2"},
        }
        await adapter.create_order("CKH511", 3, "txn-batch")

        payload = mock_client.request.call_args[0][1]
        assert payload["packageInfoList"] == [{"packageCode": "CKH511", "count": 3}]

    @pytest.mark.asyncio
    async def test_order_response_from_obj(
        self, adapter: EsimAccessProvider, mock_client: AsyncMock
    ) -> None:
        mock_client.request.return_value = {
            "success": True,
            "obj": {"orderNo": "B25032516xxxx"},
        }
        result = await adapter.create_order("CKH511", 1, "txn-123")
        assert result.order_no == "B25032516xxxx"
        assert result.status == "pending"
        assert result.iccid is None
        assert result.transaction_id == "txn-123"


# ------------------------------------------------------------------
# Query (paginated)
# ------------------------------------------------------------------


class TestGetOrderStatus:
    @pytest.mark.asyncio
    async def test_calls_query_endpoint(
        self, adapter: EsimAccessProvider, mock_client: AsyncMock
    ) -> None:
        mock_client.request.return_value = {
            "success": True, "obj": {"esimList": [], "pager": {"pageNum": 1, "pageSize": 5, "total": 0}},
        }
        await adapter.get_order_status("ORD1")
        assert mock_client.request.call_args[0][0] == ENDPOINT_QUERY

    @pytest.mark.asyncio
    async def test_sends_pager_and_order_no(
        self, adapter: EsimAccessProvider, mock_client: AsyncMock
    ) -> None:
        mock_client.request.return_value = {
            "success": True, "obj": {"esimList": [], "pager": {"pageNum": 1, "pageSize": 5, "total": 0}},
        }
        await adapter.get_order_status("ORD1")

        payload = mock_client.request.call_args[0][1]
        assert payload["orderNo"] == "ORD1"
        assert payload["pager"]["pageNum"] == 1
        assert payload["pager"]["pageSize"] == 5

    @pytest.mark.asyncio
    async def test_parses_esim_list(
        self, adapter: EsimAccessProvider, mock_client: AsyncMock
    ) -> None:
        mock_client.request.return_value = {
            "success": True,
            "obj": {
                "esimList": [
                    {
                        "orderNo": "ORD1",
                        "iccid": "89012345678901234560",
                        "esimStatus": "GOT_RESOURCE",
                    }
                ],
                "pager": {"pageNum": 1, "pageSize": 5, "total": 1},
            },
        }
        result = await adapter.get_order_status("ORD1")
        assert result.order_no == "ORD1"
        assert result.iccid == "89012345678901234560"
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_empty_esim_list_returns_unknown(
        self, adapter: EsimAccessProvider, mock_client: AsyncMock
    ) -> None:
        mock_client.request.return_value = {
            "success": True,
            "obj": {"esimList": [], "pager": {"pageNum": 1, "pageSize": 5, "total": 0}},
        }
        result = await adapter.get_order_status("ORD-MISSING")
        assert result.status == "unknown"


# ------------------------------------------------------------------
# Top-up (re-enabled)
# ------------------------------------------------------------------


class TestTopUp:
    @pytest.mark.asyncio
    async def test_calls_topup_endpoint(
        self, adapter: EsimAccessProvider, mock_client: AsyncMock
    ) -> None:
        mock_client.request.return_value = {
            "success": True,
            "obj": {"iccid": "ICC1", "totalVolume": 5368709120},
        }
        await adapter.topup_esim("ICC1", "TOPUP_CKH491", "txn-topup")
        assert mock_client.request.call_args[0][0] == ENDPOINT_TOPUP

    @pytest.mark.asyncio
    async def test_sends_correct_payload(
        self, adapter: EsimAccessProvider, mock_client: AsyncMock
    ) -> None:
        mock_client.request.return_value = {"success": True, "obj": {}}
        await adapter.topup_esim("ICC1", "TOPUP_CKH491", "txn-topup")

        payload = mock_client.request.call_args[0][1]
        assert payload["iccid"] == "ICC1"
        assert payload["packageCode"] == "TOPUP_CKH491"
        assert payload["transactionId"] == "txn-topup"

    @pytest.mark.asyncio
    async def test_returns_topup_result(
        self, adapter: EsimAccessProvider, mock_client: AsyncMock
    ) -> None:
        mock_client.request.return_value = {
            "success": True,
            "obj": {"iccid": "ICC1", "totalVolume": 5368709120},
        }
        result = await adapter.topup_esim("ICC1", "TOPUP_CKH491", "txn-topup")
        assert result.iccid == "ICC1"
        assert result.status == "completed"


# ------------------------------------------------------------------
# Cancel (re-enabled)
# ------------------------------------------------------------------


class TestCancel:
    @pytest.mark.asyncio
    async def test_calls_cancel_endpoint(
        self, adapter: EsimAccessProvider, mock_client: AsyncMock
    ) -> None:
        mock_client.request.return_value = {"success": True, "obj": {}}
        await adapter.cancel_order("ICC1")
        assert mock_client.request.call_args[0][0] == ENDPOINT_CANCEL

    @pytest.mark.asyncio
    async def test_sends_iccid(
        self, adapter: EsimAccessProvider, mock_client: AsyncMock
    ) -> None:
        mock_client.request.return_value = {"success": True, "obj": {}}
        await adapter.cancel_order("ICC1")
        payload = mock_client.request.call_args[0][1]
        assert payload["iccid"] == "ICC1"

    @pytest.mark.asyncio
    async def test_returns_cancel_result(
        self, adapter: EsimAccessProvider, mock_client: AsyncMock
    ) -> None:
        mock_client.request.return_value = {"success": True, "obj": {}}
        result = await adapter.cancel_order("ICC1")
        assert result.status == "cancelled"


# ------------------------------------------------------------------
# Balance
# ------------------------------------------------------------------


class TestBalance:
    @pytest.mark.asyncio
    async def test_calls_balance_endpoint(
        self, adapter: EsimAccessProvider, mock_client: AsyncMock
    ) -> None:
        mock_client.request.return_value = {
            "success": True, "obj": {"balance": 500000},
        }
        await adapter.get_balance()
        assert mock_client.request.call_args[0][0] == ENDPOINT_BALANCE

    @pytest.mark.asyncio
    async def test_converts_balance_to_usd(
        self, adapter: EsimAccessProvider, mock_client: AsyncMock
    ) -> None:
        mock_client.request.return_value = {
            "success": True, "obj": {"balance": 500000},
        }
        result = await adapter.get_balance()
        assert result["balance_usd"] == 50.0
        assert result["balance_raw"] == 500000


# ------------------------------------------------------------------
# Suspend — still disabled
# ------------------------------------------------------------------


class TestSuspend:
    @pytest.mark.asyncio
    async def test_suspend_raises_unavailable(self, adapter: EsimAccessProvider) -> None:
        with pytest.raises(ProviderCapabilityUnavailableError):
            await adapter.suspend_esim("ICC1")


# ------------------------------------------------------------------
# Webhook
# ------------------------------------------------------------------


class TestHandleWebhook:
    @pytest.mark.asyncio
    async def test_parses_order_status_webhook(self, adapter: EsimAccessProvider) -> None:
        payload = {
            "notifyType": "ORDER_STATUS",
            "orderNo": "B25032516xxxx",
            "ICCID": "89012345678901234560",
            "transactionId": "txn-123",
        }
        result = await adapter.handle_webhook(payload)
        assert result["event_type"] == "ORDER_STATUS"
        assert result["order_no"] == "B25032516xxxx"
        assert result["iccid"] == "89012345678901234560"
        assert result["transaction_id"] == "txn-123"

    @pytest.mark.asyncio
    async def test_handles_completed_result(self, adapter: EsimAccessProvider) -> None:
        payload = {"orderNo": "ORD1", "result": "COMPLETED", "ICCID": "ICC1"}
        result = await adapter.handle_webhook(payload)
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_handles_failed_result(self, adapter: EsimAccessProvider) -> None:
        payload = {"orderNo": "ORD1", "result": "FAILED"}
        result = await adapter.handle_webhook(payload)
        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_reads_iccid_uppercase(self, adapter: EsimAccessProvider) -> None:
        """The webhook test form uses ICCID (uppercase)."""
        payload = {"orderNo": "ORD1", "ICCID": "ICC_UPPER"}
        result = await adapter.handle_webhook(payload)
        assert result["iccid"] == "ICC_UPPER"

    @pytest.mark.asyncio
    async def test_reads_iccid_lowercase_fallback(self, adapter: EsimAccessProvider) -> None:
        payload = {"orderNo": "ORD1", "iccid": "ICC_LOWER"}
        result = await adapter.handle_webhook(payload)
        assert result["iccid"] == "ICC_LOWER"
