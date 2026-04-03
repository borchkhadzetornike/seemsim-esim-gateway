# Changelog

All notable milestones for the eSIM Gateway are documented here.
For detailed implementation notes, see the docs under `docs/history/`.

## [Phase 6] — 2026-04-01 — Final Gateway Hardening

- Added internal service auth (API key + scope-based authorization)
- Added admin endpoints: balance query, reconciliation trigger, webhook event inspection
- Added startup config validation with warnings for missing credentials
- Fixed duplicate `query_order_full` in base.py and adapter.py
- Full documentation suite (9 canonical docs)
- **147 tests passing**, 10 new auth tests

## [Phase 5] — 2026-04-01 — State Sync Hardening

- Implemented `ProviderStateSyncer` service to keep internal records in sync with provider
- Added immediate post-order sync in `OrderService.create_order()`
- Added manual refresh endpoint (`POST /v1/orders/{id}/refresh`)
- Added reconciliation job with stale order detection
- Enhanced webhook processing with dedup and provider query trigger
- Extended data model: 18 new eSIM fields, order state history, enhanced webhook events
- Migration 002 applied
- Live verification: order synced to `ready` with full eSIM details immediately
- **137 tests passing** (108 existing + 29 new)

See [State Sync Changelog](docs/history/STATE_SYNC_CHANGELOG.md) for full details.

## [Phase 4] — 2026-03-31 — eSIM Access Rewrite

- Complete rewrite of provider auth (RT-* headers, HMAC-SHA256 uppercase hex)
- Complete rewrite of HTTP client (correct envelope: `success`/`obj` instead of `code`/`data`)
- Complete rewrite of adapter (correct endpoints, field mappings)
- Re-enabled: top-up, cancel, balance query
- Live validation: catalog sync (2590 packages), balance query ($50.00), order creation
- Real order placed: `B26031800280057` (Georgia 1GB/Day, $0.90)
- **108 tests passing**

See [eSIM Access Rewrite Changelog](docs/history/ESIMACCESS_REWRITE_CHANGELOG.md) for full details.

## [Phase 3] — 2026-03-31 — Contract Revalidation

- Discovered prior integration was built against wrong API (Yoni docs vs eSIM Access)
- Side-by-side comparison documented every mismatch
- Direct API probing confirmed correct auth, endpoints, and response shapes

See [Contract Revalidation](docs/history/CONTRACT_REVALIDATION.md) for the full report.

## [Phase 2] — 2026-03-31 — Wrong Yoni Drift (Historical)

- Initial provider contract incorrectly based on `docs-yoni-tech.readme.io`
- Authentication used wrong headers and signature construction
- All live API calls returned 401 Unauthorized
- This phase is entirely superseded by Phases 3–4

## [Phase 1] — Initial Build

- FastAPI service architecture with provider adapter pattern
- SQLAlchemy async models, Alembic migrations, Redis caching
- Full order lifecycle: create, query, topup, cancel, suspend
- Webhook ingestion, idempotency, structured logging
- Docker Compose setup (app, PostgreSQL, Redis)

See [Change History Summary](docs/history/CHANGE_HISTORY_SUMMARY.md) for the phase-by-phase timeline.
