# eSIM Gateway Microservice

Production-grade eSIM Gateway microservice that integrates with the **eSIM Access** provider. Acts as a clean anti-corruption layer between your internal platform and the external provider API.

## New Engineer? Start Here

1. Read the [Service Overview](docs/overview/SERVICE_OVERVIEW.md) to understand what this service owns
2. Read the [Architecture](docs/architecture/ARCHITECTURE.md) for the component map
3. Browse the full [Documentation Index](docs/indexes/DOC_INDEX.md) for everything else

## Documentation

| Document | Description |
|----------|-------------|
| [Documentation Index](docs/indexes/DOC_INDEX.md) | Full navigation guide to all docs |
| [Service Overview](docs/overview/SERVICE_OVERVIEW.md) | What the gateway is, owns, and does not own |
| [Architecture](docs/architecture/ARCHITECTURE.md) | Component map, order flow, state sync |
| [Internal API Contract](docs/architecture/INTERNAL_API_CONTRACT.md) | Versioned HTTP endpoints and scopes |
| [Auth & Security](docs/architecture/AUTH_AND_SECURITY.md) | Internal service auth model |
| [Provider Integration Notes](docs/development/PROVIDER_INTEGRATION_NOTES.md) | eSIM Access quirks and status mapping |
| [Operations Runbook](docs/operations/OPERATIONS_RUNBOOK.md) | Running, debugging, and operating the service |
| [Testing Guide](docs/testing/TESTING_GUIDE.md) | pytest setup, categories, and fixtures |
| [CHANGELOG](CHANGELOG.md) | Major milestones in reverse chronological order |

## What This Service Owns / Does Not Own

**Owns:** Provider integration (eSIM Access API), package catalog sync, order lifecycle, state synchronization, webhook ingestion, reconciliation, internal auth, and audit trail.

**Does NOT own:** Customer-facing API, user management, pricing/billing, inventory decisions, notification delivery, or multi-provider routing.

See [Service Overview](docs/overview/SERVICE_OVERVIEW.md) for full details.

## Architecture Overview

```
┌──────────────────────────────────────────────────┐
│                 Internal Consumers                │
│           (via normalized REST API)               │
└──────────────────────┬───────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────┐
│              eSIM Gateway Service                 │
│                                                   │
│  ┌─────────┐  ┌──────────┐  ┌─────────────────┐ │
│  │   API   │──│ Services │──│   Repositories  │ │
│  │ Routers │  │  Layer   │  │    (SQLAlchemy)  │ │
│  └─────────┘  └────┬─────┘  └────────┬────────┘ │
│                     │                  │          │
│              ┌──────▼──────┐    ┌──────▼──────┐  │
│              │  Provider   │    │ PostgreSQL   │  │
│              │  Adapter    │    │   + Redis    │  │
│              └──────┬──────┘    └─────────────┘  │
│                     │                             │
└─────────────────────┼─────────────────────────────┘
                      │
┌─────────────────────▼─────────────────────────────┐
│              eSIM Access API                       │
│         (api.esimaccess.com)                       │
└───────────────────────────────────────────────────┘
```

## Folder Structure

```
seemsim-esim-gateway/
├── app/
│   ├── api/              # FastAPI routers/controllers
│   │   ├── deps.py       # Dependency injection
│   │   ├── error_handlers.py
│   │   └── v1/           # Versioned endpoints
│   ├── core/             # Config, logging, security, utilities
│   │   ├── config.py     # Pydantic Settings
│   │   ├── database.py   # SQLAlchemy async engine
│   │   ├── errors.py     # Typed exception hierarchy
│   │   ├── idempotency.py# Redis-backed idempotency
│   │   ├── logging.py    # Structured JSON logging
│   │   ├── middleware.py  # Request context / correlation IDs
│   │   ├── redis.py      # Redis connection pool
│   │   └── utils.py
│   ├── models/           # SQLAlchemy ORM models
│   ├── schemas/          # Pydantic request/response DTOs
│   ├── services/         # Business orchestration layer
│   ├── providers/        # Provider abstraction + adapters
│   │   ├── base.py       # Abstract provider interface
│   │   └── esim_access/  # eSIM Access adapter
│   │       ├── auth.py   # HMAC-SHA256 signing
│   │       ├── client.py # HTTP client with retry
│   │       └── adapter.py# Provider interface implementation
│   ├── repositories/     # Database access layer
│   ├── tasks/            # Background jobs / reconciliation
│   └── main.py           # FastAPI application factory
├── alembic/              # Database migrations
├── tests/
│   ├── unit/             # Fast, no-IO tests
│   ├── integration/      # DB/Redis/API-backed tests
│   └── contract/         # Provider schema contract tests
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── pyproject.toml
└── .env.example
```

## Local Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker (optional but recommended)

### Quick Start with Docker

```bash
cp .env.example .env
# Edit .env with your eSIM Access credentials
docker compose up -d --build
# Run migrations
docker compose exec app alembic upgrade head
```

### Local Development

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
make dev

# Start Postgres and Redis (via Docker)
docker compose up -d postgres redis

# Run migrations
make migrate

# Start the dev server
make run
```

The API is available at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `APP_NAME` | Service name | `esim-gateway` |
| `APP_ENV` | Environment (development/production) | `development` |
| `APP_DEBUG` | Enable debug mode | `false` |
| `APP_LOG_LEVEL` | Log level | `INFO` |
| `DATABASE_URL` | PostgreSQL connection string | (required) |
| `REDIS_URL` | Redis connection string | (required) |
| `ESIM_ACCESS_BASE_URL` | eSIM Access API base URL | `https://api.esimaccess.com` |
| `ESIM_ACCESS_ACCESS_CODE` | eSIM Access access code | (required) |
| `ESIM_ACCESS_SECRET_KEY` | eSIM Access secret key | (required) |
| `IDEMPOTENCY_KEY_TTL_SECONDS` | Idempotency key expiration | `86400` |
| `PROVIDER_REQUEST_TIMEOUT_SECONDS` | Provider HTTP timeout | `30` |
| `PROVIDER_MAX_RETRIES` | Max retries for transient failures | `3` |
| `CATALOG_SYNC_INTERVAL_SECONDS` | Catalog sync frequency | `3600` |
| `RECONCILIATION_INTERVAL_SECONDS` | Order reconciliation frequency | `300` |

## Commands

```bash
make help          # Show all commands
make dev           # Install dev dependencies + pre-commit
make lint          # Run ruff linter
make format        # Auto-format code
make type-check    # Run mypy
make test          # Run all tests
make test-unit     # Unit tests only
make test-cov      # Tests with coverage report
make migrate       # Run DB migrations
make run           # Start dev server
make docker-up     # Docker Compose up
make docker-down   # Docker Compose down
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/catalog/sync` | Sync product catalog from provider |
| `GET` | `/v1/catalog/products` | List all products |
| `GET` | `/v1/catalog/products/{id}` | Get product details |
| `POST` | `/v1/orders` | Create a new eSIM order |
| `GET` | `/v1/orders/{id}` | Get order details |
| `POST` | `/v1/orders/{id}/topup` | Top up an existing eSIM |
| `POST` | `/v1/orders/{id}/cancel` | Cancel an order |
| `GET` | `/v1/esims/{id}` | Get eSIM details |
| `GET` | `/v1/esims/{id}/status` | Get live eSIM status |
| `GET` | `/v1/esims/{id}/history` | Get eSIM status history |
| `POST` | `/v1/provider/webhooks/esim-access` | Webhook ingestion |
| `GET` | `/health/live` | Liveness probe |
| `GET` | `/health/ready` | Readiness probe |

## How Idempotency Works

All mutation endpoints (`POST /v1/orders`, `POST /v1/orders/{id}/topup`, `POST /v1/orders/{id}/cancel`) support the `Idempotency-Key` header.

1. Client sends a unique `Idempotency-Key` header with the request
2. The service checks Redis for an existing entry:
   - **Not found**: Acquires a lock (status=processing) with TTL and proceeds
   - **Found + completed**: Returns the stored response immediately (no provider call)
   - **Found + processing**: Returns 409 (concurrent retry protection)
3. After successful processing, the response is stored in Redis
4. If processing fails, the key is released so the request can be retried
5. A request fingerprint (hash of method + path + body) prevents reuse of keys with different payloads (returns 409)

Keys expire after `IDEMPOTENCY_KEY_TTL_SECONDS` (default: 24 hours).

## How Retries Work

The provider client uses **tenacity** for retry logic:

- **Retryable conditions**: Provider codes 101 (processing) and 102 (busy), plus HTTP 5xx errors
- **Strategy**: Exponential backoff with jitter (initial=1s, max=10s, jitter=2s)
- **Max attempts**: 3 (configurable via `PROVIDER_MAX_RETRIES`)
- **Non-retryable**: Authentication errors (501-503), validation errors (504-506), rate limits (429), timeouts

The reconciliation task periodically checks orders stuck in `pending`/`processing` states and refreshes their status from the provider.

## How to Add Another Provider

1. Create a new directory under `app/providers/` (e.g., `app/providers/new_provider/`)
2. Implement the `BaseEsimProvider` abstract interface from `app/providers/base.py`
3. Create provider-specific `auth.py` and `client.py` modules
4. Add the new provider to the dependency injection in `app/api/deps.py`
5. The service layer, repositories, and API endpoints remain unchanged

The provider adapter pattern ensures that all provider-specific behavior is isolated. Internal consumers never interact with provider payloads directly.

## Assumptions from eSIM Access Docs

The following assumptions were made based on available documentation and similar provider APIs. Each is isolated for easy adjustment:

1. **API Base Path**: `/api/v1/open/` — inferred from common eSIM provider patterns. Adjust in `EsimAccessClient.BASE_PATH`.

2. **Authentication**: HMAC-SHA256 with headers `RT-AccessCode`, `RT-RequestID`, `RT-Timestamp`, `RT-Signature`. Signature = HMAC-SHA256(secretKey, timestamp + requestId + accessCode + body). Adjust in `EsimAccessAuth._build_sign_data()`.

3. **Endpoint Paths**:
   - `package/list` — list available packages
   - `order/apply` — create an order
   - `order/query` — query order status
   - `order/cancel` — cancel an order
   - `esim/query` — query eSIM profile
   - `esim/data-usage` — check data usage
   - `esim/topup` — top up an eSIM
   - `esim/suspend` — suspend an eSIM

4. **Response Format**: `{"code": int, "msg": string, "data": object}` where code=0 indicates success.

5. **Error Codes**: 101 (processing/retry), 102 (busy/retry), 400 (query error), 501 (account not found), 502 (inactive), 503 (IP blocked), 504 (package not found), 505 (price unavailable), 506 (insufficient balance), 9999 (unknown).

6. **Webhook Events**: `ORDER_STATUS`, `ESIM_STATUS`, `DATA_USAGE`, `VALIDITY_USAGE` sent as POST to a configured callback URL.

7. **Webhook Payload Fields**: `notifyType`, `orderNo`, `iccid`, `transactionId`, `status`.

8. **Package List Response**: Contains `packageList` array with fields: `packageCode`, `name`, `type`, `volume`, `duration`, `price`, `currencyCode`, `locationCode`.

All assumptions are documented in code comments near the relevant implementation.
