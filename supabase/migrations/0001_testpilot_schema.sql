-- TestPilot AI — Supabase Postgres schema (best-practice, least-privilege app role)
-- Safe to re-run: uses IF NOT EXISTS + DROP POLICY IF EXISTS.

BEGIN;

-- ── 1. Application Postgres role (least privilege, NOT superuser) ───────────
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'testpilot_app') THEN
        CREATE ROLE testpilot_app LOGIN;
    END IF;
END $$;
ALTER ROLE testpilot_app WITH PASSWORD '4NfvgNwYMDquWGOyttoXdY4r';
-- Grant schema + future-table privileges to the app role
GRANT USAGE ON SCHEMA public TO testpilot_app;
GRANT CREATE ON SCHEMA public TO testpilot_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO testpilot_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO testpilot_app;

-- ── 2. Tables ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
  id            SERIAL PRIMARY KEY,
  email         VARCHAR(255) NOT NULL UNIQUE,
  hashed_password VARCHAR(255) NOT NULL,
  full_name     VARCHAR(255),
  is_active     BOOLEAN NOT NULL DEFAULT TRUE,
  is_verified   BOOLEAN NOT NULL DEFAULT FALSE,
  created_at    TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS users_email_idx ON users(email);

CREATE TABLE IF NOT EXISTS api_keys (
  id          SERIAL PRIMARY KEY,
  user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  key_hash    VARCHAR(64) NOT NULL UNIQUE,
  name        VARCHAR(100) NOT NULL,
  prefix      VARCHAR(12) NOT NULL,
  tier        VARCHAR(20) NOT NULL DEFAULT 'free',
  is_active   BOOLEAN NOT NULL DEFAULT TRUE,
  last_used_at TIMESTAMP,
  created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS api_keys_key_hash_idx ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS api_keys_user_idx ON api_keys(user_id);

CREATE TABLE IF NOT EXISTS subscriptions (
  id                          SERIAL PRIMARY KEY,
  user_id                     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  stripe_subscription_id      VARCHAR(255) UNIQUE,
  stripe_customer_id          VARCHAR(255) UNIQUE,
  plan_id                     VARCHAR(50) NOT NULL DEFAULT 'free',
  status                      VARCHAR(20) NOT NULL DEFAULT 'active',
  current_period_start        TIMESTAMP,
  current_period_end          TIMESTAMP,
  cancel_at_period_end        BOOLEAN NOT NULL DEFAULT FALSE,
  created_at                  TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at                  TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS subscriptions_user_idx ON subscriptions(user_id);

CREATE TABLE IF NOT EXISTS usage_logs (
  id                  SERIAL PRIMARY KEY,
  api_key_id          INTEGER NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
  user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  endpoint            VARCHAR(50) NOT NULL,
  check_type          VARCHAR(50) NOT NULL DEFAULT 'standard',
  success             BOOLEAN NOT NULL DEFAULT TRUE,
  response_time_ms    INTEGER,
  timestamp           TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS usage_logs_key_time_idx ON usage_logs(api_key_id, timestamp);
CREATE INDEX IF NOT EXISTS usage_logs_user_idx ON usage_logs(user_id);

CREATE TABLE IF NOT EXISTS failure_analyses (
  id                    SERIAL PRIMARY KEY,
  user_id               INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  error_message_hash    VARCHAR(64) NOT NULL,
  error_message         TEXT NOT NULL,
  failure_type          VARCHAR(50),
  severity              VARCHAR(20),
  category              VARCHAR(50),
  suggested_fix         TEXT,
  root_cause            TEXT,
  confidence            DOUBLE PRECISION NOT NULL DEFAULT 0,
  llm_analyzed          BOOLEAN NOT NULL DEFAULT FALSE,
  created_at            TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS failure_analyses_hash_idx ON failure_analyses(error_message_hash);
CREATE INDEX IF NOT EXISTS failure_analyses_user_idx ON failure_analyses(user_id);

-- ── 3. Grant the app role full CRUD + sequence rights (no ownership needed) ─
GRANT SELECT, INSERT, UPDATE, DELETE ON users, api_keys, subscriptions, usage_logs, failure_analyses TO testpilot_app;
GRANT USAGE, SELECT ON SEQUENCE users_id_seq, api_keys_id_seq, subscriptions_id_seq, usage_logs_id_seq, failure_analyses_id_seq TO testpilot_app;

-- ── 4. RLS: enabled on every public table (Supabase best practice) ─────────
ALTER TABLE users            ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys         ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions    ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_logs       ENABLE ROW LEVEL SECURITY;
ALTER TABLE failure_analyses ENABLE ROW LEVEL SECURITY;

-- Drop any prior policies with these names so re-runs don't fail
DROP POLICY IF EXISTS "users_self"            ON users;
DROP POLICY IF EXISTS "api_keys_self"         ON api_keys;
DROP POLICY IF EXISTS "subscriptions_self"    ON subscriptions;
DROP POLICY IF EXISTS "usage_logs_self"       ON usage_logs;
DROP POLICY IF EXISTS "failure_analyses_self" ON failure_analyses;

-- Policy names are stable; USING/WITH CHECK restrict to the calling user's rows.
CREATE POLICY "users_self" ON users TO authenticated
  USING (id = (SELECT id FROM users WHERE email = (SELECT a.email FROM auth.users a WHERE a.id = auth.uid()) LIMIT 1))
  WITH CHECK (id = (SELECT id FROM users WHERE email = (SELECT a.email FROM auth.users a WHERE a.id = auth.uid()) LIMIT 1));

CREATE POLICY "api_keys_self" ON api_keys TO authenticated
  USING (user_id = (SELECT id FROM users WHERE email = (SELECT a.email FROM auth.users a WHERE a.id = auth.uid()) LIMIT 1))
  WITH CHECK (user_id = (SELECT id FROM users WHERE email = (SELECT a.email FROM auth.users a WHERE a.id = auth.uid()) LIMIT 1));

CREATE POLICY "subscriptions_self" ON subscriptions TO authenticated
  USING (user_id = (SELECT id FROM users WHERE email = (SELECT a.email FROM auth.users a WHERE a.id = auth.uid()) LIMIT 1))
  WITH CHECK (user_id = (SELECT id FROM users WHERE email = (SELECT a.email FROM auth.users a WHERE a.id = auth.uid()) LIMIT 1));

CREATE POLICY "usage_logs_self" ON usage_logs TO authenticated
  USING (user_id = (SELECT id FROM users WHERE email = (SELECT a.email FROM auth.users a WHERE a.id = auth.uid()) LIMIT 1))
  WITH CHECK (user_id = (SELECT id FROM users WHERE email = (SELECT a.email FROM auth.users a WHERE a.id = auth.uid()) LIMIT 1));

CREATE POLICY "failure_analyses_self" ON failure_analyses TO authenticated
  USING (user_id = (SELECT id FROM users WHERE email = (SELECT a.email FROM auth.users a WHERE a.id = auth.uid()) LIMIT 1))
  WITH CHECK (user_id = (SELECT id FROM users WHERE email = (SELECT a.email FROM auth.users a WHERE a.id = auth.uid()) LIMIT 1));

COMMIT;

-- ── 5. Prove it (post-commit sanity) ───────────────────────────────────────
SELECT 'testpilot_app role created' AS check1
 WHERE EXISTS (SELECT FROM pg_roles WHERE rolname='testpilot_app');
