# Production Handoff — TestPilot AI

Everything below is what I **could not do from the dev box** because it needs
your credentials, a paid dashboard, or external service access. All code/config
is done, tested, and pushed to `main` @ `93db45d`. This is the checklist to
finish the last mile.

**Status at handoff**
- ✅ 131/131 tests passing, ruff + black clean, CI gates green
- ✅ Stripe webhook fulfilment implemented (verified against Stripe API docs)
- ✅ GDPR export/delete endpoints + tests
- ✅ Structured logging, Sentry hook, CORS allowlist
- ⬜ Production deploy still needs the steps below

---

## 1. Supabase — apply schema + create app role (one-time, ~5 min)

I validated the schema on a real local Postgres, but I couldn't reach the live
Supabase DB from here (IPv6-only route + no password). Do this once:

1. Supabase dashboard → **SQL Editor** → paste the contents of
   `supabase/migrations/0001_testpilot_schema.sql` → run.
2. Confirm it created: `users`, `api_keys`, `subscriptions`, `usage_logs`,
   `failure_analyses` + the `testpilot_app` role + RLS policies.
3. In `.env` (and Render env vars), set:
   ```
   DATABASE_URL=postgresql://postgres.<project-ref>:<your-pw>@aws-0-<region>.pooler.supabase.com:5432/postgres
   ```

## 2. Render — deploy (one-time, ~10 min)

1. Render dashboard → **New → Web Service** → point at
   `alirohimi/testpilot-ai` (Render auto-reads `render.yaml`).
2. Set env vars (the `sync: false` ones in `render.yaml`):
   - `DATABASE_URL` (from step 1)
   - `ALLOWED_ORIGINS` — your frontend origin(s), comma-separated. **Required**
     now that CORS is allowlisted.
   - `STRIPE_WEBHOOK_SECRET` (from step 3) if enabling payments
   - `OPENAI_API_KEY` if enabling LLM analysis
   - `SENTRY_DSN` (optional) — leave empty on the free tier.
3. Verify the service passes its `/health` check, then:
   ```
   curl https://<your-render-app>.onrender.com/health
   # expect: {"status":"healthy", "redis":"not_configured", ...}
   ```

## 3. Stripe — enable real payments (only if selling; skip for free tier)

1. Create two test prices in the Stripe Dashboard (Pro + Team). Put the IDs in
   `STRIPE_PRICE_PRO` / `STRIPE_PRICE_TEAM` env vars.
2. Create a webhook endpoint in the Stripe Dashboard pointing at
   `https://<your-render-app>.onrender.com/api/v1/webhooks/stripe`, subscribed
   to these four events:
   - `checkout.session.completed`
   - `invoice.payment_succeeded`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
3. Copy the **endpoint secret** into `STRIPE_WEBHOOK_SECRET`.
4. Test end-to-end: trigger a test-mode checkout in Stripe, and watch the
   webhook land in your Render logs (structured JSON log line
   `webhook checkout completed: user N -> pro`).

## 4. Verification checklist (run after each step)

| Check | How | Pass |
|---|---|---|
| App up | `curl /health` | 200, `"database":"connected"` |
| Persisted data | Register a user, then re-run `curl /health` | user row survives restart |
| CORS | Open frontend origin, check DevTools preflight | no `Access-Control` errors |
| Webhook | Stripe test event | 200 + subscription row updated |
| GDPR export | `GET /api/v1/me/export` | JSON with account + child data |
| GDPR delete | `DELETE /api/v1/me` | user + all children gone |
| Logs | Render log viewer | JSON lines, not plain text |

---

## What I did NOT touch (out of scope / needs your call)
- **Email/SMTP** — `.env.example` has SMTP vars but no code wires them yet.
  No email flows are implemented (verification, receipts). Add when needed.
- **Multi-instance rate limiting** — the app auto-falls back to in-memory
  limits. If you scale Render beyond 1 instance, point `REDIS_URL` at a real
  Redis (the code already supports it).
- **Stripe `create_subscription` client-side flow** — the *webhook* path is
  real now; the client-facing "upgrade" endpoint still calls Stripe's API
  directly, which needs your live key to exercise. Covered by step 3.
