"""Dependencies for rate limiting and usage tracking."""


def get_tier_limit(tier: str) -> int:
    """Get monthly limit for a tier."""
    limits = {
        "free": 100,
        "basic": 1000,
        "pro": 10000,
        "enterprise": -1  # unlimited
    }
    return limits.get(tier, 100)


def get_monthly_usage(db, api_key_id: int) -> int:
    """Get monthly usage count for an API key."""
    try:
        from api.models import UsageLog
        from datetime import datetime
        import calendar
        
        # Get first day of current month
        now = datetime.utcnow()
        first_day = datetime(now.year, now.month, 1)
        
        # Count usage this month
        count = db.query(UsageLog).filter(
            UsageLog.api_key_id == api_key_id,
            UsageLog.created_at >= first_day
        ).count()
        
        return count
    except Exception:
        return 0


def get_rate_limit(tier: str) -> tuple[int, int]:
    """Get rate limit (max_calls, period_seconds) for a tier."""
    limits = {
        "free": (10, 60),
        "basic": (100, 60),
        "pro": (1000, 60),
        "enterprise": (10000, 60)
    }
    return limits.get(tier, (10, 60))
