#!/usr/bin/env python3
"""
FastAPI Backend for TestPilot AI - Minimum Viable SaaS

Run with: uvicorn main:app --reload --port 8000
"""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx

app = FastAPI(
    title="TestPilot AI API",
    description="AI-powered test failure triage and scrubbing API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================
# Models
# =====================

class FailureCheck(BaseModel):
    """Request model for test failure analysis"""
    error_message: str = Field(..., description="The test failure error message")
    test_code: Optional[str] = Field(None, description="Optional test code for context")
    include_scrubbed: bool = Field(True, description="Include scrubbed version")
    use_llm: bool = Field(False, description="Use LLM for analysis (requires API key)")

class APIKeyCreate(BaseModel):
    name: str = Field(..., description="Name for this API key")
    tier: str = Field("free", description="Plan tier: free, pro, team, enterprise")

class APIKeyResponse(BaseModel):
    key: str
    name: str
    tier: str
    created_at: str
    prefix: str  # Show only first 8 chars

class UsageStats(BaseModel):
    checks_used: int
    checks_remaining: int
    tier: str
    limit: int
    reset_at: Optional[str] = None

class ApiResponse(BaseModel):
    success: bool
    result: dict
    request_id: str
    timestamp: str
    api_key_tier: str

# =====================
# In-memory storage
# Replace with PostgreSQL in production
# =====================

# Store API keys: {key_hash: {key, name, tier, prefix, created_at, checks}}
api_keys = {}
usage_counter = {}

# Free tier limits
TIER_LIMITS = {
    "free": 100,
    "pro": 5000,
    "team": 25000,
    "enterprise": 999999
}

# =====================
# TestPilot AI Integration
# =====================

def run_classifier(error_message: str) -> dict:
    """Run the classifier on error message"""
    try:
        from testpilot_ai.classifier import TestPilotClassifier, FailureType
        from testpilot_ai.scrubber import Scrubber
        from testpilot_ai.triage import TriageEngine
        
        classifier = TestPilotClassifier()
        triage = TriageEngine()
        scrubber = Scrubber()
        
        failure_type = classifier.classify(error_message)
        suggestion = triage.triage(error_message)
        scrubbed = scrubber.scrub(error_message)
        
        return {
            "failure_type": failure_type.value,
            "severity": suggestion.get("severity", "medium"),
            "category": suggestion.get("category", "unknown"),
            "suggested_fix": suggestion.get("suggested_fix", "Review manually"),
            "root_cause": suggestion.get("description", "Unknown"),
            "scrubbed_error": scrubbed if len(scrubbed) < len(error_message) else None,
            "confidence": 0.9 if failure_type != FailureType.UNKNOWN else 0.3
        }
    except Exception as e:
        return {"error": str(e), "failure_type": "unknown", "confidence": 0}

def run_llm_analysis(error_message: str, api_key: Optional[str] = None) -> dict:
    """Run LLM-based analysis"""
    if not api_key:
        return {"llm_analysis": None, "note": "No LLM API key provided"}
    
    try:
        from testpilot_ai.llm import TestPilotLLM, LLMConfig
        llm = TestPilotLLM(LLMConfig(api_key=api_key))
        if llm.is_available():
            result = llm.analyze_failure(error_message)
            return {"llm_analysis": result}
    except Exception as e:
        return {"llm_error": str(e)}
    
    return {"llm_analysis": None}

# =====================
# Authentication
# =====================

async def get_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Validate API key from header"""
    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
    
    if key_hash not in api_keys:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    key_data = api_keys[key_hash]
    
    # Check usage limit
    usage = usage_counter.get(key_hash, {"checks": 0})
    limit = TIER_LIMITS.get(key_data["tier"], 100)
    
    if usage["checks"] >= limit:
        raise HTTPException(status_code=429, detail=f"Monthly limit exceeded. Upgrade to {key_data['tier']} tier.")
    
    return {
        "key_hash": key_hash,
        "name": key_data["name"],
        "tier": key_data["tier"],
        "limit": limit
    }

# =====================
# Endpoints
# =====================

@app.get("/")
async def root():
    return {
        "service": "TestPilot AI",
        "version": "1.0.0",
        "status": "online",
        "docs": "/docs",
        "endpoints": {
            "check": "POST /api/v1/check",
            "keys": "POST /api/v1/keys",
            "usage": "GET /api/v1/usage"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/api/v1/keys", response_model=APIKeyResponse)
async def create_api_key(body: APIKeyCreate, current_key: dict = Depends(get_api_key)):
    """Create a new API key"""
    if current_key["tier"] not in ["pro", "team", "enterprise"]:
        raise HTTPException(status_code=403, detail="Upgrade required to create API keys")
    
    # Generate new key
    new_key = f"tp_{secrets.token_hex(24)}"
    key_hash = hashlib.sha256(new_key.encode()).hexdigest()
    
    api_keys[key_hash] = {
        "key": new_key,
        "name": body.name,
        "tier": current_key["tier"],
        "prefix": new_key[:8] + "...",
        "created_at": datetime.now().isoformat(),
        "checks": 0
    }
    
    return APIKeyResponse(
        key=new_key,
        name=body.name,
        tier=current_key["tier"],
        created_at=datetime.now().isoformat(),
        prefix=new_key[:8] + "..."
    )

@app.get("/api/v1/usage", response_model=UsageStats)
async def get_usage(current_key: dict = Depends(get_api_key)):
    """Get usage statistics"""
    usage = usage_counter.get(current_key["key_hash"], {"checks": 0})
    
    return UsageStats(
        checks_used=usage["checks"],
        checks_remaining=max(0, current_key["limit"] - usage["checks"]),
        tier=current_key["tier"],
        limit=current_key["limit"]
    )

@app.post("/api/v1/check", response_model=ApiResponse)
async def check_failure(
    request: FailureCheck,
    current_key: dict = Depends(get_api_key)
):
    """
    Main endpoint: Analyze a test failure
    
    - **error_message**: The test failure traceback/error
    - **test_code**: Optional test code for context
    - **include_scrubbed**: Include sensitive data scrubbed version
    - **use_llm**: Enable LLM analysis (requires API key in request)
    """
    # Increment usage
    if current_key["key_hash"] not in usage_counter:
        usage_counter[current_key["key_hash"]] = {"checks": 0}
    usage_counter[current_key["key_hash"]]["checks"] += 1
    
    # Generate request ID
    request_id = hashlib.md5(
        f"{request.error_message}{datetime.now().isoformat()}".encode()
    ).hexdigest()[:12]
    
    # Run analysis
    result = run_classifier(request.error_message)
    
    # Optional LLM analysis
    llm_result = {}
    if request.use_llm:
        llm_key = request.test_code or os.getenv("OPENAI_API_KEY")  # Inherit from test_code or env
        llm_result = run_llm_analysis(request.error_message, llm_key)
    
    response = ApiResponse(
        success=True,
        result={
            "analysis": result,
            "llm": llm_result if llm_result else None,
            "request_id": request_id,
            "timestamp": datetime.now().isoformat()
        },
        request_id=request_id,
        timestamp=datetime.now().isoformat(),
        api_key_tier=current_key["tier"]
    )
    
    return response

@app.post("/api/v1/batch-check")
async def batch_check(
    requests: List[FailureCheck],
    current_key: dict = Depends(get_api_key)
):
    """Batch process multiple failures"""
    results = []
    for req in requests:
        response = await check_failure(req, current_key)
        results.append(response.result)
    
    return {"results": results, "count": len(results)}

# =====================
# Example Requests
# =====================

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
# Manual Testing
# =====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
