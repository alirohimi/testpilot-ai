# Plugin Configuration

The pytest plugin supports the following options.

## Command-line flags

| Flag | Description |
|---|---|
| `--triate` | Enable AI triage for all failures |
| `--scrub` | Enable PII scrubbing of output |
| `--api-key=KEY` | TestPilot API key (or use `TESTPILOT_API_KEY` env) |
| `--triage-dir=PATH` | Output directory for triage results (default: `triage/`) |
| `--no-llm` | Use heuristic-only classification (no API calls) |

## pytest.ini / pyproject.toml

```ini
[pytest]
addopts = --triate --scrub --triage-dir=reports/triage
```

```toml
[tool.pytest.ini_options]
addopts = "--triate --scrub --triage-dir=reports/triage"
```

## Environment variables

| Variable | Description |
|---|---|
| `TESTPILOT_API_KEY` | Your `tp_...` API key |
| `TESTPILOT_API_URL` | API base URL (default: `https://api.testpilot.ai`) |
| `TESTPILOT_NO_LLM` | Set to `1` for heuristic-only mode |

## Offline / heuristic mode

No API key? The plugin still works with local heuristics:

```bash
pytest --triate --no-llm
```

Classification runs entirely offline using the built-in rule engine (7 rules, regex + fuzzy matching). LLM suggestions are skipped.

## Scrubbing patterns

Default patterns cover:

- Emails
- Credit card numbers
- API keys / tokens (`sk_...`, `tp_...`, `ghp_...`, AWS keys)
- IPs, phone numbers

Add custom patterns in `conftest.py`:

```python
pytest_plugins = ["testpilot_ai.plugin"]

def pytest_testpilot_scrub_patterns(patterns):
    patterns["internal_id"] = r"INT-\d{6}"
```
