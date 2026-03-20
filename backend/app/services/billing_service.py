"""
Billing service for ResuBoost AI using Stripe.

Provides:
- BillingService class for checkout, portal, and webhook handling
- Graceful ImportError handling when stripe package is absent
- Factory function get_billing_service()
"""

import logging
from datetime import datetime, timezone
from typing import Optional

try:
    import stripe
except ImportError:
    stripe = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class BillingService:
    """
    Stripe-backed billing service.

    Handles:
    - Checkout session creation
    - Customer portal session creation
    - Webhook event verification and dispatch
    """

    def __init__(
        self,
        enabled: bool,
        secret_key: Optional[str],
        webhook_secret: Optional[str],
    ) -> None:
        self.enabled = enabled
        self.secret_key = secret_key
        self.webhook_secret = webhook_secret

        if enabled and secret_key and stripe is not None:
            stripe.api_key = secret_key

    # ------------------------------------------------------------------
    # Checkout
    # ------------------------------------------------------------------

    def create_checkout_session(
        self,
        user_id: int,
        email: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        db,
    ) -> Optional[str]:
        """
        Create a Stripe Checkout session and return the session URL.

        Returns None when billing is disabled or Stripe is unavailable.
        """
        if not self.enabled:
            logger.debug("Billing disabled — skipping checkout session for user %s", user_id)
            return None

        if stripe is None:
            logger.warning("stripe package not installed — cannot create checkout session")
            return None

        try:
            # Look up or use existing customer ID from subscription
            from app.models.subscription import Subscription

            sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
            customer_kwargs = {}
            if sub and sub.stripe_customer_id:
                customer_kwargs["customer"] = sub.stripe_customer_id
            else:
                customer_kwargs["customer_email"] = email

            session = stripe.checkout.Session.create(
                mode="subscription",
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={"user_id": str(user_id)},
                **customer_kwargs,
            )
            logger.info("Checkout session created for user %s: %s", user_id, session.id)
            return session.url
        except Exception as exc:
            logger.error("Failed to create checkout session for user %s: %s", user_id, exc)
            return None

    # ------------------------------------------------------------------
    # Portal
    # ------------------------------------------------------------------

    def create_portal_session(
        self,
        stripe_customer_id: str,
        return_url: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create a Stripe Customer Portal session and return the URL.

        Returns None when billing is disabled or Stripe is unavailable.
        """
        if not self.enabled:
            logger.debug(
                "Billing disabled — skipping portal session for customer %s", stripe_customer_id
            )
            return None

        if stripe is None:
            logger.warning("stripe package not installed — cannot create portal session")
            return None

        try:
            kwargs = {"customer": stripe_customer_id}
            if return_url:
                kwargs["return_url"] = return_url

            session = stripe.billing_portal.Session.create(**kwargs)  # type: ignore[arg-type]
            logger.info("Portal session created for customer %s", stripe_customer_id)
            return session.url
        except Exception as exc:
            logger.error(
                "Failed to create portal session for customer %s: %s", stripe_customer_id, exc
            )
            return None

    # ------------------------------------------------------------------
    # Webhooks
    # ------------------------------------------------------------------

    def handle_webhook_event(self, payload: bytes, sig_header: str, db) -> bool:
        """
        Verify and dispatch a Stripe webhook event.

        Returns True if the event was handled, False on error.
        """
        if stripe is None:
            logger.warning("stripe package not installed — cannot handle webhook")
            return False

        if not self.webhook_secret:
            logger.warning("STRIPE_WEBHOOK_SECRET not set — cannot verify webhook signature")
            return False

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, self.webhook_secret)
        except stripe.error.SignatureVerificationError as exc:
            logger.warning("Invalid webhook signature: %s", exc)
            return False
        except Exception as exc:
            logger.error("Failed to parse webhook payload: %s", exc)
            return False

        event_type = event["type"]
        event_data = event["data"]["object"]

        dispatch = {
            "checkout.session.completed": self._handle_checkout_completed,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
            "invoice.payment_failed": self._handle_payment_failed,
        }

        handler = dispatch.get(event_type)
        if handler is None:
            logger.debug("Unhandled webhook event type: %s", event_type)
            return True  # acknowledge unhandled events

        try:
            handler(event_data, db)
            return True
        except Exception as exc:
            logger.error("Error handling webhook %s: %s", event_type, exc)
            return False

    # ------------------------------------------------------------------
    # Private webhook handlers
    # ------------------------------------------------------------------

    def _handle_checkout_completed(self, session, db) -> None:
        """
        Handle checkout.session.completed.

        Creates or updates a Subscription record with the Stripe IDs and plan.
        """
        from app.models.subscription import Subscription

        user_id = int(session.get("metadata", {}).get("user_id", 0))
        if not user_id:
            logger.warning("checkout.session.completed missing user_id in metadata")
            return

        customer_id = session.get("customer")
        subscription_id = session.get("subscription")

        sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        if sub is None:
            sub = Subscription(user_id=user_id)
            db.add(sub)

        sub.stripe_customer_id = customer_id
        sub.stripe_subscription_id = subscription_id
        sub.plan = "pro_monthly"  # default; updated by subscription.updated event
        sub.status = "active"
        db.commit()
        logger.info("Subscription created/updated for user %s (customer: %s)", user_id, customer_id)

    def _handle_subscription_updated(self, subscription, db) -> None:
        """
        Handle customer.subscription.updated.

        Updates plan, status, and current_period_end.
        """
        from app.models.subscription import Subscription

        stripe_sub_id = subscription.get("id")
        sub = (
            db.query(Subscription)
            .filter(Subscription.stripe_subscription_id == stripe_sub_id)
            .first()
        )
        if sub is None:
            logger.warning("subscription.updated: no local subscription for %s", stripe_sub_id)
            return

        # Determine plan from price interval
        items = subscription.get("items", {}).get("data", [])
        if items:
            interval = items[0].get("plan", {}).get("interval", "month")
            sub.plan = "pro_annual" if interval == "year" else "pro_monthly"

        sub.status = subscription.get("status", sub.status)

        period_end = subscription.get("current_period_end")
        if period_end:
            sub.current_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc)

        db.commit()
        logger.info(
            "Subscription %s updated: plan=%s status=%s", stripe_sub_id, sub.plan, sub.status
        )

    def _handle_subscription_deleted(self, subscription, db) -> None:
        """
        Handle customer.subscription.deleted.

        Downgrades the user to the free plan.
        """
        from app.models.subscription import Subscription

        stripe_sub_id = subscription.get("id")
        sub = (
            db.query(Subscription)
            .filter(Subscription.stripe_subscription_id == stripe_sub_id)
            .first()
        )
        if sub is None:
            logger.warning("subscription.deleted: no local subscription for %s", stripe_sub_id)
            return

        sub.plan = "free"
        sub.status = "canceled"
        sub.stripe_subscription_id = None
        db.commit()
        logger.info("Subscription %s deleted — user downgraded to free", stripe_sub_id)

    def _handle_payment_failed(self, invoice, db) -> None:
        """
        Handle invoice.payment_failed.

        Sets subscription status to past_due and sends a payment-failed email.
        """
        from app.models.subscription import Subscription
        from app.models.user import User
        from app.services.email_service import get_email_service

        customer_id = invoice.get("customer")
        sub = db.query(Subscription).filter(Subscription.stripe_customer_id == customer_id).first()
        if sub is None:
            logger.warning("invoice.payment_failed: no subscription for customer %s", customer_id)
            return

        sub.status = "past_due"
        db.commit()

        # Send payment-failed email
        try:
            from app.config import get_settings

            settings = get_settings()
            user = db.query(User).filter(User.id == sub.user_id).first()
            if user:
                email_service = get_email_service()
                update_url = f"{settings.app_url}/settings/billing"
                html = email_service.render_payment_failed(
                    name=user.full_name or user.username,
                    update_url=update_url,
                )
                email_service.send(
                    to=user.email,
                    subject="Action required: your ResuBoost payment failed",
                    html=html,
                )
        except Exception as exc:
            logger.error(
                "Failed to send payment-failed email for customer %s: %s", customer_id, exc
            )

        logger.info("Subscription for customer %s set to past_due", customer_id)


# ------------------------------------------------------------------
# Factory
# ------------------------------------------------------------------


def get_billing_service() -> BillingService:
    """Return a BillingService configured from application settings."""
    from app.config import get_settings

    settings = get_settings()
    return BillingService(
        enabled=settings.enable_billing,
        secret_key=settings.stripe_secret_key,
        webhook_secret=settings.stripe_webhook_secret,
    )
