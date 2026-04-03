"""Contract-style tests ensuring the adapter correctly maps external schemas.

All test data shapes match the live eSIM Access API responses observed on
2026-03-31 against api.esimaccess.com. These tests are the executable
specification for the eSIM Access integration.

Source of truth: docs.esimaccess.com + CONTRACT_REVALIDATION.md
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.errors import ProviderCapabilityUnavailableError
from app.providers.esim_access.adapter import EsimAccessProvider


@pytest.fixture
def adapter() -> EsimAccessProvider:
    return EsimAccessProvider(client=AsyncMock())


# ------------------------------------------------------------------
# Package List Contract
# ------------------------------------------------------------------


class TestPackageListContract:
    """Response envelope: {success: true, obj: {packageList: [...]}}
    Each package has: packageCode, slug, name, price (int/10000=USD),
    currencyCode, volume (bytes), duration, durationUnit, location,
    locationCode, description, activeType, retailPrice, speed, etc.
    """

    @pytest.mark.asyncio
    async def test_real_live_package_shape(self, adapter: EsimAccessProvider) -> None:
        """Verbatim from live API call on 2026-03-31."""
        adapter._client.request.return_value = {
            "success": True,
            "errorCode": "0",
            "errorMsg": None,
            "obj": {
                "packageList": [
                    {
                        "packageCode": "CKH002",
                        "slug": "ES_3_30",
                        "name": "Spain 3GB 30Days",
                        "price": 18000,
                        "currencyCode": "USD",
                        "volume": 3221225472,
                        "smsStatus": 0,
                        "dataType": 1,
                        "unusedValidTime": 180,
                        "duration": 30,
                        "durationUnit": "DAY",
                        "location": "ES",
                        "locationCode": "ES",
                        "description": "Spain 3GB 30Days",
                        "activeType": 2,
                        "favorite": False,
                        "retailPrice": 36000,
                        "speed": "3G/4G/5G",
                        "ipExport": "NL/FR",
                        "supportTopUpType": 2,
                        "fupPolicy": "",
                        "locationNetworkList": [],
                    }
                ]
            },
        }

        packages = await adapter.sync_products()
        assert len(packages) == 1

        pkg = packages[0]
        assert pkg.package_code == "CKH002"
        assert pkg.name == "Spain 3GB 30Days"
        assert pkg.price == 1.8
        assert pkg.currency == "USD"
        assert pkg.data_volume_mb == 3072
        assert pkg.duration_days == 30
        assert "ES" in pkg.countries
        assert pkg.location_code == "ES"

    @pytest.mark.asyncio
    async def test_georgia_package(self, adapter: EsimAccessProvider) -> None:
        adapter._client.request.return_value = {
            "success": True,
            "obj": {
                "packageList": [
                    {
                        "packageCode": "PJCB7UMFE",
                        "slug": "GE_500M_1",
                        "name": "Georgia 500MB/Day",
                        "price": 9000,
                        "currencyCode": "USD",
                        "volume": 524288000,
                        "duration": 1,
                        "durationUnit": "DAY",
                        "location": "GE",
                        "locationCode": "GE",
                        "activeType": 2,
                    }
                ]
            },
        }

        packages = await adapter.sync_products()
        pkg = packages[0]
        assert pkg.package_code == "PJCB7UMFE"
        assert pkg.price == 0.9
        assert pkg.data_volume_mb == 500
        assert "GE" in pkg.countries


# ------------------------------------------------------------------
# Order Contract
# ------------------------------------------------------------------


class TestOrderContract:
    """POST /api/v1/open/esim/order
    Request: {transactionId, packageInfoList: [{packageCode, count}]}
    Response: {success: true, obj: {orderNo: "..."}}
    """

    @pytest.mark.asyncio
    async def test_order_request_shape(self, adapter: EsimAccessProvider) -> None:
        adapter._client.request.return_value = {
            "success": True, "obj": {"orderNo": "B26033120580005"},
        }
        await adapter.create_order("CKH511", 1, "txn-001")

        payload = adapter._client.request.call_args[0][1]
        assert "transactionId" in payload
        assert "packageInfoList" in payload
        assert payload["packageInfoList"][0]["packageCode"] == "CKH511"
        assert payload["packageInfoList"][0]["count"] == 1

    @pytest.mark.asyncio
    async def test_order_response_reads_from_obj(self, adapter: EsimAccessProvider) -> None:
        adapter._client.request.return_value = {
            "success": True,
            "errorCode": "0",
            "obj": {"orderNo": "B26033120580005"},
        }
        result = await adapter.create_order("CKH511", 1, "txn-001")
        assert result.order_no == "B26033120580005"
        assert result.status == "pending"
        assert result.iccid is None


# ------------------------------------------------------------------
# Query Contract
# ------------------------------------------------------------------


class TestQueryContract:
    """POST /api/v1/open/esim/query
    Request: {orderNo?, iccid?, pager: {pageNum, pageSize}}
    Response: {success: true, obj: {esimList: [...], pager: {pageNum, pageSize, total}}}
    """

    @pytest.mark.asyncio
    async def test_query_request_has_pager(self, adapter: EsimAccessProvider) -> None:
        adapter._client.request.return_value = {
            "success": True,
            "obj": {"esimList": [], "pager": {"pageNum": 1, "pageSize": 5, "total": 0}},
        }
        await adapter.get_order_status("ORD-001")

        payload = adapter._client.request.call_args[0][1]
        assert "pager" in payload
        assert payload["pager"]["pageNum"] == 1
        assert 5 <= payload["pager"]["pageSize"] <= 500

    @pytest.mark.asyncio
    async def test_query_response_reads_esim_list(self, adapter: EsimAccessProvider) -> None:
        adapter._client.request.return_value = {
            "success": True,
            "errorCode": "0",
            "obj": {
                "esimList": [
                    {
                        "orderNo": "ORD-001",
                        "iccid": "8943108170005579276",
                        "esimStatus": "GOT_RESOURCE",
                        "smsStatus": 1,
                        "msisdn": "4367844378927",
                    }
                ],
                "pager": {"pageNum": 1, "pageSize": 5, "total": 1},
            },
        }
        result = await adapter.get_order_status("ORD-001")
        assert result.order_no == "ORD-001"
        assert result.iccid == "8943108170005579276"
        assert result.status == "completed"


# ------------------------------------------------------------------
# Top-Up Contract (documented and re-enabled)
# ------------------------------------------------------------------


class TestTopUpContract:
    """POST /api/v1/open/esim/topup
    Request: {iccid, packageCode, transactionId}
    Response: {success: true, obj: {transactionId, iccid, expiredTime, totalVolume, ...}}
    """

    @pytest.mark.asyncio
    async def test_topup_does_not_raise(self, adapter: EsimAccessProvider) -> None:
        adapter._client.request.return_value = {
            "success": True,
            "obj": {
                "transactionId": "fb9b22193f3c45aab4f052efbc878f30",
                "iccid": "89852245280001354019",
                "expiredTime": "2023-08-24T17:01:37+0000",
                "totalVolume": 5368709120,
                "totalDuration": 35,
                "orderUsage": 907415004,
            },
        }
        result = await adapter.topup_esim("89852245280001354019", "TOPUP_CKH491", "txn-topup")
        assert result.status == "completed"
        assert result.iccid == "89852245280001354019"


# ------------------------------------------------------------------
# Cancel Contract (documented and re-enabled)
# ------------------------------------------------------------------


class TestCancelContract:
    @pytest.mark.asyncio
    async def test_cancel_does_not_raise(self, adapter: EsimAccessProvider) -> None:
        adapter._client.request.return_value = {"success": True, "obj": None}
        result = await adapter.cancel_order("89012345678901234560")
        assert result.status == "cancelled"


# ------------------------------------------------------------------
# Suspend — NOT documented
# ------------------------------------------------------------------


class TestSuspendContract:
    @pytest.mark.asyncio
    async def test_suspend_not_documented(self, adapter: EsimAccessProvider) -> None:
        with pytest.raises(ProviderCapabilityUnavailableError):
            await adapter.suspend_esim("ICC")
