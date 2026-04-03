# State Synchronization Design

**Date**: 2026-03-31
**Scope**: Provider state → internal state synchronization for eSIM Gateway
**Source of truth**: docs.esimaccess.com + verified live responses (SANDBOX_EVIDENCE.md)

---

## 1. Current Gap

### Provider Truth (verified live — 2026-03-31)

After a successful order, the eSIM Access query endpoint (`/api/v1/open/esim/query`)
returns full eSIM fulfillment details immediately:

| Field | Example |
|-------|---------|
| esimTranNo | 26033119290005 |
| orderNo | B26033119290003 |
| transactionId | 520372b9-… |
| iccid | 8910300000044404757 |
| imsi | 310840118124583 |
| ac | LPA:1$rsp-eu.simlessly.com$C5F541… |
| qrCodeUrl | https://p.qrsim.net/90f197… |
| shortUrl | https://p.qrsim.net/90f197… |
| smdpStatus | RELEASED |
| esimStatus | GOT_RESOURCE |
| pin / puk / apn | 6313 / 25363068 / isp |
| totalVolume | 1073741824 (1 GB) |
| totalDuration / durationUnit | 1 / DAY |
| orderUsage | 0 |
| expiredTime | 2026-09-27T19:29:36+0000 |
| supportTopUpType | 3 |
| fupPolicy | 1 Mbps |
| packageList | [{packageName, packageCode, …}] |

### Internal State (current)

After order creation the gateway persists:

- `ProviderOrder`: status=pending, iccid=null, provider_status missing
- **No Esim record** (eSIM Access order response only returns `orderNo`, no iccid)

### The Gap

The provider has a fully provisioned eSIM but internal DB shows
`status=pending, iccid=null` indefinitely. There is no mechanism to:

1. Automatically query provider after order and merge state
2. Manually trigger a refresh
3. Periodically reconcile stale orders
4. Process webhooks that could update state

---

## 2. Proposed Data Flow

### 2.1 Immediate Post-Order Sync

```
Order created → provider returns orderNo →
  immediately query /api/v1/open/esim/query with orderNo →
  if esimList: create/update Esim, update order status, record history →
  source: "post_order_sync"
```

### 2.2 Manual Refresh

```
POST /v1/orders/{id}/refresh →
  locate internal order →
  query provider with provider_order_no →
  merge state into order + eSIM records →
  record history (source: "manual_refresh") →
  return updated order with eSIM details
```

### 2.3 Reconciliation Job

```
Every N minutes (default 5 min):
  select orders: non-terminal, stale or missing sync →
  for each: query provider, merge state →
  record history (source: "reconciliation")
```

### 2.4 Webhook Processing

```
Webhook received →
  persist raw payload to webhook_events →
  extract orderNo / ICCID / notifyType →
  trigger provider query refresh (don't trust webhook alone) →
  merge state from provider query →
  record history (source: "webhook")
```

---

## 3. Status Mapping

### Provider esimStatus → Internal Status

| Provider (raw) | Internal | Description |
|----------------|----------|-------------|
| GOT_RESOURCE | ready | eSIM provisioned, not yet installed |
| IN_USE | active | eSIM installed and in use |
| USED_UP | consumed | Data/validity exhausted |
| DELETED | cancelled | eSIM cancelled/deleted |
| *(unknown)* | unknown_provider_state | Stored raw, mapped conservatively |

### Terminal Statuses

`consumed`, `cancelled`, `failed` — provider updates must not downgrade these.

### Status Transition Rules

- pending → ready (post-order sync finds GOT_RESOURCE)
- pending → active (if already IN_USE)
- ready → active (user starts using)
- active → consumed (data/time exhausted)
- ready/active → cancelled (cancelled by user/admin)
- pending → failed (order creation failed)

---

## 4. Update Precedence Rules

1. **Provider query** is the richest fulfillment source — always preferred
2. **Webhook** may trigger refresh but should not be the sole data source
3. **Never overwrite** non-null internal values with null provider values
4. **Prefer fresher** provider data when a meaningful timestamp exists
5. **Never downgrade** terminal statuses accidentally
6. **Preserve** raw provider payloads for audit in all flows
7. **Record history** for every meaningful state transition

---

## 5. Schema Changes

### ProviderOrder (additions)

| Column | Type | Purpose |
|--------|------|---------|
| provider_status | String(100), nullable | Raw provider status (e.g. GOT_RESOURCE) |
| last_provider_sync_at | DateTime(tz), nullable | Last successful provider query timestamp |
| last_provider_payload | JSONB, nullable | Full provider query response obj |

### Esim (additions)

| Column | Type | Maps from |
|--------|------|-----------|
| provider_esim_tran_no | String(128) | esimTranNo |
| imsi | String(64) | imsi |
| qr_code_url | Text | qrCodeUrl |
| short_url | Text | shortUrl |
| smdp_status | String(50) | smdpStatus |
| esim_status | String(50) | esimStatus (raw) |
| pin | String(32) | pin |
| puk | String(32) | puk |
| apn | String(128) | apn |
| total_volume | BigInteger | totalVolume (bytes) |
| total_duration | Integer | totalDuration |
| duration_unit | String(20) | durationUnit |
| order_usage | BigInteger | orderUsage (bytes) |
| activate_time | DateTime(tz) | activateTime |
| installation_time | DateTime(tz) | installationTime |
| expired_time | DateTime(tz) | expiredTime |
| support_topup_type | Integer | supportTopUpType |
| fup_policy | String(255) | fupPolicy |
| raw_provider_payload | JSONB | Latest full eSIM record from query |

### ProviderWebhookEvent (additions)

| Column | Type | Purpose |
|--------|------|---------|
| provider_event_id | String(128), nullable | Provider-assigned event ID if present |
| received_at | DateTime(tz), non-null | Explicit receive timestamp |
| processed_at | DateTime(tz), nullable | When processing completed |
| processing_status | String(50), non-null | pending / processed / failed |

### New: OrderStateHistory

| Column | Type |
|--------|------|
| id | String(64), PK |
| order_id | String(64), indexed |
| old_status | String(50), nullable |
| new_status | String(50), nullable |
| old_provider_status | String(100), nullable |
| new_provider_status | String(100), nullable |
| source | String(50) — post_order_sync / manual_refresh / reconciliation / webhook |
| payload_json | JSONB, nullable |
| created_at | DateTime(tz) |

---

## 6. Concurrency Safety

Multiple flows can update the same order concurrently:

- Post-order sync (during order creation)
- Manual refresh (admin API call)
- Reconciliation job (scheduled background task)
- Webhook processing (inbound provider notification)

Mitigations:

1. **Redis-based distributed lock** on reconciliation job prevents duplicate runs
2. **Row-level locking** (`SELECT … FOR UPDATE`) when updating orders/eSIMs
3. **Unique constraint** on `esims.iccid` prevents duplicate eSIM records
4. **Idempotent merge logic** — same provider data applied twice yields same result
5. **Terminal status guard** — cannot accidentally downgrade consumed/cancelled/failed

---

## 7. Reconciliation Strategy

**Candidate selection**:
- Non-terminal status (not consumed, cancelled, failed)
- provider_order_no is not null
- AND at least one of:
  - last_provider_sync_at is NULL
  - last_provider_sync_at older than stale threshold (default 10 min)

**Cadence**: Every 5 minutes (configurable via `reconciliation_interval_seconds`)

**Safety**: Redis lock prevents concurrent runs. Each order is synced independently.
Failures on one order don't block others.

---

## 8. Webhook Processing Strategy

1. Always persist raw payload first (audit trail)
2. Extract known fields conservatively (orderNo, ICCID/iccid, notifyType, transactionId)
3. On successful extraction, trigger a provider query refresh for the affected order
4. Trust the provider query result over webhook data
5. Duplicate payloads: detect by checking if same order_no+event_type was already processed
6. Processing failures: record error on webhook_events, preserve raw payload

---

## 9. Risks & Assumptions

1. Provider query response shape is verified against live data (SANDBOX_EVIDENCE.md)
2. **Multiple eSIMs per order**: handle all entries in esimList but document as uncommon
3. **Webhook field casing**: handle both `ICCID` and `iccid` (observed in docs/examples)
4. **Real webhook payload**: not yet observed live — implementation is conservative
5. **Race conditions**: mitigated by row locking + Redis locks + idempotent merges
6. **Provider datetime format**: `2026-09-27T19:29:36+0000` — parsed with timezone normalization
