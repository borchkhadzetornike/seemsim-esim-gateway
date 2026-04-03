# State Synchronization Changelog

**Date**: 2026-03-31
**Scope**: Provider state → internal state synchronization

---

## Summary

Implemented reliable provider state synchronization so that internal order and eSIM
records are kept in sync with the eSIM Access API. After this change, a successfully
placed order no longer remains stuck as `status=pending, iccid=null` when the
provider has already provisioned the eSIM.

---

## What Changed

### 1. Data Model / Schema (Migration 002)

**New columns on `provider_orders`:**
- `provider_status` — raw provider status string (e.g. GOT_RESOURCE)
- `last_provider_sync_at` — timestamp of last successful provider query
- `last_provider_payload` — full JSONB of last provider query response

**New columns on `esims` (18 fields):**
- `provider_esim_tran_no`, `imsi`, `qr_code_url`, `short_url`
- `smdp_status`, `esim_status` (raw provider status)
- `pin`, `puk`, `apn`
- `total_volume` (bytes, BigInteger), `total_duration`, `duration_unit`, `order_usage` (bytes)
- `activate_time`, `installation_time`, `expired_time` (DateTimeTZ)
- `support_topup_type`, `fup_policy`
- `raw_provider_payload` (latest full eSIM record from provider query)

**New columns on `provider_webhook_events`:**
- `provider_event_id` — provider-assigned event ID if present
- `received_at` — explicit receive timestamp
- `processed_at` — when processing completed
- `processing_status` — pending / processed / failed (replaces boolean `processed` semantically)

**New table: `order_state_history`:**
- Tracks every meaningful state transition with source, old/new status,
  old/new provider status, raw payload, and timestamp

**Also fixed:** `provider_products.location_code` column type from `String(10)` to
`String(255)` in the migration (was already altered in production via direct SQL).

### 2. Provider Query → Internal State Mapper (`app/services/state_sync.py`)

New `ProviderStateSyncer` service that:
- Queries provider via `query_order_full()` for the complete esimList
- Merges all eSIM records into internal state
- Maps provider `esimStatus` to internal status:
  - GOT_RESOURCE → ready
  - IN_USE → active
  - USED_UP → consumed
  - DELETED → cancelled
  - (unknown) → unknown_provider_state
- Never overwrites non-null internal values with null provider values
- Never downgrades terminal statuses (consumed, cancelled, failed)
- Records `OrderStateHistory` for every meaningful transition
- Records `EsimStatusHistory` for every eSIM status change
- Parses LPA activation code into smdp_address + matching_id
- Parses provider datetime format (`2026-09-27T19:29:36+0000`)

### 3. Immediate Post-Order Sync (`app/services/order.py`)

After successful provider order creation, `OrderService.create_order()` now:
1. Persists the order with `provider_order_no` as before
2. **Immediately** queries the provider via `ProviderStateSyncer.sync_order()`
3. If the provider has eSIM details, creates/updates Esim records inline
4. If the sync fails, the order is still returned (safe fallback to pending)

### 4. Manual Refresh Endpoint (`POST /v1/orders/{id}/refresh`)

New endpoint that:
- Queries provider for latest state
- Merges into internal order + eSIM records
- Records state history (source: `manual_refresh`)
- Returns enriched response with full eSIM details

Also added: `GET /v1/orders/{id}/esims` for fetching associated eSIMs.

### 5. Reconciliation Job (`app/tasks/reconciliation.py`)

Updated `reconcile_pending_orders()` to:
- Use `ProviderStateSyncer` instead of raw status update (creates eSIM records)
- Select orders by expanded criteria: non-terminal + stale or never-synced
- Use `OrderRepository.get_orders_needing_sync()` with stale threshold (10 min)
- Record state history for each reconciled order (source: `reconciliation`)

### 6. Webhook Infrastructure (`app/services/webhook.py`)

Enhanced `WebhookService.process_webhook()` to:
- Set `processing_status` field (pending/processed/failed)
- Set `processed_at` timestamp on completion
- Detect duplicate webhooks (same order_no + event_type already processed)
- **Trigger provider query refresh** after webhook processing (trusts provider
  query over webhook data for full state merge, source: `webhook`)

### 7. Provider Adapter (`app/providers/esim_access/adapter.py`)

Added `query_order_full()` method that returns the complete `obj` from
`/api/v1/open/esim/query` with a large page size (500) for state sync.

Also added default `query_order_full()` to `BaseEsimProvider` that wraps
`get_order_status()` for provider-agnostic compatibility.

### 8. Repository Enhancements

- `OrderRepository.get_orders_needing_sync()` — finds stale/incomplete orders
- `OrderRepository.get_by_id_locked()` — row-level locking for concurrent safety
- `EsimRepository.get_by_iccid_locked()` — row-level locking
- `WebhookRepository.find_processed_duplicate()` — dedup check
- `WebhookRepository.mark_processed()` — now sets `processed_at` + `processing_status`

### 9. Schema Updates

- `OrderOut` now includes `provider_status` and `last_provider_sync_at`
- New `OrderDetailOut` with embedded `esims: list[EsimDetailOut]`
- New `EsimDetailOut` with all 18+ provider detail fields
- New `OrderRefreshResponse` for the refresh endpoint
- `EsimOut` enriched with all new provider detail fields

---

## Migration Summary

**Migration 002** (`alembic/versions/002_state_sync.py`):
- Adds 3 columns to `provider_orders`
- Adds 18 columns to `esims`
- Adds 4 columns to `provider_webhook_events`
- Creates `order_state_history` table with 2 indexes
- Fixes `provider_products.location_code` column width

---

## Status Mapping Summary

| Provider esimStatus | Internal order.status | Internal esim.status |
|--------------------|-----------------------|---------------------|
| GOT_RESOURCE | ready | ready |
| IN_USE | active | active |
| USED_UP | consumed | consumed |
| DELETED | cancelled | cancelled |
| *(unknown)* | unknown_provider_state | unknown_provider_state |

Terminal statuses (`consumed`, `cancelled`, `failed`) are never downgraded.

---

## Test Summary

- **24 new unit tests** in `tests/unit/services/test_state_sync.py`
- **5 new integration tests** in `tests/integration/api/test_order_refresh.py`
- **137 total tests pass** (108 existing + 29 new)

---

## Still-Unverified Webhook Assumptions

1. **Real webhook payload shape**: conservative mapping based on docs.esimaccess.com;
   field casing (ICCID vs iccid) and exact field presence not yet verified live
2. **notifyType values**: ORDER_STATUS, ESIM_STATUS, DATA_USAGE, VALIDITY_USAGE are
   documented but not observed in a real inbound webhook
3. **Webhook dedup mechanism**: currently checks order_no + event_type; may need
   refinement when real webhook patterns are observed
4. **Webhook-triggered refresh**: triggers provider query after webhook processing;
   assumes provider query is always richer than webhook payload — needs live validation
