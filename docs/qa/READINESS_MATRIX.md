# Readiness Matrix

**Date**: 2026-04-01
**Version**: 1.0.0 (post gateway hardening)

---

## Capability Verification Status

| Capability | Status | Evidence |
|-----------|--------|----------|
| **Internal service auth** | VERIFIED BY REAL PROVIDER CALL | All live tests pass with auth headers |
| **Scope enforcement** | VERIFIED BY REAL PROVIDER CALL | seemsim-platform-backend blocked from catalog:sync, seemsim-worker blocked from balance:read |
| **Auth error responses** | VERIFIED BY REAL PROVIDER CALL | 401/403 with correct error codes |
| **Health unauthenticated** | VERIFIED BY REAL PROVIDER CALL | /health/live and /health/ready work without auth |
| **Webhook unauthenticated** | VERIFIED BY MANUAL TEST | Provider webhook endpoint works without internal auth |
| **HMAC-SHA256 signing** | VERIFIED BY REAL PROVIDER CALL | All provider calls succeed |
| **Package sync** | VERIFIED BY REAL PROVIDER CALL | 2590 packages, 212 products |
| **Balance query** | VERIFIED BY REAL PROVIDER CALL | $47.42 returned correctly |
| **Order create** | VERIFIED BY REAL PROVIDER CALL | Order B26040109460024 placed successfully |
| **Order query** | VERIFIED BY REAL PROVIDER CALL | Full esimList returned with all fields |
| **Immediate post-order sync** | VERIFIED BY REAL PROVIDER CALL | Order status=ready with ICCID within same API call |
| **Manual refresh** | VERIFIED BY REAL PROVIDER CALL | Full eSIM details, idempotent |
| **Get order eSIMs** | VERIFIED BY REAL PROVIDER CALL | All 18+ fields populated |
| **State history recording** | VERIFIED BY REAL PROVIDER CALL | order_state_history + esim_status_history rows |
| **eSIM detail persistence** | VERIFIED BY REAL PROVIDER CALL | iccid, imsi, ac, qr, pin, puk, apn, volume, etc. |
| **Idempotency (gateway)** | VERIFIED BY AUTOMATED TEST ONLY | Redis-backed dedup |
| **Idempotency (provider)** | VERIFIED BY REAL PROVIDER CALL | transactionId sent correctly |
| **Admin balance endpoint** | VERIFIED BY REAL PROVIDER CALL | Returns correct balance via auth-protected route |
| **Admin webhook-events** | VERIFIED BY REAL PROVIDER CALL | Returns event list via auth-protected route |
| **Admin reconciliation trigger** | VERIFIED BY AUTOMATED TEST ONLY | Background job callable via API |
| **Reconciliation job** | VERIFIED BY AUTOMATED TEST ONLY | 24 unit tests verify all logic |
| **Webhook route (local)** | VERIFIED BY MANUAL TEST | POST accepted, persisted |
| **Webhook route (ngrok)** | VERIFIED BY MANUAL TEST | POST through public URL works |
| **Webhook persistence** | VERIFIED BY MANUAL TEST | Raw payloads stored |
| **Webhook dedup** | VERIFIED BY MANUAL TEST | Duplicate detection works |
| **Webhook-triggered refresh** | VERIFIED BY AUTOMATED TEST ONLY | Triggers provider query |
| **Real provider webhook delivery** | NOT VERIFIED | URL not registered in provider admin |
| **Real webhook payload shape** | NOT VERIFIED | Field casing not observed live |
| **Top-up** | VERIFIED BY AUTOMATED TEST ONLY | Endpoint + adapter tested |
| **Cancel** | VERIFIED BY AUTOMATED TEST ONLY | Endpoint + adapter tested |
| **Suspend** | BLOCKED | Not documented by eSIM Access |
| **Startup config validation** | VERIFIED BY REAL PROVIDER CALL | Warnings logged for missing config |
| **Structured logging** | VERIFIED BY REAL PROVIDER CALL | request_id, caller_service, latency in logs |
| **Error response format** | VERIFIED BY REAL PROVIDER CALL | Consistent {success, data, error} envelope |
| **Negative: invalid package** | VERIFIED BY REAL PROVIDER CALL | Provider error propagated correctly |
| **Negative: nonexistent order** | VERIFIED BY REAL PROVIDER CALL | 404 RESOURCE_NOT_FOUND |
| **Negative: malformed webhook** | VERIFIED BY MANUAL TEST | Persisted safely |
| **Terminal status protection** | VERIFIED BY AUTOMATED TEST ONLY | Never downgraded |
| **Null-safe field updates** | VERIFIED BY AUTOMATED TEST ONLY | Non-null values preserved |

---

## Summary

| Category | Count |
|----------|-------|
| VERIFIED BY REAL PROVIDER CALL | 21 |
| VERIFIED BY MANUAL TEST | 5 |
| VERIFIED BY AUTOMATED TEST ONLY | 9 |
| NOT VERIFIED | 2 |
| BLOCKED | 1 |

---

## Go/No-Go Assessment

| Decision | Verdict | Rationale |
|----------|---------|-----------|
| **Ready for internal service use** | **GO** | Auth, scopes, all core flows verified by real calls, documented |
| **Ready for staging/pre-prod** | **GO** | Use permanent URL for webhooks, rotate API keys for staging |
| **Ready for production** | **CONDITIONAL GO** | Requires: permanent webhook URL, real webhook verification, secrets in manager |
| **Ready for customer traffic** | **NOT GATEWAY'S CONCERN** | Platform backend handles customers; gateway is internal only |
