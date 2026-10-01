"""JWT authentication for TestPilot AI."""

import os
from datetime import datetime, timedelta

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .database import get_db_session
from .models import APIKey, User

# Security settings
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week
API_KEY_PREFIX = "tp_"

security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def get_password_hash(password: str) -> str:
    """Hash a password with bcrypt (truncated to bcrypt's 72-byte limit)."""
    pwd = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pwd, bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    import uuid

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4()),  # Unique token ID to prevent replay
        }
    )
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_api_key(user_id: int, name: str, tier: str = "free") -> tuple[str, str, str]:
    """
    Create a new API key for a user.

    Returns:
        (full_key, key_hash, key_prefix) - full_key should be shown once;
        key_hash is stored; key_prefix is the display prefix.
    """
    import hashlib
    import secrets

    # Generate random key
    random_part = secrets.token_hex(24)
    full_key = f"{API_KEY_PREFIX}{random_part}"
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    prefix = f"{full_key[:8]}..."

    return full_key, key_hash, prefix


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Authenticate user with email and password."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db_session),
) -> User:
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]
        )
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return user


async def get_api_key_user(
    request: Request = None, db: Session = Depends(get_db_session)
) -> dict:
    """
    Get user from API key.

    Expects X-API-Key header with value like: tp_abc123...
    """
    # Extract API key from header
    api_key_header = request.headers.get("X-API-Key") if request else None

    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-API-Key header"
        )
    if not api_key_header.startswith(API_KEY_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key format"
        )

    import hashlib

    key_hash = hashlib.sha256(api_key_header.encode()).hexdigest()

    # Find API key in database
    api_key = db.query(APIKey).filter(APIKey.key_hash == key_hash).first()
    if not api_key or not api_key.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
        )

    # Check tier limits
    from .dependencies import get_tier_limit

    limit = get_tier_limit(api_key.tier)

    # Check monthly usage
    from .dependencies import get_monthly_usage

    usage = get_monthly_usage(db, api_key.id)
    if usage >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Monthly limit exceeded ({usage}/{limit}). Upgrade your plan.",
        )

    # Update last used
    api_key.last_used_at = datetime.utcnow()
    db.commit()

    return {
        "user_id": api_key.user_id,
        "key_id": api_key.id,
        "tier": api_key.tier,
        "name": api_key.name,
        "limit": limit,
        "usage": usage,
    }


def require_tier(required_tier: str):
    """Dependency to check if user has required tier."""

    async def checker(current_user: User = Depends(get_current_user)):
        # This would need access to subscription info
        # Simplified for now
        return current_user

    return checker
