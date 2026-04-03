> **Historical Document:** This review was written against the original Yoni provider integration, which has since been replaced by eSIM Access. See [Contract Revalidation](CONTRACT_REVALIDATION.md) and [eSIM Access Rewrite Changelog](ESIMACCESS_REWRITE_CHANGELOG.md) for the migration story.

# Pre-Flight Review

**Date**: 2026-03-31
**Reviewer**: Integration engineer (pre-live-testing pass)

---

## Phase 0 — Code Review Against Verification Docs

### What was re-checked

| Area | File | Status |
|------|------|--------|
| Auth header names | `auth.py` → `build_headers()` | `appId`, `timestamp`, `sign` — matches docs |
| Signature plain string | `auth.py` → `_build_plain()` | `appId&timestamp&path` — matches docs |
| Signature algorithm | `auth.py` → `sign()` | `HMAC-SHA256(appSecret, plain).hexdigest()` — matches docs |
| Timestamp format | `auth.py` → `generate_timestamp()` | `str(int(time.time() * 1000))` — matches docs |
| Endpoint paths | `adapter.py` constants | `/v1/package/e-sim/list`, `/v1/order/e-sim`, `/v1/order/e-sim/page`, `/v1/order/e-sim/flow` — matches docs |
| Path joining | `client.py` → `_request_with_retry()` | Paths are absolute, prepended with `/` if missing, passed directly to httpx — correct |
| idempotentKey forwarding | `adapter.py` → `create_order()` | Sent via `extra_headers` → merged in `build_headers()` — correct |
| Package array parsing | `adapter.py` → `sync_products()` | Reads `data.get("data", [])` as flat array — matches docs |
| Package field names | `adapter.py` → `_map_package()` | Reads `packageName`, `flow`, `days`, `packageType`, `countryEn`, `mcc` — matches docs |
| Order response | `adapter.py` → `create_order()` | Returns `status="pending"`, `iccid=None`, reads only `orderNo` — matches docs |
| Order list pagination | `adapter.py` → `get_order_status()` | Sends `current`/`size`/`orderNo`, reads `data.records` — matches docs |
| Usage fields | `adapter.py` → `get_esim_status()` | Reads `total`/`usage` as strings — matches docs |
| Webhook fields | `adapter.py` → `handle_webhook()` | Reads `result`, `orderNo`, `iccid`, `lpa`, `packageCode`, `packageName`, `price`, `currency` — matches docs |
| Unsupported capabilities | `adapter.py` | topup/cancel/suspend raise `ProviderCapabilityUnavailableError` — correct |

### Fixes applied before live testing

#### Fix 1: Empty body serialization (client.py)

**Issue**: When `payload={}` (e.g., package list), the condition `if payload` evaluated to `False` (empty dict is falsy), causing POST to be sent with no body at all. The docs show `payload = {}` being sent.

**Root cause**: `body_str = json_lib.dumps(payload) if payload else ""` — empty dict short-circuits.

**Fix**: Always serialize the payload: `body_str = json_lib.dumps(payload, separators=(",", ":"))`. Always send `content=body_str` in POST.

**Risk**: None — empty dict serializes to `{}` which is a valid JSON body.

#### Fix 2: HTTP 401 silently swallowed (client.py)

**Issue**: Provider returning HTTP 401 was not caught. The response JSON `{"code":401,...}` didn't match any error code handler (our map only covers 501-506, 400, 9999). Result: catalog sync returned `packages_synced: 0` with no error — a silent failure.

**Root cause**: Missing HTTP status code check for 401 between the 429 and 500 checks.

**Fix**: Added explicit check: `if response.status_code == 401: raise ProviderAuthenticationError(...)`.

**Risk**: None — authentication errors should always be surfaced.

---

## Phase 1 — Environment Pre-Flight

| Check | Result |
|-------|--------|
| Gateway starts | OK |
| Database connectivity | OK (PostgreSQL) |
| Redis connectivity | OK |
| Migrations applied | OK (`001` at head) |
| `/health/live` | OK |
| `/health/ready` | OK (database: ok, redis: ok) |
| Automated tests | **112 passed**, 0 failures, clean lint |
| APP_ID set | Yes (32 chars) |
| APP_SECRET set | Yes (32 chars) |
| APP_ENV | development |

### Provider URL Discovery

| Host | SSL Cert | Response | Verdict |
|------|----------|----------|---------|
| `sandbox-api.yoni-esim.com` | **INVALID** — cert is for `crm.yoni-tech.com` | nginx 405 Not Allowed | Broken / offline |
| `api.yoni-esim.com` | **VALID** — cert for `api.yoni-esim.com` | `{"code":401,...}` (documented error format) | **Correct API host** |
| `api.esimaccess.com` | Valid — cert for `*.esimaccess.com` | Different API format (`errorCode`/`errorMsg`) | Different platform / API version |

**Selected host**: `https://api.yoni-esim.com`

### Current Blocker: Authentication

The provider returns HTTP 401 with the documented auth-error envelope:
```json
{"code":401,"error":true,"msg":"Unauthorized","success":false}
```

Our signing implementation matches the docs verbatim. Possible causes:
1. **Credentials not yet activated** — docs say Step 2 is "log in to the client portal and initialize your appSecret"
2. **Incorrect appId or appSecret**
3. **IP restriction** — provider may have IP allowlisting enabled

**Action required**: Verify credentials are active on the provider portal at `sandbox-partner.yoni-esim.com/developers`.

---

## Summary

- Code review: **PASS** — implementation matches verified contract
- Two pre-live fixes applied (empty body serialization, 401 error handling)
- Environment: **PASS** — all infrastructure healthy
- Provider authentication: **BLOCKED** — 401 Unauthorized
- Live testing: **BLOCKED** pending credential resolution
