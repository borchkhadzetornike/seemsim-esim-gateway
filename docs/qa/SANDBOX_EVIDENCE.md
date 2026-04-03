# Sandbox Evidence

**Date**: 2026-03-31  
**Provider**: api.esimaccess.com  
**All evidence sanitized**: Credentials removed, only structural data shown.

---

## 1. Package List — Request/Response

**Request**:
```
POST /api/v1/open/package/list
Headers: RT-AccessCode, RT-RequestID, RT-Timestamp, RT-Signature, Content-Type: application/json
Body: {}
```

**Response** (first package, verbatim):
```json
{
  "success": true,
  "errorCode": "0",
  "errorMsg": null,
  "obj": {
    "packageList": [
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
        "locationNetworkList": [
          {
            "locationName": "Spain",
            "locationLogo": "/img/flags/es.png",
            "locationCode": "ES",
            "operatorList": [
              {"operatorName": "Vodafone", "networkType": "4G"},
              {"operatorName": "Orange", "networkType": "4G"}
            ]
          }
        ]
      }
    ]
  }
}
```

**Total packages returned**: 2590

---

## 2. Balance Query

**Request**: `POST /api/v1/open/balance/query` body: `{}`

**Response (before order)**:
```json
{"success": true, "errorCode": "0", "errorMsg": null, "obj": {"balance": 500000}}
```

**Response (after order)**:
```json
{"success": true, "errorCode": "0", "errorMsg": null, "obj": {"balance": 491400}}
```

---

## 3. Order Creation

**Gateway request**:
```
POST http://localhost:8000/v1/orders
Headers:
  Content-Type: application/json
  Idempotency-Key: gw-test-ge-1774985374
Body: {"package_code": "P1X57VWMR", "quantity": 1}
```

**Provider request (from gateway to provider)**:
```
POST https://api.esimaccess.com/api/v1/open/esim/order
Headers: RT-AccessCode, RT-RequestID, RT-Timestamp, RT-Signature
Body: {"transactionId":"520372b9-508f-4661-b3cf-0f9d8f6ea9e1","packageInfoList":[{"packageCode":"P1X57VWMR","count":1}]}
```

**Provider response**:
```json
{
  "success": true,
  "errorCode": "0",
  "errorMsg": null,
  "obj": {
    "orderNo": "B26033119290003",
    "transactionId": "520372b9-508f-4661-b3cf-0f9d8f6ea9e1"
  }
}
```

**Gateway response**:
```json
{
  "success": true,
  "data": {
    "id": "cd22ce73-f1ff-441a-9d1c-7729d0e9ffca",
    "provider_order_no": "B26033119290003",
    "transaction_id": "520372b9-508f-4661-b3cf-0f9d8f6ea9e1",
    "package_code": "P1X57VWMR",
    "quantity": 1,
    "status": "pending",
    "iccid": null,
    "failure_reason": null,
    "created_at": "2026-03-31T19:29:35.175938Z",
    "updated_at": "2026-03-31T19:29:36.395587Z"
  },
  "error": null
}
```

---

## 4. Order Query (direct provider)

**Request**:
```json
POST /api/v1/open/esim/query
Body: {"orderNo": "B26033119290003", "pager": {"pageNum": 1, "pageSize": 5}}
```

**Response** (full eSIM details):
```json
{
  "success": true,
  "errorCode": "0",
  "errorMsg": null,
  "obj": {
    "esimList": [
      {
        "esimTranNo": "26033119290005",
        "orderNo": "B26033119290003",
        "transactionId": "520372b9-508f-4661-b3cf-0f9d8f6ea9e1",
        "imsi": "310840118124583",
        "iccid": "8910300000044404757",
        "smsStatus": 0,
        "msisdn": "",
        "ac": "LPA:1$rsp-eu.simlessly.com$C5F541D4E3174EA38A74B6EF7CCB80FF",
        "qrCodeUrl": "https://p.qrsim.net/90f19728db9445fb9ebfb525e0db2798.png",
        "shortUrl": "https://p.qrsim.net/90f19728db9445fb9ebfb525e0db2798",
        "smdpStatus": "RELEASED",
        "eid": "",
        "activeType": 2,
        "dataType": 2,
        "activateTime": null,
        "expiredTime": "2026-09-27T19:29:36+0000",
        "installationTime": null,
        "totalVolume": 1073741824,
        "totalDuration": 1,
        "durationUnit": "DAY",
        "orderUsage": 0,
        "esimStatus": "GOT_RESOURCE",
        "pin": "6313",
        "puk": "25363068",
        "apn": "isp",
        "ipExport": "FR/NL",
        "supportTopUpType": 3,
        "fupPolicy": "1 Mbps",
        "packageList": [
          {
            "packageName": "Georgia 1GB/Day FUP1Mbps",
            "packageCode": "P1X57VWMR",
            "slug": "GE_1_Daily_1Mbps",
            "duration": 1,
            "volume": 1073741824,
            "locationCode": "GE",
            "createTime": "2026-03-31T19:29:36+0000",
            "esimTranNo": "26033119290005",
            "transactionId": "520372b9-508f-4661-b3cf-0f9d8f6ea9e1"
          }
        ]
      }
    ],
    "pager": {
      "pageSize": 5,
      "pageNum": 1,
      "total": 1
    }
  }
}
```

---

## 5. Key eSIM Details

| Field | Value |
|-------|-------|
| orderNo | B26033119290003 |
| esimTranNo | 26033119290005 |
| transactionId | 520372b9-508f-4661-b3cf-0f9d8f6ea9e1 |
| iccid | 8910300000044404757 |
| imsi | 310840118124583 |
| ac (LPA) | LPA:1$rsp-eu.simlessly.com$C5F541D4E3174EA38A74B6EF7CCB80FF |
| qrCodeUrl | https://p.qrsim.net/90f19728db9445fb9ebfb525e0db2798.png |
| shortUrl | https://p.qrsim.net/90f19728db9445fb9ebfb525e0db2798 |
| esimStatus | GOT_RESOURCE |
| smdpStatus | RELEASED |
| pin | 6313 |
| puk | 25363068 |
| apn | isp |
| totalVolume | 1073741824 (1 GB) |
| expiredTime | 2026-09-27T19:29:36+0000 |

---

## 6. Internal Database Record

```
id:                cd22ce73-f1ff-441a-9d1c-7729d0e9ffca
provider_order_no: B26033119290003
transaction_id:    520372b9-508f-4661-b3cf-0f9d8f6ea9e1
package_code:      P1X57VWMR
quantity:          1
status:            pending
iccid:             (null — not yet updated from provider)
idempotency_key:   gw-test-ge-1774985374
created_at:        2026-03-31 19:29:35.175938+00
```

---

## 7. Idempotency Evidence

**Replay (same key, same payload)**:
```json
{
  "success": true,
  "data": {
    "id": "cd22ce73-f1ff-441a-9d1c-7729d0e9ffca",
    "provider_order_no": "B26033119290003",
    "status": "pending"
  }
}
```
Result: Same order returned, no duplicate.

**Conflict (same key, different payload)**:
```json
{
  "success": false,
  "error": {
    "error_code": "IDEMPOTENCY_CONFLICT",
    "detail": "Idempotency key already used with a different request"
  }
}
```

---

## 8. Negative Test Evidence

**Invalid package code**:
```json
{
  "success": false,
  "error": {
    "error_code": "PROVIDER_VALIDATION_ERROR",
    "detail": "[310241] base data plan code:[INVALID_DOES_NOT_EXIST] doesn`t exist."
  }
}
```

**Missing required field**:
```json
{
  "detail": [
    {"type": "missing", "loc": ["body", "package_code"], "msg": "Field required"}
  ]
}
```

---

## 9. Webhook Evidence

**Status**: No webhook received.  
**Reason**: Webhook URL likely not configured in console.esimaccess.com/developer/index, and the `webhook_events` table does not exist in the database schema.

---

## 10. Gateway Logs (order flow)

```
provider_request_start    path=/api/v1/open/esim/order
provider_request_complete path=/api/v1/open/esim/order status_code=200 elapsed_ms=1149.49
order_created             order_id=cd22ce73-... provider_order_no=B26033119290003 status=pending
idempotency_completed     key=gw-test-ge-1774985374
request_completed         method=POST path=/v1/orders status_code=201 elapsed_ms=1387.68
```
