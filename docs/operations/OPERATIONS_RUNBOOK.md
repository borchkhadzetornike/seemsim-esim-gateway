# Operations Runbook

## Common Scenarios

### Orders Stuck in Pending

**Symptoms**: Order has `status=pending` and `iccid=null` for more than a few minutes.

**Diagnosis**:
1. Check if `provider_order_no` is set — if null, the provider never received the order
2. Check `last_provider_sync_at` — if null, post-order sync may have failed
3. Check operation_logs for the order's create_order operation

**Resolution**:
```bash
# Manual refresh via API
curl -X POST http://gateway:8000/v1/orders/{order_id}/refresh \
  -H "Authorization: Bearer sk_admin_..."

# Or trigger reconciliation
curl -X POST http://gateway:8000/v1/admin/reconciliation/trigger \
  -H "Authorization: Bearer sk_worker_..."
```

### Provider Auth Failure

**Symptoms**: 502 errors with `PROVIDER_AUTH_ERROR`.

**Diagnosis**:
1. Check logs for `provider_request_complete` with `status_code=401`
2. Verify `ESIM_ACCESS_ACCESS_CODE` and `ESIM_ACCESS_SECRET_KEY` are set and correct
3. Check if the provider rotated credentials

**Resolution**: Update credentials in `.env` or secrets manager and restart the gateway.

### Webhook Processing Failure

**Symptoms**: Webhook events with `processing_status=failed`.

**Diagnosis**:
```bash
# List recent webhook events
curl http://gateway:8000/v1/admin/webhook-events?limit=20 \
  -H "Authorization: Bearer sk_admin_..."
```

Check the `processing_error` field for each failed event.

**Resolution**: The raw payload is always preserved. Fix the processing issue, then the next webhook or manual refresh will correct the state.

### How Reconciliation Works

The reconciliation job runs every 5 minutes and:
1. Acquires a Redis distributed lock (prevents duplicate execution)
2. Selects orders that are: non-terminal status, have a `provider_order_no`, and are either never-synced or last synced >10 minutes ago
3. For each order, queries the provider and merges state
4. Records state history for any changes
5. Commits all updates and releases the lock

**Manual trigger**:
```bash
curl -X POST http://gateway:8000/v1/admin/reconciliation/trigger \
  -H "Authorization: Bearer sk_worker_..."
```

### How to Diagnose Provider Failures

**Key log fields to search**:
- `provider_request_start` / `provider_request_complete` — every provider API call
- `status_code` — HTTP status from provider
- `elapsed_ms` — latency
- `error` — error details
- `order_id` — internal order ID
- `provider_order_no` — provider-assigned order number

**Key log events**:
| Event | Meaning |
|-------|---------|
| `order_created` | Order placed successfully |
| `post_order_sync_complete` | Immediate sync after order |
| `post_order_sync_failed` | Sync failed (order still saved) |
| `order_state_synced` | State merged from provider |
| `webhook_duplicate_detected` | Duplicate webhook skipped |
| `webhook_processing_failed` | Webhook processing error |
| `reconcile_orders_start` | Reconciliation job starting |
| `auth_invalid_key` | Invalid API key attempt |
| `auth_insufficient_scope` | Scope authorization failure |

### How to Diagnose Auth Failures

**401 errors** (missing/invalid key):
- Check `auth_invalid_key` events in logs
- Verify the calling service's API key matches what's in `INTERNAL_SERVICE_CLIENTS`

**403 errors** (insufficient scope or disabled):
- Check `auth_insufficient_scope` or `auth_disabled_client` in logs
- Verify the service has the required scope for the endpoint
- Check if the service client is `"enabled": true`

### Health Check Degraded

If `/health/ready` returns `"status": "degraded"`:
- Check `checks.database` and `checks.redis` in the response
- Verify PostgreSQL and Redis are running and reachable
- Check connection strings in environment

### Environment Profiles

| Setting | Development | Staging | Production |
|---------|------------|---------|------------|
| `APP_ENV` | development | staging | production |
| `APP_DEBUG` | true | false | false |
| `APP_LOG_LEVEL` | DEBUG | INFO | INFO |
| Logging format | Console | JSON | JSON |
| `ESIM_ACCESS_BASE_URL` | api.esimaccess.com | api.esimaccess.com | api.esimaccess.com |
| Service clients | Dev keys | Staging keys | Production keys |
