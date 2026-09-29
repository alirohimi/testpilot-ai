# Triage Rules

The built-in heuristic engine uses 7 classification rules when LLM is unavailable or disabled.

## Rules

| Rule | Pattern | Category |
|---|---|---|
| `connection-reset` | `Connection reset|Broken pipe|ECONNRESET` | Infrastructure |
| `timeout` | `Timeout|timed out|deadline exceeded` | Environment |
| `assertion-fail` | `AssertionError|assert |expected` | Assertion |
| `not-implemented` | `NotImplementedError|not implemented` | Logic |
| `import-error` | `ImportError|ModuleNotFoundError` | Environment |
| `type-error` | `TypeError|type error` | Logic |
| `value-error` | `ValueError|value error` | Assertion |

## LLM Classification

With `--triate` (no `--no-llm`), the LLM analyzes the full traceback and suggests:

- **Category** — Infrastructure / Environment / Assertion / Logic / Unknown
- **Likely cause** — Human-readable explanation
- **Suggested fix** — Actionable recommendation
- **Confidence** — 0.0–1.0

## Custom Rules

Add patterns in `conftest.py`:

```python
def pytest_testpilot_rules(rules):
    rules.append({
        "name": "kubernetes-crash",
        "pattern": r"CrashLoopBackOff|ImagePullBackOff",
        "category": "Infrastructure",
        "suggestion": "Check pod logs with kubectl describe pod <pod>",
    })
```
