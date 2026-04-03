# eSIM Gateway — Documentation Index

> Navigation guide for all documentation in this repository.
> Start with the Overview and Architecture docs, then explore based on your role.

## Quick Start Reading Order

1. [Service Overview](../overview/SERVICE_OVERVIEW.md) — what this service is and owns
2. [Architecture](../architecture/ARCHITECTURE.md) — component map and data flows
3. [Internal API Contract](../architecture/INTERNAL_API_CONTRACT.md) — HTTP endpoints and scopes
4. [Auth & Security](../architecture/AUTH_AND_SECURITY.md) — service authentication model
5. [Operations Runbook](../operations/OPERATIONS_RUNBOOK.md) — how to run, debug, and operate

## By Category

### Overview
| Document | Purpose |
|----------|---------|
| [Service Overview](../overview/SERVICE_OVERVIEW.md) | What the gateway is, owns, and does not own |

### Architecture & Design
| Document | Purpose |
|----------|---------|
| [Architecture](../architecture/ARCHITECTURE.md) | Component map, order flow, state sync paths |
| [State Sync Design](../architecture/STATE_SYNC_DESIGN.md) | Four sync paths, concurrency, schema design |
| [Internal API Contract](../architecture/INTERNAL_API_CONTRACT.md) | Versioned HTTP contract for integrators |
| [Auth & Security](../architecture/AUTH_AND_SECURITY.md) | Internal service client auth, HMAC, rotation |

### Development
| Document | Purpose |
|----------|---------|
| [Provider Integration Notes](../development/PROVIDER_INTEGRATION_NOTES.md) | eSIM Access endpoints, quirks, status mapping |
| [Webhook Setup Notes](../development/WEBHOOK_SETUP_NOTES.md) | Provider webhook registration and handler behavior |
| [Future Work](../development/FUTURE_WORK.md) | Prioritized roadmap and known gaps |

### Operations
| Document | Purpose |
|----------|---------|
| [Operations Runbook](../operations/OPERATIONS_RUNBOOK.md) | Stuck orders, provider auth, health checks, debugging |

### Testing
| Document | Purpose |
|----------|---------|
| [Testing Guide](../testing/TESTING_GUIDE.md) | How to run pytest, test categories, auth fixtures |

### QA Evidence & Reports
| Document | Purpose |
|----------|---------|
| [Readiness Matrix](../qa/READINESS_MATRIX.md) | Current go/no-go verification matrix |
| [Gateway Final Test Report](../qa/GATEWAY_FINAL_TEST_REPORT.md) | Auth finalization test pass |
| [Final Gateway Test Report](../qa/FINAL_GATEWAY_TEST_REPORT.md) | Live order + state sync test pass |
| [Webhook Live Evidence](../qa/WEBHOOK_LIVE_EVIDENCE.md) | Manual webhook POST evidence |
| [Sandbox Evidence](../qa/SANDBOX_EVIDENCE.md) | Raw API shape evidence (partially stale) |
| [Final Pre-Flight](../qa/FINAL_PRE_FLIGHT.md) | Pre-flight checklist before validation |
| [Test Run Report](../qa/TEST_RUN_REPORT.md) | Mar 31 live test run (historical) |
| [Package Shortlist](../qa/PACKAGE_SHORTLIST.md) | Cheap test package comparison |
| [Final Readiness Matrix](../qa/FINAL_READINESS_MATRIX.md) | Earlier readiness snapshot (superseded by Readiness Matrix) |

### History & Changelog
| Document | Purpose |
|----------|---------|
| [Change History Summary](../history/CHANGE_HISTORY_SUMMARY.md) | Phase-by-phase project timeline |
| [State Sync Changelog](../history/STATE_SYNC_CHANGELOG.md) | Implementation changelog for state sync |
| [eSIM Access Rewrite Changelog](../history/ESIMACCESS_REWRITE_CHANGELOG.md) | Yoni → eSIM Access migration details |
| [Contract Revalidation](../history/CONTRACT_REVALIDATION.md) | Why Yoni integration was wrong |
| [Gateway Finalization Plan](../history/GATEWAY_FINALIZATION_PLAN.md) | Hardening plan (all phases completed) |
| [Final Recommendation](../history/FINAL_RECOMMENDATION.md) | Pre-state-sync executive summary (historical) |
| [Pre-Flight Review](../history/PRE_FLIGHT_REVIEW.md) | Yoni-era code review (historical only) |
| [Changelog Repair](../history/CHANGELOG_REPAIR.md) | Yoni-era repair log (historical only) |
| [Provider Contract Verification](../history/PROVIDER_CONTRACT_VERIFICATION.md) | Yoni verification (obsolete — see Contract Revalidation) |

## Notes for Future Work
- Documents under `history/` are preserved for context but may reference outdated provider (Yoni) or pre-state-sync state
- The canonical provider integration is **eSIM Access** — see [Provider Integration Notes](../development/PROVIDER_INTEGRATION_NOTES.md)
- QA evidence docs are point-in-time snapshots; check dates when referencing
