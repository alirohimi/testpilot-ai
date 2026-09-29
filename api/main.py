"""Main FastAPI application for TestPilot AI SaaS."""

import os
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Initialize database
from .database import init_db, get_db_session
from .models import Base
from .auth import (
    create_access_token,
    authenticate_user,
    get_password_hash,
    get_current_user,
    create_api_key,
    get_api_key_user,
    security
)
from .stripe_integration import (
    create_subscription,
    cancel_subscription,
    get_user_plan,
    get_user_limits,
    handle_webhook
)
from .rate_limiter import rate_limit, API_RATE_LIMITS

# Import TestPilot AI core
try:
    from testpilot_ai.classifier import TestPilotClassifier, FailureType
    from testpilot_ai.scrubber import Scrubber
    from testpilot_ai.triage import TriageEngine
    from testpilot_ai.llm import TestPilotLLM, LLMConfig
    TESTPILOT_AVAILABLE = True
except ImportError:
    TESTPILOT_AVAILABLE = False
    print("⚠️  TestPilot AI core not available in API context")

# Create FastAPI app
app = FastAPI(
    title="TestPilot AI API",
    description="AI-powered test failure triage and scrubbing API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================
# Request/Response Models
# =====================

class UserRegister(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    plan: str

class APIKeyCreate(BaseModel):
    name: str
    tier: str = "free"

class APIKeyResponse(BaseModel):
    key: str
    name: str
    tier: str
    created_at: str
    prefix: str

class FailureCheck(BaseModel):
    error_message: str
    test_code: Optional[str] = None
    include_scrubbed: bool = True
    use_llm: bool = False

class UsageStats(BaseModel):
    checks_used: int
    checks_remaining: int
    plan: str
    limit: int
    reset_at: Optional[str] = None

class ApiResponse(BaseModel):
    success: bool
    result: dict
    request_id: str
    timestamp: str
    plan: str


# =====================
# Database Initialization
# =====================

@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    init_db()
    print("🚀 TestPilot AI API started")


# =====================
# Auth Endpoints
# =====================

@app.post("/api/v1/auth/register", response_model=TokenResponse)
async def register(user_data: UserRegister, db=Depends(get_db_session)):
    """Register a new user."""
    from sqlalchemy.exc import IntegrityError
    
    # Check if user exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create access token
    access_token = create_access_token(data={"sub": str(db_user.id)})
    
    return TokenResponse(
        access_token=access_token,
        user_id=db_user.id,
        plan="free"
    )


@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db=Depends(get_db_session)):
    """Login and get access token."""
    user = authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        plan=get_user_plan(user)
    )


@app.get("/api/v1/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info."""
    limits = get_user_limits(current_user)
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "plan": limits["plan"],
        "monthly_limit": limits["monthly_limit"],
        "features": limits["features"]
    }


# =====================
# API Key Endpoints
# =====================

@app.post("/api/v1/keys", response_model=APIKeyResponse)
async def create_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db_session)
):
    """Create a new API key."""
    import hashlib
    import secrets
    
    # Generate key
    random_part = secrets.token_hex(24)
    full_key = f"tp_{random_part}"
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    prefix = f"{full_key[:8]}..."
    
    # Create API key record
    api_key = APIKey(
        user_id=current_user.id,
        key_hash=key_hash,
        name=key_data.name,
        prefix=prefix,
        tier=key_data.tier
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    return APIKeyResponse(
        key=full_key,
        name=key_data.name,
        tier=key_data.tier,
        created_at=api_key.created_at.isoformat(),
        prefix=prefix
    )


@app.get("/api/v1/keys")
async def list_keys(
    current_user: User = Depends(get_current_user),
    db=Depends(get_db_session)
):
    """List all API keys for user."""
    keys = db.query(APIKey).filter(APIKey.user_id == current_user.id).all()
    
    return [
        {
            "id": k.id,
            "name": k.name,
            "prefix": k.prefix,
            "tier": k.tier,
            "is_active": k.is_active,
            "created_at": k.created_at.isoformat(),
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None
        }
        for k in keys
    ]


@app.delete("/api/v1/keys/{key_id}")
async def delete_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db_session)
):
    """Delete an API key."""
    key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    ).first()
    
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    db.delete(key)
    db.commit()
    
    return {"success": True}


# =====================
# Usage Endpoints
# =====================

@app.get("/api/v1/usage", response_model=UsageStats)
async def get_usage(
    current_user: User = Depends(get_current_user),
    db=Depends(get_db_session)
):
    """Get usage statistics."""
    plan = get_user_plan(current_user)
    limits = get_user_limits(current_user)
    
    # Count this month's usage
    from sqlalchemy import func
    from datetime import date
    
    month_start = date.today().replace(day=1)
    usage_count = db.query(UsageLog).filter(
        UsageLog.user_id == current_user.id,
        UsageLog.timestamp >= month_start
    ).count()
    
    return UsageStats(
        checks_used=usage_count,
        checks_remaining=max(0, limits["monthly_limit"] - usage_count),
        plan=plan,
        limit=limits["monthly_limit"]
    )


# =====================
# Core API Endpoints
# =====================

@app.post("/api/v1/check", response_model=ApiResponse)
@rate_limit(max_calls=API_RATE_LIMITS["check"]["max_calls"], period=API_RATE_LIMITS["check"]["period"])
async def check_failure(
    request: FailureCheck,
    api_key_info: dict = Depends(get_api_key_user)
):
    """
    Main endpoint: Analyze a test failure
    
    - **error_message**: The test failure traceback/error
    - **test_code**: Optional test code for context
    - **include_scrubbed**: Include sensitive data scrubbed version
    - **use_llm**: Enable LLM analysis
    """
    if not TESTPILOT_AVAILABLE:
        raise HTTPException(status_code=503, detail="TestPilot AI not configured")
    
    # Log usage
    from .database import SessionLocal
    db = SessionLocal()
    try:
        usage = UsageLog(
            api_key_id=api_key_info["key_id"],
            user_id=api_key_info["user_id"],
            endpoint="/check",
            check_type="llm" if request.use_llm else "standard",
            success=True
        )
        db.add(usage)
        db.commit()
    finally:
        db.close()
    
    # Run analysis
    classifier = TestPilotClassifier()
    triage = TriageEngine()
    scrubber = Scrubber()
    
    failure_type = classifier.classify(request.error_message)
    suggestion = triage.triage(request.error_message)
    scrubbed = scrubber.scrub(request.error_message)
    
    # LLM analysis (if requested)
    llm_result = None
    if request.use_llm:
        llm_key = os.getenv("OPENAI_API_KEY")
        if llm_key:
            try:
                llm = TestPilotLLM(LLMConfig(api_key=llm_key))
                if llm.is_available():
                    llm_result = llm.analyze_failure(request.error_message)
            except Exception as e:
                llm_result = {"error": str(e)}
    
    result = {
        "failure_type": failure_type.value,
        "severity": suggestion.get("severity", "medium"),
        "category": suggestion.get("category", "unknown"),
        "suggested_fix": suggestion.get("suggested_fix", "Review manually"),
        "root_cause": suggestion.get("description", "Unknown"),
        "confidence": 0.9 if failure_type != FailureType.UNKNOWN else 0.3,
    }
    
    if request.include_scrubbed and len(scrubbed) < len(request.error_message):
        result["scrubbed_error"] = scrubbed
    
    if llm_result:
        result["llm_analysis"] = llm_result
    
    request_id = hashlib.md5(
        f"{request.error_message}{datetime.utcnow().isoformat()}".encode()
    ).hexdigest()[:12]
    
    return ApiResponse(
        success=True,
        result=result,
        request_id=request_id,
        timestamp=datetime.utcnow().isoformat(),
        plan=api_key_info["tier"]
    )


@app.post("/api/v1/batch-check")
@rate_limit(max_calls=API_RATE_LIMITS["batch_check"]["max_calls"], period=API_RATE_LIMITS["batch_check"]["period"])
async def batch_check(
    requests: List[FailureCheck],
    api_key_info: dict = Depends(get_api_key_user)
):
    """Process multiple failures in batch."""
    results = []
    for req in requests:
        response = await check_failure(req, api_key_info)
        results.append(response.result)
    
    return {"results": results, "count": len(results)}


# =====================
# Subscription Endpoints
# =====================

@app.get("/api/v1/subscription")
async def get_subscription(
    current_user: User = Depends(get_current_user)
):
    """Get current subscription details."""
    plan = get_user_plan(current_user)
    limits = get_user_limits(current_user)
    
    return {
        "plan": plan,
        "monthly_limit": limits["monthly_limit"],
        "features": limits["features"],
        "usage": limits["monthly_limit"]  # Would be real usage in production
    }


@app.post("/api/v1/subscription/upgrade")
async def upgrade_subscription(
    plan: str,
    current_user: User = Depends(get_current_user)
):
    """Upgrade subscription plan."""
    if plan not in ["pro", "team", "enterprise"]:
        raise HTTPException(status_code=400, detail="Invalid plan")
    
    try:
        result = create_subscription(current_user, plan)
        return {"success": True, "subscription": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/subscription/cancel")
async def cancel_subscription_endpoint(
    current_user: User = Depends(get_current_user)
):
    """Cancel current subscription."""
    # Get active subscription
    active_sub = current_user.subscriptions.filter(
        Subscription.status == "active"
    ).first()
    
    if not active_sub or not active_sub.stripe_subscription_id:
        raise HTTPException(status_code=400, detail="No active subscription")
    
    try:
        result = cancel_subscription(active_sub.stripe_subscription_id)
        return {"success": True, "cancellation": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================
# Webhook Endpoint
# =====================

@app.post("/api/v1/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    raw_body: bytes
):
    """Handle Stripe webhook events."""
    signature = request.headers.get("stripe-signature")
    
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")
    
    try:
        result = handle_webhook(raw_body, signature)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =====================
# Health & Info
# =====================

@app.get("/")
async def root():
    return {
        "service": "TestPilot AI API",
        "version": "2.0.0",
        "status": "online",
        "docs": "/docs",
        "endpoints": {
            "auth_register": "POST /api/v1/auth/register",
            "auth_login": "POST /api/v1/auth/login",
            "check": "POST /api/v1/check",
            "batch_check": "POST /api/v1/batch-check",
            "usage": "GET /api/v1/usage",
            "keys": "POST /api/v1/keys",
            "subscription": "GET /api/v1/subscription"
        }
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected",
        "redis": "connected" if redis_client else "not_configured"
    }


@app.get("/examples")
async def get_examples():
    return {
        "example_1": {
            "error_message": "AssertionError: Expected 5 but got 3",
            "test_code": "assert result == 5"
        },
        "example_2": {
            "error_message": "ModuleNotFoundError: No module named 'requests'",
            "test_code": "import requests"
        },
        "example_3": {
            "error_message": "PermissionError: [Errno 13] Permission denied: '/etc/passwd'",
            "test_code": "open('/etc/passwd', 'r')"
        }
    }


# =====================
# Run with: uvicorn api.main:app --reload
# =====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
