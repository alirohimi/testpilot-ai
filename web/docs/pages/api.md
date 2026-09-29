# API Reference

Base URL: `https://api.testpilot.ai` (or your self-hosted endpoint)

All endpoints require either `Authorization: Bearer <JWT>` or `X-API-Key: tp_...`.

## Auth

### Register

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "strongpassword",
  "full_name": "Jane Doe"
}
```

Response: `201 Created` — `{ "access_token", "token_type", "user": {...} }`

### Login

```http
POST /api/v1/auth/login
Content-Type: application/json

{ "email": "user@example.com", "password": "..." }
```

### API Keys

```http
GET  /api/v1/auth/keys          — List keys
POST /api/v1/auth/keys          — Create key
DELETE /api/v1/auth/keys/{id}   — Revoke key
```

## Triage

```http
POST /api/v1/triage/classify
POST /api/v1/triage/run         — Full triage pipeline
GET  /api/v1/triage/results     — Get results
```

## Scrub

```http
POST /api/v1/scrub
Body: { "text": "<test output>" }
```

## Usage

```http
GET /api/v1/usage/summary       — Credits used, plan info
```

## Health

```http
GET /api/v1/health
```

Full interactive spec: `/docs` (Swagger UI)
