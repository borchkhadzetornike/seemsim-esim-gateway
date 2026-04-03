"""Integration tests for the order refresh endpoint (POST /v1/orders/{id}/refresh).

Verifies the full flow: API -> OrderService -> ProviderStateSyncer -> DB.
"""

from __future__ import annotations

import copy
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.deps import get_provider
from app.models.order import ProviderOrder
from app.providers.base import BaseEsimProvider

LIVE_QUERY_OBJ = {
    "esimList": [
        {
            "esimTranNo": "26033119290005",
            "orderNo": "B26033119290003",
            "transactionId": "txn-test",
            "imsi": "310840118124583",
            "iccid": "8910300000044404757",
            "smsStatus": 0,
            "msisdn": "",
            "ac": "LPA:1$rsp-eu.simlessly.com$C5F541D4E3174EA38A74B6EF7CCB80FF",
            "qrCodeUrl": "https://p.qrsim.net/90f197.png",
            "shortUrl": "https://p.qrsim.net/90f197",
            "smdpStatus": "RELEASED",
            "esimStatus": "GOT_RESOURCE",
            "pin": "6313",
            "puk": "25363068",
            "apn": "isp",
            "totalVolume": 1073741824,
            "totalDuration": 1,
            "durationUnit": "DAY",
            "orderUsage": 0,
            "expiredTime": "2026-09-27T19:29:36+0000",
            "activateTime": None,
            "installationTime": None,
            "supportTopUpType": 3,
            "fupPolicy": "1 Mbps",
            "packageList": [],
        }
    ],
    "pager": {"pageSize": 5, "pageNum": 1, "total": 1},
}


@pytest.fixture
def refresh_provider() -> AsyncMock:
    from app.providers.base import ProviderOrderResult

    mock = AsyncMock(spec=BaseEsimProvider)
    mock.provider_name = "esim_access"
    mock.create_order.return_value = ProviderOrderResult(
        order_no="B26033119290003",
        transaction_id="txn-test",
        status="pending",
        iccid=None,
        raw={"orderNo": "B26033119290003"},
    )
    mock.query_order_full.return_value = copy.deepcopy(LIVE_QUERY_OBJ)
    return mock


@pytest.mark.asyncio
async def test_create_order_triggers_post_order_sync(
    app,
    client: AsyncClient,
    refresh_provider: AsyncMock,
) -> None:
    """Verify order creation now triggers immediate post-order sync."""
    app.dependency_overrides[get_provider] = lambda: refresh_provider

    create_resp = await client.post(
        "/v1/orders",
        json={"package_code": "P1X57VWMR", "quantity": 1},
    )
    assert create_resp.status_code == 201
    order_data = create_resp.json()["data"]

    # Post-order sync should have already updated the order
    assert order_data["status"] == "ready"
    assert order_data["provider_status"] == "GOT_RESOURCE"
    assert order_data["iccid"] == "8910300000044404757"


@pytest.mark.asyncio
async def test_refresh_returns_esim_details(
    app,
    client: AsyncClient,
    refresh_provider: AsyncMock,
) -> None:
    """Manual refresh returns full eSIM details even when no state change."""
    app.dependency_overrides[get_provider] = lambda: refresh_provider

    create_resp = await client.post(
        "/v1/orders",
        json={"package_code": "P1X57VWMR", "quantity": 1},
    )
    order_id = create_resp.json()["data"]["id"]

    refresh_resp = await client.post(f"/v1/orders/{order_id}/refresh")
    assert refresh_resp.status_code == 200

    data = refresh_resp.json()["data"]
    assert data["order"]["status"] == "ready"
    assert len(data["order"]["esims"]) == 1

    esim = data["order"]["esims"][0]
    assert esim["iccid"] == "8910300000044404757"
    assert esim["activation_code"].startswith("LPA:1$")
    assert esim["pin"] == "6313"
    assert esim["esim_status"] == "GOT_RESOURCE"


@pytest.mark.asyncio
async def test_refresh_detects_status_change(
    app,
    client: AsyncClient,
    refresh_provider: AsyncMock,
) -> None:
    """Refresh detects status change when provider state changes."""
    app.dependency_overrides[get_provider] = lambda: refresh_provider

    create_resp = await client.post(
        "/v1/orders",
        json={"package_code": "P1X57VWMR", "quantity": 1},
    )
    order_id = create_resp.json()["data"]["id"]

    # Change provider response to IN_USE
    updated = copy.deepcopy(LIVE_QUERY_OBJ)
    updated["esimList"][0]["esimStatus"] = "IN_USE"
    refresh_provider.query_order_full.return_value = updated

    refresh_resp = await client.post(f"/v1/orders/{order_id}/refresh")
    data = refresh_resp.json()["data"]

    assert data["state_changed"] is True
    assert data["order"]["status"] == "active"
    assert data["order"]["provider_status"] == "IN_USE"


@pytest.mark.asyncio
async def test_refresh_nonexistent_order(client: AsyncClient) -> None:
    resp = await client.post("/v1/orders/nonexistent-id/refresh")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_order_esims(
    app,
    client: AsyncClient,
    refresh_provider: AsyncMock,
) -> None:
    app.dependency_overrides[get_provider] = lambda: refresh_provider

    create_resp = await client.post(
        "/v1/orders",
        json={"package_code": "P1X57VWMR", "quantity": 1},
    )
    order_id = create_resp.json()["data"]["id"]

    # Refresh to populate eSIMs
    await client.post(f"/v1/orders/{order_id}/refresh")

    # Get eSIMs
    esims_resp = await client.get(f"/v1/orders/{order_id}/esims")
    assert esims_resp.status_code == 200
    esims = esims_resp.json()["data"]
    assert len(esims) == 1
    assert esims[0]["iccid"] == "8910300000044404757"
