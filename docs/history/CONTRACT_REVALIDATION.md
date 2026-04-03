# Contract Re-Validation Report

**Date**: 2026-03-31  
**Purpose**: Re-baseline the eSIM Access provider integration against `docs.esimaccess.com` (the user's actual source of truth), and identify all mismatches introduced by the prior Yoni-based repair.

---

## Executive Summary

The prior "repair pass" used `docs-yoni-tech.readme.io` as its source of truth and rewrote the provider integration toward a **completely different API contract** (Yoni eSIM). The user's actual provider account is at **console.esimaccess.com** and uses the **eSIM Access public API** at `api.esimaccess.com`. These are two different API contracts with different authentication, endpoints, field names, and response envelopes. The Yoni-based repair is the root cause of the persistent 401 errors.

**Verdict: The current implementation is fundamentally wrong. It must be reverted to the eSIM Access contract.**

---

## Sources Consulted

| Source | URL | Trust Level |
|--------|-----|-------------|
| User-provided endpoints | `/api/v1/open/esim/order`, `/esim/query`, `/esim/topup` | **Primary** |
| eSIM Access help center | `esimaccess.com/docs/` | **Primary** |
| eSIM Access API docs portal | `docs.esimaccess.com` | **Primary** (JS-rendered, partial extraction) |
| eSIM Access "Making first API call" walkthrough | `esimaccess.com/making-the-first-api-call/` | **Primary** |
| eSIM Access "Making a purchase" walkthrough | `esimaccess.com/making-an-esim-purchase-with-the-api/` | **Primary** |
| eSIM Access "Top Up" walkthrough | `esimaccess.com/esim-top-up-with-the-api` | **Primary** (contains verbatim JSON) |
| eSIM Access "Cancel" walkthrough | `esimaccess.com/making-an-api-cancel-request` | **Primary** |
| eSIM Access webhook docs | `esimaccess.com/webhook-test-form/` | **Primary** |
| eSIM Access Google Apps Script wrapper | `esimaccess.com/google-apps-script-api-wrapper` | **Secondary** (confirms RT-AccessCode) |
| Web search synthesized results | Multiple | **Secondary** (cross-referenced) |
| Yoni tech docs (used by prior repair) | `docs-yoni-tech.readme.io` | **UNTRUSTED for this account** |

---

## 1. Authentication — Side-by-Side Comparison

### eSIM Access Public Contract (CORRECT)

| Header | Description |
|--------|-------------|
| `RT-AccessCode` | AccessCode from console.esimaccess.com developer page |
| `RT-RequestID` | Unique UUID per request |
| `RT-Timestamp` | Current time in milliseconds since epoch |
| `RT-Signature` | HMAC-SHA256 signature, **uppercase hex** |

**Signature algorithm:**
```
signData = timestamp + requestId + accessCode + body
signature = HMAC-SHA256(secretKey, signData).hex().toUpperCase()
```
- `body` = JSON string of request body (empty string `""` for GET or empty body)
- No separators between components
- Output is **uppercase** hex

**Credentials**: `AccessCode` + `secretKey` from `console.esimaccess.com/developer/index`

### Current Implementation (WRONG — Yoni contract)

| Header | Description |
|--------|-------------|
| `appId` | Application ID |
| `timestamp` | Millisecond timestamp |
| `sign` | HMAC-SHA256 signature, lowercase hex |

**Signature algorithm:**
```
plain = appId + "&" + timestamp + "&" + path
sign = HMAC-SHA256(appSecret, plain).hexdigest()
```
- Uses `&` separators
- Signs the URL path, not the body
- No requestId
- Output is **lowercase** hex

### Mismatches

| Aspect | eSIM Access (correct) | Current code (wrong) | Impact |
|--------|----------------------|---------------------|--------|
| Header names | `RT-AccessCode`, `RT-RequestID`, `RT-Timestamp`, `RT-Signature` | `appId`, `timestamp`, `sign` | **Auth fails — 401** |
| Credential names | `AccessCode`, `secretKey` | `app_id`, `app_secret` | Config mismatch |
| Sign input | `timestamp + requestId + accessCode + body` | `appId + "&" + timestamp + "&" + path` | **Signature invalid** |
| Sign includes body | Yes | No | **Signature invalid** |
| Sign includes requestId | Yes (UUID) | No | **Signature invalid** |
| Sign includes path | No | Yes | **Signature invalid** |
| Separators | None (concatenation) | `&` | **Signature invalid** |
| Output format | Uppercase hex | Lowercase hex | **Signature invalid** |

**This alone explains the 401 errors.**

---

## 2. Base URL

| Aspect | eSIM Access (correct) | Current code (wrong) |
|--------|----------------------|---------------------|
| Base URL | `https://api.esimaccess.com` | `https://api.yoni-esim.com` (in .env) / `https://sandbox-api.yoni-esim.com` (default) |
| Console | `console.esimaccess.com` | N/A |

---

## 3. Endpoint Paths — Side-by-Side Comparison

### eSIM Access Public Contract (CORRECT)

Base path: `/api/v1/open`

| Operation | Full Path (from user + docs) |
|-----------|------------------------------|
| Package List | `/api/v1/open/package/list` (inferred from Postman collection structure) |
| Order (create) | `/api/v1/open/esim/order` (user-confirmed) |
| Query (order/eSIM) | `/api/v1/open/esim/query` (user-confirmed) |
| Top-Up | `/api/v1/open/esim/topup` (user-confirmed) |
| Cancel | `/api/v1/open/esim/cancel` (inferred from cancel walkthrough) |
| Balance | `/api/v1/open/merchant/balance` (inferred from "Get Merchant Balance" name) |

### Current Implementation (WRONG — Yoni paths)

| Operation | Implemented Path |
|-----------|-----------------|
| Package List | `/v1/package/e-sim/list` |
| Order (create) | `/v1/order/e-sim` |
| Order List | `/v1/order/e-sim/page` |
| Usage | `/v1/order/e-sim/flow` |
| Top-Up | ❌ disabled |
| Cancel | ❌ disabled |

### Mismatches

| Operation | eSIM Access (correct) | Current code (wrong) |
|-----------|----------------------|---------------------|
| Package List | `/api/v1/open/package/list` | `/v1/package/e-sim/list` |
| Order | `/api/v1/open/esim/order` | `/v1/order/e-sim` |
| Query | `/api/v1/open/esim/query` | `/v1/order/e-sim/page` |
| Top-Up | `/api/v1/open/esim/topup` | ❌ disabled |
| Cancel | `/api/v1/open/esim/cancel` (probable) | ❌ disabled |
| Usage | likely via `/api/v1/open/esim/query` fields | `/v1/order/e-sim/flow` |
| Balance | `/api/v1/open/merchant/balance` (probable) | ❌ not implemented |

**Every single endpoint path is wrong.**

---

## 4. Response Envelope

### eSIM Access (CORRECT)
```json
{
    "errorCode": null,
    "errorMsg": null,
    "success": true,
    "obj": { ... }
}
```
- Success indicator: `success` field (boolean)
- Data location: `obj` field
- Error info: `errorCode` + `errorMsg`

### Current Implementation (WRONG)
```json
{
    "code": 0,
    "msg": "",
    "data": { ... }
}
```
- Success indicator: `code == 0`
- Data location: `data` field
- Error info: numeric `code` + `msg`

### Mismatches

| Aspect | eSIM Access (correct) | Current code (wrong) |
|--------|----------------------|---------------------|
| Success check | `success == true` | `code == 0` |
| Data field | `obj` | `data` |
| Error field | `errorCode` / `errorMsg` | `code` / `msg` |

**All response parsing is broken.**

---

## 5. Package List Response

### eSIM Access (CORRECT) — verbatim from top-up walkthrough
```json
{
    "success": true,
    "obj": {
        "packageList": [
            {
                "packageCode": "TOPUP_CKH491",
                "name": "North America 1GB 7Days",
                "price": 70000,
                "currencyCode": "USD",
                "volume": 1073741824,
                "unusedValidTime": 30,
                "duration": 7,
                "durationUnit": "DAY",
                "location": "US,CA",
                "description": "North America 1GB 7Days",
                "activeType": 1
            }
        ]
    }
}
```

### Current Implementation (WRONG)
Reads `data` (flat array), with fields: `packageName`, `flow`, `days`, `packageType`, `countryEn`, `mcc`

### Mismatches

| Aspect | eSIM Access (correct) | Current code (wrong) |
|--------|----------------------|---------------------|
| Location in response | `obj.packageList[]` | `data[]` (flat) |
| Name field | `name` | `packageName` |
| Volume field | `volume` (bytes) | `flow` (MB) |
| Volume unit | Bytes (e.g. 1073741824 = 1GB) | MB |
| Duration field | `duration` (number) | `days` (string) |
| Duration unit field | `durationUnit` ("DAY") | *(missing)* |
| Price format | Integer (÷10000 = USD) | Float |
| Currency field | `currencyCode` | *(empty string)* |
| Location field | `location` ("US,CA") | `mcc` |
| Description field | `description` | *(missing)* |
| Active type field | `activeType` | *(missing)* |
| Unused valid time | `unusedValidTime` | *(missing)* |
| Country field | *(not in package)* | `countryEn` |
| Package type | *(not observed)* | `packageType` |

---

## 6. Order Request

### eSIM Access (CORRECT) — from purchase walkthrough
```json
{
    "packageCode": "...",
    "price": 70000,
    "amount": 70000,
    "transactionId": "unique_id"
}
```
- `price`: from package list (integer, ÷10000 = USD)
- `amount`: total cost (same as price for quantity 1)
- `transactionId`: user-generated unique string

### Current Implementation (WRONG)
```json
{
    "packageCode": "..."
}
```
Plus `idempotentKey` as a custom HTTP header.

### Mismatches

| Aspect | eSIM Access (correct) | Current code (wrong) |
|--------|----------------------|---------------------|
| `price` field | Required | ❌ Missing |
| `amount` field | Required | ❌ Missing |
| `transactionId` field | In body | ❌ Missing (was `idempotentKey` header) |
| Idempotency mechanism | `transactionId` in body | `idempotentKey` HTTP header |

---

## 7. Order Response

### eSIM Access (CORRECT)
Returns `orderNo` on success (from purchase walkthrough):
```json
{
    "success": true,
    "obj": {
        "orderNo": "B25012220580005"
    }
}
```

### Current Implementation
Reads `data.orderNo` → **wrong field path** (should be `obj.orderNo`)

---

## 8. Query (Order/eSIM status)

### eSIM Access (CORRECT) — from purchase walkthrough
Request:
```json
{
    "orderNo": "B25012220580005"
}
```
Response includes eSIM details:
```json
{
    "success": true,
    "obj": {
        "esimList": [
            {
                "iccid": "8943108170005579276",
                "smsStatus": 1,
                "msisdn": "4367844378927",
                "packageList": [...]
            }
        ]
    }
}
```

### Current Implementation (WRONG)
- Uses `/v1/order/e-sim/page` with pagination params `{"current": 1, "size": 1, "orderNo": "..."}`
- Reads `data.records[]`

### Mismatches

| Aspect | eSIM Access (correct) | Current code (wrong) |
|--------|----------------------|---------------------|
| Endpoint | `/api/v1/open/esim/query` | `/v1/order/e-sim/page` |
| Request | `{"orderNo": "..."}` | `{"current": 1, "size": 1, "orderNo": "..."}` |
| Response | `obj.esimList[]` with iccid, packageList, etc. | `data.records[]` |

---

## 9. Top-Up

### eSIM Access (CORRECT) — verbatim from top-up walkthrough
Request:
```json
{
    "iccid": "89852245280001354019",
    "packageCode": "TOPUP_CKH491",
    "transactionId": "test_top_up_TOPUP_CKH491_05",
    "amount": 70000
}
```
Response:
```json
{
    "success": true,
    "obj": {
        "transactionId": "fb9b22193f3c45aab4f052efbc878f30",
        "iccid": "89852245280001354019",
        "expiredTime": "2023-08-24T17:01:37+0000",
        "totalVolume": 5368709120,
        "totalDuration": 35,
        "orderUsage": 907415004
    }
}
```

### Current Implementation
❌ Raises `ProviderCapabilityUnavailableError` — top-up is documented and supported!

---

## 10. Cancel

### eSIM Access (CORRECT) — from cancel walkthrough
Request: includes `iccid` in body  
Response: success confirmation, eSIM status changes to `CANCELED`

### Current Implementation
❌ Raises `ProviderCapabilityUnavailableError` — cancel is documented and supported!

---

## 11. Webhooks

### eSIM Access (CORRECT) — from webhook test form

**Notification types:**
- `ORDER_STATUS` – eSIM(s) ready for download
- `ESIM_STATUS` – eSIM is in use
- `DATA_USAGE` – Data is 100MB or less
- `VALIDITY_USAGE` – Validity is 1 day

**Fields** (from webhook test form):
- `orderNo`
- `ICCID` (uppercase in test form)
- `transactionId` (note: appears as `transactonId` in test form — possible typo)

### Current Implementation (WRONG)
- Hardcodes `event_type = "ORDER_STATUS"` only
- Reads `result` field (`COMPLETED`/`FAILED`) — **not confirmed in eSIM Access docs**
- Reads `iccid` (lowercase) — may need to check `ICCID` (uppercase)
- Reads `lpa`, `packageCode`, `packageName`, `price`, `currency` — **not confirmed for eSIM Access**
- Does NOT read `transactionId` — **this IS a documented field**

---

## 12. Configuration Field Names

| Aspect | eSIM Access terminology | Current config |
|--------|------------------------|----------------|
| Credential 1 | `AccessCode` | `esim_access_app_id` |
| Credential 2 | `secretKey` | `esim_access_app_secret` |
| Env var 1 | `ESIM_ACCESS_ACCESS_CODE` | `ESIM_ACCESS_APP_ID` |
| Env var 2 | `ESIM_ACCESS_SECRET_KEY` | `ESIM_ACCESS_APP_SECRET` |

The actual credential **values** in `.env` appear to have been obtained from console.esimaccess.com, but the field names are wrong.

---

## 13. Capabilities Comparison

| Capability | eSIM Access docs | Current implementation |
|------------|-----------------|----------------------|
| Package List | ✅ Documented | ❌ Wrong endpoint + response parsing |
| Order | ✅ Documented | ❌ Wrong endpoint + missing required fields |
| Query | ✅ Documented | ❌ Wrong endpoint + wrong response parsing |
| Top-Up | ✅ Documented with verbatim JSON | ❌ Disabled (ProviderCapabilityUnavailableError) |
| Cancel | ✅ Documented with walkthrough | ❌ Disabled (ProviderCapabilityUnavailableError) |
| Balance | ✅ Documented | ❌ Not implemented |
| Webhooks | ✅ 4 types documented | ⚠️ Partially implemented, likely wrong field mapping |
| Suspend | ❓ Not clearly documented | ❌ Disabled |

---

## 14. Account Identification

**Evidence that the user's account uses the eSIM Access public contract:**

1. User explicitly stated: "My source of truth is docs.esimaccess.com"
2. User provided exact eSIM Access endpoint paths: `/api/v1/open/esim/order`, `/query`, `/topup`
3. User references "AccessCode and secretKey from the eSIM Access console"
4. Credentials in `.env` were obtained from `console.esimaccess.com`
5. The `api.yoni-esim.com` host (current implementation) returned 401 with these credentials
6. The `api.esimaccess.com` host is confirmed by multiple eSIM Access articles

**Conclusion: The account uses the eSIM Access public contract with `RT-*` auth headers, NOT the Yoni `appId/sign` contract.**

---

## 15. Root Cause of 401 Errors

The previous repair:
1. Changed authentication from `RT-AccessCode/RT-Signature` to `appId/sign` → **wrong headers**
2. Changed base URL from `api.esimaccess.com` to `api.yoni-esim.com` → **wrong host**
3. Changed sign string from `timestamp+requestId+accessCode+body` to `appId&timestamp&path` → **wrong signature**
4. Changed endpoint paths from `/api/v1/open/...` to `/v1/...` → **wrong paths**
5. Changed response envelope from `success/obj` to `code/data` → **wrong parsing**

The user's credentials are valid eSIM Access credentials. Sending them with Yoni headers to a Yoni host produces 401 because they don't exist in the Yoni system.

---

## 16. LIVE VERIFICATION RESULTS

All items below were verified by real API calls on 2026-03-31 using the user's credentials against `api.esimaccess.com`.

### Authentication: VERIFIED
- `RT-AccessCode` + `RT-RequestID` + `RT-Timestamp` + `RT-Signature` → **200 OK**
- Yoni `appId`/`sign` headers → **"Req Header:[RT-AccessCode] is null"** (rejected)
- Sign string: `timestamp + requestId + accessCode + body` → **works**
- Uppercase hex output → **works**

### Endpoint Paths: ALL VERIFIED

| Endpoint | Path | Status | Notes |
|----------|------|--------|-------|
| Package List | `/api/v1/open/package/list` | ✅ 200 | Returns 2590 packages |
| Order | `/api/v1/open/esim/order` | ✅ Auth OK | Validation: needs `transactionId` + `packageInfoList` |
| Query | `/api/v1/open/esim/query` | ✅ 200 | Needs `pager: {pageNum, pageSize}` (pageSize 5-500) |
| Top-Up | `/api/v1/open/esim/topup` | ✅ Auth OK | Needs `packageCode`, `transactionId`, `iccid` |
| Cancel | `/api/v1/open/esim/cancel` | ✅ Auth OK | Needs `iccid` or `esimTranNo` |
| Balance | `/api/v1/open/balance/query` | ✅ 200 | Returns `{balance: 500000}` ($50.00) |
| Yoni paths (`/v1/...`) | `/v1/package/e-sim/list` etc. | ❌ 404 | Do not exist |

### Response Envelope: VERIFIED
```json
{
    "success": true,
    "errorCode": "0",
    "errorMsg": null,
    "obj": { ... }
}
```
Error responses: `errorCode` is a string like `"000105"`, `"310241"`, etc.

### Package List Response: VERIFIED (verbatim from live call)
```json
{
    "packageCode": "CKH002",
    "slug": "ES_3_30",
    "name": "Spain 3GB 30Days",
    "price": 18000,
    "currencyCode": "USD",
    "volume": 3221225472,
    "smsStatus": 0,
    "dataType": 1,
    "unusedValidTime": 180,
    "duration": 30,
    "durationUnit": "DAY",
    "location": "ES",
    "locationCode": "ES",
    "description": "Spain 3GB 30Days",
    "activeType": 2,
    "favorite": false,
    "retailPrice": 36000,
    "speed": "3G/4G/5G",
    "ipExport": "NL/FR",
    "supportTopUpType": 2,
    "fupPolicy": "",
    "locationNetworkList": [...]
}
```
- Price unit: integer, divide by 10000 for USD (18000 = $1.80)
- Volume unit: bytes (3221225472 = 3GB)
- Nested under `obj.packageList[]`

### Order Request Schema: VERIFIED BY VALIDATION ERRORS
```json
{
    "transactionId": "unique_string",      // REQUIRED
    "packageInfoList": [                    // REQUIRED, 1-100 items
        {
            "packageCode": "CKH511",       // REQUIRED
            "count": 1                     // REQUIRED (batch quantity)
        }
    ]
}
```
NOTE: This differs from the 2023 walkthrough which showed `{packageCode, price, amount, transactionId}`. The API has apparently been updated to use `packageInfoList` array format with batch support.

### Query Response Schema: VERIFIED
```json
{
    "success": true,
    "errorCode": "0",
    "obj": {
        "esimList": [...],
        "pager": {"pageSize": 5, "pageNum": 1, "total": 0}
    }
}
```

### Account Balance: VERIFIED
- Path: `/api/v1/open/balance/query`
- Balance: 500000 ($50.00 USD)

### Georgia Packages Found: 19 packages
Cheapest:
- `PJCB7UMFE` — Georgia 500MB/Day — $0.90
- `P1X57VWMR` — Georgia 1GB/Day FUP1Mbps — $0.90
- `PYA78QW9K` — Georgia 1GB/Day — $1.40
- `CKH511` — Georgia 1GB 7Days — $1.50

### Items Still Needing Post-Order Verification

| # | Item | Status |
|---|------|--------|
| 1 | Order response shape (what fields does `obj` contain after successful order?) | Needs real order |
| 2 | Query response `esimList[]` field details (iccid, lpa, smdpAddress, etc.) | Needs real order |
| 3 | Webhook payload exact field names and casing | Needs real webhook |
| 4 | Whether `price` is needed in `packageInfoList` items | Seems optional based on probe |
| 5 | Top-up: whether `amount` is still required | Needs real eSIM to test |

---

## 17. Recommended Next Steps

### Step 1: Rewrite provider integration ← CURRENT
Auth is proven. Now update:
- Auth module: `RT-*` headers, `timestamp+requestId+accessCode+body` sign string, uppercase hex
- Config: rename fields back to `access_code`/`secret_key`, base URL to `api.esimaccess.com`
- Client: response envelope `success`/`obj` instead of `code`/`data`
- Adapter: all endpoint paths to `/api/v1/open/...`, correct field mappings
- Order: `transactionId` + `packageInfoList` body format
- Query: `pager` object required
- Re-enable top-up and cancel
- Add balance endpoint support

### Step 2: Resume live validation
Continue from Phase 2 (catalog discovery) with the corrected contract.

---

## Appendix: Credential Values in .env

The credentials currently stored as `ESIM_ACCESS_APP_ID` and `ESIM_ACCESS_APP_SECRET` are the `AccessCode` and `secretKey` from console.esimaccess.com. They are confirmed working. The env var names should be updated to `ESIM_ACCESS_ACCESS_CODE` and `ESIM_ACCESS_SECRET_KEY` for clarity.
