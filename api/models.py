"""Database models for TestPilot AI SaaS."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


class User(Base):
    """User account model."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    usage_logs = relationship("UsageLog", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"


class APIKey(Base):
    """API key for programmatic access."""
    __tablename__ = "api_keys"
    __table_args__ = (UniqueConstraint("key_hash", name="uq_key_hash"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    key_hash = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    prefix = Column(String(12), nullable=False)  # First 8 chars + "..."
    tier = Column(String(20), default="free")
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="api_keys")
    usage_logs = relationship("UsageLog", back_populates="api_key", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<APIKey {self.prefix}... ({self.tier})>"


class Subscription(Base):
    """User subscription plan."""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    stripe_subscription_id = Column(String(255), unique=True, nullable=True)
    stripe_customer_id = Column(String(255), unique=True, nullable=True)
    plan_id = Column(String(50), nullable=False)  # free, pro, team, enterprise
    status = Column(String(20), default="active")  # active, cancelled, past_due, trialing
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="subscriptions")

    def __repr__(self):
        return f"<Subscription {self.plan_id} - {self.status}>"


class UsageLog(Base):
    """Tracks API usage for billing and analytics."""
    __tablename__ = "usage_logs"
    __table_args__ = (UniqueConstraint("api_key_id", "timestamp", name="uq_key_timestamp"),)

    id = Column(Integer, primary_key=True, index=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    endpoint = Column(String(50), nullable=False)
    check_type = Column(String(50), default="standard")  # standard, llm, batch
    success = Column(Boolean, default=True)
    response_time_ms = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    api_key = relationship("APIKey", back_populates="usage_logs")
    user = relationship("User", back_populates="usage_logs")

    def __repr__(self):
        return f"<UsageLog {self.endpoint} at {self.timestamp}>"


class FailureAnalysis(Base):
    """Stores past failure analyses for pattern learning."""
    __tablename__ = "failure_analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    error_message_hash = Column(String(64), index=True, nullable=False)
    error_message = Column(Text, nullable=False)
    failure_type = Column(String(50), nullable=True)
    severity = Column(String(20), nullable=True)
    category = Column(String(50), nullable=True)
    suggested_fix = Column(Text, nullable=True)
    root_cause = Column(Text, nullable=True)
    confidence = Column(Float, default=0.0)
    llm_analyzed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<FailureAnalysis {self.id} - {self.failure_type}>"
