# Provider Integration Notes — eSIM Access

## Source of Truth

- **Documentation**: [docs.esimaccess.com](https://docs.esimaccess.com)
- **API Base URL**: `https://api.esimaccess.com`
- **Console**: `console.esimaccess.com/developer/index`

## Authentication

| Header | Value |
|--------|-------|
| `RT-AccessCode` | Access code from console |
| `RT-RequestID` | UUID (unique per request) |
| `RT-Timestamp` | Unix milliseconds |
| `RT-Signature` | HMAC-SHA256 uppercase hex |

**Sign string**: `timestamp + requestId + accessCode + jsonBody` (concatenated, no separators)

**Signature**: `HMAC-SHA256(secretKey, signString).hexdigest().upper()`

## API Endpoints

All endpoints use POST with JSON bodies.

| Endpoint | Purpose |
|----------|---------|
| `/api/v1/open/package/list` | Package catalog |
| `/api/v1/open/esim/order` | Create order |
| `/api/v1/open/esim/query` | Query order/eSIM details (paginated) |
| `/api/v1/open/esim/topup` | Top up existing eSIM |
| `/api/v1/open/esim/cancel` | Cancel unused eSIM |
| `/api/v1/open/balance/query` | Account balance |

## Response Envelope

```json
{
  "success": true,
  "errorCode": "0",
  "errorMsg": null,
  "obj": { ... }
}
```

## Key Quirks

### Price Format
Prices are integers in **1/10000 USD**. Example: `9000` = $0.90.

### Volume Format
Data volumes are in **bytes**. Example: `1073741824` = 1 GB.

### Query Pagination
The query endpoint requires a `pager` object:
```json
{"orderNo": "...", "pager": {"pageNum": 1, "pageSize": 500}}
```
`pageSize` must be between 5 and 500.

### Order Response
The order endpoint returns only `orderNo` in the response. ICCID and eSIM details are available via the query endpoint.

### Instant Fulfillment
Orders for most packages are fulfilled instantly — the provider returns `esimStatus: GOT_RESOURCE` on the first query. The gateway's post-order sync handles this by querying immediately after order placement.

## Verified Live Response Shape (from real order)

```json
{
  "esimTranNo": "26040109460026",
  "orderNo": "B26040109460024",
  "transactionId": "6ffdae4a-baf9-40f4-bf2d-f1a206b181a4",
  "iccid": "8910300000040030312",
  "imsi": "310840115441965",
  "ac": "LPA:1$rsp-eu.simlessly.com$20FDE2B61DDD4DEF9CBE89C55EADFC22",
  "qrCodeUrl": "https://p.qrsim.net/0f0a6ce01d9643b690a7b2046159331d.png",
  "shortUrl": "https://p.qrsim.net/0f0a6ce01d9643b690a7b2046159331d",
  "smdpStatus": "RELEASED",
  "esimStatus": "GOT_RESOURCE",
  "pin": "7668",
  "puk": "72330085",
  "apn": "isp",
  "totalVolume": 1073741824,
  "totalDuration": 1,
  "durationUnit": "DAY",
  "orderUsage": 0,
  "expiredTime": "2026-09-28T09:47:00+0000",
  "supportTopUpType": 3,
  "fupPolicy": "1 Mbps"
}
```

## Status Mapping

| Provider `esimStatus` | Internal status |
|-----------------------|-----------------|
| GOT_RESOURCE | ready |
| IN_USE | active |
| USED_UP | consumed |
| DELETED | cancelled |
| (unknown) | unknown_provider_state |

## What to Watch For

1. **Provider datetime format**: `2026-09-28T09:47:00+0000` — the `+0000` timezone offset needs special parsing
2. **Field casing in webhooks**: Docs show `ICCID` (uppercase) but real payloads may vary
3. **`transactionId` typo**: Some docs show `transationId` (missing 'c')
4. **Balance integers**: Balance is in 1/10000 USD units, same as prices
5. **Cancel uses ICCID**: The cancel endpoint takes `iccid`, not `orderNo`
