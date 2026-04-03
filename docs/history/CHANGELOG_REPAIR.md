> **Historical Document:** This changelog documents repairs toward the Yoni provider contract, which has since been replaced by eSIM Access.

# Provider Contract Repair Changelog

**Date**: 2026-03-31
**Scope**: eSIM Access (Yoni-eSIM) provider integration
**Source of truth**: `PROVIDER_CONTRACT_VERIFICATION.md`

---

## Repaired Mismatches

### 1. Authentication Headers

| Before (wrong)    | After (verified)     |
|-------------------|----------------------|
| `RT-AccessCode`   | `appId`              |
| `RT-RequestID`    | *(removed — not in spec)* |
| `RT-Timestamp`    | `timestamp`          |
| `RT-Signature`    | `sign`               |

**Files**: `app/providers/esim_access/auth.py`

### 2. Signature String-to-Sign

| Before (wrong)                              | After (verified)                     |
|---------------------------------------------|--------------------------------------|
| `timestamp + requestId + accessCode + body` | `appId + "&" + timestamp + "&" + path` |
| No separator                                | `&` separator                        |
| Included body and requestId                 | Body and requestId excluded          |

**Files**: `app/providers/esim_access/auth.py` — `_build_plain()`, `sign()`

### 3. Constructor Parameter Names

| Before              | After            |
|---------------------|------------------|
| `access_code`       | `app_id`         |
| `secret_key`        | `app_secret`     |

**Files**: `app/providers/esim_access/auth.py`, `app/api/deps.py`, `app/core/config.py`

### 4. Base Path and Endpoint Paths

| Before (wrong)                  | After (verified)           |
|---------------------------------|----------------------------|
| `BASE_PATH = "/api/v1/open"`   | *(removed — paths are absolute)* |
| `/api/v1/open/package/list`    | `/v1/package/e-sim/list`   |
| `/api/v1/open/order/apply`     | `/v1/order/e-sim`          |
| `/api/v1/open/order/query`     | `/v1/order/e-sim/page`     |
| `/api/v1/open/esim/data-usage` | `/v1/order/e-sim/flow`     |
| `/api/v1/open/esim/query`      | *(removed — not a real endpoint)* |
| `/api/v1/open/esim/topup`      | *(removed — undocumented)* |
| `/api/v1/open/order/cancel`    | *(removed — undocumented)* |
| `/api/v1/open/esim/suspend`    | *(removed — undocumented)* |

**Files**: `app/providers/esim_access/client.py`, `app/providers/esim_access/adapter.py`

### 5. Package List Request and Response

| Aspect         | Before (wrong)                    | After (verified)              |
|----------------|-----------------------------------|-------------------------------|
| Request body   | `{"type": "BASE"}`                | `{}` (empty)                  |
| Response shape | `data.packageList` (nested)       | `data` (flat array)           |
| Name field     | `name`                            | `packageName`                 |
| Volume field   | `volume`                          | `flow` (int, MB)              |
| Duration field | `duration`                        | `days` (string)               |
| Type field     | `type`                            | `packageType`                 |
| Currency field | `currencyCode`                    | *(not in package response)*   |
| Location field | `locationCode`                    | `mcc` (comma-separated)       |
| Country field  | *(not read)*                      | `countryEn`                   |

**Files**: `app/providers/esim_access/adapter.py` — `sync_products()`, `_map_package()`

### 6. Order Request Payload

| Aspect         | Before (wrong)                                 | After (verified)                  |
|----------------|------------------------------------------------|-----------------------------------|
| Body fields    | `packageCode`, `quantity`, `transactionId`     | `packageCode` only (`email` optional) |
| Idempotency    | Not sent to provider                           | `idempotentKey` header on request |

**Files**: `app/providers/esim_access/adapter.py` — `create_order()`

### 7. Order Response Parsing

| Aspect         | Before (wrong)                        | After (verified)              |
|----------------|---------------------------------------|-------------------------------|
| Expected fields| `orderNo`, `status`, `iccid`, `esimList` | `orderNo` only             |
| Initial status | Derived from response                 | Always `"pending"`            |
| ICCID          | Extracted from response               | `None` (arrives via webhook)  |

**Files**: `app/providers/esim_access/adapter.py` — `create_order()`

### 8. Order Query / Order List

| Aspect         | Before (wrong)                 | After (verified)                        |
|----------------|--------------------------------|-----------------------------------------|
| Endpoint       | `order/query`                  | `/v1/order/e-sim/page`                  |
| Payload        | `{"orderNo": "..."}`          | `{"current": 1, "size": 1, "orderNo": "..."}` |
| Response       | `data` as flat dict            | `data.records[...]`                     |

**Files**: `app/providers/esim_access/adapter.py` — `get_order_status()`

### 9. Data Usage Endpoint and Response

| Aspect         | Before (wrong)                        | After (verified)                    |
|----------------|---------------------------------------|-------------------------------------|
| Endpoint       | `esim/data-usage`                     | `/v1/order/e-sim/flow`              |
| Payload        | `{"iccid": "..."}`                    | `{"orderNo": "...", "iccid": "..."}` |
| Response fields| `totalVolume`, `usedVolume` (numbers) | `total`, `usage` (strings, MB)      |
| Other fields   | `esimStatus`, `daysRemaining`         | *(not in documented response)*      |

**Files**: `app/providers/esim_access/adapter.py` — `get_esim_status()`

### 10. Webhook Payload Parsing

| Aspect          | Before (wrong)                          | After (verified)                       |
|-----------------|-----------------------------------------|----------------------------------------|
| Event type      | Read from `notifyType` field            | Hardcoded `"ORDER_STATUS"` (only documented webhook) |
| Status field    | Read from `status`                      | Read from `result` (`COMPLETED`/`FAILED`) |
| Phantom fields  | `notifyType`, `transactionId`           | *(removed)*                            |
| Missing fields  | *(not read)*                            | `lpa`, `packageCode`, `packageName`, `price`, `currency` now parsed |

**Files**: `app/providers/esim_access/adapter.py` — `handle_webhook()`

### 11. Unsupported Capabilities

Topup, cancel, and suspend endpoints are not documented in the current API.
These methods now raise `ProviderCapabilityUnavailableError` (HTTP 501) instead
of attempting calls to non-existent endpoints.

**Files**: `app/providers/esim_access/adapter.py`, `app/core/errors.py`

### 12. Configuration

| Aspect          | Before                                 | After                                  |
|-----------------|----------------------------------------|----------------------------------------|
| Base URL default| `https://api.esimaccess.com`           | `https://sandbox-api.yoni-esim.com`    |
| Config field    | `esim_access_access_code`              | `esim_access_app_id`                   |
| Config field    | `esim_access_secret_key`               | `esim_access_app_secret`               |

**Files**: `app/core/config.py`, `.env.example`

---

## Test Changes

- **Rewrote** `tests/unit/core/test_auth.py` — verifies exact `appId&timestamp&path` plain string, correct header names, absence of RT-* headers
- **Rewrote** `tests/unit/providers/test_client.py` — verifies exact endpoint paths (`/v1/package/e-sim/list`, etc.), auth header presence, extra header forwarding
- **Rewrote** `tests/unit/providers/test_adapter.py` — verifies flat array parsing, real field names, order-only-returns-orderNo, pagination params, string usage fields, documented webhook fields, unsupported capability errors
- **Rewrote** `tests/contract/test_esim_access_contract.py` — enforces exact doc-sourced response shapes as executable specification
- **Updated** `tests/integration/api/test_orders.py` — reflects `status="pending"`, `iccid=None`
- **Updated** `tests/integration/api/test_webhooks.py` — uses documented webhook payload shape
- **Updated** `tests/unit/services/test_order_service.py` — reflects pending status, tests cancel raises unavailable
- **Removed** all tests asserting phantom fields (`notifyType`, `transactionId`, `esimList`, `totalVolume`, `usedVolume`, `packageList` nesting)

**Result**: 112 tests pass, 0 failures, clean lint.

---

## Remaining Blockers Requiring Provider Confirmation

| # | Item | Why it blocks |
|---|------|---------------|
| 1 | **Production base URL** | Docs only show `sandbox-api.yoni-esim.com`. The production host (`api.esimaccess.com`? `api.yoni-esim.com`?) must be confirmed with eSIM Access support. |
| 2 | **Currency in package response** | Package objects do not include a currency field. The contract price currency (account-level?) must be confirmed. Currently defaulting to empty string. |
| 3 | **Order list record fields** | The order list endpoint (`/v1/order/e-sim/page`) response `records[*]` schema is not fully documented. Fields like `iccid`, `lpa`, `result`, `status` are inferred from the webhook schema. |
| 4 | **eSIM profile query** | No dedicated eSIM query endpoint exists. `get_esim()` uses order list filtered by `iccid`. This may not return full profile data (smdp_address, matching_id). |
| 5 | **Topup / Cancel / Suspend** | Marketing FAQ mentions cancel/revoke/suspend as v1.1 features. When endpoints are published, implementations can be added. Currently raises 501. |
| 6 | **Webhook signature verification** | No documented mechanism for verifying webhook authenticity (no HMAC on inbound webhooks). Confirm with provider whether IP allowlisting or another method is available. |
| 7 | **Additional webhook types** | FAQ mentions `ESIM_STATUS`, `DATA_USAGE`, `VALIDITY_USAGE` notification types, but no payload schemas are documented. Only `ORDER_STATUS` is implemented. |
| 8 | **Usage endpoint `orderNo` requirement** | Docs show `orderNo` as required for `/v1/order/e-sim/flow`. The adapter resolves this via an extra order-list lookup by iccid, adding latency. Confirm if `iccid`-only queries are supported. |
