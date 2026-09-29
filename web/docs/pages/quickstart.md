# Quickstart

Get TestPilot AI triaging your test failures in under 5 minutes.

## 1. Create an account

Sign up at [TestPilot AI](/ui/auth) or via API:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "your-password", "full_name": "Your Name"}'
```

## 2. Get an API key

After signing in, create a key from the [dashboard](/ui/keys) or via API:

```bash
curl -X POST http://localhost:8000/api/v1/auth/keys \
  -H "Authorization: Bearer <your-jwt>" \
  -H "Content-Type: application/json" \
  -d '{"name": "local-dev", "plan": "free"}'
```

Copy the `tp_...` key — it's shown **only once**.

## 3. Install the pytest plugin

```bash
pip install testpilot-ai-plugin[pytest]
```

## 4. Configure

```bash
export TESTPILOT_API_KEY="tp_your_key_here"
```

Or add to `pytest.ini` / `pyproject.toml`:

```ini
[pytest]
addopts = --triate --scrub
```

## 5. Run your tests

```bash
pytest --triate --scrub
```

You'll see:

```
✓ classified 12 failures | ✓ scrubbed 84 PII tokens
→ Triaged to /triage/results.json
```

## What's next?

- Read the [Plugin Configuration](/docs/plugin-config) guide
- Explore the [API Reference](/docs/api)
- Learn about [Triage Rules](/docs/triage-rules)
