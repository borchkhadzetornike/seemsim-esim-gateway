# Authentication and Security

## Auth Model: Config-Driven API Keys

The gateway uses a simple, practical API key model suitable for internal service-to-service communication.

### How It Works

1. Each calling service (seemsim-platform-backend, seemsim-worker, seemsim-admin, etc.) has a dedicated API key
2. Keys are configured via the `INTERNAL_SERVICE_CLIENTS` environment variable (JSON array)
3. Callers pass their key in the `Authorization: Bearer <key>` header
4. The gateway validates the key, checks enabled status, and verifies scopes
5. Caller identity is injected into structured logs for tracing

### Client Configuration Format

```json
[
  {
    "name": "seemsim-platform-backend",
    "api_key": "sk_platform_<random>",
    "enabled": true,
    "scopes": ["catalog:read", "orders:create", "orders:read", "orders:refresh", "esims:read", "balance:read", "topup:create", "cancel:create"]
  },
  {
    "name": "seemsim-worker",
    "api_key": "sk_worker_<random>",
    "enabled": true,
    "scopes": ["catalog:sync", "reconciliation:run", "orders:refresh"]
  },
  {
    "name": "seemsim-admin",
    "api_key": "sk_admin_<random>",
    "enabled": true,
    "scopes": ["catalog:read", "catalog:sync", "orders:create", "orders:read", "orders:refresh", "esims:read", "balance:read", "topup:create", "cancel:create", "reconciliation:run", "admin:ops"]
  }
]
```

### Key Rotation

1. Add new key for the service (with a different api_key value)
2. Update the calling service to use the new key
3. Disable the old key by setting `"enabled": false`
4. Remove the old key after confirming no traffic uses it

### Unauthenticated Endpoints

| Endpoint | Reason |
|----------|--------|
| `GET /health/live` | Kubernetes/Docker health probes |
| `GET /health/ready` | Kubernetes/Docker readiness probes |
| `POST /v1/provider/webhooks/esim-access` | Provider-initiated callback |

### Webhook Security

The webhook endpoint is unauthenticated because the provider initiates calls to it. Security measures:
- Raw payload is always persisted before processing (forensic evidence)
- Processing failures don't lose data
- Duplicate detection prevents replay-based state corruption
- The webhook triggers a provider query for authoritative state (doesn't trust webhook alone)

### Future Upgrade: JWT Service Auth

When the platform outgrows API keys:
1. Deploy an internal token issuer (or use an identity provider)
2. Services request short-lived JWTs with scope claims
3. Gateway validates JWT signature and expiry
4. Swap `get_caller_identity` dependency to JWT validation
5. The scope model and CallerIdentity dataclass remain the same

The upgrade is a single dependency change — no route or scope changes needed.

### Secrets Management

**Current**: Keys are in the `.env` file and `INTERNAL_SERVICE_CLIENTS` env var.

**Production recommendations**:
- Use a secrets manager (AWS Secrets Manager, HashiCorp Vault, GCP Secret Manager)
- Inject secrets as environment variables at runtime
- Never commit real keys to version control
- Rotate keys periodically
- Monitor auth failures in logs (`auth_invalid_key`, `auth_disabled_client`, `auth_insufficient_scope`)
