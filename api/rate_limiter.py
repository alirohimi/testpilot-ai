"""Rate limiting using Redis."""

import os
import time
from functools import wraps
from typing import Callable, Any
from fastapi import Request
import inspect

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = None

if REDIS_AVAILABLE:
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        redis_client.ping()
        print("✅ Redis connected successfully")
    except Exception as e:
        print(f"⚠️  Redis connection failed: {e}")
        redis_client = None


def rate_limit(max_calls: int = 100, period: int = 3600, key_prefix: str = "ratelimit"):
    """
    Rate limiting decorator.
    
    Args:
        max_calls: Maximum number of calls allowed
        period: Time period in seconds
        key_prefix: Prefix for Redis key
    """
    def decorator(func: Callable) -> Callable:
        # Get the original function signature
        sig = inspect.signature(func)
        
        # Build new signature with request parameter if not present
        params = list(sig.parameters.values())
        request_param = None
        for p in params:
            if p.name == 'http_request':
                request_param = p
                break
        
        if request_param is None:
            # Add http_request as first parameter
            new_param = inspect.Parameter('http_request', inspect.Parameter.KEYWORD_ONLY, default=None)
            params = [new_param] + params
        
        new_sig = sig.replace(parameters=params)
        
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Extract request - FastAPI passes Request as 'http_request' kwarg
            request = kwargs.get('http_request')
            
            # If not found, check positional args for Request object
            if request is None and len(args) > 0:
                potential_request = args[0]
                # Only use it if it's actually a Request (has scope attribute)
                if hasattr(potential_request, 'scope') and potential_request.scope.get('type') == 'http':
                    request = potential_request
            
            if request:
                client_id = request.client.host if request.client else "unknown"
            else:
                client_id = "unknown"
            
            key = f"{key_prefix}:{client_id}:{func.__name__}"
            
            if redis_client:
                # Use Redis for distributed rate limiting
                current = redis_client.incr(key)
                if current == 1:
                    redis_client.expire(key, period)
                
                if current > max_calls:
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=429,
                        detail=f"Rate limit exceeded. Max {max_calls} calls per {period}s."
                    )
            else:
                # Fallback to in-memory (single instance)
                if not hasattr(rate_limit, '_stores'):
                    rate_limit._stores = {}
                
                if key not in rate_limit._stores:
                    rate_limit._stores[key] = {"count": 0, "reset": time.time() + period}
                
                store = rate_limit._stores[key]
                if time.time() > store["reset"]:
                    store["count"] = 0
                    store["reset"] = time.time() + period
                
                store["count"] += 1
                if store["count"] > max_calls:
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=429,
                        detail=f"Rate limit exceeded. Max {max_calls} calls per {period}s."
                    )
            
            return await func(*args, **kwargs)
        
        # Preserve the signature for FastAPI's dependency injection
        wrapper.__signature__ = new_sig  # type: ignore[attr-defined]
        
        return wrapper
    return decorator


class RateLimiter:
    """Rate limiter class for more complex scenarios."""
    
    def __init__(self, max_calls: int = 100, period: int = 3600):
        self.max_calls = max_calls
        self.period = period
    
    def is_allowed(self, key: str) -> tuple[bool, int]:
        """
        Check if request is allowed.
        
        Returns:
            (is_allowed, remaining_calls)
        """
        if not redis_client:
            return True, self.max_calls
        
        cache_key = f"ratelimit:{key}"
        current = redis_client.incr(cache_key)
        
        if current == 1:
            redis_client.expire(cache_key, self.period)
        
        remaining = max(0, self.max_calls - current)
        is_allowed = current <= self.max_calls
        
        return is_allowed, remaining
    
    def get_reset_time(self, key: str) -> int:
        """Get seconds until rate limit resets."""
        if not redis_client:
            return self.period
        
        cache_key = f"ratelimit:{key}"
        ttl = redis_client.ttl(cache_key)
        return ttl if ttl > 0 else self.period


# Rate limit configurations
API_RATE_LIMITS = {
    "check": {"max_calls": 60, "period": 60},  # 60 checks per minute
    "batch_check": {"max_calls": 10, "period": 60},  # 10 batches per minute
    "create_key": {"max_calls": 5, "period": 3600},  # 5 keys per hour
    "usage": {"max_calls": 30, "period": 60},  # 30 reads per minute
}

# Per-tier rate limits
TIER_RATE_LIMITS = {
    "free": {"checks_per_month": 100, "requests_per_minute": 10},
    "pro": {"checks_per_month": 5000, "requests_per_minute": 60},
    "team": {"checks_per_month": 25000, "requests_per_minute": 200},
    "enterprise": {"checks_per_month": 999999, "requests_per_minute": 1000},
}


def get_tier_limit(tier: str) -> int:
    """Get monthly check limit for tier."""
    return TIER_RATE_LIMITS.get(tier, TIER_RATE_LIMITS["free"])["checks_per_month"]


def get_monthly_usage(db, api_key_id: int) -> int:
    """Get current month's usage for an API key."""
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    # This would query the database - simplified version
    # In production, use proper SQL query
    return 0  # Placeholder
