> **Note:** This is an earlier readiness snapshot. See [Readiness Matrix](READINESS_MATRIX.md) for the most current version.

# Final Readiness Matrix

**Date**: 2026-04-01
**Gateway version**: post state-sync hardening

---

## Capability Verification Status

| Capability | Status | Evidence |
|-----------|--------|----------|
| **Authentication (HMAC-SHA256)** | VERIFIED BY REAL PROVIDER CALL | All live API calls succeed with RT-* headers |
| **Package sync** | VERIFIED BY REAL PROVIDER CALL | 2590 packages synced, 212 products |
| **Balance query** | VERIFIED BY REAL PROVIDER CALL | Returns $47.42 balance correctly |
| **Order create** | VERIFIED BY REAL PROVIDER CALL | Order B26040109460024 placed, $0.90 |
| **Order query** | VERIFIED BY REAL PROVIDER CALL | Full esimList returned with all fields |
| **Immediate post-order sync** | VERIFIED BY REAL PROVIDER CALL | Order status=ready, iccid populated, eSIM record created within same API call |
| **Manual refresh** | VERIFIED BY REAL PROVIDER CALL | POST /v1/orders/{id}/refresh returns full eSIM details, state_changed=false on repeat |
| **Get order eSIMs** | VERIFIED BY REAL PROVIDER CALL | GET /v1/orders/{id}/esims returns rich eSIM data |
| **Idempotency (gateway)** | VERIFIED BY AUTOMATED TEST ONLY | Redis-backed idempotency key dedup |
| **Idempotency (provider)** | VERIFIED BY REAL PROVIDER CALL | transactionId sent in order request |
| **Reconciliation job** | VERIFIED BY AUTOMATED TEST ONLY | Unit tests pass; no natural stale orders to reconcile live |
| **State history recording** | VERIFIED BY REAL PROVIDER CALL | order_state_history and esim_status_history rows created for real order |
| **eSIM detail persistence** | VERIFIED BY REAL PROVIDER CALL | All 18+ fields populated: iccid, imsi, ac, qr, pin, puk, apn, volume, etc. |
| **Webhook route (local)** | VERIFIED BY MANUAL TEST | POST to /v1/provider/webhooks/esim-access works |
| **Webhook route (ngrok)** | VERIFIED BY MANUAL TEST | POST through ngrok public URL works |
| **Webhook persistence** | VERIFIED BY MANUAL TEST | Raw payloads stored in provider_webhook_events |
| **Webhook dedup** | VERIFIED BY MANUAL TEST | Duplicate order_no+event_type detected and short-circuited |
| **Webhook-triggered refresh** | VERIFIED BY AUTOMATED TEST ONLY | Triggers provider query after webhook; not tested with real provider webhook |
| **Real provider webhook delivery** | NOT VERIFIED | No webhook received — URL not yet registered in eSIM Access admin |
| **Real webhook payload shape** | NOT VERIFIED | Field casing and exact fields not observed in live provider webhook |
| **Top-up** | VERIFIED BY AUTOMATED TEST ONLY | Endpoint exists, auth/path correct per contract |
| **Cancel** | VERIFIED BY AUTOMATED TEST ONLY | Endpoint exists, auth/path correct per contract |
| **Suspend** | BLOCKED | Not documented by eSIM Access, disabled by design |
| **Negative: invalid package** | VERIFIED BY REAL PROVIDER CALL | Provider returns 310241 error, gateway propagates correctly |
| **Negative: nonexistent order refresh** | VERIFIED BY REAL PROVIDER CALL | Returns 404 RESOURCE_NOT_FOUND |
| **Negative: malformed webhook** | VERIFIED BY MANUAL TEST | Payload persisted safely, event_type=UNKNOWN |
| **Terminal status protection** | VERIFIED BY AUTOMATED TEST ONLY | consumed/cancelled/failed never downgraded |
| **Null-safe field updates** | VERIFIED BY AUTOMATED TEST ONLY | Non-null values never overwritten by null |

---

## Summary

| Category | Count |
|----------|-------|
| VERIFIED BY REAL PROVIDER CALL | 12 |
| VERIFIED BY MANUAL TEST | 4 |
| VERIFIED BY AUTOMATED TEST ONLY | 7 |
| NOT VERIFIED | 2 |
| BLOCKED | 1 |

---

## Go/No-Go

| Decision | Verdict | Rationale |
|----------|---------|-----------|
| Sandbox readiness | **GO** | All core flows verified by real provider calls |
| Operational readiness | **CONDITIONAL GO** | Requires webhook URL registration + live webhook verification |
| Production pilot readiness | **NOT YET** | Webhook delivery and real payload verification required first |
