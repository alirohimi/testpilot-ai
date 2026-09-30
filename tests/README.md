# TestPilot AI - Test Suite

## Overview

This test suite provides comprehensive coverage for the TestPilot AI application including:
- **Authentication**: Signup, login, session management
- **CRUD Operations**: API key management (Create, Read, Delete)
- **Core API**: Failure check and batch check endpoints
- **Integration**: Full user journey tests
- **Security**: Password handling, token security, user isolation
- **Frontend**: Page structure and cross-page consistency

## The Signup Error

The error **"The string did not match the expected pattern"** occurs because:

1. **Browser-level validation**: The HTML input uses `type="email"` which validates format client-side
2. **Missing server-side validation**: The `UserRegister` model uses `email: str` (plain string) instead of `EmailStr`
3. **Missing email-validator dependency**: Pydantic v2's `EmailStr` requires `email-validator` package

### Fix Required

In `api/main.py`, change line 68:
```python
# FROM:
class UserRegister(BaseModel):
    email: str

# TO:
from pydantic import EmailStr

class UserRegister(BaseModel):
    email: EmailStr
```

And install the dependency:
```bash
pip install email-validator
```

## Running Tests

### Quick Start
```bash
cd /opt/data/projects/testpilot-ai
source venv/bin/activate
pytest tests/ -v
```

### Run Specific Test Files
```bash
pytest tests/test_api_auth.py -v
pytest tests/test_api_login.py -v
pytest tests/test_api_crud.py -v
pytest tests/test_api_integration.py -v
pytest tests/test_frontend_e2e_local.py -v
```

### Run with Coverage
```bash
pytest tests/ -v --cov=api --cov-report=html
```

### Run Specific Test Class
```bash
pytest tests/test_api_auth.py::TestSignUp -v
pytest tests/test_api_crud.py::TestAPIKeyCreate -v
```

## Test Coverage

| Category | File | Status |
|----------|------|--------|
| **Signup** | `test_api_auth.py` | Created |
| **Login** | `test_api_login.py` | Created |
| **API Key CRUD** | `test_api_crud.py` | Created |
| **Integration** | `test_api_integration.py` | Created |
| **Frontend E2E** | `test_frontend_e2e_local.py` | Created |
| **Shared Fixtures** | `conftest.py` | Created |

## Test Categories

### Auth Tests (`test_api_auth.py`)
- Valid registration with/without name
- Duplicate email rejection
- Invalid email formats
- Short/empty passwords
- Special characters in emails
- Unicode emails
- Long email addresses

### Login Tests (`test_api_login.py`)
- Successful login
- Wrong password
- Non-existent user
- Empty/missing fields
- Case sensitivity
- Whitespace handling
- Invalid email formats
- Token format validation
- Concurrent logins

### CRUD Tests (`test_api_crud.py`)
- Create: Valid keys, missing fields, invalid tiers
- Read: Empty lists, populated lists, user isolation
- Delete: Success, 404, cross-user deletion prevention
- Token security: No key leaks in list responses
- Usage endpoint

### Integration Tests (`test_api_integration.py`)
- Full signup → login → create key → check failure journey
- Multi-user isolation
- Password hashing verification
- LLM check (when available)
- Batch checks
- Unicode error messages
- Rapid requests (rate limiting)

### Frontend Tests (`test_frontend_e2e_local.py`)
- Page structure validation
- Form element presence
- API endpoint configuration
- Cross-page consistency (fonts, paths)
- Security checks (no hardcoded credentials)
- HTTPS enforcement

## Fixing the Signup Issue

The root cause is missing server-side email validation. Apply this fix:

```python
# api/main.py
from pydantic import BaseModel, Field
from pydantic import EmailStr  # ADD THIS
from typing import Optional

class UserRegister(BaseModel):
    email: EmailStr  # CHANGE FROM str
    password: str
    full_name: Optional[str] = None
```

Then add `email-validator` to your dependencies:
```bash
pip install email-validator
```

## CI/CD Integration

Add to your `.github/workflows/test.yml`:
```yaml
- name: Run Tests
  run: |
    source venv/bin/activate
    pip install pytest httpx email-validator
    pytest tests/ -v --cov=api --cov-report=xml
```

## Notes

- Tests use SQLite in-memory database for isolation
- Database is cleaned up after each test via `cleanup_db` fixture
- Some tests document current behavior (may indicate bugs)
- Security tests verify no credential leakage
- Cross-user isolation tests ensure data security
