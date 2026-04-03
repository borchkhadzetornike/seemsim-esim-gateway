# Internal API Contract

**Version**: 1.0.0
**Base URL**: `http://esim-gateway:8000` (internal network)

All endpoints except health and webhooks require `Authorization: Bearer <api_key>`.

---

## Health (Unauthenticated)

### `GET /health/live`
- **Purpose**: Liveness probe
- **Auth**: None
- **Response**: `{"status": "ok", "service": "esim-gateway", "timestamp": "..."}`

### `GET /health/ready`
- **Purpose**: Readiness probe (DB + Redis connectivity)
- **Auth**: None
- **Response**: `{"status": "ok|degraded", "checks": {"database": "ok", "redis": "ok"}}`

---

## Catalog

### `POST /v1/catalog/sync`
- **Purpose**: Sync package catalog from eSIM Access provider
- **Scope**: `catalog:sync`
- **Request body**: None
- **Response**: `{"data": {"products_synced": 212, "packages_synced": 2590}}`
- **Side effects**: Creates/updates provider_products and provider_packages rows
- **Provider call**: Yes (`/api/v1/open/package/list`)
- **Idempotency**: Safe to call repeatedly; full upsert

### `GET /v1/catalog/products`
- **Purpose**: List all product groups
- **Scope**: `catalog:read`
- **Response**: `{"data": [{"id", "name", "location_code", "is_active", "package_count"}]}`

### `GET /v1/catalog/products/{product_id}`
- **Purpose**: Get product with packages
- **Scope**: `catalog:read`
- **Response**: `{"data": {"id", "name", "packages": [...]}}`

---

## Orders

### `POST /v1/orders`
- **Purpose**: Create a new eSIM order
- **Scope**: `orders:create`
- **Request body**: `{"package_code": "P1X57VWMR", "quantity": 1}`
- **Headers**: `Idempotency-Key` (optional, recommended)
- **Response** (201): `{"data": {"id", "provider_order_no", "status", "iccid", ...}}`
- **Side effects**: Creates order + triggers post-order sync (creates eSIM record)
- **Provider call**: Yes (order + query)
- **Idempotency**: Redis-backed via Idempotency-Key header; provider-level via transactionId

### `GET /v1/orders/{order_id}`
- **Purpose**: Get order details
- **Scope**: `orders:read`
- **Provider call**: No (reads from DB)

### `POST /v1/orders/{order_id}/refresh`
- **Purpose**: Force-refresh order state from provider
- **Scope**: `orders:refresh`
- **Response**: `{"data": {"order": {..., "esims": [...]}, "state_changed": bool}}`
- **Provider call**: Yes (query)
- **Idempotency**: Safe; idempotent

### `GET /v1/orders/{order_id}/esims`
- **Purpose**: Get eSIMs associated with an order
- **Scope**: `orders:read`
- **Response**: `{"data": [{"iccid", "status", "activation_code", "qr_code_url", ...}]}`
- **Provider call**: No

### `POST /v1/orders/{order_id}/topup`
- **Purpose**: Top up an existing eSIM
- **Scope**: `topup:create`
- **Request body**: `{"package_code": "...", "iccid": "..."}`
- **Provider call**: Yes (`/api/v1/open/esim/topup`)

### `POST /v1/orders/{order_id}/cancel`
- **Purpose**: Cancel an order/eSIM
- **Scope**: `cancel:create`
- **Provider call**: Yes (`/api/v1/open/esim/cancel`)

---

## eSIMs

### `GET /v1/esims/{esim_id}`
- **Purpose**: Get eSIM details
- **Scope**: `esims:read`

### `GET /v1/esims/{esim_id}/status`
- **Purpose**: Get live eSIM status from provider
- **Scope**: `esims:read`
- **Provider call**: Yes (query)

### `GET /v1/esims/{esim_id}/history`
- **Purpose**: Get eSIM status change history
- **Scope**: `esims:read`
- **Provider call**: No

---

## Admin

### `GET /v1/admin/balance`
- **Purpose**: Query provider account balance
- **Scope**: `balance:read`
- **Response**: `{"data": {"balance_raw": 474200, "balance_usd": 47.42}}`
- **Provider call**: Yes (`/api/v1/open/balance/query`)

### `POST /v1/admin/reconciliation/trigger`
- **Purpose**: Manually trigger reconciliation job
- **Scope**: `reconciliation:run`
- **Response**: `{"data": {"reconciled_count": 0}}`
- **Provider call**: Yes (queries stale orders)

### `GET /v1/admin/webhook-events?limit=50`
- **Purpose**: List recent webhook events for debugging
- **Scope**: `admin:ops`
- **Response**: `{"data": [{"id", "event_type", "order_no", "processing_status", ...}]}`

---

## Provider Webhooks (Unauthenticated — provider calls this)

### `POST /v1/provider/webhooks/esim-access`
- **Purpose**: Receive provider webhook notifications
- **Auth**: None (provider-initiated)
- **Request body**: Raw provider payload
- **Response**: `{"data": {"received": true, "event_id": "..."}}`
- **Side effects**: Persists event, processes status update, triggers provider refresh

---

## Error Response Format

All errors follow this envelope:

```json
{
  "success": false,
  "data": null,
  "error": {
    "error_code": "AUTHENTICATION_ERROR",
    "detail": "Missing authorization header"
  }
}
```

### Error Codes
| Code | HTTP | Meaning |
|------|------|---------|
| AUTHENTICATION_ERROR | 401 | Missing or invalid API key |
| AUTHORIZATION_ERROR | 403 | Valid key but insufficient scope or disabled |
| RESOURCE_NOT_FOUND | 404 | Order/eSIM/product not found |
| VALIDATION_ERROR | 422 | Invalid request body |
| IDEMPOTENCY_CONFLICT | 409 | Same key, different payload |
| PROVIDER_ERROR | 502 | Provider communication error |
| PROVIDER_AUTH_ERROR | 502 | Provider auth failure |
| PROVIDER_VALIDATION_ERROR | 422 | Provider rejected request |
| PROVIDER_TIMEOUT | 504 | Provider request timeout |
| PROVIDER_UNAVAILABLE | 503 | Provider service down |
| PROVIDER_CAPABILITY_UNAVAILABLE | 501 | Unsupported operation (e.g., suspend) |

---

## Scope Reference

| Scope | Endpoints |
|-------|-----------|
| `catalog:read` | GET /v1/catalog/products, GET /v1/catalog/products/{id} |
| `catalog:sync` | POST /v1/catalog/sync |
| `orders:create` | POST /v1/orders |
| `orders:read` | GET /v1/orders/{id}, GET /v1/orders/{id}/esims |
| `orders:refresh` | POST /v1/orders/{id}/refresh |
| `esims:read` | GET /v1/esims/{id}, GET /v1/esims/{id}/status, GET /v1/esims/{id}/history |
| `balance:read` | GET /v1/admin/balance |
| `topup:create` | POST /v1/orders/{id}/topup |
| `cancel:create` | POST /v1/orders/{id}/cancel |
| `reconciliation:run` | POST /v1/admin/reconciliation/trigger |
| `admin:ops` | GET /v1/admin/webhook-events |
