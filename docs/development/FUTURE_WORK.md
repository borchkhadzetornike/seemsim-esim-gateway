# Future Work

## Priority 1 — Before Production

### Real Webhook Verification
- Register webhook URL in eSIM Access admin console
- Place a test order and observe real inbound webhook
- Verify field casing, `notifyType`, and exact payload shape
- Update webhook mapping if real payload differs from docs
- **Status**: BLOCKED on provider admin configuration

### Permanent Webhook URL
- Replace ngrok with a stable public endpoint
- Options: cloud load balancer, reverse proxy, or ingress controller
- Update the eSIM Access webhook registration accordingly

### Top-up / Cancel Live Verification
- Test top-up with a real eSIM that supports it (`supportTopUpType > 0`)
- Test cancel on an unused/expendable eSIM
- Document any provider behavior differences

### Secrets Management
- Move `ESIM_ACCESS_ACCESS_CODE`, `ESIM_ACCESS_SECRET_KEY`, and `INTERNAL_SERVICE_CLIENTS` to a secrets manager
- Inject as environment variables at deployment time
- Remove secrets from `.env` file in version control

## Priority 2 — Near-Term Improvements

### JWT Service Auth Upgrade
- Replace API key auth with short-lived JWT tokens
- Deploy internal token issuer or integrate identity provider
- Scope model and CallerIdentity remain unchanged
- Migration path is a single dependency swap in `app/core/auth.py`

### Monitoring and Alerting
- Add Prometheus metrics endpoint (`/metrics`)
- Key metrics: request latency, provider call latency, error rates, reconciliation counts
- Set up alerts for: provider auth failures, high error rates, reconciliation stuck

### Request Rate Limiting
- Add per-client rate limits (especially for order creation)
- Use Redis-based sliding window counter

### Database Connection Pooling
- Review and tune async connection pool settings for production load
- Consider PgBouncer for connection pooling at scale

## Priority 3 — Platform Integration

### Platform Backend Integration
- Build platform API service that wraps gateway calls
- Add customer-facing logic: user accounts, order ownership, pricing
- Gateway remains internal; platform API is customer-facing

### Multi-Provider Support
- Add second provider adapter (e.g., another eSIM wholesaler)
- Implement provider routing (by region, price, availability)
- Gateway architecture already supports this via `BaseEsimProvider` abstraction

### Event Publishing
- Publish order state changes as events (e.g., Redis Streams, SQS, Kafka)
- Enable downstream services to react to order completion, eSIM activation, etc.
- Currently available via polling or webhook processing

### Catalog Intelligence
- Country/region search endpoint
- Price comparison across packages
- Package recommendation engine

## Priority 4 — Scale and Reliability

### Horizontal Scaling
- Gateway is stateless (all state in PostgreSQL + Redis)
- Can run multiple instances behind a load balancer
- Redis distributed locks prevent duplicate reconciliation

### Celery / Task Queue
- Replace in-process scheduler with Celery or equivalent
- Separate worker processes for reconciliation and catalog sync
- Better observability and retry management for background tasks

### Database Migrations in CI/CD
- Run Alembic migrations as part of deployment pipeline
- Add migration health checks before app startup

### API Versioning Strategy
- Current: all routes under `/v1/`
- When breaking changes needed: add `/v2/` routes alongside `/v1/`
- Deprecation policy: announce, overlap, remove
