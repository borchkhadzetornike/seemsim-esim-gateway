# Testing Guide

## Running Tests

```bash
# Full suite
python -m pytest tests/ -x -q

# Specific category
python -m pytest tests/unit/ -q
python -m pytest tests/integration/ -q
python -m pytest tests/contract/ -q

# Specific file
python -m pytest tests/integration/api/test_auth.py -v
```

## Test Structure

```
tests/
├── conftest.py                          # Shared fixtures (DB, Redis, app, client)
├── contract/
│   └── test_esim_access_contract.py     # Provider contract tests (auth, signing, paths)
├── integration/api/
│   ├── test_auth.py                     # Auth/authz integration tests (10 tests)
│   ├── test_catalog.py                  # Catalog sync/read tests
│   ├── test_health.py                   # Health endpoint tests
│   ├── test_order_refresh.py            # Order refresh + state sync tests
│   ├── test_orders.py                   # Order CRUD tests
│   └── test_webhooks.py                 # Webhook ingestion tests
├── unit/core/
│   ├── test_auth.py                     # HMAC auth unit tests
│   ├── test_errors.py                   # Error hierarchy tests
│   └── test_idempotency.py             # Idempotency manager tests
├── unit/providers/
│   ├── test_adapter.py                  # Provider adapter tests
│   └── test_client.py                   # HTTP client tests
├── unit/repositories/
│   └── test_order_repo.py              # Repository tests
├── unit/services/
│   ├── test_catalog_service.py          # Catalog service tests
│   ├── test_order_service.py            # Order service tests
│   └── test_state_sync.py              # State sync tests (24 tests)
```

## Test Categories

### Contract Tests (9 tests)
Verify the eSIM Access provider contract: header names, signature generation, endpoint paths, response envelope parsing.

### Auth Integration Tests (10 tests)
Verify:
- Missing auth header returns 401
- Invalid API key returns 401
- Disabled client returns 403
- Insufficient scope returns 403
- Valid key + sufficient scope succeeds
- Health endpoints remain unauthenticated
- Webhook endpoint remains unauthenticated

### State Sync Tests (24 tests)
Verify:
- Post-order sync populates ICCID and status
- All eSIM details persisted correctly
- Manual refresh updates stale state
- Duplicate syncs don't create duplicate eSIMs
- Null provider fields don't overwrite existing values
- Unknown statuses mapped conservatively
- Terminal statuses never downgraded
- History recorded for meaningful transitions

## Test Database

Tests use an in-memory SQLite database (via `aiosqlite`), NOT PostgreSQL. The `JSONBCompat` type automatically falls back to plain JSON on SQLite.

## Auth in Tests

The default `client` fixture overrides `get_caller_identity` to return a test identity with all scopes. This means existing tests work without auth headers.

For auth-specific tests, the `test_auth.py` file uses its own `auth_app` / `auth_client` fixtures that use the real auth flow with a test registry.

## Live Provider Tests

Live provider tests are NOT part of the automated suite. They are run manually against the real eSIM Access API and documented in:
- `docs/SANDBOX_EVIDENCE.md`
- `docs/FINAL_GATEWAY_TEST_REPORT.md`

### What Still Needs Live Verification

| Capability | Status |
|-----------|--------|
| Real webhook delivery | NOT VERIFIED — webhook URL not registered in provider admin |
| Top-up with real eSIM | AUTOMATED TESTS ONLY |
| Cancel with real eSIM | AUTOMATED TESTS ONLY |
| Suspend | BLOCKED — not supported by provider |
