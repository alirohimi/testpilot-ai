# TestPilot AI

[![PyPI version](https://badge.fury.io/py/testpilot-ai.svg)](https://badge.fury.io/py/testpilot-ai)
[![CI](https://github.com/alirohimi/testpilot-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/alirohimi/testpilot-ai/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/releases/python-313/)

**AI-powered test-failure triage for Python.** One pytest plugin, one REST API,
one deployable SaaS — all in one repo.

---

## What is TestPilot AI?

TestPilot AI is a pytest plugin + REST API that uses AI to:

- **Triage** test failures — classify each failure by root cause, severity, and
  recommended action
- **Scrub** sensitive data (PII, tokens, credentials) from test output before
  it reaches an LLM or a log aggregator
- **Classify** failures into actionable buckets (flaky, env, assertion,
  timeout, data)
- **Suggest** concrete fixes

It ships three ways:

| Mode | What you get | When to use |
|---|---|---|
| **pytest plugin** (`pytest --testpilot`) | Triage + scrub + classify in your local test run | Dev, CI pre-merge |
| **REST API** (FastAPI, port 8000) | `POST /api/v1/check` — one test output in, triage verdict out | CI pipelines, IDE integrations |
| **SaaS** (Render free + Supabase) | Full dashboard, API keys, rate limits, Stripe billing | Production / team use |

## Repository layout

```
api/                     # FastAPI REST app (auth, keys, check, health)
src/testpilot_ai/        # The core library (plugin, triage, scrubber, classifier, llm)
tests/                   # pytest suite (120 tests, all passing)
web/                     # Static site (landing, dashboard, docs) → GitHub Pages
supabase/migrations/     # Production Postgres schema (idempotent)
scripts/                 # deploy.sh, test.sh helpers
docs/                    # Longer-form docs (SaaS readiness, build summary, API docs)
render.yaml              # Render free-tier web-service blueprint
fly.toml                 # Fly.io alternative deploy
docker-compose.yml       # Local dev (Postgres + Redis + app)
FREE_TIER_DEPLOY.md      # No-credit-card deploy guide (Render + Supabase)
CONTRIBUTING.md          # How to contribute
```

## Quick start — pytest plugin

```bash
pip install testpilot-ai
pytest --testpilot --testpilot-scrub
```

Options:

| Flag | Effect |
|---|---|
| `--testpilot` | Enable AI triage on test failures |
| `--testpilot-scrub` | Scrub PII/credentials from output before triage |
| `--testpilot-classify` | Add classification buckets |
| `--testpilot-api-key=...` | Your OpenAI key (optional; falls back to heuristics without it) |

## Quick start — REST API (local)

```bash
git clone https://github.com/alirohimi/testpilot-ai.git
cd testpilot-ai
uv venv .venv && source .venv/bin/activate
uv pip install -e ".[test]"

# SQLite (zero-config)
DATABASE_URL= .venv/bin/uvicorn api.main:app --port 8000

# or Postgres (Supabase / local)
DATABASE_URL="postgresql://user:pass@localhost:5432/testpilot" \
  .venv/bin/uvicorn api.main:app --port 8000
```

Key endpoints:

```
GET  /health                 # liveness + DB connectivity
GET  /openapi.json           # full OpenAPI spec
POST /api/v1/auth/register   # { email, password, full_name? }
POST /api/v1/auth/login      # { email, password }
POST /api/v1/keys            # create an API key (authenticated)
POST /api/v1/check           # one test output → triage verdict
POST /api/v1/batch-check     # N test outputs in one call
```

## Deploy — free tier (no credit card)

See [**FREE_TIER_DEPLOY.md**](FREE_TIER_DEPLOY.md) for the full guide. Short
version:

1. Create a free [Supabase](https://supabase.com) project.
2. Run the schema in `supabase/migrations/0001_testpilot_schema.sql` in the
   Supabase SQL editor.
3. Create a free [Render](https://render.com) web service from this repo —
   `render.yaml` is auto-detected.
4. Set `DATABASE_URL` (Supabase URI), `SECRET_KEY`, `JWT_SECRET_KEY` as env
   vars. Done.

The app uses in-memory rate limiting when `REDIS_URL` is unset, so no paid
Redis is needed.

## Run the tests

```bash
pytest tests/ -q                # 120 tests, all passing
```

Or:

```bash
scripts/test.sh
```

## License

MIT — see [LICENSE](LICENSE).
