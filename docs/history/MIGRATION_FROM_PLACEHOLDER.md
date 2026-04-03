# Migration from placeholder-allinone

## Migration Details

- **Source:** `placeholder-allinone/placeholder-esim-gateway/`
- **Target:** `git@github.com:borchkhadzetornike/seemsim-esim-gateway.git`
- **Date:** 2026-04-03
- **Branch:** main

## What Was Migrated

- Full application source (`app/` — API, services, providers, repositories, models, schemas, core)
- Database migrations (`alembic/` — initial schema, state sync)
- Test suites (`tests/` — unit, integration, contract)
- Docker configuration (`Dockerfile`, `docker-compose.yml`)
- Build tooling (`Makefile`, `pyproject.toml`, `.pre-commit-config.yaml`)
- Environment template (`.env.example`)
- Documentation (`docs/` tree — architecture, operations, testing, QA evidence, history)
- Root docs (`README.md`, `CHANGELOG.md`)

## Normalization Applied

- Renamed all "Placeholder" / "PlaceholderSIM" references to "SeemsIM" in docs
- Updated folder structure references from `placeholder-esim-gateway` to `seemsim-esim-gateway`
- Updated cross-service references to use `seemsim-*` naming
- Removed OS artifacts (.DS_Store)

## Excluded from Migration

- `.env` files (contain secrets; use `.env.example` template)
- `__pycache__/`, `.pytest_cache/`, `.mypy_cache/` (build artifacts)
- `.git/` from source (new repo has its own Git history)

## Unresolved Items

- Provider (eSIM Access) sandbox credentials need to be configured per environment
- Webhook callback URL needs to be updated for production deployment
- Alembic migrations should be verified against target database
