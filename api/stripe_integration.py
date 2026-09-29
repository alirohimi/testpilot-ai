"""Stripe payment integration for TestPilot AI."""

import os
from typing import Optional, Dict, Any
from datetime import datetime
import stripe

from .database import get_db_session
from .models import User, Subscription

# Configure Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_placeholder")

# Pricing plans
PLANS = {
    "free": {
        "stripe_price_id": None,
        "monthly_limit": 100,
        "features": ["basic_scrubbing", "failure_classification"]
    },
    "pro": {
        "stripe_price_id": os.getenv("STRIPE_PRICE_PRO", "price_pro_placeholder"),
        "monthly_limit": 5000,
        "features": ["llm_analysis", "batch_processing", "email_support"]
    },
    "team": {
        "stripe_price_id": os.getenv("STRIPE_PRICE_TEAM", "price_team_placeholder"),
        "monthly_limit": 25000,
        "features": ["slack_integration", "jira_sync", "priority_support", "team_workspaces"]
    },
    "enterprise": {
        "stripe_price_id": os.getenv("STRIPE_PRICE_ENTERPRISE", "price_enterprise_placeholder"),
        "monthly_limit": 999999,
        "features": ["unlimited", "on_premise", "sso", "custom_integrations", "dedicated_support"]
    }
}


def get_customer_email(stripe_customer_id: str) -> Optional[str]:
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
            metadata={
                "user_id": str(user.id),
                "plan": "free"
            }
        )
        return customer.id
    except stripe.error.StripeError as e:
        raise Exception(f"Failed to create Stripe customer: {e}")


def create_subscription(user: User, plan: str) -> Dict[str, Any]:
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
                user_id=user.id,
                stripe_customer_id=stripe_customer_id,
                plan_id=plan
            )
            user.subscriptions.append(subscription)
        else:
            existing_sub.stripe_customer_id = stripe_customer_id
    
    # Create subscription
    try:
        subscription = stripe.Subscription.create(
            customer=stripe_customer_id,
            items=[{"price": plan_config["stripe_price_id"]}],
            metadata={
                "user_id": str(user.id),
                "plan": plan
            }
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
                status="active"
            )
            user.subscriptions.append(sub)
        
        return {
            "subscription_id": subscription.id,
            "status": subscription.status,
            "current_period_end": subscription.current_period_end
        }
    except stripe.error.StripeError as e:
        raise Exception(f"Failed to create subscription: {e}")


def cancel_subscription(subscription_id: str) -> Dict[str, Any]:
    """Cancel a subscription at period end."""
    try:
        subscription = stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True
        )
        return {
            "status": "cancelled_at_period_end",
            "current_period_end": subscription.current_period_end
        }
    except stripe.error.StripeError as e:
        raise Exception(f"Failed to cancel subscription: {e}")


def get_user_plan(user: User) -> str:
    """Get current plan for user."""
    # Check for active subscription
    active_sub = user.subscriptions.filter(
        Subscription.status == "active"
    ).order_by(Subscription.created_at.desc()).first()
    
    if active_sub:
        return active_sub.plan_id
    
    return "free"


def get_user_limits(user: User) -> Dict[str, Any]:
    """Get usage limits for user's plan."""
    plan = get_user_plan(user)
    plan_config = PLANS.get(plan, PLANS["free"])
    
    return {
        "plan": plan,
        "monthly_limit": plan_config["monthly_limit"],
        "features": plan_config["features"]
    }


# Webhook handlers
def handle_webhook(payload: bytes, sig_header: str) -> Dict[str, Any]:
    """Handle Stripe webhook events."""
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_placeholder")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        raise Exception("Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise Exception("Invalid signature")
    
    # Handle events
    if event.type == "checkout.session.completed":
        # Fulfill the order
        session = event.data.object
        user_id = session.metadata.get("user_id")
        # Update subscription in database
        return {"status": "webhook_received"}
    
    elif event.type == "invoice.payment_succeeded":
        invoice = event.data.object
        # Update subscription status
        return {"status": "payment_succeeded"}
    
    elif event.type == "customer.subscription.updated":
        subscription = event.data.object
        # Update plan/limits
        return {"status": "subscription_updated"}
    
    elif event.type == "customer.subscription.deleted":
        subscription = event.data.object
        # Downgrade to free
        return {"status": "subscription_deleted"}
    
    return {"status": "event_handled"}
