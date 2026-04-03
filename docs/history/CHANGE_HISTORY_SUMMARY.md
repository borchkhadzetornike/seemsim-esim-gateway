# Change History Summary

## Phase 1: Initial Build
- FastAPI service architecture with provider adapter pattern
- SQLAlchemy async models, Alembic migrations, Redis caching
- Full order lifecycle: create, query, topup, cancel, suspend
- Webhook ingestion, idempotency, structured logging
- Docker Compose setup (app, PostgreSQL, Redis)

## Phase 2: Wrong Yoni Drift
- Initial provider contract was incorrectly based on `docs-yoni-tech.readme.io`
- Authentication used wrong headers (`appId`, `timestamp`, `sign`) and wrong signature
- Base URL pointed to `api.yoni-esim.com` instead of `api.esimaccess.com`
- Response parsing expected Yoni envelope (`{code, msg, data}`) instead of eSIM Access envelope
- All live API calls returned 401 Unauthorized

## Phase 3: Contract Revalidation
- User corrected source of truth to `docs.esimaccess.com`
- Side-by-side comparison documented every mismatch
- Direct API probing confirmed correct auth, endpoints, and response shapes
- `CONTRACT_REVALIDATION.md` produced as permanent reference

## Phase 4: eSIM Access Rewrite
- Complete rewrite of provider auth (`RT-*` headers, HMAC-SHA256 uppercase)
- Complete rewrite of HTTP client (correct envelope parsing)
- Complete rewrite of adapter (correct endpoints, field mappings)
- Re-enabled: package list, order, query, topup, cancel, balance
- All provider-specific tests rewritten
- Live validation: catalog sync (2590 packages), balance query, order creation, query
- Real order placed: `B26031800280057` (Georgia 1GB/Day, $0.90)

## Phase 5: State Sync Hardening
- **Problem**: Orders stuck as `pending` with `iccid=null` even when provider had eSIM ready
- **Solution**: Implemented `ProviderStateSyncer` service
- Added immediate post-order sync in `OrderService.create_order()`
- Added manual refresh endpoint (`POST /v1/orders/{id}/refresh`)
- Added reconciliation job with stale order detection
- Enhanced webhook processing with dedup and provider query trigger
- Extended data model: 18 new eSIM fields, order state history, enhanced webhook events
- Migration 002 applied
- 29 new tests (24 unit + 5 integration), 137 total passing
- Live verification: order `B26040109460024` synced to `ready` with full eSIM details immediately

## Phase 6: Final Gateway Hardening (Current)
- **Internal service auth**: API key + scope-based authorization
- **Admin endpoints**: balance query, reconciliation trigger, webhook event inspection
- **Startup config validation**: warnings for missing credentials/clients
- **Fixed**: duplicate `query_order_full` in base.py and adapter.py
- **Documentation**: full knowledge base (9 docs)
- 10 new auth tests, 147 total passing
- Live verification: auth enforced, scopes working, admin endpoints functional
