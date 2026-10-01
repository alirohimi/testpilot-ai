"""TestPilot AI - production-hardening tests

Covers:
- P1b: Stripe webhook fulfillment (DB writes, not stubs)
- P1c: LLM analysis path (mocked OpenAI client, no network)
- P2b: GDPR data export + account deletion endpoints

All tests use the shared `client` / `test_session` fixtures from conftest.py.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

# =====================================================================
# P1b — Stripe webhook fulfilment
# =====================================================================


class TestStripeWebhookFulfilment:
    """The webhook handler must persist subscription state to the DB."""

    @staticmethod
    def _make_event(event_type: str, data_object=None) -> MagicMock:
        """Build a minimal mock Stripe event object."""
        event = MagicMock()
        event.type = event_type
        event.data.object = data_object or MagicMock()
        return event

    def test_webhook_with_no_db_returns_acknowledged(self):
        """When no DB session is passed, the handler should acknowledge without DB writes."""
        from api.stripe_integration import handle_webhook

        # Bypass real Stripe construct_event by patching it to return our mock
        mock_event = self._make_event("checkout.session.completed")
        with patch(
            "api.stripe_integration.stripe.Webhook.construct_event",
            return_value=mock_event,
        ):
            result = handle_webhook(b"payload", "t=1,v1=x", db=None)
        assert result["status"] == "acknowledged_no_db"
        assert result["event_type"] == "checkout.session.completed"

    def test_webhook_checkout_fulfillment_writes_subscription(self, test_session):
        """checkout.session.completed must create/activate a subscription row."""
        from api.models import Subscription, User
        from api.stripe_integration import handle_webhook

        # Seed a user
        user = User(email="webhook-user@example.com", hashed_password="$2b$dummy")
        test_session.add(user)
        test_session.commit()
        test_session.refresh(user)

        # Build a mock checkout session
        session_obj = MagicMock()
        session_obj.metadata = {"user_id": str(user.id), "plan": "pro"}
        session_obj.customer = "cus_test123"
        session_obj.subscription = "sub_test123"

        mock_event = self._make_event(
            "checkout.session.completed", data_object=session_obj
        )

        with patch(
            "api.stripe_integration.stripe.Webhook.construct_event",
            return_value=mock_event,
        ):
            result = handle_webhook(b"payload", "t=1,v1=x", db=test_session)

        assert result["status"] == "fulfilled"
        assert result["user_id"] == user.id

        # Verify DB state
        sub = (
            test_session.query(Subscription)
            .filter(Subscription.user_id == user.id)
            .first()
        )
        assert sub is not None
        assert sub.plan_id == "pro"
        assert sub.status == "active"
        assert sub.stripe_customer_id == "cus_test123"
        assert sub.stripe_subscription_id == "sub_test123"

    def test_webhook_subscription_deleted_downgrades_to_free(self, test_session):
        """customer.subscription.deleted must downgrade the user to free."""
        from api.models import Subscription, User
        from api.stripe_integration import handle_webhook

        user = User(email="del-user@example.com", hashed_password="$2b$dummy")
        test_session.add(user)
        test_session.commit()
        test_session.refresh(user)

        sub = Subscription(
            user_id=user.id,
            stripe_customer_id="cus_del",
            stripe_subscription_id="sub_del",
            plan_id="pro",
            status="active",
        )
        test_session.add(sub)
        test_session.commit()

        stripe_sub = MagicMock()
        stripe_sub.id = "sub_del"
        stripe_sub.customer = "cus_del"
        stripe_sub.status = "canceled"
        mock_event = self._make_event(
            "customer.subscription.deleted", data_object=stripe_sub
        )

        with patch(
            "api.stripe_integration.stripe.Webhook.construct_event",
            return_value=mock_event,
        ):
            result = handle_webhook(b"payload", "t=1,v1=x", db=test_session)

        assert result["status"] == "downgraded_to_free"

        test_session.refresh(sub)
        assert sub.status == "canceled"
        assert sub.plan_id == "free"

    def test_webhook_invalid_signature_raises(self):
        """An invalid signature must raise an Exception (endpoint maps to 400)."""
        from api.stripe_integration import handle_webhook

        with patch(
            "api.stripe_integration.stripe.Webhook.construct_event",
            side_effect=Exception("Invalid signature"),
        ):
            with pytest.raises(Exception, match="Invalid signature"):
                handle_webhook(b"payload", "bad_sig", db=None)


# =====================================================================
# P1c — LLM analysis path (mocked OpenAI, no network)
# =====================================================================


class TestLLMPath:
    """Verify LLM analysis works without a real API key, via mocks."""

    @staticmethod
    def _mock_openai_response(json_content: str):
        """Build a MagicMock that mimics the OpenAI chat.completions API."""
        message = MagicMock()
        message.content = json_content
        choice = MagicMock()
        choice.message = message
        response = MagicMock()
        response.choices = [choice]
        return response

    def test_llm_no_api_key_returns_error(self):
        """With no API key, analyze_failure must return a clean error dict."""
        from src.testpilot_ai.llm import LLMConfig, TestPilotLLM

        analyzer = TestPilotLLM(LLMConfig(api_key=None))
        # Clear the cached module-level analyzer's key too, in case it leaked
        result = analyzer.analyze_failure("assert 1 == 2")
        assert "error" in result
        assert result["category"] == "unknown"

    def test_llm_mocked_success(self):
        """With a mocked OpenAI client, analyze_failure parses JSON correctly."""
        from src.testpilot_ai.llm import LLMConfig, TestPilotLLM

        expected = json.dumps(
            {
                "category": "assertion_failure",
                "root_cause": "Expected value mismatch",
                "suggested_fix": "Update the expected value",
                "severity": "medium",
                "confidence": 0.85,
            }
        )
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._mock_openai_response(
            expected
        )

        analyzer = TestPilotLLM(LLMConfig(api_key="sk-test-mock"))
        analyzer._client = mock_client  # Bypass lazy import

        result = analyzer.analyze_failure(
            "AssertionError: 1 != 2", test_code="assert 1 == 2"
        )
        assert result["category"] == "assertion_failure"
        assert result["severity"] == "medium"
        assert result["confidence"] == 0.85

    def test_llm_mocked_invalid_json_returns_raw(self):
        """If the LLM returns non-JSON, the parser must return raw_response."""
        from src.testpilot_ai.llm import LLMConfig, TestPilotLLM

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._mock_openai_response(
            "This is not JSON but a plain text analysis."
        )

        analyzer = TestPilotLLM(LLMConfig(api_key="sk-test-mock"))
        analyzer._client = mock_client

        result = analyzer.analyze_failure("Some error")
        assert "raw_response" in result
        assert result["category"] == "unknown"

    def test_llm_api_exception_returns_error(self):
        """If the API call raises, analyze_failure must catch and return error."""
        from src.testpilot_ai.llm import LLMConfig, TestPilotLLM

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API rate limit")

        analyzer = TestPilotLLM(LLMConfig(api_key="sk-test-mock"))
        analyzer._client = mock_client

        result = analyzer.analyze_failure("Any error")
        assert "error" in result
        assert "rate limit" in result["error"]


# =====================================================================
# P2b — GDPR data portability & erasure
# =====================================================================


class TestGDPR:
    """GDPR data export and account deletion via the API."""

    def test_export_user_data(self, client, auth_headers, test_session):
        """GET /api/v1/me/export must return all the user's data."""
        import sqlalchemy

        from api.models import FailureAnalysis

        # The registered_user fixture in conftest creates the most recent user
        uid_row = test_session.execute(
            sqlalchemy.text("SELECT id FROM users ORDER BY id DESC LIMIT 1")
        ).fetchone()
        user_id = uid_row[0]

        fa = FailureAnalysis(
            user_id=user_id,
            error_message_hash="abc123",
            error_message="AssertionError: 1 != 2",
            failure_type="assertion_failure",
            severity="medium",
            confidence=0.9,
        )
        test_session.add(fa)
        test_session.commit()

        resp = client.get("/api/v1/me/export", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["account"]["id"] == user_id
        assert len(data["failure_analyses"]) == 1
        assert data["failure_analyses"][0]["failure_type"] == "assertion_failure"

    def test_delete_account_cascades_children(self, client, auth_headers, test_session):
        """DELETE /api/v1/me must remove the user and all child rows."""
        import sqlalchemy

        from api.models import APIKey, FailureAnalysis, Subscription, UsageLog, User

        uid_row = test_session.execute(
            sqlalchemy.text("SELECT id FROM users ORDER BY id DESC LIMIT 1")
        ).fetchone()
        user_id = uid_row[0]

        # Seed child rows so we can verify they cascade-delete
        sub = Subscription(user_id=user_id, plan_id="pro", status="active")
        test_session.add(sub)
        test_session.commit()

        resp = client.delete("/api/v1/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert resp.json()["deleted_user_id"] == user_id

        # User gone
        test_session.expire_all()
        assert test_session.query(User).filter(User.id == user_id).first() is None

        # Child rows gone (portable explicit delete, not DB-level CASCADE)
        assert (
            test_session.query(Subscription)
            .filter(Subscription.user_id == user_id)
            .count()
            == 0
        )
        assert test_session.query(APIKey).filter(APIKey.user_id == user_id).count() == 0
        assert (
            test_session.query(UsageLog).filter(UsageLog.user_id == user_id).count()
            == 0
        )
        assert (
            test_session.query(FailureAnalysis)
            .filter(FailureAnalysis.user_id == user_id)
            .count()
            == 0
        )

    def test_delete_account_requires_auth(self, client):
        """DELETE /api/v1/me without a token must return 401/403."""
        resp = client.delete("/api/v1/me")
        assert resp.status_code in (401, 403)
