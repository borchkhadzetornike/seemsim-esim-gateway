# Webhook Setup Notes

**Date**: 2026-04-01
**Purpose**: Document what must be registered in the eSIM Access admin and how the gateway handles webhooks

---

## Callback URL to Register

Register this exact URL in the eSIM Access admin panel:

```
https://<your-ngrok-host>/v1/provider/webhooks/esim-access
```

**Note**: This is a temporary ngrok URL for development/testing. For production, replace with a
permanent public URL pointing to the gateway's `/v1/provider/webhooks/esim-access` route.

---

## Expected Webhook Event Types

Based on docs.esimaccess.com, the following notification types are supported:

| notifyType | Description |
|------------|-------------|
| ORDER_STATUS | Order fulfillment status change |
| ESIM_STATUS | eSIM profile status change |
| DATA_USAGE | Data usage threshold notification |
| VALIDITY_USAGE | Validity usage threshold notification |

---

## Gateway Response Behavior

The webhook endpoint provides:

1. **Fast 2xx acknowledgment** — returns HTTP 200 with `{"success": true, "data": {"received": true, "event_id": "..."}}` immediately after persisting the raw payload
2. **Raw payload persistence** — the entire incoming JSON is stored in `provider_webhook_events.payload` before any processing
3. **Processing is inline but failure-safe** — if processing fails, the raw payload is still persisted and the event is marked `processing_status: "failed"` with the error message
4. **Idempotent/dedup** — duplicate webhooks (same `order_no` + `event_type` already processed) are detected and short-circuited
5. **Provider query refresh** — after processing a webhook, the gateway queries the provider for full authoritative state, rather than trusting the webhook payload alone

---

## Provider Response Requirements

Based on eSIM Access docs, the provider expects:
- **HTTP 200** response to acknowledge receipt
- No specific response body format is documented as required by the provider

The gateway returns a structured JSON response which satisfies the HTTP 200 requirement.

---

## Field Mapping Assumptions (Not Yet Verified Live)

The webhook handler normalizes these fields from the raw payload:

| Raw field | Normalized key | Notes |
|-----------|---------------|-------|
| `notifyType` | `event_type` | e.g. ORDER_STATUS, ESIM_STATUS |
| `orderNo` | `order_no` | Provider order number |
| `ICCID` or `iccid` | `iccid` | Case may vary per docs |
| `transactionId` or `transationId` | `transaction_id` | Typo-tolerant |
| `result` | `status` | Mapped to internal status |

**These mappings are conservative and need live webhook verification.**

---

## What the User Must Do

1. Log into the eSIM Access admin portal
2. Navigate to webhook/notification settings
3. Register the callback URL above
4. Enable the notification types: ORDER_STATUS, ESIM_STATUS, DATA_USAGE, VALIDITY_USAGE
5. Save and verify with a test notification if available

After registration, place a new order and observe whether a webhook arrives at the gateway.
