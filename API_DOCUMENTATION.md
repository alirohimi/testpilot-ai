# TestPilot AI API - Complete Documentation

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Stripe account (for payments)
- OpenAI API key (optional, for LLM features)

### Installation

```bash
# Clone repository
git clone https://github.com/alirohimi/testpilot-ai.git
cd testpilot-ai

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your configuration

# Initialize database
alembic upgrade head

# Run development server
uvicorn api.main:app --reload --port 8000
```

### Docker Deployment

```bash
# Start with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f api
```

---

## 📚 API Documentation

Base URL: `http://localhost:8000`

Interactive docs: `http://localhost:8000/docs`

### Authentication

#### Register User
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123",
  "full_name": "John Doe"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user_id": 1,
  "plan": "free"
}
```

#### Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

#### Get Current User
```http
GET /api/v1/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

---

### API Keys

#### Create API Key
```http
POST /api/v1/keys
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Content-Type: application/json

{
  "name": "Production Key",
  "tier": "pro"
}
```

**Response:**
```json
{
  "key": "tp_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "name": "Production Key",
  "tier": "pro",
  "created_at": "2026-09-29T12:00:00Z",
  "prefix": "tp_a1b2c3d4..."
}
```

⚠️ **Save this key securely!** It will only be shown once.

#### List API Keys
```http
GET /api/v1/keys
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

#### Delete API Key
```http
DELETE /api/v1/keys/{key_id}
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

---

### Core API

#### Analyze Test Failure
```http
POST /api/v1/check
X-API-Key: tp_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
Content-Type: application/json

{
  "error_message": "AssertionError: Expected 5 but got 3",
  "test_code": "assert result == 5",
  "include_scrubbed": true,
  "use_llm": false
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "failure_type": "assertion_error",
    "severity": "medium",
    "category": "test_logic",
    "suggested_fix": "Check the expected value in the assertion",
    "root_cause": "Test expectation does not match actual result",
    "confidence": 0.9,
    "scrubbed_error": "AssertionError: Expected 5 but got 3"
  },
  "request_id": "a1b2c3d4e5f6",
  "timestamp": "2026-09-29T12:00:00Z",
  "plan": "pro"
}
```

#### Batch Analysis
```http
POST /api/v1/batch-check
X-API-Key: tp_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
Content-Type: application/json

[
  {
    "error_message": "AssertionError: Expected 5 but got 3"
  },
  {
    "error_message": "ModuleNotFoundError: No module named 'requests'"
  }
]
```

---

### Usage & Billing

#### Get Usage Stats
```http
GET /api/v1/usage
X-API-Key: tp_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

**Response:**
```json
{
  "checks_used": 150,
  "checks_remaining": 4850,
  "plan": "pro",
  "limit": 5000
}
```

#### Get Subscription Details
```http
GET /api/v1/subscription
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

#### Upgrade Subscription
```http
POST /api/v1/subscription/upgrade
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Content-Type: application/json

{
  "plan": "pro"
}
```

#### Cancel Subscription
```http
POST /api/v1/subscription/cancel
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

---

## 💰 Pricing

| Plan | Price | Monthly Checks | Features |
|------|-------|----------------|----------|
| **Free** | $0 | 100 | Basic scrubbing, classification |
| **Pro** | $19/mo | 5,000 | LLM analysis, batch processing |
| **Team** | $49/mo | 25,000 | Slack alerts, Jira sync, priority support |
| **Enterprise** | $199/mo | Unlimited | On-premise, SSO, custom integrations |

---

## 🔒 Security

- All passwords are hashed with bcrypt
- API keys are hashed with SHA-256
- JWT tokens expire after 7 days
- Rate limiting prevents abuse
- CORS configured for browser access

---

## 📊 Monitoring

The API includes:
- ✅ Health check endpoint (`/health`)
- ✅ Error tracking with Sentry
- ✅ Usage logging
- ✅ Rate limiting per tier

---

## 🚀 Deployment

### Fly.io
```bash
fly launch
fly deploy
```

### Render
```bash
# Connect GitHub repo to Render
# Configure environment variables
# Deploy automatically on push
```

### Docker
```bash
docker-compose up -d
```

---

## 🧪 Testing

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=api --cov-report=html
```

---

## 📝 Environment Variables

See `.env.example` for all required variables.

---

## 🤝 Support

- 📧 Email: support@testpilot.ai
- 💬 Slack: #support
- 📚 Docs: https://testpilot.ai/docs
- 🐛 Issues: https://github.com/alirohimi/testpilot-ai/issues

---

*Last updated: September 29, 2026*
