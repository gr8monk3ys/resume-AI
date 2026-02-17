"""
Authentication router for Clerk-based auth.

Clerk handles user registration, login, password management, and session tokens
externally. This router provides:
- GET /me: Return current user info (validates Clerk session)
- POST /webhook: Clerk webhook handler for user lifecycle events
- POST /logout: Client-side logout acknowledgment
- DELETE /delete-account: Deactivate user account
- GET /export-data: Export user data for GDPR compliance
"""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db, safe_commit
from app.middleware.audit import AuditEventType, get_audit_logger
from app.middleware.auth import get_current_user
from app.middleware.security import get_client_ip
from app.models.profile import Profile
from app.models.user import User
from app.schemas.user import ClerkWebhookUserData, UserResponse

logger = logging.getLogger(__name__)

settings = get_settings()
router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.

    Validates the Clerk session token and returns the local user record.
    If the user does not exist locally, the get_current_user dependency
    will auto-provision one (just-in-time).
    """
    return current_user


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def clerk_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Handle Clerk webhook events for user lifecycle management.

    Clerk sends webhooks via Svix for these event types:
    - user.created: New user registered in Clerk
    - user.updated: User profile updated in Clerk
    - user.deleted: User deleted from Clerk

    Security:
        Webhook signatures are verified using the svix library and
        the CLERK_WEBHOOK_SECRET environment variable. Requests with
        invalid or missing signatures are rejected with 400.
    """
    audit_logger = get_audit_logger()
    ip_address = get_client_ip(request)

    # Read the raw request body for signature verification
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8")

    # Get Svix verification headers
    svix_id = request.headers.get("svix-id")
    svix_timestamp = request.headers.get("svix-timestamp")
    svix_signature = request.headers.get("svix-signature")

    if not all([svix_id, svix_timestamp, svix_signature]):
        logger.warning("Clerk webhook missing Svix headers from %s", ip_address)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing webhook signature headers",
        )

    # Verify the webhook signature
    webhook_secret = getattr(settings, "clerk_webhook_secret", None) or ""
    if not webhook_secret:
        logger.error("CLERK_WEBHOOK_SECRET is not configured. Cannot verify webhooks.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook verification not configured",
        )

    try:
        from svix.webhooks import Webhook

        wh = Webhook(webhook_secret)
        payload = wh.verify(
            body_str,
            {
                "svix-id": svix_id,
                "svix-timestamp": svix_timestamp,
                "svix-signature": svix_signature,
            },
        )
    except Exception as e:
        logger.warning("Clerk webhook signature verification failed: %s", e)
        audit_logger.log_security_violation(
            violation_type="webhook_signature_invalid",
            details={"error": str(e), "svix_id": svix_id},
            ip_address=ip_address,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature",
        )

    event_type = payload.get("type", "")
    event_data = payload.get("data", {})

    logger.info("Processing Clerk webhook event: %s", event_type)

    if event_type == "user.created":
        _handle_user_created(event_data, db, audit_logger, ip_address)
    elif event_type == "user.updated":
        _handle_user_updated(event_data, db, audit_logger, ip_address)
    elif event_type == "user.deleted":
        _handle_user_deleted(event_data, db, audit_logger, ip_address)
    else:
        logger.debug("Ignoring unhandled Clerk webhook event type: %s", event_type)

    return {"status": "ok"}


def _handle_user_created(
    event_data: dict,
    db: Session,
    audit_logger,
    ip_address: str,
) -> None:
    """
    Handle user.created webhook from Clerk.

    Creates a local User record and an associated Profile if the user
    does not already exist (may have been auto-provisioned by JIT).
    """
    clerk_data = ClerkWebhookUserData(**event_data)
    clerk_id = clerk_data.id
    email = clerk_data.get_primary_email()
    full_name = clerk_data.get_full_name()
    username = clerk_data.username or clerk_id

    # Check if user was already auto-provisioned via JIT
    existing_user = db.query(User).filter(User.clerk_id == clerk_id).first()
    if existing_user:
        # Update with complete data from Clerk
        if email and existing_user.email != email:
            # Only update if not conflicting with another user
            conflict = db.query(User).filter(User.email == email, User.id != existing_user.id).first()
            if not conflict:
                existing_user.email = email
        if full_name:
            existing_user.full_name = full_name
        if clerk_data.username and existing_user.username != clerk_data.username:
            conflict = (
                db.query(User)
                .filter(User.username == clerk_data.username, User.id != existing_user.id)
                .first()
            )
            if not conflict:
                existing_user.username = clerk_data.username

        safe_commit(db, "update JIT-provisioned user from webhook")

        # Ensure profile exists
        if not existing_user.profile:
            profile = Profile(
                user_id=existing_user.id,
                name=full_name or existing_user.username,
                email=email or existing_user.email,
            )
            db.add(profile)
            safe_commit(db, "create profile for JIT user")

        audit_logger.log_event(
            AuditEventType.REGISTER,
            f"Clerk user.created webhook updated JIT user {clerk_id}",
            user_id=existing_user.id,
            username=existing_user.username,
            ip_address=ip_address,
            success=True,
        )
        return

    # Check for email conflict and link if found
    if email:
        existing_by_email = db.query(User).filter(User.email == email).first()
        if existing_by_email:
            existing_by_email.clerk_id = clerk_id
            if full_name:
                existing_by_email.full_name = full_name
            safe_commit(db, "link existing user to Clerk via webhook")

            if not existing_by_email.profile:
                profile = Profile(
                    user_id=existing_by_email.id,
                    name=full_name or existing_by_email.username,
                    email=email,
                )
                db.add(profile)
                safe_commit(db, "create profile for linked user")

            audit_logger.log_event(
                AuditEventType.REGISTER,
                f"Clerk user.created linked existing user to {clerk_id}",
                user_id=existing_by_email.id,
                username=existing_by_email.username,
                ip_address=ip_address,
                success=True,
            )
            return

    # Ensure username uniqueness
    base_username = username
    counter = 1
    while db.query(User).filter(User.username == username).first():
        username = f"{base_username}_{counter}"
        counter += 1

    # Create new user
    user = User(
        clerk_id=clerk_id,
        username=username,
        email=email or f"{clerk_id}@clerk.placeholder",
        full_name=full_name,
        is_active=True,
    )
    db.add(user)
    db.flush()  # Get user.id without full commit

    # Create associated profile
    profile = Profile(
        user_id=user.id,
        name=full_name or username,
        email=email or user.email,
    )
    db.add(profile)
    safe_commit(db, "create user and profile from Clerk webhook")
    db.refresh(user)

    audit_logger.log_event(
        AuditEventType.REGISTER,
        f"New user created from Clerk webhook: {clerk_id} ({username})",
        user_id=user.id,
        username=username,
        ip_address=ip_address,
        success=True,
    )


def _handle_user_updated(
    event_data: dict,
    db: Session,
    audit_logger,
    ip_address: str,
) -> None:
    """
    Handle user.updated webhook from Clerk.

    Updates the local User record with changed fields from Clerk
    (email, username, full_name).
    """
    clerk_data = ClerkWebhookUserData(**event_data)
    clerk_id = clerk_data.id

    user = db.query(User).filter(User.clerk_id == clerk_id).first()
    if not user:
        logger.warning(
            "Received user.updated webhook for unknown Clerk user %s. Ignoring.",
            clerk_id,
        )
        return

    updated_fields = []

    # Update email if changed and not conflicting
    new_email = clerk_data.get_primary_email()
    if new_email and new_email != user.email:
        conflict = db.query(User).filter(User.email == new_email, User.id != user.id).first()
        if not conflict:
            user.email = new_email
            updated_fields.append("email")
            # Also update profile email if profile exists
            if user.profile:
                user.profile.email = new_email

    # Update full_name if changed
    new_full_name = clerk_data.get_full_name()
    if new_full_name and new_full_name != user.full_name:
        user.full_name = new_full_name
        updated_fields.append("full_name")
        # Also update profile name
        if user.profile:
            user.profile.name = new_full_name

    # Update username if changed and not conflicting
    if clerk_data.username and clerk_data.username != user.username:
        conflict = (
            db.query(User)
            .filter(User.username == clerk_data.username, User.id != user.id)
            .first()
        )
        if not conflict:
            user.username = clerk_data.username
            updated_fields.append("username")

    if updated_fields:
        safe_commit(db, "update user from Clerk webhook")
        audit_logger.log_event(
            AuditEventType.DATA_UPDATED,
            f"User {user.username} updated from Clerk webhook: {', '.join(updated_fields)}",
            user_id=user.id,
            username=user.username,
            ip_address=ip_address,
            details={"updated_fields": updated_fields},
            success=True,
        )
    else:
        logger.debug("No changes detected in user.updated webhook for %s", clerk_id)


def _handle_user_deleted(
    event_data: dict,
    db: Session,
    audit_logger,
    ip_address: str,
) -> None:
    """
    Handle user.deleted webhook from Clerk.

    Deactivates the local User record (soft delete) rather than
    hard-deleting, to preserve data integrity for related records.
    """
    clerk_id = event_data.get("id", "")
    if not clerk_id:
        logger.warning("Received user.deleted webhook without user ID. Ignoring.")
        return

    user = db.query(User).filter(User.clerk_id == clerk_id).first()
    if not user:
        logger.warning(
            "Received user.deleted webhook for unknown Clerk user %s. Ignoring.",
            clerk_id,
        )
        return

    user.is_active = False
    safe_commit(db, "deactivate user from Clerk webhook")

    audit_logger.log_event(
        AuditEventType.ACCOUNT_DELETED,
        f"User {user.username} deactivated via Clerk user.deleted webhook",
        user_id=user.id,
        username=user.username,
        ip_address=ip_address,
        success=True,
    )


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Acknowledge user logout.

    The actual session termination is handled by Clerk on the frontend.
    This endpoint exists for audit logging and any server-side cleanup.
    """
    audit_logger = get_audit_logger()
    ip_address = get_client_ip(request)
    request_id = getattr(request.state, "request_id", None)

    audit_logger.log_event(
        AuditEventType.LOGOUT,
        f"User {current_user.username} logged out",
        user_id=current_user.id,
        username=current_user.username,
        ip_address=ip_address,
        request_id=request_id,
        success=True,
    )

    return {"message": "Successfully logged out"}


@router.delete("/delete-account", status_code=status.HTTP_200_OK)
async def delete_account(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Deactivate the current user's account.

    Performs a soft delete by setting is_active=False. The user record
    and all associated data are preserved for data integrity. To fully
    remove the user from Clerk, the frontend should call Clerk's
    deleteUser API separately.
    """
    audit_logger = get_audit_logger()
    ip_address = get_client_ip(request)
    request_id = getattr(request.state, "request_id", None)

    current_user.is_active = False
    safe_commit(db, "deactivate user account")

    audit_logger.log_event(
        AuditEventType.ACCOUNT_DELETED,
        f"User {current_user.username} deactivated their account",
        user_id=current_user.id,
        username=current_user.username,
        ip_address=ip_address,
        request_id=request_id,
        success=True,
    )

    return {"message": "Account has been deactivated"}


@router.get("/export-data")
async def export_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Export all user data for GDPR compliance.

    Returns a JSON object containing the user's profile, resumes,
    job applications, cover letters, and career journal entries.
    """
    audit_logger = get_audit_logger()

    user_data = {
        "user": {
            "id": current_user.id,
            "clerk_id": current_user.clerk_id,
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
        },
    }

    # Export profile data if it exists
    if current_user.profile:
        profile = current_user.profile
        user_data["profile"] = {
            "name": profile.name,
            "email": profile.email,
            "phone": profile.phone,
            "linkedin": profile.linkedin,
            "github": profile.github,
            "portfolio": profile.portfolio,
        }

        # Export resumes
        if hasattr(profile, "resumes") and profile.resumes:
            user_data["resumes"] = [
                {
                    "id": r.id,
                    "title": getattr(r, "title", None),
                    "created_at": r.created_at.isoformat() if hasattr(r, "created_at") and r.created_at else None,
                }
                for r in profile.resumes
            ]

        # Export job applications
        if hasattr(profile, "job_applications") and profile.job_applications:
            user_data["job_applications"] = [
                {
                    "id": j.id,
                    "company": getattr(j, "company", None),
                    "position": getattr(j, "position", None),
                    "status": getattr(j, "status", None),
                    "created_at": j.created_at.isoformat() if hasattr(j, "created_at") and j.created_at else None,
                }
                for j in profile.job_applications
            ]

        # Export cover letters
        if hasattr(profile, "cover_letters") and profile.cover_letters:
            user_data["cover_letters"] = [
                {
                    "id": c.id,
                    "title": getattr(c, "title", None),
                    "created_at": c.created_at.isoformat() if hasattr(c, "created_at") and c.created_at else None,
                }
                for c in profile.cover_letters
            ]

        # Export journal entries
        if hasattr(profile, "journal_entries") and profile.journal_entries:
            user_data["journal_entries"] = [
                {
                    "id": e.id,
                    "title": getattr(e, "title", None),
                    "content": getattr(e, "content", None),
                    "created_at": e.created_at.isoformat() if hasattr(e, "created_at") and e.created_at else None,
                }
                for e in profile.journal_entries
            ]

    audit_logger.log_event(
        AuditEventType.DATA_EXPORTED,
        f"User {current_user.username} exported their data",
        user_id=current_user.id,
        username=current_user.username,
        success=True,
    )

    return user_data
