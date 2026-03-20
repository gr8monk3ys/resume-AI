"""
Tests for billing endpoints.

Tests:
- GET /api/billing/status — free plan when no subscription, pro when subscription exists, 401 unauthorized
- POST /api/billing/checkout — 401 unauthorized, 503 when Stripe not configured
- POST /api/billing/portal — 404 when no subscription with Stripe customer
- POST /api/billing/webhook — 400 when no stripe-signature header
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.subscription import Subscription
from app.models.user import User


class TestBillingStatus:
    """Tests for GET /api/billing/status."""

    @pytest.mark.asyncio
    async def test_status_unauthorized(self, client: AsyncClient):
        """Returns 401 when no auth token provided."""
        response = await client.get("/api/billing/status")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_status_free_when_no_subscription(
        self, client: AsyncClient, test_user: User, auth_headers: dict
    ):
        """Returns free plan and active status when user has no subscription record."""
        response = await client.get("/api/billing/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["plan"] == "free"
        assert data["status"] == "active"
        assert data["current_period_end"] is None
        assert data["usage"] == []

    @pytest.mark.asyncio
    async def test_status_pro_when_subscription_exists(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Returns pro plan details when a subscription record exists."""
        sub = Subscription(
            user_id=test_user.id,
            plan="pro_monthly",
            status="active",
            stripe_customer_id="cus_test123",
            stripe_subscription_id="sub_test123",
        )
        db.add(sub)
        db.commit()

        response = await client.get("/api/billing/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["plan"] == "pro_monthly"
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_status_past_due_subscription(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Returns past_due status when subscription is past due."""
        sub = Subscription(
            user_id=test_user.id,
            plan="pro_monthly",
            status="past_due",
            stripe_customer_id="cus_pastdue",
        )
        db.add(sub)
        db.commit()

        response = await client.get("/api/billing/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["plan"] == "pro_monthly"
        assert data["status"] == "past_due"


class TestCheckout:
    """Tests for POST /api/billing/checkout."""

    @pytest.mark.asyncio
    async def test_checkout_unauthorized(self, client: AsyncClient):
        """Returns 401 when no auth token provided."""
        response = await client.post(
            "/api/billing/checkout",
            json={"price_id": "price_test123"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_checkout_stripe_not_configured(
        self, client: AsyncClient, test_user: User, auth_headers: dict
    ):
        """Returns 503 when Stripe is not configured (billing disabled in test env)."""
        response = await client.post(
            "/api/billing/checkout",
            json={
                "price_id": "price_test123",
                "success_url": "http://localhost:3000/settings/billing?success=true",
                "cancel_url": "http://localhost:3000/settings/billing",
            },
            headers=auth_headers,
        )
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_checkout_missing_price_id(
        self, client: AsyncClient, test_user: User, auth_headers: dict
    ):
        """Returns 422 when price_id is missing."""
        response = await client.post(
            "/api/billing/checkout",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestPortal:
    """Tests for POST /api/billing/portal."""

    @pytest.mark.asyncio
    async def test_portal_unauthorized(self, client: AsyncClient):
        """Returns 401 when no auth token provided."""
        response = await client.post("/api/billing/portal")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_portal_no_subscription(
        self, client: AsyncClient, test_user: User, auth_headers: dict
    ):
        """Returns 404 when user has no subscription."""
        response = await client.post("/api/billing/portal", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_portal_subscription_without_customer_id(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Returns 404 when subscription exists but has no Stripe customer ID."""
        sub = Subscription(
            user_id=test_user.id,
            plan="pro_monthly",
            status="active",
            stripe_customer_id=None,
        )
        db.add(sub)
        db.commit()

        response = await client.post("/api/billing/portal", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_portal_stripe_not_configured(
        self, client: AsyncClient, db: Session, test_user: User, auth_headers: dict
    ):
        """Returns 503 when subscription exists with customer ID but Stripe not configured."""
        sub = Subscription(
            user_id=test_user.id,
            plan="pro_monthly",
            status="active",
            stripe_customer_id="cus_test123",
        )
        db.add(sub)
        db.commit()

        response = await client.post("/api/billing/portal", headers=auth_headers)
        assert response.status_code == 503


class TestWebhook:
    """Tests for POST /api/billing/webhook."""

    @pytest.mark.asyncio
    async def test_webhook_no_signature_header(self, client: AsyncClient):
        """Returns 400 when stripe-signature header is missing."""
        response = await client.post(
            "/api/billing/webhook",
            content=b'{"type": "checkout.session.completed"}',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_webhook_does_not_require_auth(self, client: AsyncClient):
        """Webhook endpoint does not require JWT auth (returns 400, not 401, without signature)."""
        response = await client.post(
            "/api/billing/webhook",
            content=b"{}",
        )
        # 400 (missing signature) not 401 (unauthorized) confirms no auth required
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_webhook_invalid_signature(self, client: AsyncClient):
        """Returns 400 when stripe-signature header is present but invalid."""
        response = await client.post(
            "/api/billing/webhook",
            content=b'{"type": "checkout.session.completed"}',
            headers={
                "Content-Type": "application/json",
                "stripe-signature": "t=invalid,v1=badsig",
            },
        )
        # Billing is disabled in tests so the service returns False → 400
        assert response.status_code == 400
