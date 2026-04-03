# Webhook Live Evidence

**Date**: 2026-04-01
**Purpose**: Document real webhook observations during final validation pass

---

## Real Provider Webhook Delivery

**Result: NO REAL PROVIDER WEBHOOK RECEIVED**

After placing order `B26040109460024` (packageCode `P1X57VWMR`, $0.90 Georgia 1GB/Day FUP1Mbps),
no webhook was delivered by the provider to the ngrok endpoint.

### Likely reason
The webhook callback URL has not yet been registered in the eSIM Access admin portal.
The provider cannot send webhooks to an unregistered URL.

### Evidence
- ngrok tunnel was online and reachable throughout testing
- ngrok inspection API showed only manual test requests and health checks
- No new webhook events in `provider_webhook_events` table with `order_no = 'B26040109460024'`
- The only post-order webhook event was an artifact from the immediate post-order sync, not a provider-sent webhook

---

## Manual Webhook Route Testing

### Local direct test
```
POST http://localhost:8000/v1/provider/webhooks/esim-access
Payload: {"notifyType":"ORDER_STATUS","orderNo":"TEST-LOCAL-001","ICCID":"8900000000000000001","transactionId":"test-txn-local","result":"COMPLETED"}
Response: {"success":true,"data":{"received":true,"event_id":"fa40416a-..."}}
DB: event persisted, processing_status=processed
```

### Ngrok public URL test
```
POST https://0870-185-115-6-66.ngrok-free.app/v1/provider/webhooks/esim-access
Payload: {"notifyType":"ORDER_STATUS","orderNo":"TEST-NGROK-001","ICCID":"8900000000000000002","transactionId":"test-txn-ngrok","result":"COMPLETED"}
Response: {"success":true,"data":{"received":true,"event_id":"46f07c23-..."}}
DB: event persisted, processing_status=processed
```

### Duplicate replay test
```
POST (same payload as ngrok test above)
Response: {"success":true,"data":{"received":true,"event_id":"39e3dd29-..."}}
DB: new row created but duplicate detected → immediately marked processed without re-running handlers
```

### Malformed payload test
```
POST with {"garbage": true}
Response: {"success":true,"data":{"received":true,"event_id":"57df6274-..."}}
DB: event persisted safely, event_type="UNKNOWN"
```

---

## Field Casing Observations

Based on manual testing with documented payload format:
- `notifyType` — successfully extracted as `event_type`
- `orderNo` — successfully extracted as `order_no`
- `ICCID` (uppercase) — handled in the adapter's `handle_webhook` method
- `transactionId` — successfully extracted as `transaction_id`

**CRITICAL CAVEAT**: These are from manual test payloads constructed per docs.esimaccess.com.
Real provider payloads have NOT been observed yet.

---

## Persistence Evidence

| Test | Event Persisted | Processing Status | Duplicate Detected |
|------|----------------|-------------------|--------------------|
| Local direct | Yes | processed | N/A (first) |
| Ngrok public | Yes | processed | N/A (first) |
| Duplicate replay | Yes | processed | Yes (skipped handlers) |
| Malformed | Yes | processed | N/A |

---

## Still Unverified

1. Real provider webhook payload shape and field casing
2. Whether `notifyType` is the actual field name used by provider
3. Whether `ICCID` is uppercase or lowercase in real payloads
4. Whether `transactionId` has the documented typo (`transationId`)
5. Whether the provider sends webhooks for instant fulfillment (GOT_RESOURCE) at all
6. Whether the provider retries failed deliveries
7. Actual webhook signing/authentication mechanism (if any)
