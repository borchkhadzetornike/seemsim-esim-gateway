"""Tests for ProviderStateSyncer — the provider→internal state merge layer.

Uses verified live response shapes from SANDBOX_EVIDENCE.md as executable truth.
"""

from __future__ import annotations

import copy
import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.esim import Esim
from app.models.order import ProviderOrder
from app.models.order_state_history import OrderStateHistory
from app.repositories.esim import EsimRepository
from app.repositories.order_state_history import OrderStateHistoryRepository
from app.services.state_sync import (
    ProviderStateSyncer,
    _parse_provider_dt,
    _set_if_present,
    _set_int_if_present,
)

# ---------------------------------------------------------------------------
# Verified live response shape from SANDBOX_EVIDENCE.md
# ---------------------------------------------------------------------------

LIVE_ESIM_RECORD = {
    "esimTranNo": "26033119290005",
    "orderNo": "B26033119290003",
    "transactionId": "520372b9-508f-4661-b3cf-0f9d8f6ea9e1",
    "imsi": "310840118124583",
    "iccid": "8910300000044404757",
    "smsStatus": 0,
    "msisdn": "",
    "ac": "LPA:1$rsp-eu.simlessly.com$C5F541D4E3174EA38A74B6EF7CCB80FF",
    "qrCodeUrl": "https://p.qrsim.net/90f19728db9445fb9ebfb525e0db2798.png",
    "shortUrl": "https://p.qrsim.net/90f19728db9445fb9ebfb525e0db2798",
    "smdpStatus": "RELEASED",
    "eid": "",
    "activeType": 2,
    "dataType": 2,
    "activateTime": None,
    "expiredTime": "2026-09-27T19:29:36+0000",
    "installationTime": None,
    "totalVolume": 1073741824,
    "totalDuration": 1,
    "durationUnit": "DAY",
    "orderUsage": 0,
    "esimStatus": "GOT_RESOURCE",
    "pin": "6313",
    "puk": "25363068",
    "apn": "isp",
    "ipExport": "FR/NL",
    "supportTopUpType": 3,
    "fupPolicy": "1 Mbps",
    "packageList": [
        {
            "packageName": "Georgia 1GB/Day FUP1Mbps",
            "packageCode": "P1X57VWMR",
            "slug": "GE_1_Daily_1Mbps",
            "duration": 1,
            "volume": 1073741824,
            "locationCode": "GE",
            "createTime": "2026-03-31T19:29:36+0000",
            "esimTranNo": "26033119290005",
            "transactionId": "520372b9-508f-4661-b3cf-0f9d8f6ea9e1",
        }
    ],
}

LIVE_QUERY_OBJ = {
    "esimList": [LIVE_ESIM_RECORD],
    "pager": {"pageSize": 5, "pageNum": 1, "total": 1},
}


@pytest.fixture
def provider() -> AsyncMock:
    mock = AsyncMock()
    mock.provider_name = "esim_access"
    mock.query_order_full.return_value = copy.deepcopy(LIVE_QUERY_OBJ)
    return mock


def _make_order(
    status: str = "pending",
    provider_order_no: str = "B26033119290003",
    iccid: str | None = None,
    provider_status: str | None = None,
) -> ProviderOrder:
    return ProviderOrder(
        id=str(uuid.uuid4()),
        provider_name="esim_access",
        provider_order_no=provider_order_no,
        transaction_id=str(uuid.uuid4()),
        package_code="P1X57VWMR",
        quantity=1,
        status=status,
        provider_status=provider_status,
        iccid=iccid,
    )


# ---------------------------------------------------------------------------
# Test 1: Post-order sync populates ICCID and updates status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_order_sync_populates_iccid_and_status(
    db_session: AsyncSession, provider: AsyncMock
) -> None:
    order = _make_order(status="pending", iccid=None)
    db_session.add(order)
    await db_session.flush()

    syncer = ProviderStateSyncer(provider, db_session)
    result = await syncer.sync_order(order, "post_order_sync")

    assert result.state_changed is True
    assert result.order.status == "ready"
    assert result.order.provider_status == "GOT_RESOURCE"
    assert result.order.iccid == "8910300000044404757"
    assert result.order.last_provider_sync_at is not None
    assert result.order.last_provider_payload is not None
    assert len(result.esims) == 1


# ---------------------------------------------------------------------------
# Test 2: Provider query mapping persists eSIM details correctly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_esim_details_persisted_correctly(
    db_session: AsyncSession, provider: AsyncMock
) -> None:
    order = _make_order(status="pending")
    db_session.add(order)
    await db_session.flush()

    syncer = ProviderStateSyncer(provider, db_session)
    result = await syncer.sync_order(order, "post_order_sync")

    esim = result.esims[0]
    assert esim.iccid == "8910300000044404757"
    assert esim.provider_esim_tran_no == "26033119290005"
    assert esim.imsi == "310840118124583"
    assert esim.activation_code == "LPA:1$rsp-eu.simlessly.com$C5F541D4E3174EA38A74B6EF7CCB80FF"
    assert esim.smdp_address == "rsp-eu.simlessly.com"
    assert esim.matching_id == "C5F541D4E3174EA38A74B6EF7CCB80FF"
    assert esim.qr_code_url == "https://p.qrsim.net/90f19728db9445fb9ebfb525e0db2798.png"
    assert esim.short_url == "https://p.qrsim.net/90f19728db9445fb9ebfb525e0db2798"
    assert esim.smdp_status == "RELEASED"
    assert esim.esim_status == "GOT_RESOURCE"
    assert esim.status == "ready"
    assert esim.pin == "6313"
    assert esim.puk == "25363068"
    assert esim.apn == "isp"
    assert esim.total_volume == 1073741824
    assert esim.total_duration == 1
    assert esim.duration_unit == "DAY"
    assert esim.order_usage == 0
    assert esim.support_topup_type == 3
    assert esim.fup_policy == "1 Mbps"
    assert esim.expired_time is not None
    assert esim.raw_provider_payload is not None


# ---------------------------------------------------------------------------
# Test 3: Manual refresh updates stale internal state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_manual_refresh_updates_stale_state(
    db_session: AsyncSession, provider: AsyncMock
) -> None:
    order = _make_order(status="pending", iccid=None)
    db_session.add(order)
    await db_session.flush()

    syncer = ProviderStateSyncer(provider, db_session)

    # First sync
    await syncer.sync_order(order, "post_order_sync")
    assert order.status == "ready"

    # Simulate provider status change
    updated_obj = copy.deepcopy(LIVE_QUERY_OBJ)
    updated_obj["esimList"][0]["esimStatus"] = "IN_USE"
    provider.query_order_full.return_value = updated_obj

    result = await syncer.sync_order(order, "manual_refresh")

    assert result.state_changed is True
    assert result.order.status == "active"
    assert result.order.provider_status == "IN_USE"


# ---------------------------------------------------------------------------
# Test 4: Reconciliation updates pending orders with provider data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reconciliation_creates_esim_for_pending_order(
    db_session: AsyncSession, provider: AsyncMock
) -> None:
    order = _make_order(status="pending", iccid=None)
    db_session.add(order)
    await db_session.flush()

    syncer = ProviderStateSyncer(provider, db_session)
    result = await syncer.sync_order(order, "reconciliation")

    assert result.state_changed is True
    assert len(result.esims) == 1
    assert result.esims[0].iccid == "8910300000044404757"

    # Verify esim is persisted
    repo = EsimRepository(db_session)
    esim = await repo.get_by_iccid("8910300000044404757")
    assert esim is not None
    assert esim.order_id == order.id


# ---------------------------------------------------------------------------
# Test 5: Duplicate sync does not duplicate eSIM records
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_duplicate_sync_no_duplicate_esims(
    db_session: AsyncSession, provider: AsyncMock
) -> None:
    order = _make_order(status="pending")
    db_session.add(order)
    await db_session.flush()

    syncer = ProviderStateSyncer(provider, db_session)

    await syncer.sync_order(order, "post_order_sync")
    result2 = await syncer.sync_order(order, "manual_refresh")

    assert len(result2.esims) == 1

    repo = EsimRepository(db_session)
    esims = await repo.get_by_order_id(order.id)
    assert len(esims) == 1


# ---------------------------------------------------------------------------
# Test 6: Null provider fields do not wipe existing internal values
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_null_provider_fields_do_not_wipe_existing(
    db_session: AsyncSession, provider: AsyncMock
) -> None:
    order = _make_order(status="pending")
    db_session.add(order)
    await db_session.flush()

    syncer = ProviderStateSyncer(provider, db_session)
    await syncer.sync_order(order, "post_order_sync")

    esim = (await EsimRepository(db_session).get_by_order_id(order.id))[0]
    assert esim.pin == "6313"
    assert esim.apn == "isp"

    # Provider now returns null for some fields
    sparse_obj = copy.deepcopy(LIVE_QUERY_OBJ)
    sparse_obj["esimList"][0]["pin"] = None
    sparse_obj["esimList"][0]["apn"] = None
    sparse_obj["esimList"][0]["qrCodeUrl"] = None
    provider.query_order_full.return_value = sparse_obj

    await syncer.sync_order(order, "manual_refresh")

    esim_after = await EsimRepository(db_session).get_by_iccid("8910300000044404757")
    assert esim_after is not None
    assert esim_after.pin == "6313"
    assert esim_after.apn == "isp"
    assert esim_after.qr_code_url is not None


# ---------------------------------------------------------------------------
# Test 7: Unknown provider status is stored safely and mapped conservatively
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_provider_status_mapped_conservatively(
    db_session: AsyncSession, provider: AsyncMock
) -> None:
    unknown_obj = copy.deepcopy(LIVE_QUERY_OBJ)
    unknown_obj["esimList"][0]["esimStatus"] = "SOME_NEW_STATUS"
    provider.query_order_full.return_value = unknown_obj

    order = _make_order(status="pending")
    db_session.add(order)
    await db_session.flush()

    syncer = ProviderStateSyncer(provider, db_session)
    result = await syncer.sync_order(order, "post_order_sync")

    assert result.order.status == "unknown_provider_state"
    assert result.order.provider_status == "SOME_NEW_STATUS"
    assert result.esims[0].esim_status == "SOME_NEW_STATUS"


# ---------------------------------------------------------------------------
# Test 8: History is recorded for meaningful transitions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_history_recorded_for_transitions(
    db_session: AsyncSession, provider: AsyncMock
) -> None:
    order = _make_order(status="pending")
    db_session.add(order)
    await db_session.flush()

    syncer = ProviderStateSyncer(provider, db_session)
    result = await syncer.sync_order(order, "post_order_sync")
    assert result.state_changed is True

    history_repo = OrderStateHistoryRepository(db_session)
    entries = await history_repo.get_by_order_id(order.id)
    assert len(entries) >= 1
    entry = entries[0]
    assert entry.old_status == "pending"
    assert entry.new_status == "ready"
    assert entry.source == "post_order_sync"
    assert entry.old_provider_status is None
    assert entry.new_provider_status == "GOT_RESOURCE"


# ---------------------------------------------------------------------------
# Test 9: Terminal status is not downgraded
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_terminal_status_not_downgraded(
    db_session: AsyncSession, provider: AsyncMock
) -> None:
    order = _make_order(status="cancelled", provider_status="DELETED")
    db_session.add(order)
    await db_session.flush()

    syncer = ProviderStateSyncer(provider, db_session)
    result = await syncer.sync_order(order, "reconciliation")

    assert result.order.status == "cancelled"


# ---------------------------------------------------------------------------
# Test 10: Order remains stable if provider query returns empty esimList
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_esimlist_keeps_order_stable(
    db_session: AsyncSession, provider: AsyncMock
) -> None:
    provider.query_order_full.return_value = {"esimList": [], "pager": {}}

    order = _make_order(status="pending")
    db_session.add(order)
    await db_session.flush()

    syncer = ProviderStateSyncer(provider, db_session)
    result = await syncer.sync_order(order, "post_order_sync")

    assert result.state_changed is False
    assert result.order.status == "pending"
    assert len(result.esims) == 0
    assert result.order.last_provider_sync_at is not None


# ---------------------------------------------------------------------------
# Test 11: Order without provider_order_no is skipped
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_order_without_provider_order_no_skipped(
    db_session: AsyncSession, provider: AsyncMock
) -> None:
    order = _make_order(status="pending", provider_order_no=None)  # type: ignore[arg-type]
    order.provider_order_no = None
    db_session.add(order)
    await db_session.flush()

    syncer = ProviderStateSyncer(provider, db_session)
    result = await syncer.sync_order(order, "post_order_sync")

    assert result.state_changed is False
    provider.query_order_full.assert_not_called()


# ---------------------------------------------------------------------------
# Test 12: Provider query failure is handled gracefully
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provider_query_failure_handled_gracefully(
    db_session: AsyncSession, provider: AsyncMock
) -> None:
    provider.query_order_full.side_effect = Exception("Provider timeout")

    order = _make_order(status="pending")
    db_session.add(order)
    await db_session.flush()

    syncer = ProviderStateSyncer(provider, db_session)
    result = await syncer.sync_order(order, "post_order_sync")

    assert result.state_changed is False
    assert result.order.status == "pending"


# ---------------------------------------------------------------------------
# Test 13: Repeated refresh is safe and idempotent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_repeated_refresh_idempotent(
    db_session: AsyncSession, provider: AsyncMock
) -> None:
    order = _make_order(status="pending")
    db_session.add(order)
    await db_session.flush()

    syncer = ProviderStateSyncer(provider, db_session)

    r1 = await syncer.sync_order(order, "post_order_sync")
    assert r1.state_changed is True

    r2 = await syncer.sync_order(order, "manual_refresh")
    assert r2.state_changed is False
    assert r2.order.status == "ready"


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_set_if_present_sets_value(self) -> None:
        class Obj:
            field: str | None = None

        obj = Obj()
        _set_if_present(obj, "field", "hello")
        assert obj.field == "hello"

    def test_set_if_present_skips_none(self) -> None:
        class Obj:
            field: str = "existing"

        obj = Obj()
        _set_if_present(obj, "field", None)
        assert obj.field == "existing"

    def test_set_if_present_skips_empty_string(self) -> None:
        class Obj:
            field: str = "existing"

        obj = Obj()
        _set_if_present(obj, "field", "")
        assert obj.field == "existing"

    def test_set_int_if_present_sets_value(self) -> None:
        class Obj:
            field: int | None = None

        obj = Obj()
        _set_int_if_present(obj, "field", 42)
        assert obj.field == 42

    def test_set_int_if_present_handles_invalid(self) -> None:
        class Obj:
            field: int | None = None

        obj = Obj()
        _set_int_if_present(obj, "field", "not_a_number")
        assert obj.field is None

    def test_parse_provider_dt_valid(self) -> None:
        dt = _parse_provider_dt("2026-09-27T19:29:36+0000")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 9

    def test_parse_provider_dt_none(self) -> None:
        assert _parse_provider_dt(None) is None

    def test_parse_provider_dt_empty(self) -> None:
        assert _parse_provider_dt("") is None

    def test_parse_provider_dt_invalid(self) -> None:
        assert _parse_provider_dt("not-a-date") is None

    def test_map_status_known(self) -> None:
        assert ProviderStateSyncer.map_status("GOT_RESOURCE") == "ready"
        assert ProviderStateSyncer.map_status("IN_USE") == "active"
        assert ProviderStateSyncer.map_status("USED_UP") == "consumed"
        assert ProviderStateSyncer.map_status("DELETED") == "cancelled"

    def test_map_status_unknown(self) -> None:
        assert ProviderStateSyncer.map_status("SOMETHING_NEW") == "unknown_provider_state"
