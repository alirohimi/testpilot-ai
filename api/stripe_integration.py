"""Stripe payment integration for TestPilot AI."""

import logging
import os
from datetime import datetime
from typing import Any

import stripe

from .models import Subscription, User

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_placeholder")

# Pricing plans
PLANS = {
    "free": {
        "stripe_price_id": None,
        "monthly_limit": 100,
        "features": ["basic_scrubbing", "failure_classification"],
    },
    "pro": {
        "stripe_price_id": os.getenv("STRIPE_PRICE_PRO", "price_pro_placeholder"),
        "monthly_limit": 5000,
        "features": ["llm_analysis", "batch_processing", "email_support"],
    },
    "team": {
        "stripe_price_id": os.getenv("STRIPE_PRICE_TEAM", "price_team_placeholder"),
        "monthly_limit": 25000,
        "features": [
            "slack_integration",
            "jira_sync",
            "priority_support",
            "team_workspaces",
        ],
    },
    "enterprise": {
        "stripe_price_id": os.getenv(
            "STRIPE_PRICE_ENTERPRISE", "price_enterprise_placeholder"
        ),
        "monthly_limit": 999999,
        "features": [
            "unlimited",
            "on_premise",
            "sso",
            "custom_integrations",
            "dedicated_support",
        ],
    },
}


def get_customer_email(stripe_customer_id: str) -> str | None:
    """Get customer email from Stripe."""
    try:
        customer = stripe.Customer.retrieve(stripe_customer_id)
        return customer.email
    except stripe.error.StripeError:
        return None


def create_stripe_customer(user: User, email: str) -> str:
    """Create a Stripe customer and return customer ID."""
    try:
        customer = stripe.Customer.create(
            email=email,
            name=user.full_name or user.email,
            metadata={"user_id": str(user.id), "plan": "free"},
        )
        return customer.id
    except stripe.error.StripeError as e:
        raise Exception(f"Failed to create Stripe customer: {e}")


def create_subscription(user: User, plan: str) -> dict[str, Any]:
    """Create a new subscription for a user."""
    plan_config = PLANS.get(plan)
    if not plan_config or not plan_config["stripe_price_id"]:
        raise ValueError(f"Invalid plan: {plan}")

    # Get or create Stripe customer
    existing_sub = user.subscriptions.first()
    if existing_sub and existing_sub.stripe_customer_id:
        stripe_customer_id = existing_sub.stripe_customer_id
    else:
        stripe_customer_id = create_stripe_customer(user, user.email)
        # Update user record
        if not existing_sub:
            subscription = Subscription(
                user_id=user.id, stripe_customer_id=stripe_customer_id, plan_id=plan
            )
            user.subscriptions.append(subscription)
        else:
            existing_sub.stripe_customer_id = stripe_customer_id

    # Create subscription
    try:
        subscription = stripe.Subscription.create(
            customer=stripe_customer_id,
            items=[{"price": plan_config["stripe_price_id"]}],
            metadata={"user_id": str(user.id), "plan": plan},
        )

        # Update database
        if existing_sub:
            existing_sub.stripe_subscription_id = subscription.id
            existing_sub.plan_id = plan
            existing_sub.status = "active"
            existing_sub.current_period_start = datetime.fromtimestamp(
                subscription.current_period_start
            )
            existing_sub.current_period_end = datetime.fromtimestamp(
                subscription.current_period_end
            )
        else:
            sub = Subscription(
                user_id=user.id,
                stripe_subscription_id=subscription.id,
                stripe_customer_id=stripe_customer_id,
                plan_id=plan,
                status="active",
            )
            user.subscriptions.append(sub)

        return {
            "subscription_id": subscription.id,
            "status": subscription.status,
            "current_period_end": subscription.current_period_end,
        }
    except stripe.error.StripeError as e:
        raise Exception(f"Failed to create subscription: {e}")


def cancel_subscription(subscription_id: str) -> dict[str, Any]:
    """Cancel a subscription at period end."""
    try:
        subscription = stripe.Subscription.modify(
            subscription_id, cancel_at_period_end=True
        )
        return {
            "status": "cancelled_at_period_end",
            "current_period_end": subscription.current_period_end,
        }
    except stripe.error.StripeError as e:
        raise Exception(f"Failed to cancel subscription: {e}")


def get_user_plan(db, user: User) -> str:
    """Get current plan for user."""
    # Check for active subscription via db query
    from api.models import Subscription

    active_sub = (
        db.query(Subscription)
        .filter(Subscription.user_id == user.id, Subscription.status == "active")
        .order_by(Subscription.created_at.desc())
        .first()
    )

    if active_sub:
        return active_sub.plan_id

    return "free"


def get_user_limits(db, user: User) -> dict[str, Any]:
    """Get usage limits for user's plan."""
    plan = get_user_plan(db, user)
    plan_config = PLANS.get(plan, PLANS["free"])

    return {
        "plan": plan,
        "monthly_limit": plan_config["monthly_limit"],
        "features": plan_config["features"],
    }


# Webhook handlers
def handle_webhook(payload: bytes, sig_header: str, db=None) -> dict[str, Any]:
    """Handle Stripe webhook events and persist subscription changes to the DB.

    Args:
        payload: raw request body (bytes)
        sig_header: Stripe-Signature header
        db: SQLAlchemy session (injected by the endpoint)

    Returns: dict describing what was done (JSON-serializable).

    Raises: Exception on invalid payload/signature (endpoint maps to 400).
    """
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_placeholder")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        raise Exception("Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise Exception("Invalid signature")

    # No DB session (e.g. unit test calling in isolation) — acknowledge only.
    if db is None:
        return {"status": "acknowledged_no_db", "event_type": event.type}

    def _find_sub_by_customer(customer_id: str) -> Subscription | None:
        return (
            db.query(Subscription)
            .filter(Subscription.stripe_customer_id == customer_id)
            .order_by(Subscription.created_at.desc())
            .first()
        )

    def _find_sub_by_subscription_id(subscription_id: str) -> Subscription | None:
        return (
            db.query(Subscription)
            .filter(Subscription.stripe_subscription_id == subscription_id)
            .order_by(Subscription.created_at.desc())
            .first()
        )

    # ---------------------------------------------------------------
    if event.type == "checkout.session.completed":
        session = event.data.object
        user_id = int(session.metadata.get("user_id", 0))
        customer_id = session.customer
        subscription_id = session.subscription
        plan = session.metadata.get("plan", "pro")

        if not user_id:
            return {"status": "ignored", "reason": "missing user_id metadata"}

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"status": "ignored", "reason": f"unknown user {user_id}"}

        sub = (
            _find_sub_by_customer(customer_id) if customer_id else None
        ) or Subscription(user_id=user_id)

        sub.stripe_customer_id = customer_id
        sub.stripe_subscription_id = subscription_id
        sub.plan_id = plan
        sub.status = "active"
        db.add(sub)
        db.commit()
        logger.info(f"webhook checkout completed: user {user_id} -> {plan}")
        return {"status": "fulfilled", "user_id": user_id, "plan": plan}

    # ---------------------------------------------------------------
    elif event.type == "invoice.payment_succeeded":
        invoice = event.data.object
        customer_id = invoice.customer
        # Invoice.period_start / period_end are unix timestamps (Stripe API)
        sub = _find_sub_by_customer(customer_id) if customer_id else None
        if not sub:
            return {"status": "ignored", "reason": f"unknown customer {customer_id}"}

        sub.status = "active"
        if getattr(invoice, "period_start", None):
            sub.current_period_start = datetime.fromtimestamp(invoice.period_start)
        if getattr(invoice, "period_end", None):
            sub.current_period_end = datetime.fromtimestamp(invoice.period_end)
        db.commit()
        logger.info(
            "webhook payment succeeded: customer %s active until %s",
            customer_id,
            sub.current_period_end,
        )
        return {"status": "payment_recorded", "customer": customer_id}

    # ---------------------------------------------------------------
    elif event.type == "customer.subscription.updated":
        s = event.data.object
        sub = _find_sub_by_subscription_id(s.id)
        if not sub and s.customer:
            sub = _find_sub_by_customer(s.customer)
        if not sub:
            return {"status": "ignored", "reason": f"unknown subscription {s.id}"}

        sub.status = s.status  # active, past_due, trialing, canceled...
        sub.cancel_at_period_end = bool(getattr(s, "cancel_at_period_end", False))
        if getattr(s, "current_period_start", None):
            sub.current_period_start = datetime.fromtimestamp(s.current_period_start)
        if getattr(s, "current_period_end", None):
            sub.current_period_end = datetime.fromtimestamp(s.current_period_end)
        # Plan change: derive from the price on the first item
        items = getattr(s, "items", None)
        if items and getattr(items, "data", None):
            price_id = items.data[0].price.id
            for plan_name, cfg in PLANS.items():
                if cfg["stripe_price_id"] == price_id:
                    sub.plan_id = plan_name
                    break
        db.commit()
        logger.info(
            f"webhook subscription updated: {s.id} -> {sub.status}/{sub.plan_id}"
        )
        return {"status": "updated", "subscription": s.id, "plan": sub.plan_id}

    # ---------------------------------------------------------------
    elif event.type == "customer.subscription.deleted":
        s = event.data.object
        sub = _find_sub_by_subscription_id(s.id)
        if not sub and s.customer:
            sub = _find_sub_by_customer(s.customer)
        if not sub:
            return {"status": "ignored", "reason": f"unknown subscription {s.id}"}

        sub.status = "canceled"
        sub.plan_id = "free"
        sub.cancel_at_period_end = False
        db.commit()
        logger.info(f"webhook subscription deleted: {s.id} -> downgraded to free")
        return {"status": "downgraded_to_free", "subscription": s.id}

    return {"status": "event_handled", "event_type": event.type}
