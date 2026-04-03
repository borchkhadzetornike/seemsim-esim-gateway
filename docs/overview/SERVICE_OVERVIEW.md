# eSIM Gateway — Service Overview

## What It Is

The eSIM Gateway is an **internal platform service** that acts as an anti-corruption layer between the business platform and the eSIM Access provider API. It translates provider-specific operations into a clean, stable internal API that other services can depend on.

## What It Is Responsible For

- **Provider integration**: All communication with the eSIM Access API (`api.esimaccess.com`)
- **Package catalog**: Syncing, storing, and serving the provider's package catalog
- **Order lifecycle**: Creating orders, tracking status, and managing eSIM provisioning
- **State synchronization**: Keeping internal order/eSIM records in sync with provider truth
- **Webhook ingestion**: Receiving and processing provider webhook notifications
- **Reconciliation**: Background job to catch up on stale/incomplete orders
- **Internal auth**: Authenticating and authorizing internal service callers
- **Audit trail**: Recording state transitions, operation logs, and raw provider payloads

## What It Is NOT Responsible For

- **Customer-facing API**: The gateway is internal-only. Web/mobile apps must NOT call it directly.
- **User management**: No concept of end users, customers, or accounts
- **Pricing/billing**: Does not manage customer pricing, margins, or invoicing
- **Inventory management**: Does not decide which packages to offer customers
- **Notification delivery**: Does not send emails, push notifications, or SMS to end users
- **Multi-provider routing**: Currently supports only eSIM Access. Multi-provider support is a future extension.

## How Other Services Should Use It

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Platform API  │     │ Admin Panel  │     │ Worker       │
│ (backend)     │     │ (backend)    │     │ (background) │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                     │
       │ Authorization:     │ Authorization:      │ Authorization:
       │ Bearer sk_...      │ Bearer sk_...       │ Bearer sk_...
       │                    │                     │
       └────────────┬───────┴─────────────┬───────┘
                    │                     │
              ┌─────▼─────────────────────▼─────┐
              │        eSIM Gateway              │
              │   (internal service, port 8000)  │
              └──────────────┬──────────────────┘
                             │
                    ┌────────▼────────┐
                    │  eSIM Access    │
                    │  Provider API   │
                    └─────────────────┘
```

### Auth Model
- Each calling service has a dedicated API key
- Keys are scoped to specific operations
- Pass via `Authorization: Bearer <api_key>` header

### Key Principles
1. Gateway is the **only** service that talks to the provider
2. All other services interact with eSIMs through the gateway
3. Gateway stores authoritative internal state for orders and eSIMs
4. Gateway handles retries, idempotency, and error translation
