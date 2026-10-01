# TestPilot AI — Free-Tier Deployment (no credit card)

A production-grade stack that runs entirely on **free** tiers with **persistent**
Postgres. No paid services, no credit card required.

| Layer | Service | Cost | Why |
|---|---|---|---|
| **App** | Render free web service | $0 | Managed deploy, auto-SSL, source-build from this repo |
| **Database** | Supabase (managed Postgres) | $0 | **Persistent** — data survives restarts and idle-sleeps |
| **Cache** | *(none — in-memory fallback)* | $0 | App auto-detects missing Redis and falls back to in-memory rate limiting |

> **The key property:** Render free instances *sleep* after ~15 min of no traffic,
> so an in-container SQLite DB would lose data on each wake. Supabase Postgres
> lives outside the app, so user data **persists** across cold starts. That's the
> whole reason for this stack.

---

## 1. What's already in the repo (no action needed)

- `render.yaml` — blueprint for the Render free web service (Python 3.13,
  `uvicorn api.main:app` on `$PORT`, `/health` health-check, `REDIS_URL=""` so
  the app uses in-memory rate limiting).
- `supabase/migrations/0001_testpilot_schema.sql` — the full schema:
  5 tables (`users`, `api_keys`, `subscriptions`, `usage_logs`,
  `failure_analyses`), indexes, a least-privilege `testpilot_app` role, and
  row-level-security policies keyed to Supabase's `auth.uid()`.
  **Idempotent** — safe to re-apply (`IF NOT EXISTS` / `DROP POLICY IF EXISTS`).
- Password hashing uses **`bcrypt` directly** (passlib 1.7.4 is incompatible
  with bcrypt 5.x). Truncates to bcrypt's 72-byte limit.
- On first boot, `init_db()` runs `Base.metadata.create_all()`, so any table
  the ORM defines that's missing will be created automatically.

---

## 2. You do (2 manual steps — both free, no card)

### Step 1 — Supabase: create project + apply schema + copy the DB connection string

1. `supabase.com` → **New project**.
   - Any name (e.g. `testpilot`). Region near you.
   - Choose a **DB password** — it's shown **once**. Save it; you can't
     retrieve it later.
2. **Apply the schema.** In the Supabase project, open
   **SQL Editor → New query**, paste the entire contents of
   `supabase/migrations/0001_testpilot_schema.sql`, click **Run**.
   (Supabase already has the `authenticated`/`anon`/`service_role` roles and
   `auth.users`/`auth.uid()` that the RLS policies reference — those are
   built in, so the file applies cleanly there. You do **not** need to
   create them.)
3. **Connection string:** Supabase → **Project Settings → Database →
   Connection string → URI**, use the **db.** form:
   ```
   postgresql://postgres.<project-ref>:<DB_PASSWORD>@db.<project-ref>.supabase.co:5432/postgres
   ```
   Copy it. You'll paste it into Render as `DATABASE_URL`.

   > Locally `.env` uses the `postgresql+psycopg2://` SQLAlchemy dialect, which
   > is fine for dev. For Render just use the plain `postgresql://` URI from
   > Supabase — `psycopg2-binary` is already a dependency.

### Step 2 — Render: deploy the app

1. `render.com` → **New → Web Service → Connect to Git Repo** → pick
   `alirohimi/testpilot-ai`.
2. Render auto-detects the `render.yaml` blueprint. Confirm:
   - **Environment:** Python 3.13
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
   - **Health check path:** `/health`
   - **Instance:** Free
3. Under **Environment Variables**, add:
   | Key | Value |
   |---|---|
   | `DATABASE_URL` | the Supabase URI from Step 1.3 |
   | `SECRET_KEY` | Render can auto-generate, or paste any 32+ char string |
   | `JWT_SECRET_KEY` | a strong random string (≠ the app secret) |
   | `REDIS_URL` | leave empty / unset (in-memory fallback kicks in) |
   | `OPENAI_API_KEY` | *optional* — only if you want LLM-based triage |
   | `STRIPE_SECRET_KEY` | *optional* — only if you want billing |
4. **Create Web Service.**

---

## 3. Verify end-to-end (the persistence proof)

Once the Render URL is live (e.g. `https://testpilot-ai.onrender.com`):

1. **Health + Postgres:**
   ```bash
   curl -s https://<your-render-host>/health
   ```
   Expect `"database": "connected"` and **no** `sqlite` fallback in the output.
2. **API shape:**
   ```bash
   curl -s https://<your-render-host>/openapi.json | head
   ```
   Confirms the real FastAPI app is serving (routes present).
3. **Register a user:**
   ```bash
   curl -s -X POST https://<your-render-host>/api/v1/auth/register \
     -H 'Content-Type: application/json' \
     -d '{"email":"persist@test.com","password":"Pass12345!","full_name":"Persist Test"}'
   ```
   Get back a 200 + token. Confirm the row exists in Supabase:
   **Supabase → Table Editor → `users`** → your email is there.
4. **The persistence test:**
   - Wait >15 min (let Render sleep), *or* force a fresh boot from the
     Render dashboard (**Manual Deploy → Copy last deploy**).
   - Then **login** with the earlier user:
     ```bash
     curl -s -X POST https://<your-render-host>/api/v1/auth/login \
       -H 'Content-Type: application/json' \
       -d '{"email":"persist@test.com","password":"Pass12345!"}'
     ```
   - If the old user still logs in, the data **survived** the restart.
     That's the proof this stack is production-grade, not a toy.

> **Expected cold start:** the first request after ~15 min idle takes 30–60 s
> to wake the free instance. That's normal for Render free tier. If it ever
> bothers you, upgrade *just that one service* to a $7/mo instance —
> Supabase stays free.

---

## 4. Known caveats

- **Render free = cold starts** (above). Acceptable for a demo / early SaaS.
- **`OPENAI_API_KEY` / `STRIPE_*` are optional.** Without them the app runs the
  heuristic triage path only; LLM-backed analysis and Stripe billing return
  503 "feature unavailable" — by design, not an error.
- **Redis:** not required. `REDIS_URL` unset → in-memory rate limiter. Set a
  real Redis URL later only if you need shared state across multiple
  instances.
- **Schema migrations:** `init_db()` creates ORM-defined tables on boot.
  The `supabase/migrations/*.sql` file is the *source of truth* for the
  production schema (least-priv role + RLS). Keep both in sync when you add
  columns.

## 5. Security notes

- `testpilot_app` role is the least-privilege app role in the migration:
  it has `SELECT/INSERT/UPDATE/DELETE` on the app tables only — not
  superuser, not `authenticated` (which RLS restricts).
- RLS policies on all 5 tables are keyed to the current Supabase auth user
  via `auth.uid()` — a user can only read/write their own rows.
- `SECRET_KEY` and `JWT_SECRET_KEY` **must** be strong and unique in prod
  (Render can auto-generate; just don't reuse a dev key).
