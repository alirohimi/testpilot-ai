# CLAUDE.md — TestPilot AI Repository Guidelines

## Repository Boundaries

| Path | Role | May import |
|------|------|-----------|
| `src/testpilot_ai/` | Pure library (pytest plugin, triage, scrubber, classifier, LLM client, parsers, Slack alerts) | stdlib, `openai`, `httpx`, `rich` — **no FastAPI, no SQLAlchemy, no server code** |
| `api/` | FastAPI SaaS backend (auth, keys, check, webhook, GDPR, health, rate-limiting, Stripe) | `testpilot_ai` (core), FastAPI, SQLAlchemy, httpx, stripe |
| `tests/` | Pytest suite (mirrors `src/` + `api/` structure) | `testpilot_ai`, `api` (via TestClient) |
| `web/` | Static GitHub Pages (landing, dashboard, docs) | Nothing (pure HTML/CSS/JS) |
| `supabase/migrations/` | Idempotent Postgres schema | N/A |

**Rule**: `src/testpilot_ai/` must remain dependency-light so it can be installed
by a user's CI as a GitHub Action without pulling in the entire SaaS stack.

## Python / FastAPI / Pytest Conventions

- **Python**: 3.13+ (`requires-python = ">=3.13"`)
- **Package**: setuptools via `pyproject.toml`; install with `pip install -e ".[test]"`
- **Source layout**: `src/testpilot_ai/` (not top-level `testpilot_ai/`)
- **API framework**: FastAPI + uvicorn; routes in `api/main.py` (monolithic for now —
  extract to routers in a future refactor)
- **DB**: SQLAlchemy 2.0 (async via aiosqlite for SQLite, psycopg2 for Postgres);
  engine config in `api/database.py`
- **Testing**: pytest + pytest-asyncio (`asyncio_mode = "auto"`); 131 tests, all passing
- **Lint**: ruff (E, F, W, I, UP rules; line-length 100; target py313)
- **Format**: black (line-length 100, matching ruff)
- **Type**: mypy (advisory in CI — `continue-on-error: true`; not a gate)

## CI/CD Pipeline

- **Workflow**: `.github/workflows/ci.yml` — 3 jobs: `lint` → `test` → `build`
- **Lint**: ruff + black + mypy (advisory)
- **Test**: `pytest tests/ -v --tb=short --cov=api --cov=src.testpilot_ai`
- **Build**: Docker (ghcr.io), main-branch-only, `packages: write` permission
- **Triggers**: push to main/master + pull_request to main/master

## Strict Secret-Redaction Rules

1. **Never commit** `.env`, `*.pem`, `*.key`, `id_rsa`, or any file containing
   API keys, passwords, tokens, or connection strings with real credentials.
2. `.env.example` is the **template only** — placeholders, never real values.
3. The Supabase role password in `supabase/migrations/0001_testpilot_schema.sql`
   is a **known exception** (committed for bootstrap convenience). Before making
   the repo public, rotate this password in Supabase and replace with a
   `current_setting('testpilot_role_password')` reference or Render env var.
4. CI secrets (`GITHUB_TOKEN`, `SLACK_WEBHOOK_URL`, `STRIPE_SECRET_KEY`,
   `OPENAI_API_KEY`) are injected by the platform — never hardcoded.
5. The `scrubber.py` module redacts PII/secrets from test output **before** it
   reaches any LLM or log aggregator. All new output paths must route through
   `scrubber.scrub()` or `scrubber.scrub_dict()`.
6. Pre-commit gate: `git-deliver.sh` blocks any commit that stages a file
   matching `.env`, `*secret*`, `*.pem`, `*.key`, or `id_rsa`.

## Deployment

| Target | Config | Notes |
|--------|--------|-------|
| Render (free-tier) | `render.yaml` | Python 3.13, oregon, `pip install -r requirements.txt` |
| Fly.io (alt) | `fly.toml` | |
| Docker / GHCR | `Dockerfile` | `python:3.13-slim`, uvicorn on 8000 |
| GitHub Pages | `web/` + `deploy-gh-pages.sh` | Static site |
| Supabase (DB) | `supabase/migrations/` | Project `ijwpyikcbqdskuynwsuz`, pooler port 6543 |

## Dependency Management

- **Single source of truth**: `pyproject.toml` (all deps + optional extras)
- `requirements.txt` is a **frozen copy** for Render's `pip install -r` path —
  regenerate with `python -c "from pyproject import ..."` or manually after
  changing `pyproject.toml`. Keep versions in sync.
- `uv.lock` is the lockfile for `uv`-based development.
