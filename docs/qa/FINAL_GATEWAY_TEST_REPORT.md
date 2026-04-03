# Final Gateway Test Report

**Date**: 2026-04-01
**Engineer**: eSIM Gateway validation pass
**Purpose**: Final end-to-end validation including state synchronization and webhook readiness

---

## Environment

| Parameter | Value |
|-----------|-------|
| Provider host | `https://api.esimaccess.com` |
| Environment type | Production-like (real provider API) |
| Ngrok webhook URL | `https://0870-185-115-6-66.ngrok-free.app/v1/provider/webhooks/esim-access` |
| Gateway host | `localhost:8000` (Docker container) |
| Database | PostgreSQL 16 (Docker, healthy) |
| Redis | Redis 7 (Docker, healthy) |
| Migration applied | 001 (initial) + 002 (state sync) |
| Starting balance | $48.28 USD |
| Ending balance | $47.42 USD |
| **Total spend this pass** | **~$0.86 USD** (one order) |

---

## Package Selected

| Field | Value |
|-------|-------|
| packageCode | P1X57VWMR |
| packageName | Georgia 1GB/Day FUP1Mbps |
| price | $0.90 |
| location | GE (Georgia) |
| Reason | Cheapest available Georgia-only package |

---

## Live Calls Executed

### 1. Catalog Sync
```
POST /v1/catalog/sync
Result: 212 products, 2590 packages synced
```

### 2. Balance Query
```
Provider API: /api/v1/open/balance/query
Result: balance=482800 ($48.28)
```

### 3. Order Create (CRITICAL TEST)
```
POST /v1/orders
Body: {"package_code":"P1X57VWMR","quantity":1}
Header: Idempotency-Key: final-validation-order-1743500818

Result:
  order_id: c2f80432-f1a9-46ec-895b-971366749b14
  provider_order_no: B26040109460024
  transaction_id: 6ffdae4a-baf9-40f4-bf2d-f1a206b181a4
  status: ready (NOT pending — post-order sync worked)
  provider_status: GOT_RESOURCE
  iccid: 8910300000040030312
  last_provider_sync_at: 2026-04-01T09:47:00.536740Z
```

### 4. Manual Refresh (twice)
```
POST /v1/orders/c2f80432-.../refresh
1st call: state_changed=false, full eSIM details returned
2nd call: state_changed=false, idempotent (no duplicate history)
```

### 5. Get Order eSIMs
```
GET /v1/orders/c2f80432-.../esims
Result: 1 eSIM with all 18+ fields populated
```

### 6. Ending Balance
```
Provider API: /api/v1/open/balance/query
Result: balance=474200 ($47.42)
```

---

## State Sync Results

### Immediate Post-Order Sync
**PASSED — VERIFIED BY REAL PROVIDER CALL**

The single most important test of this validation pass. After order creation:
- Order status immediately moved from `pending` to `ready` within the same API call
- `provider_status` set to `GOT_RESOURCE`
- `iccid` populated: `8910300000040030312`
- `last_provider_sync_at` set
- eSIM record created with full details:
  - `provider_esim_tran_no`: 26040109460026
  - `smdp_status`: RELEASED
  - `esim_status`: GOT_RESOURCE
  - `activation_code`: LPA:1$rsp-eu.simlessly.com$20FDE2B61DDD4DEF9CBE89C55EADFC22
  - `qr_code_url`: https://p.qrsim.net/0f0a6ce01d9643b690a7b2046159331d.png
  - `imsi`: 310840115441965
  - `pin`: 7668 / `puk`: 72330085 / `apn`: isp
  - `total_volume`: 1073741824 (1GB) / `duration`: 1 DAY
  - `expired_time`: 2026-09-28T09:47:00Z
- State history: 1 entry (pending -> ready, source: post_order_sync)
- eSIM history: 1 entry (allocated -> ready, source: post_order_sync)

### Manual Refresh
**PASSED — VERIFIED BY REAL PROVIDER CALL**

- Queried provider successfully
- Returned full eSIM details including all fields
- `state_changed: false` (correct — state already synced)
- Repeated calls are idempotent: no duplicate history entries
- No null-wiping of existing data

### Reconciliation
**PASSED — VERIFIED BY AUTOMATED TEST ONLY**

No natural stale orders available for live reconciliation testing.
Unit tests (24 tests) verify the reconciliation path comprehensively.

---

## Webhook Results

### Route Functionality
**PASSED — VERIFIED BY MANUAL TEST**

- Local: POST to `/v1/provider/webhooks/esim-access` succeeds
- Ngrok: POST through public URL succeeds
- Payloads are persisted in `provider_webhook_events`
- Processing status tracked (pending/processed/failed)
- Duplicate detection works (same order_no + event_type)
- Malformed payloads are persisted safely

### Real Provider Webhook Delivery
**NOT VERIFIED**

No webhook was received from the provider for order `B26040109460024`.

**Root cause**: The webhook callback URL has not been registered in the eSIM Access admin portal.
The provider cannot deliver webhooks to an unregistered URL.

**Action required**: Register `https://<permanent-url>/v1/provider/webhooks/esim-access` in the
eSIM Access admin, then place a new order to verify live webhook delivery.

---

## Negative / Resilience Results

| Test | Result |
|------|--------|
| Refresh nonexistent order | 404 RESOURCE_NOT_FOUND (correct) |
| Invalid package code order | Provider error 310241 propagated (correct) |
| Malformed webhook payload | Persisted safely, event_type=UNKNOWN |
| Duplicate webhook replay | Detected, no duplicate side effects |
| Repeated manual refresh | Idempotent, no duplicate state history |
| Data integrity after all tests | 1 eSIM row, 1 state history, 1 eSIM history (no duplicates) |

---

## Automated Test Results

```
137 passed, 4 warnings in 7.83s
```

All tests pass including 24 state sync unit tests and 5 integration tests.
Warnings are pre-existing mock-related warnings, unrelated to current changes.

---

## Bugs Found

**None.** No code changes were needed during this validation pass.
The state sync implementation worked correctly on the first real test.

---

## Fixes Applied

**None.** No `TEST_FIXES.md` needed.

---

## Remaining Blockers

1. **Webhook URL not registered in eSIM Access admin** — must be configured to receive real webhooks
2. **Real webhook payload shape unknown** — field casing and exact fields not observed live
3. **Webhook-triggered state refresh unverified live** — only tested manually and in automated tests
4. **Top-up and cancel not verified with real calls** — only automated test coverage
5. **Suspend not supported** — not documented by eSIM Access

---

## Final Recommendations

### Sandbox Readiness: GO

All core flows are verified by real provider calls:
- Authentication, catalog sync, balance query, order creation, order query
- State synchronization works end-to-end: no orders stuck in pending
- Full eSIM details captured and persisted
- Manual refresh and negative paths work correctly

### Operational Readiness: CONDITIONAL GO

The gateway is operationally functional but requires:
1. Webhook URL registration in eSIM Access admin
2. At least one verified real webhook delivery
3. Permanent public URL (not ngrok) for production

### Production Pilot Readiness: NOT YET

Before production pilot:
1. Complete webhook verification with real provider delivery
2. Set up a permanent webhook endpoint (not ngrok)
3. Verify top-up and cancel with at least one real call each
4. Configure monitoring/alerting for reconciliation job
5. Set up proper secrets management (not .env file)
