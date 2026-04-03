# eSIM Access Contract Rewrite Changelog

**Date**: 2026-03-31  
**Scope**: Complete revert of Yoni-based contract; rewrite to verified eSIM Access public API  
**Source of truth**: `CONTRACT_REVALIDATION.md` (all items live-verified against `api.esimaccess.com`)

---

## Root Cause

The prior "repair pass" used `docs-yoni-tech.readme.io` as its source. This was a **different API** from the user's actual provider account at `console.esimaccess.com`. Every aspect of the integration — auth, endpoints, response parsing, field names — was wrong, causing persistent 401 errors.

---

## Changes Made

### 1. Authentication (`app/providers/esim_access/auth.py`) — FULL REWRITE

| Aspect | Before (Yoni — wrong) | After (eSIM Access — correct) |
|--------|----------------------|-------------------------------|
| Header 1 | `appId` | `RT-AccessCode` |
| Header 2 | *(none)* | `RT-RequestID` (UUID) |
| Header 3 | `timestamp` | `RT-Timestamp` |
| Header 4 | `sign` | `RT-Signature` |
| Sign input | `appId + "&" + timestamp + "&" + path` | `timestamp + requestId + accessCode + body` |
| Separators | `&` | None (direct concatenation) |
| Body in sign | No | **Yes** |
| RequestID in sign | No | **Yes** |
| Path in sign | Yes | No |
| Output case | lowercase hex | **UPPERCASE hex** |
| Constructor | `app_id, app_secret` | `access_code, secret_key` |

### 2. HTTP Client (`app/providers/esim_access/client.py`) — FULL REWRITE

| Aspect | Before | After |
|--------|--------|-------|
| Default base URL | `https://sandbox-api.yoni-esim.com` | `https://api.esimaccess.com` |
| Response success check | `code == 0` | `success == true` |
| Data field | `data` | `obj` |
| Error field | `code` (int) + `msg` | `errorCode` (string) + `errorMsg` |
| Auth headers built with | `path` | `body` (JSON string) |
| `extra_headers` param | Supported | Removed (not needed — transactionId goes in body) |

### 3. Provider Adapter (`app/providers/esim_access/adapter.py`) — FULL REWRITE

| Operation | Before (Yoni path) | After (eSIM Access path) |
|-----------|-------------------|--------------------------|
| Package List | `/v1/package/e-sim/list` | `/api/v1/open/package/list` |
| Order | `/v1/order/e-sim` | `/api/v1/open/esim/order` |
| Query | `/v1/order/e-sim/page` | `/api/v1/open/esim/query` |
| Top-Up | ❌ disabled | `/api/v1/open/esim/topup` ✅ |
| Cancel | ❌ disabled | `/api/v1/open/esim/cancel` ✅ |
| Balance | ❌ not implemented | `/api/v1/open/balance/query` ✅ |
| Usage | `/v1/order/e-sim/flow` | Via query response fields |
| Suspend | ❌ disabled | ❌ disabled (not documented) |

#### Package List Parsing

| Aspect | Before | After |
|--------|--------|-------|
| Data location | `data[]` (flat array) | `obj.packageList[]` |
| Name field | `packageName` | `name` |
| Volume field | `flow` (MB) | `volume` (bytes, ÷1048576) |
| Duration field | `days` (string) | `duration` (number) |
| Price field | `price` (float) | `price` (int, ÷10000 = USD) |
| Currency field | *(empty)* | `currencyCode` |
| Location field | `mcc` | `location` / `locationCode` |
| Country field | `countryEn` | Derived from `location` |

#### Order Request

| Aspect | Before | After |
|--------|--------|-------|
| Body | `{packageCode}` | `{transactionId, packageInfoList: [{packageCode, count}]}` |
| Idempotency | `idempotentKey` HTTP header | `transactionId` in body |
| Batch support | No | Yes (via `count` field) |

#### Order Response

| Aspect | Before | After |
|--------|--------|-------|
| Order number | `data.orderNo` | `obj.orderNo` |

#### Query

| Aspect | Before | After |
|--------|--------|-------|
| Request | `{current, size, orderNo}` | `{orderNo, pager: {pageNum, pageSize}}` |
| `pageSize` range | No constraint | 5-500 (provider-enforced) |
| Response | `data.records[]` | `obj.esimList[]` |

#### Re-enabled: Top-Up

| Aspect | Value |
|--------|-------|
| Endpoint | `/api/v1/open/esim/topup` |
| Request | `{iccid, packageCode, transactionId}` |
| Status | Verified by live probe (auth succeeds, needs real iccid) |

#### Re-enabled: Cancel

| Aspect | Value |
|--------|-------|
| Endpoint | `/api/v1/open/esim/cancel` |
| Request | `{iccid}` or `{esimTranNo}` |
| Status | Verified by live probe (auth succeeds, needs real iccid) |

#### New: Balance

| Aspect | Value |
|--------|-------|
| Endpoint | `/api/v1/open/balance/query` |
| Response | `obj.balance` (int, ÷10000 = USD) |
| Status | Verified by live call: balance = 500000 ($50.00) |

### 4. Configuration

| File | Before | After |
|------|--------|-------|
| `config.py` | `esim_access_app_id`, `esim_access_app_secret` | `esim_access_access_code`, `esim_access_secret_key` |
| `config.py` | Default URL: `sandbox-api.yoni-esim.com` | Default URL: `api.esimaccess.com` |
| `.env` | `ESIM_ACCESS_APP_ID`, `ESIM_ACCESS_APP_SECRET` | `ESIM_ACCESS_ACCESS_CODE`, `ESIM_ACCESS_SECRET_KEY` |
| `.env` | `ESIM_ACCESS_BASE_URL=api.yoni-esim.com` | `ESIM_ACCESS_BASE_URL=api.esimaccess.com` |
| `deps.py` | `app_id=`, `app_secret=` | `access_code=`, `secret_key=` |
| `conftest.py` | `ESIM_ACCESS_APP_ID`, `ESIM_ACCESS_APP_SECRET` | `ESIM_ACCESS_ACCESS_CODE`, `ESIM_ACCESS_SECRET_KEY` |

### 5. Webhook Parsing

| Aspect | Before | After |
|--------|--------|-------|
| Event type | Hardcoded `ORDER_STATUS` | Read from `notifyType` (fallback `ORDER_STATUS`) |
| ICCID field | `iccid` (lowercase) | `ICCID` (uppercase) with lowercase fallback |
| Transaction ID | Not read | `transactionId` (documented field) |
| Other fields | `lpa, packageCode, packageName, price, currency, result` | Same — kept conservatively |

---

## Test Changes

- **Rewrote** `tests/unit/core/test_auth.py` — 16 tests: RT-* headers, `timestamp+requestId+accessCode+body` sign string, uppercase hex, no Yoni headers
- **Rewrote** `tests/unit/providers/test_client.py` — 15 tests: `/api/v1/open/...` paths, `success`/`obj` envelope, string error codes, RT-* header presence
- **Rewrote** `tests/unit/providers/test_adapter.py` — 23 tests: `obj.packageList` parsing, price ÷10000, volume ÷1MB, `transactionId + packageInfoList` order body, `pager` in query, topup/cancel enabled, balance endpoint, webhook ICCID uppercase
- **Rewrote** `tests/contract/test_esim_access_contract.py` — 9 tests: verbatim live API shapes, Georgia package, order/query/topup/cancel/suspend contracts

**Result: 108 tests pass, 0 failures.**

---

## Remaining Items Needing Live Verification

| # | Item | Status |
|---|------|--------|
| 1 | Order response — exact fields in `obj` after successful paid order | Needs real order |
| 2 | Query response — full `esimList[]` record fields (iccid, lpa, ac, smdpAddress, esimStatus, etc.) | Needs real order |
| 3 | Webhook — exact payload field names and casing in real delivery | Needs real webhook |
| 4 | Top-up — whether `amount` is required in addition to `packageCode` | Needs real eSIM |
| 5 | Cancel — confirm `iccid` vs `esimTranNo` field name preference | Needs real eSIM |
| 6 | eSIM status field values — exact enum strings (GOT_RESOURCE, IN_USE, etc.) | Needs real order |
| 7 | Usage data — whether query response includes totalVolume/orderUsage or separate endpoint | Needs real order |
