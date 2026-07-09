"""
Unit tests for app.services.billing_service.BillingService.

These tests exercise the real dispatch/branching logic of the billing
service (checkout, portal, webhook verification and event handlers)
against a real SQLite test database, with the `stripe` SDK mocked out.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.models.subscription import Subscription
from app.models.user import User
from app.services.billing_service import BillingService, get_billing_service


def make_service(enabled=True, secret_key="sk_test_123", webhook_secret="whsec_test"):
    return BillingService(enabled=enabled, secret_key=secret_key, webhook_secret=webhook_secret)


class TestCreateCheckoutSession:
    def test_returns_none_when_billing_disabled(self, db: Session, test_user: User):
        service = make_service(enabled=False)
        result = service.create_checkout_session(
            user_id=test_user.id,
            email=test_user.email,
            price_id="price_123",
            success_url="https://app/success",
            cancel_url="https://app/cancel",
            db=db,
        )
        assert result is None

    def test_returns_none_when_stripe_unavailable(self, db: Session, test_user: User):
        service = make_service()
        with patch("app.services.billing_service.stripe", None):
            result = service.create_checkout_session(
                user_id=test_user.id,
                email=test_user.email,
                price_id="price_123",
                success_url="https://app/success",
                cancel_url="https://app/cancel",
                db=db,
            )
        assert result is None

    def test_uses_customer_email_when_no_existing_subscription(self, db: Session, test_user: User):
        service = make_service()
        fake_session = MagicMock(id="cs_test_1", url="https://checkout.stripe.com/cs_test_1")

        with patch("app.services.billing_service.stripe") as mock_stripe:
            mock_stripe.checkout.Session.create.return_value = fake_session
            result = service.create_checkout_session(
                user_id=test_user.id,
                email=test_user.email,
                price_id="price_123",
                success_url="https://app/success",
                cancel_url="https://app/cancel",
                db=db,
            )

        assert result == "https://checkout.stripe.com/cs_test_1"
        _, kwargs = mock_stripe.checkout.Session.create.call_args
        assert kwargs["customer_email"] == test_user.email
        assert "customer" not in kwargs
        assert kwargs["metadata"] == {"user_id": str(test_user.id)}

    def test_reuses_stripe_customer_id_from_existing_subscription(
        self, db: Session, test_user: User, pro_subscription: Subscription
    ):
        service = make_service()
        fake_session = MagicMock(id="cs_test_2", url="https://checkout.stripe.com/cs_test_2")

        with patch("app.services.billing_service.stripe") as mock_stripe:
            mock_stripe.checkout.Session.create.return_value = fake_session
            result = service.create_checkout_session(
                user_id=test_user.id,
                email=test_user.email,
                price_id="price_123",
                success_url="https://app/success",
                cancel_url="https://app/cancel",
                db=db,
            )

        assert result == "https://checkout.stripe.com/cs_test_2"
        _, kwargs = mock_stripe.checkout.Session.create.call_args
        assert kwargs["customer"] == pro_subscription.stripe_customer_id
        assert "customer_email" not in kwargs

    def test_returns_none_on_stripe_error(self, db: Session, test_user: User):
        service = make_service()
        with patch("app.services.billing_service.stripe") as mock_stripe:
            mock_stripe.checkout.Session.create.side_effect = RuntimeError("stripe down")
            result = service.create_checkout_session(
                user_id=test_user.id,
                email=test_user.email,
                price_id="price_123",
                success_url="https://app/success",
                cancel_url="https://app/cancel",
                db=db,
            )
        assert result is None


class TestCreatePortalSession:
    def test_returns_none_when_billing_disabled(self):
        service = make_service(enabled=False)
        result = service.create_portal_session(stripe_customer_id="cus_123")
        assert result is None

    def test_returns_none_when_stripe_unavailable(self):
        service = make_service()
        with patch("app.services.billing_service.stripe", None):
            result = service.create_portal_session(stripe_customer_id="cus_123")
        assert result is None

    def test_creates_session_without_return_url(self):
        service = make_service()
        fake_session = MagicMock(url="https://billing.stripe.com/portal_1")

        with patch("app.services.billing_service.stripe") as mock_stripe:
            mock_stripe.billing_portal.Session.create.return_value = fake_session
            result = service.create_portal_session(stripe_customer_id="cus_123")

        assert result == "https://billing.stripe.com/portal_1"
        _, kwargs = mock_stripe.billing_portal.Session.create.call_args
        assert kwargs == {"customer": "cus_123"}

    def test_creates_session_with_return_url(self):
        service = make_service()
        fake_session = MagicMock(url="https://billing.stripe.com/portal_2")

        with patch("app.services.billing_service.stripe") as mock_stripe:
            mock_stripe.billing_portal.Session.create.return_value = fake_session
            result = service.create_portal_session(
                stripe_customer_id="cus_123", return_url="https://app/settings"
            )

        assert result == "https://billing.stripe.com/portal_2"
        _, kwargs = mock_stripe.billing_portal.Session.create.call_args
        assert kwargs == {"customer": "cus_123", "return_url": "https://app/settings"}

    def test_returns_none_on_stripe_error(self):
        service = make_service()
        with patch("app.services.billing_service.stripe") as mock_stripe:
            mock_stripe.billing_portal.Session.create.side_effect = RuntimeError("boom")
            result = service.create_portal_session(stripe_customer_id="cus_123")
        assert result is None


class TestHandleWebhookEvent:
    def test_returns_false_when_stripe_unavailable(self, db: Session):
        service = make_service()
        with patch("app.services.billing_service.stripe", None):
            result = service.handle_webhook_event(b"{}", "sig", db)
        assert result is False

    def test_returns_false_when_webhook_secret_missing(self, db: Session):
        service = make_service(webhook_secret=None)
        with patch("app.services.billing_service.stripe") as mock_stripe:
            result = service.handle_webhook_event(b"{}", "sig", db)
        assert result is False
        mock_stripe.Webhook.construct_event.assert_not_called()

    def test_returns_false_on_invalid_signature(self, db: Session):
        service = make_service()

        class FakeSignatureError(Exception):
            pass

        with patch("app.services.billing_service.stripe") as mock_stripe:
            mock_stripe.error.SignatureVerificationError = FakeSignatureError
            mock_stripe.Webhook.construct_event.side_effect = FakeSignatureError("bad sig")
            result = service.handle_webhook_event(b"{}", "bad-sig", db)

        assert result is False

    def test_returns_false_on_unparseable_payload(self, db: Session):
        service = make_service()

        with patch("app.services.billing_service.stripe") as mock_stripe:
            mock_stripe.error.SignatureVerificationError = type("SigErr", (Exception,), {})
            mock_stripe.Webhook.construct_event.side_effect = ValueError("bad json")
            result = service.handle_webhook_event(b"not json", "sig", db)

        assert result is False

    def test_acknowledges_unhandled_event_type(self, db: Session):
        service = make_service()
        fake_event = {"type": "payment_intent.created", "data": {"object": {}}}

        with patch("app.services.billing_service.stripe") as mock_stripe:
            mock_stripe.error.SignatureVerificationError = type("SigErr", (Exception,), {})
            mock_stripe.Webhook.construct_event.return_value = fake_event
            result = service.handle_webhook_event(b"{}", "sig", db)

        assert result is True

    def test_dispatches_checkout_completed(self, db: Session, test_user: User):
        service = make_service()
        fake_event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {"user_id": str(test_user.id)},
                    "customer": "cus_new",
                    "subscription": "sub_new",
                }
            },
        }

        with patch("app.services.billing_service.stripe") as mock_stripe:
            mock_stripe.error.SignatureVerificationError = type("SigErr", (Exception,), {})
            mock_stripe.Webhook.construct_event.return_value = fake_event
            result = service.handle_webhook_event(b"{}", "sig", db)

        assert result is True
        sub = db.query(Subscription).filter(Subscription.user_id == test_user.id).first()
        assert sub is not None
        assert sub.stripe_customer_id == "cus_new"
        assert sub.stripe_subscription_id == "sub_new"
        assert sub.plan == "pro_monthly"
        assert sub.status == "active"

    def test_handler_exception_returns_false(self, db: Session):
        service = make_service()
        # Missing metadata entirely still returns True per _handle_checkout_completed's
        # own guard, so force a real exception via a non-dict data object instead.
        fake_event = {
            "type": "checkout.session.completed",
            "data": {"object": None},
        }

        with patch("app.services.billing_service.stripe") as mock_stripe:
            mock_stripe.error.SignatureVerificationError = type("SigErr", (Exception,), {})
            mock_stripe.Webhook.construct_event.return_value = fake_event
            result = service.handle_webhook_event(b"{}", "sig", db)

        assert result is False


class TestHandleCheckoutCompleted:
    def test_creates_new_subscription(self, db: Session, test_user: User):
        service = make_service()
        session = {
            "metadata": {"user_id": str(test_user.id)},
            "customer": "cus_abc",
            "subscription": "sub_abc",
        }

        service._handle_checkout_completed(session, db)

        sub = db.query(Subscription).filter(Subscription.user_id == test_user.id).first()
        assert sub is not None
        assert sub.stripe_customer_id == "cus_abc"
        assert sub.stripe_subscription_id == "sub_abc"
        assert sub.plan == "pro_monthly"
        assert sub.status == "active"

    def test_updates_existing_subscription(
        self, db: Session, test_user: User, free_subscription: Subscription
    ):
        service = make_service()
        session = {
            "metadata": {"user_id": str(test_user.id)},
            "customer": "cus_upgraded",
            "subscription": "sub_upgraded",
        }

        service._handle_checkout_completed(session, db)

        db.refresh(free_subscription)
        assert free_subscription.stripe_customer_id == "cus_upgraded"
        assert free_subscription.plan == "pro_monthly"
        assert free_subscription.status == "active"

    def test_missing_user_id_is_noop(self, db: Session):
        service = make_service()
        session = {"metadata": {}, "customer": "cus_x", "subscription": "sub_x"}

        service._handle_checkout_completed(session, db)

        assert db.query(Subscription).count() == 0


class TestHandleSubscriptionUpdated:
    def test_updates_plan_status_and_period_end(
        self, db: Session, test_user: User, pro_subscription: Subscription
    ):
        service = make_service()
        period_end_ts = int(datetime(2027, 1, 1, tzinfo=timezone.utc).timestamp())
        subscription = {
            "id": pro_subscription.stripe_subscription_id,
            "status": "active",
            "current_period_end": period_end_ts,
            "items": {"data": [{"plan": {"interval": "year"}}]},
        }

        service._handle_subscription_updated(subscription, db)

        db.refresh(pro_subscription)
        assert pro_subscription.plan == "pro_annual"
        assert pro_subscription.status == "active"
        assert pro_subscription.current_period_end == datetime(
            2027, 1, 1, tzinfo=timezone.utc
        ).replace(tzinfo=None)

    def test_monthly_interval_maps_to_pro_monthly(
        self, db: Session, pro_subscription: Subscription
    ):
        service = make_service()
        subscription = {
            "id": pro_subscription.stripe_subscription_id,
            "status": "active",
            "items": {"data": [{"plan": {"interval": "month"}}]},
        }

        service._handle_subscription_updated(subscription, db)

        db.refresh(pro_subscription)
        assert pro_subscription.plan == "pro_monthly"

    def test_unknown_subscription_id_is_noop(self, db: Session):
        service = make_service()
        subscription = {"id": "sub_does_not_exist", "status": "active", "items": {"data": []}}

        # Should not raise even though no matching row exists.
        service._handle_subscription_updated(subscription, db)


class TestHandleSubscriptionDeleted:
    def test_downgrades_to_free(self, db: Session, pro_subscription: Subscription):
        service = make_service()
        subscription = {"id": pro_subscription.stripe_subscription_id}

        service._handle_subscription_deleted(subscription, db)

        db.refresh(pro_subscription)
        assert pro_subscription.plan == "free"
        assert pro_subscription.status == "canceled"
        assert pro_subscription.stripe_subscription_id is None

    def test_unknown_subscription_id_is_noop(self, db: Session):
        service = make_service()
        subscription = {"id": "sub_does_not_exist"}

        service._handle_subscription_deleted(subscription, db)


class TestHandlePaymentFailed:
    def test_marks_past_due_and_sends_email(
        self, db: Session, test_user: User, pro_subscription: Subscription
    ):
        service = make_service()
        invoice = {"customer": pro_subscription.stripe_customer_id}
        fake_email_service = MagicMock()
        fake_email_service.render_payment_failed.return_value = "<html></html>"

        with patch("app.services.email_service.get_email_service", return_value=fake_email_service):
            service._handle_payment_failed(invoice, db)

        db.refresh(pro_subscription)
        assert pro_subscription.status == "past_due"
        fake_email_service.send.assert_called_once()
        _, kwargs = fake_email_service.send.call_args
        assert kwargs["to"] == test_user.email

    def test_unknown_customer_is_noop(self, db: Session):
        service = make_service()
        invoice = {"customer": "cus_does_not_exist"}

        service._handle_payment_failed(invoice, db)

    def test_email_failure_does_not_raise(
        self, db: Session, test_user: User, pro_subscription: Subscription
    ):
        service = make_service()
        invoice = {"customer": pro_subscription.stripe_customer_id}

        with patch(
            "app.services.email_service.get_email_service",
            side_effect=RuntimeError("email down"),
        ):
            # Should not raise even though email sending blows up.
            service._handle_payment_failed(invoice, db)

        db.refresh(pro_subscription)
        assert pro_subscription.status == "past_due"


class TestGetBillingService:
    def test_builds_service_from_settings(self):
        fake_settings = MagicMock(
            enable_billing=True,
            stripe_secret_key="sk_from_settings",
            stripe_webhook_secret="whsec_from_settings",
        )
        with patch("app.config.get_settings", return_value=fake_settings):
            service = get_billing_service()

        assert isinstance(service, BillingService)
        assert service.enabled is True
        assert service.secret_key == "sk_from_settings"
        assert service.webhook_secret == "whsec_from_settings"
