"""
Billing router for Stripe checkout, portal, and webhook handling.
"""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.billing import (
    BillingStatusResponse,
    CheckoutRequest,
    CheckoutResponse,
    PortalResponse,
)
from app.services.billing_service import get_billing_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["Billing"])


@router.get("/status", response_model=BillingStatusResponse)
def get_billing_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BillingStatusResponse:
    """
    Return the current user's subscription status.

    Returns free/active defaults when no subscription record exists.
    """
    sub = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()

    if sub is None:
        return BillingStatusResponse(plan="free", status="active")

    return BillingStatusResponse(
        plan=str(sub.plan),
        status=str(sub.status),
        current_period_end=sub.current_period_end,  # type: ignore[arg-type]
        usage=[],
    )


@router.post("/checkout", response_model=CheckoutResponse, status_code=status.HTTP_200_OK)
def create_checkout_session(
    body: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CheckoutResponse:
    """
    Create a Stripe Checkout session for upgrading to a paid plan.

    Raises 503 when Stripe is not configured or billing is disabled.
    """
    from app.config import get_settings

    settings = get_settings()

    billing_service = get_billing_service()

    success_url = body.success_url or f"{settings.app_url}/settings/billing?success=true"
    cancel_url = body.cancel_url or f"{settings.app_url}/settings/billing"

    try:
        checkout_url = billing_service.create_checkout_session(
            user_id=int(current_user.id),
            email=str(current_user.email),
            price_id=body.price_id,
            success_url=success_url,
            cancel_url=cancel_url,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    if checkout_url is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not configured. Please contact support.",
        )

    return CheckoutResponse(checkout_url=checkout_url)


@router.post("/portal", response_model=PortalResponse, status_code=status.HTTP_200_OK)
def create_portal_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PortalResponse:
    """
    Create a Stripe Customer Portal session for managing the subscription.

    Raises 404 when no subscription or no Stripe customer ID is found.
    Raises 503 when Stripe is not configured.
    """
    from app.config import get_settings

    settings = get_settings()

    sub = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()

    if sub is None or not sub.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found.",
        )

    billing_service = get_billing_service()
    return_url = f"{settings.app_url}/settings/billing"

    portal_url = billing_service.create_portal_session(
        stripe_customer_id=str(sub.stripe_customer_id),
        return_url=return_url,
    )

    if portal_url is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing portal is not available. Please contact support.",
        )

    return PortalResponse(portal_url=portal_url)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
    stripe_signature: str = Header(None, alias="stripe-signature"),
) -> dict:
    """
    Handle incoming Stripe webhook events.

    Does not require JWT authentication — Stripe signature verification is used instead.
    Returns 400 if the signature header is missing or the event cannot be verified.
    """
    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing stripe-signature header.",
        )

    payload = await request.body()

    billing_service = get_billing_service()
    success = billing_service.handle_webhook_event(
        payload=payload,
        sig_header=stripe_signature,
        db=db,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook verification failed or event could not be processed.",
        )

    return {"received": True}
