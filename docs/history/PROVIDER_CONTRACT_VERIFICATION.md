> **Historical Document:** This verification was against the Yoni provider. The current provider is eSIM Access. See [Contract Revalidation](CONTRACT_REVALIDATION.md) for why we pivoted.

# Provider Contract Verification Report

**Provider**: eSIM Access (Yoni-eSIM)
**Documentation sources**:
- `https://docs-yoni-tech.readme.io/reference/esim-api-quick-start` (API Quick Start + Signature)
- `https://docs-yoni-tech.readme.io/reference/esim-package-list` (Package List endpoint)
- `https://docs-yoni-tech.readme.io/reference/esim-order` (Order endpoint)
- `https://docs-yoni-tech.readme.io/reference/esim-order-list` (Order List endpoint)
- `https://docs-yoni-tech.readme.io/reference/esim-usage` (Usage endpoint)
- `https://docs-yoni-tech.readme.io/reference/esim-webhook` (Webhook)
- `https://docs-yoni-tech.readme.io/reference/esim_errors` (Error codes)
- `https://esimaccess.com/docs/what-api-authentication-method-do-you-support/`
- `https://esimaccess.com/docs/what-webhook-notifications-do-you-send/`

**Report date**: 2026-03-31

---

## 1. Authentication Headers

### Doc source

From the API Quick Start (docs-yoni-tech.readme.io/reference/esim-api-quick-start):

> All APIs require header-based authentication. Please include the following parameters in the HTTP header:

| Name        | Type   | Required | Description                          |
|-------------|--------|----------|--------------------------------------|
| `appId`     | String | yes      | Application ID assigned by platform  |
| `timestamp` | String | yes      | Current timestamp in milliseconds    |
| `sign`      | String | yes      | HMAC-SHA256 signature string         |

The Order endpoint additionally requires:

| Name             | Type   | Required | Description                          |
|------------------|--------|----------|--------------------------------------|
| `idempotentKey`  | String | yes      | Unique identifier for idempotency    |

### Implementation

File: `app/providers/esim_access/auth.py`, function `build_headers()` (line 48-59)

Headers produced:

```
RT-AccessCode  (should be: appId)
RT-RequestID   (should not exist — not in docs)
RT-Timestamp   (should be: timestamp)
RT-Signature   (should be: sign)
```

### Verdict: MISMATCH — production-blocking

Every header name is wrong:
- `RT-AccessCode` → must be `appId`
- `RT-RequestID` → does not exist in the provider spec
- `RT-Timestamp` → must be `timestamp`
- `RT-Signature` → must be `sign`

Additionally, the provider supports a native `idempotentKey` header on the order endpoint that the implementation does not send.

---

## 2. Signature Algorithm

### Doc source

From API Quick Start:

> Generate Signature: Use the assigned `appSecret` to encrypt the concatenated string with HMAC-SHA256, and convert the result into a hexadecimal string (Hex String).

Python example straight from the docs:

```python
sign = hmac.new(
    app_secret.encode("utf-8"),
    plain.encode("utf-8"),
    hashlib.sha256
).hexdigest()
```

### Implementation

File: `app/providers/esim_access/auth.py`, function `sign()` (line 39-46)

Uses `hmac.new(..., hashlib.sha256).hexdigest()`.

### Verdict: VERIFIED

The algorithm itself (HMAC-SHA256, hex output, lowercase) is correct. The key (`appSecret`) maps to our `secret_key` constructor param. The crypto primitive is right; only the input string fed to it is wrong (see next section).

---

## 3. String-to-Sign Construction

### Doc source

From API Quick Start:

> Concatenate String: Format: `appId + "&" + timestamp + "&" + path`
> - Use the `&` symbol to join each part.
> - Note: The parameter order must always be fixed as `appId -> timestamp -> path`.

Concrete example from docs:

```python
app_id = "Your app ID"
timestamp = str(int(time.time() * 1000))
path = "/v1/package/e-sim/list"
plain = f"{app_id}&{timestamp}&{path}"
```

### Implementation

File: `app/providers/esim_access/auth.py`, function `_build_sign_data()` (line 61-62)

```python
return f"{timestamp}{request_id}{self._access_code}{body}"
```

### Verdict: MISMATCH — production-blocking

| Aspect            | Docs require                         | Implementation produces                    |
|-------------------|--------------------------------------|--------------------------------------------|
| Components        | `appId`, `timestamp`, `path`         | `timestamp`, `requestId`, `accessCode`, `body` |
| Separator         | `&` between each component           | No separator (direct concatenation)        |
| Includes body?    | No                                   | Yes                                        |
| Includes path?    | Yes                                  | No                                         |
| Includes requestId?| No                                  | Yes                                        |
| Component order   | appId → timestamp → path             | timestamp → requestId → accessCode → body  |

The signed string is completely different. Every request will fail auth.

---

## 4. Timestamp Format

### Doc source

From API Quick Start:

```python
timestamp = str(int(time.time() * 1000))
```

Millisecond Unix epoch, as a string.

### Implementation

File: `app/providers/esim_access/auth.py`, function `generate_timestamp()` (line 34-37)

```python
return str(int(time.time() * 1000))
```

### Verdict: VERIFIED

Exact match.

---

## 5. Endpoint Paths

### Doc source

| Operation     | Documented URL path              | Doc page                                   |
|---------------|----------------------------------|--------------------------------------------|
| Package List  | `/v1/package/e-sim/list`         | docs-yoni-tech.readme.io/reference/esim-package-list |
| Order         | `/v1/order/e-sim`                | docs-yoni-tech.readme.io/reference/esim-order        |
| Order List    | `/v1/order/e-sim/page`           | docs-yoni-tech.readme.io/reference/esim-order-list   |
| Usage         | `/v1/order/e-sim/flow`           | docs-yoni-tech.readme.io/reference/esim-usage        |
| Topup         | **Not documented**               | —                                          |
| Cancel        | **Not documented**               | —                                          |
| Suspend       | **Not documented**               | —                                          |
| eSIM Query    | **Not documented** (use Order List + filter by iccid) | —              |

### Implementation

File: `app/providers/esim_access/client.py` line 58: `BASE_PATH = "/api/v1/open"`
File: `app/providers/esim_access/adapter.py`, various methods:

| Operation     | Implementation sends                         | Docs require                  |
|---------------|----------------------------------------------|-------------------------------|
| Package List  | `/api/v1/open/package/list`                  | `/v1/package/e-sim/list`      |
| Order         | `/api/v1/open/order/apply`                   | `/v1/order/e-sim`             |
| Order Query   | `/api/v1/open/order/query`                   | `/v1/order/e-sim/page`        |
| eSIM Query    | `/api/v1/open/esim/query`                    | Not a documented endpoint     |
| Usage         | `/api/v1/open/esim/data-usage`               | `/v1/order/e-sim/flow`        |
| Topup         | `/api/v1/open/esim/topup`                    | Not documented                |
| Cancel        | `/api/v1/open/order/cancel`                  | Not documented                |
| Suspend       | `/api/v1/open/esim/suspend`                  | Not documented                |

### Verdict: MISMATCH — production-blocking

- The base path prefix `/api/v1/open` does not exist. Actual prefix is `/v1`.
- Every endpoint suffix is wrong (e.g., `package/list` vs `package/e-sim/list`).
- Three endpoints (topup, cancel, suspend) do not appear in the current docs at all. The eSIM Access marketing site mentions cancel/revoke/suspend as v1.1 features, but they have no documented API paths or schemas.
- The "eSIM query" concept is not a separate endpoint; the order list endpoint filtered by `iccid` serves this purpose.

---

## 6. Request Methods

### Doc source

Every documented endpoint specifies:

> Request Method: POST

### Implementation

File: `app/providers/esim_access/client.py`, function `_request_with_retry()` (line 116)

```python
response = await client.post(url, content=body_str, headers=headers)
```

### Verdict: VERIFIED

All requests use POST. Correct.

---

## 7. Request Payload Schemas

### Doc source

**Package List** — no required body. The docs show an empty body (`payload = {}`). The implementation sends `{"type": "BASE"}` which is not a documented parameter.

**Order** — documented request body:

```json
{ "packageCode": "YN2602130xxxxx", "email": "[email protected]" }
```

| Field       | Required | Type   |
|-------------|----------|--------|
| packageCode | yes      | String |
| email       | no       | String |

**Order List** — documented request body:

```json
{ "current": 1, "size": 2, "orderNo": "...", "iccid": "..." }
```

| Field    | Required | Type   |
|----------|----------|--------|
| current  | yes      | Number |
| size     | yes      | Number |
| orderNo  | no       | String |
| iccid    | no       | String |

**Usage** — documented request body:

```json
{ "orderNo": "...", "iccid": "..." }
```

### Implementation

File: `app/providers/esim_access/adapter.py`

| Operation    | Implementation sends                                    | Docs require                                   |
|--------------|---------------------------------------------------------|------------------------------------------------|
| Package List | `{"type": "BASE"}` (line 47)                            | `{}` (empty body)                              |
| Order        | `{"packageCode":..., "quantity":..., "transactionId":...}` (line 60-64) | `{"packageCode":..., "email":...}` |
| Order Query  | `{"orderNo": ...}` (line 77)                            | `{"current":1, "size":10, "orderNo":...}`      |
| eSIM Query   | `{"iccid": ...}` (line 89)                              | No separate endpoint                           |
| Usage        | `{"iccid": ...}` (line 103)                             | `{"orderNo":..., "iccid":...}`                 |
| Topup        | `{"packageCode":..., "iccid":..., "transactionId":...}` | No documented endpoint                         |
| Cancel       | `{"orderNo": ...}` (line 143)                           | No documented endpoint                         |
| Suspend      | `{"iccid": ...}` (line 154)                             | No documented endpoint                         |

### Verdict: MISMATCH — production-blocking

- Order payload sends `quantity` and `transactionId` which are not documented fields. Does not send `email`.
- Package list sends `type` filter which is not documented.
- Order list/query requires pagination params `current`/`size` which the implementation does not send.
- Usage endpoint requires `orderNo` in addition to `iccid`; the implementation only sends `iccid`.

---

## 8. Response Envelope

### Doc source

From the Errors page (docs-yoni-tech.readme.io/reference/esim_errors):

**Post-authentication responses** use:

```json
{ "code": 0, "data": ..., "msg": "success" }
```

**Authentication-stage errors** use:

```json
{ "code": 401, "error": true, "msg": "Unauthorized", "success": false }
```

The `data` field varies by endpoint:
- Package List: `data` is a **direct array** of package objects
- Order: `data` is `{"orderNo": "..."}`
- Order List: `data` is `{"records": [...], "total": N}`
- Usage: `data` is `{"total": "1024", "usage": "407.00"}`

### Implementation

File: `app/providers/esim_access/client.py`, function `_handle_response()` (line 159-191)

Checks `code == 0` for success → correct.

File: `app/providers/esim_access/adapter.py`:
- Package List (line 48): reads `data.get("data", {}).get("packageList", [])` — expects `data.packageList` but docs return `data` as a flat array.
- Order (line 66): reads `data.get("data", {})` — correct structure, but field mapping is wrong (see payload schemas).
- Usage (line 104): reads `data.get("data", {})` and looks for `totalVolume`/`usedVolume` — docs return `total`/`usage` as strings.

### Verdict: PARTIAL MISMATCH — production-blocking

The `code`/`data`/`msg` envelope is correct. However:

| Aspect                  | Docs                            | Implementation reads             |
|-------------------------|---------------------------------|----------------------------------|
| Package list `data`     | Direct array `[{...}]`          | `data.packageList` (nested)      |
| Usage data fields       | `total` (string), `usage` (string) | `totalVolume`, `usedVolume` (numbers) |
| Order list              | `data.records[...]`             | `data` as flat dict              |

---

## 9. Success / Error Codes

### Doc source

From the Errors page:

| Code | Message                                          |
|------|--------------------------------------------------|
| 0    | Success                                          |
| 101  | Request is being processed, please retry shortly |
| 102  | The server is busy. Please try again later       |
| 400  | Query error                                      |
| 501  | Account does not exist                           |
| 502  | Account is inactive                              |
| 503  | IP address is not allowed                        |
| 504  | Plans does not exist                             |
| 505  | Plan price is not available                      |
| 506  | Insufficient account balance or credit           |
| 9999 | Unknown error                                    |

Authentication errors return HTTP 4xx/5xx with `{"code": 401, "error": true, ...}`.

### Implementation

File: `app/providers/esim_access/client.py` (lines 42-52, 159-191)

```python
RETRYABLE_CODES = {101, 102}
ERROR_CODE_MAP = {
    501: ProviderAuthenticationError,
    502: ProviderAuthenticationError,
    503: ProviderAuthenticationError,
    504: ProviderValidationError,
    505: ProviderValidationError,
    506: ProviderValidationError,
}
```

Code 0 = success (line 163). Code 400 mapped (line 179). Code 9999 mapped (line 182).

### Verdict: VERIFIED

The error codes, their numeric values, and the classification into retryable (101, 102) vs. terminal categories are correct. The mapping to internal error types is reasonable. The only minor gap is that HTTP-level auth errors (401) with the `"error": true` envelope shape are not explicitly handled as a distinct branch — they would fall through to the generic HTTP 4xx path, which is acceptable.

---

## 10. Webhook Existence

### Doc source

From docs-yoni-tech.readme.io/reference/esim-webhook:

> eSIM Order Webhook — Request Method: POST

The webhook exists and is configured via the client portal developer page. It fires on order completion/failure.

From esimaccess.com/docs/what-webhook-notifications-do-you-send:

> Notification types: ORDER_STATUS, ESIM_STATUS, DATA_USAGE, VALIDITY_USAGE

### Implementation

File: `app/api/v1/webhooks.py` — ingestion endpoint at `POST /v1/provider/webhooks/esim-access`
File: `app/services/webhook.py` — processes events
File: `app/providers/esim_access/adapter.py`, function `handle_webhook()` (line 164)

### Verdict: VERIFIED (webhook exists)

The provider does send webhooks. The implementation has an ingestion endpoint. However, the payload handling is wrong (see sections 11 and 12).

---

## 11. Webhook Event Names

### Doc source

The **webhook spec page** (docs-yoni-tech.readme.io/reference/esim-webhook) documents exactly **one** webhook type: the **eSIM Order Webhook**. There is no `notifyType` or `event_type` field in the payload. The `result` field carries `"COMPLETED"` or `"FAILED"`.

The **marketing FAQ page** (esimaccess.com/docs/what-webhook-notifications-do-you-send) mentions four notification types: `ORDER_STATUS`, `ESIM_STATUS`, `DATA_USAGE`, `VALIDITY_USAGE`. However, the technical API docs only document the order webhook.

### Implementation

File: `app/providers/esim_access/adapter.py`, function `handle_webhook()` (line 164-180):

```python
"event_type": payload.get("notifyType", payload.get("event_type", "UNKNOWN")),
```

File: `app/services/webhook.py`, function `_handle_event()` (line 57-62):

Branches on `ORDER_STATUS`, `ESIM_STATUS`, `DATA_USAGE`, `VALIDITY_USAGE`.

### Verdict: MISMATCH — blocks correct webhook processing

- The documented payload has no `notifyType` field. The implementation looks for `notifyType` first.
- The documented payload uses `result` (values: `COMPLETED` or `FAILED`) not `status` or `event_type`.
- Only the order completion/failure webhook is documented with a concrete schema. The other three event types (`ESIM_STATUS`, `DATA_USAGE`, `VALIDITY_USAGE`) exist as marketing concepts but have no documented payload schemas.

---

## 12. Webhook Payload Fields

### Doc source

From docs-yoni-tech.readme.io/reference/esim-webhook, the concrete payload:

```json
{
    "orderNo": "2026032516xxxxxxxxxxx",
    "currency": "4",
    "iccid": "8910010000xxxxxxxxxx",
    "lpa": "LPA:1$rsp.demo$69C32E7Dxxxxxxxx",
    "packageCode": "YN2602130xxxxxx",
    "packageName": "Malaysia, 1 Day, 1GB, 256kbps",
    "price": "9.99",
    "result": "COMPLETED"
}
```

| Field       | Type   | Description                                 |
|-------------|--------|---------------------------------------------|
| orderNo     | String | Unique order number                         |
| currency    | String | Currency code (1=RMB, 2=USD, 3=EUR, ...)   |
| iccid       | String | ICCID of the eSIM                           |
| lpa         | String | LPA activation string                       |
| packageCode | String | Package identifier                          |
| packageName | String | Package name                                |
| price       | String | Price in contract currency                  |
| result      | String | `FAILED` or `COMPLETED`                     |

Retry policy: up to 3 total attempts, retries at 3s and 6s.

### Implementation

File: `app/providers/esim_access/adapter.py`, function `handle_webhook()` (line 164-180):

Reads: `notifyType`, `orderNo`, `iccid`, `transactionId`, `status`

| Field docs provide | Implementation reads | Match? |
|-------------------|---------------------|--------|
| `orderNo`         | `orderNo`           | Yes    |
| `iccid`           | `iccid`             | Yes    |
| `result`          | `status`            | **No** — wrong field name |
| `lpa`             | not read            | Missing |
| `packageCode`     | not read            | Missing |
| `packageName`     | not read            | Missing |
| `price`           | not read            | Missing |
| `currency`        | not read            | Missing |
| (does not exist)  | `notifyType`        | **Phantom field** |
| (does not exist)  | `transactionId`     | **Phantom field** |

### Verdict: MISMATCH — blocks correct webhook processing

The implementation reads two fields that don't exist (`notifyType`, `transactionId`), misnames the status field (`status` vs `result`), and ignores six fields the provider actually sends (`lpa`, `packageCode`, `packageName`, `price`, `currency`, `result`).

---

## 13. Additional Findings: Package Response Field Mapping

### Doc source

From docs-yoni-tech.readme.io/reference/esim-package-list, the package object:

```json
{
    "packageName": "Japan, 1 Day, 500M, 256kbps",
    "packageCode": "YN26021300xxxx",
    "price": "0.5",
    "simType": "1",
    "packageType": "1",
    "mcc": "440,441",
    "country": "日本",
    "countryEn": "Japan",
    "flow": 500,
    "apn": "mobile.demo.com",
    "effectiveDays": 60,
    "operator": "Docomo / Softbank / Rakuten Mobile / KDDI",
    "days": "1"
}
```

### Implementation

File: `app/providers/esim_access/adapter.py`, function `_map_package()` (line 182-202):

| Doc field        | Type    | Implementation reads | Match? |
|------------------|---------|---------------------|--------|
| `packageName`    | String  | `name`              | **No** — wrong key |
| `packageCode`    | String  | `packageCode`       | Yes    |
| `price`          | String  | `price` (cast to float) | Partial — string in docs |
| `flow`           | Number (MB) | `volume`         | **No** — wrong key |
| `days`           | String  | `duration`          | **No** — wrong key |
| `countryEn`      | String  | not read            | Missing |
| `country`        | String  | not read            | Missing |
| `mcc`            | String  | not read            | Missing |
| `effectiveDays`  | Number  | not read            | Missing |
| `packageType`    | String  | `type`              | **No** — wrong key |
| `currencyCode`   | —       | `currencyCode`      | **No** — field does not exist; no currency field in package response |
| `locationCode`   | —       | `locationCode`      | **No** — field does not exist |

### Verdict: MISMATCH — production-blocking

Package parsing will extract zero meaningful data. `name`, `volume`, `duration`, `currencyCode`, and `locationCode` do not exist in the provider response.

---

## 14. Additional Findings: Order Response Field Mapping

### Doc source

Order response:

```json
{ "code": 0, "data": { "orderNo": "20260325162390116407xxxxxx" }, "msg": "success" }
```

The order response contains **only** `orderNo`. No `iccid`, no `status`, no `esimList`, no `transactionId`. The ICCID and LPA are delivered later via webhook or queried via the Order List endpoint.

### Implementation

File: `app/providers/esim_access/adapter.py`, function `create_order()` (line 57-74):

Reads `orderNo`, `status`, `iccid`, `esimList` from `data`.

### Verdict: MISMATCH

The implementation expects `iccid` and `status` in the order response. The provider only returns `orderNo`. The ICCID is delivered asynchronously via webhook. The implementation will set `iccid=None` (acceptable fallback) but will fail to find `status`, defaulting to `"unknown"`.

---

## 15. Additional Findings: Usage Response Field Mapping

### Doc source

```json
{ "code": 0, "data": { "total": "1024", "usage": "407.00" }, "msg": "success" }
```

Both `total` and `usage` are **strings** in MB.

### Implementation

File: `app/providers/esim_access/adapter.py`, function `get_esim_status()` (line 102-121):

Reads `totalVolume`, `usedVolume`, `esimStatus`, `daysRemaining`.

### Verdict: MISMATCH — will return null data

None of the field names match. `totalVolume`/`usedVolume`/`esimStatus`/`daysRemaining` do not exist. The docs provide `total`/`usage` only.

---

## 16. Additional Finding: Provider-Native Idempotency

### Doc source

From the order endpoint docs:

| Header Name    | Required | Description                                    |
|----------------|----------|------------------------------------------------|
| `idempotentKey`| yes      | A unique identifier for request idempotency    |

### Implementation

The implementation manages idempotency entirely on our side via Redis (file `app/core/idempotency.py`). It does **not** send the `idempotentKey` header to the provider.

### Verdict: MISMATCH — should also send provider header

The provider requires `idempotentKey` on order requests. Without it, duplicate orders may be created on the provider side even if our gateway prevents them internally.

---

# Summary: Blocking Inferences for Production Readiness

Every item below must be resolved before this service can make a single successful API call.

| # | Area | Specific Issue | File to Fix |
|---|------|---------------|-------------|
| 1 | **Auth header names** | `RT-AccessCode`/`RT-RequestID`/`RT-Timestamp`/`RT-Signature` must become `appId`/`timestamp`/`sign`. Remove `RT-RequestID` entirely. | `app/providers/esim_access/auth.py` → `build_headers()` |
| 2 | **String-to-sign** | Must be `appId + "&" + timestamp + "&" + path`, not `timestamp + requestId + accessCode + body`. The `sign()` method needs a `path` parameter, not `request_id`/`body`. | `app/providers/esim_access/auth.py` → `_build_sign_data()`, `sign()` |
| 3 | **Base path** | `BASE_PATH = "/api/v1/open"` must be removed. Paths start with `/v1/...` directly. | `app/providers/esim_access/client.py` line 58 |
| 4 | **Endpoint paths** | `package/list` → `package/e-sim/list`; `order/apply` → `order/e-sim`; `order/query` → `order/e-sim/page`; `esim/data-usage` → `order/e-sim/flow`. Remove `esim/query` (use order list filtered by iccid). | `app/providers/esim_access/adapter.py` — every method |
| 5 | **Package response parsing** | `packageList` nested key doesn't exist; `data` is a direct array. Field names: `packageName` not `name`, `flow` not `volume`, `days` not `duration`, `packageType` not `type`. No `currencyCode` or `locationCode` fields — use `countryEn` and `mcc`. | `app/providers/esim_access/adapter.py` → `sync_products()`, `_map_package()` |
| 6 | **Order request payload** | Remove `quantity` and `transactionId`. Add optional `email`. | `app/providers/esim_access/adapter.py` → `create_order()` |
| 7 | **Order response parsing** | Only `orderNo` is returned. No `iccid`, `status`, or `esimList`. ICCID arrives via webhook. | `app/providers/esim_access/adapter.py` → `create_order()` |
| 8 | **Order query** | Must send `current`/`size` pagination params. Response is in `data.records[...]`. | `app/providers/esim_access/adapter.py` → `get_order_status()` |
| 9 | **Usage response parsing** | Fields are `total`/`usage` (strings, MB), not `totalVolume`/`usedVolume`. No `esimStatus` or `daysRemaining`. | `app/providers/esim_access/adapter.py` → `get_esim_status()` |
| 10 | **Webhook payload** | No `notifyType` or `transactionId` fields. Status is in `result` (values: `COMPLETED`/`FAILED`). Must read `lpa`, `packageCode`, `packageName`, `price`, `currency`. | `app/providers/esim_access/adapter.py` → `handle_webhook()` |
| 11 | **Provider idempotentKey header** | Must send `idempotentKey` header on order requests. | `app/providers/esim_access/client.py` or `adapter.py` |
| 12 | **Topup/Cancel/Suspend endpoints** | Not documented in current API. Must either remove or guard behind feature flags pending confirmation from eSIM Access support. | `app/providers/esim_access/adapter.py` |
| 13 | **Sandbox vs Production URL** | Docs show `sandbox-api.yoni-esim.com`. Production URL (likely `api.esimaccess.com` or `api.yoni-esim.com`) must be confirmed with provider. | `app/core/config.py`, `app/providers/esim_access/client.py` |
