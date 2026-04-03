# Architecture

## System Components

```
app/
├── api/v1/          # HTTP route handlers (FastAPI routers)
│   ├── admin.py     # Admin/ops endpoints (balance, reconciliation, webhook events)
│   ├── catalog.py   # Product catalog CRUD + sync
│   ├── esims.py     # eSIM detail/status/history
│   ├── health.py    # Liveness and readiness probes
│   ├── orders.py    # Order CRUD, refresh, topup, cancel
│   └── webhooks.py  # Provider webhook ingestion
├── core/            # Cross-cutting concerns
│   ├── auth.py      # Service-to-service authentication and authorization
│   ├── config.py    # Pydantic settings (env-driven)
│   ├── database.py  # SQLAlchemy async engine/session
│   ├── errors.py    # Error hierarchy (AppError, ProviderError, AuthError)
│   ├── idempotency.py # Redis-backed idempotency
│   ├── logging.py   # Structured logging (structlog)
│   ├── middleware.py # Request context (request_id, caller_service)
│   ├── redis.py     # Redis connection management
│   └── utils.py     # Utility functions
├── models/          # SQLAlchemy ORM models
├── providers/       # Provider adapter layer
│   ├── base.py      # Abstract provider interface
│   └── esim_access/ # eSIM Access implementation
│       ├── adapter.py  # Provider adapter (maps API to internal types)
│       ├── auth.py     # HMAC-SHA256 request signing
│       └── client.py   # HTTP client with retry/error handling
├── repositories/    # Data access layer
├── schemas/         # Pydantic request/response schemas
├── services/        # Business logic layer
│   ├── catalog.py   # Catalog sync service
│   ├── esim.py      # eSIM service
│   ├── order.py     # Order service (with post-order sync)
│   ├── state_sync.py # Provider state → internal state mapper
│   └── webhook.py   # Webhook processing service
└── tasks/           # Background jobs
    └── reconciliation.py # Periodic reconciliation + catalog sync
```

## Request Flow: Order Creation

```
1. Caller → POST /v1/orders {package_code, quantity}
2. Auth middleware validates Bearer token + orders:create scope
3. OrderService.create_order():
   a. Generate transaction_id (UUID)
   b. Create ProviderOrder record (status=pending)
   c. Call provider: POST /api/v1/open/esim/order
   d. Update order with provider_order_no
   e. Immediate post-order sync:
      - Query provider: POST /api/v1/open/esim/query
      - Merge esimList into Esim records
      - Map provider status (GOT_RESOURCE → ready)
      - Record OrderStateHistory + EsimStatusHistory
   f. Return order (status=ready, iccid populated)
4. Response → {order_id, provider_order_no, status, iccid, ...}
```

## State Sync Flow

Four paths merge provider state into internal records:

| Source | Trigger | When |
|--------|---------|------|
| **Post-order sync** | Order creation | Immediately after order placement |
| **Manual refresh** | `POST /v1/orders/{id}/refresh` | On-demand by internal tools |
| **Reconciliation** | Background job | Every 5 minutes for stale orders |
| **Webhook** | Provider notification | When provider sends webhook |

All paths use `ProviderStateSyncer.sync_order()` which:
1. Queries provider for full order/eSIM data
2. Merges into internal ProviderOrder + Esim records
3. Maps provider status to internal status
4. Records state history for audit

## Provider Authentication

eSIM Access uses HMAC-SHA256 request signing:
```
Headers: RT-AccessCode, RT-RequestID (UUID), RT-Timestamp (ms), RT-Signature
SignInput: timestamp + requestId + accessCode + jsonBody
Signature: HMAC-SHA256(secretKey, signInput).hexdigest().upper()
```

## Data Model

Key tables:
- `provider_orders` — order records with provider status + sync metadata
- `esims` — eSIM records with 18+ provider-sourced fields
- `provider_products` / `provider_packages` — catalog
- `order_state_history` — audit trail for order transitions
- `esim_status_history` — audit trail for eSIM transitions
- `provider_webhook_events` — raw webhook payloads + processing status
- `operation_logs` — all provider API call records
- `idempotency_records` — persistent idempotency audit
