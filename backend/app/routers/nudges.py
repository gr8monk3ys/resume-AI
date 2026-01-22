"""
Nudge system router — surfaces actionable follow-up cards.
"""

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_user_profile
from app.middleware.auth import get_current_user
from app.models.interview_event import InterviewEvent
from app.models.job_application import JobApplication
from app.models.resume import Resume
from app.models.user import User
from app.schemas.nudge import DraftRequest, DraftResponse, NudgeItem, NudgeResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/nudges", tags=["Nudges"])

MAX_NUDGES = 20


def _handle_ai_error(e: Exception, operation: str, user_id: int) -> HTTPException:
    settings = get_settings()
    logger.error(f"{operation} failed for user {user_id}: {str(e)}")
    if settings.debug:
        return HTTPException(status_code=500, detail=f"{operation} failed: {str(e)}")
    return HTTPException(status_code=500, detail=f"{operation} failed. Please try again later.")


@router.get("", response_model=NudgeResponse)
def list_nudges(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compute actionable nudges from existing user data."""
    profile = get_user_profile(current_user, db)
    nudges: list[NudgeItem] = []
    today = date.today()
    now = datetime.now(timezone.utc)
    today_str = today.isoformat()

    # --- overdue_followup (priority 1) ---
    overdue_events = (
        db.query(InterviewEvent)
        .filter(
            InterviewEvent.profile_id == profile.id,
            InterviewEvent.follow_up_date != None,  # noqa: E711
            InterviewEvent.follow_up_done == False,  # noqa: E712
        )
        .all()
    )
    for ev in overdue_events:
        if ev.follow_up_date and str(ev.follow_up_date) < today_str:
            days = (today - date.fromisoformat(str(ev.follow_up_date))).days
            nudges.append(
                NudgeItem(
                    nudge_type="overdue_followup",
                    entity_type="interview_event",
                    entity_id=int(ev.id),
                    company=str(ev.company),
                    position=str(ev.position),
                    title=f"Overdue follow-up: {ev.company}",
                    description=f"Your follow-up for the {ev.position} role was due {days} day{'s' if days != 1 else ''} ago.",
                    color="#ef4444",
                    days_ago=days,
                )
            )

    # --- interview_prep (priority 2) ---
    two_days_later_str = (today + timedelta(days=2)).isoformat()
    upcoming_events = (
        db.query(InterviewEvent)
        .filter(
            InterviewEvent.profile_id == profile.id,
            InterviewEvent.scheduled_date >= today_str,
            InterviewEvent.scheduled_date <= two_days_later_str,
            InterviewEvent.is_completed == False,  # noqa: E712
        )
        .all()
    )
    for ev in upcoming_events:
        nudges.append(
            NudgeItem(
                nudge_type="interview_prep",
                entity_type="interview_event",
                entity_id=int(ev.id),
                company=str(ev.company),
                position=str(ev.position),
                title=f"Prep for {ev.company} interview",
                description=f"Your {ev.event_type.replace('_', ' ')} for {ev.position} is on {ev.scheduled_date}.",
                color="#3b82f6",
                scheduled_date=str(ev.scheduled_date),
            )
        )

    # --- thank_you (priority 3) ---
    cutoff_48h = now - timedelta(hours=48)
    completed_recent = (
        db.query(InterviewEvent)
        .filter(
            InterviewEvent.profile_id == profile.id,
            InterviewEvent.is_completed == True,  # noqa: E712
            InterviewEvent.updated_at >= cutoff_48h,
        )
        .all()
    )
    for ev in completed_recent:
        nudges.append(
            NudgeItem(
                nudge_type="thank_you",
                entity_type="interview_event",
                entity_id=int(ev.id),
                company=str(ev.company),
                position=str(ev.position),
                title=f"Send thank-you to {ev.company}",
                description=f"You completed your {ev.event_type.replace('_', ' ')} for {ev.position} — send a thank-you note!",
                color="#10b981",
            )
        )

    # --- stale_followup (priority 4) ---
    seven_days_ago = today - timedelta(days=7)
    stale_apps = (
        db.query(JobApplication)
        .filter(
            JobApplication.profile_id == profile.id,
            JobApplication.status == "Applied",
            JobApplication.application_date != None,  # noqa: E711
            JobApplication.application_date <= seven_days_ago,
            JobApplication.response_date == None,  # noqa: E711
        )
        .all()
    )
    for app in stale_apps:
        days = (today - app.application_date).days
        nudges.append(
            NudgeItem(
                nudge_type="stale_followup",
                entity_type="job",
                entity_id=int(app.id),
                company=str(app.company),
                position=str(app.position),
                title=f"Follow up with {app.company}",
                description=f"Applied {days} days ago for {app.position} with no response.",
                color="#f97316",
                days_ago=days,
                recruiter_name=str(app.recruiter_name) if app.recruiter_name else None,
                recruiter_email=str(app.recruiter_email) if app.recruiter_email else None,
            )
        )

    # --- application_velocity (priority 5) ---
    # Count applications this week (Mon-Sun)
    week_start = today - timedelta(days=today.weekday())
    week_apps = (
        db.query(JobApplication)
        .filter(
            JobApplication.profile_id == profile.id,
            JobApplication.application_date != None,  # noqa: E711
            JobApplication.application_date >= week_start,
        )
        .count()
    )
    if week_apps < 5:
        nudges.append(
            NudgeItem(
                nudge_type="application_velocity",
                entity_type="metric",
                entity_id=None,
                title="Pick up the pace this week",
                description=f"You've submitted {week_apps} application{'s' if week_apps != 1 else ''} this week — aim for at least 5.",
                color="#a855f7",
            )
        )

    # --- resume_freshness (priority 6) ---
    thirty_days_ago = now - timedelta(days=30)
    stale_resumes = (
        db.query(Resume)
        .filter(
            Resume.profile_id == profile.id,
            Resume.updated_at < thirty_days_ago,
        )
        .all()
    )
    for resume in stale_resumes:
        days = (now - resume.updated_at).days if resume.updated_at else 30
        nudges.append(
            NudgeItem(
                nudge_type="resume_freshness",
                entity_type="resume",
                entity_id=int(resume.id),
                title=f'Update "{resume.version_name}"',
                description=f"This resume hasn't been updated in {days} days.",
                color="#f59e0b",
                days_ago=days,
            )
        )

    # Cap at MAX_NUDGES (already in priority order)
    return NudgeResponse(nudges=nudges[:MAX_NUDGES], generated_at=now)


@router.post("/draft", response_model=DraftResponse)
async def generate_draft(
    request: DraftRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate AI draft content for a nudge action."""
    from app.services.llm_service import get_llm_service

    prompts = {
        "stale_followup": (
            f"Write a professional, concise follow-up email for a job application.\n"
            f"Company: {request.company}\n"
            f"Position: {request.position}\n"
            f"{'Recruiter: ' + request.recruiter_name if request.recruiter_name else ''}\n"
            f"{'Additional context: ' + request.additional_context if request.additional_context else ''}\n\n"
            f"Format: Start with 'Subject: ...' on the first line, then the email body.\n"
            f"Keep it under 150 words. Be enthusiastic but not pushy."
        ),
        "interview_prep": (
            f"Generate interview preparation notes for:\n"
            f"Company: {request.company}\n"
            f"Position: {request.position}\n"
            f"{'Additional context: ' + request.additional_context if request.additional_context else ''}\n\n"
            f"Include:\n"
            f"1. Key questions to prepare for\n"
            f"2. Company talking points\n"
            f"3. Questions to ask the interviewer\n"
            f"4. Quick tips for confidence\n"
            f"Format in markdown."
        ),
        "overdue_followup": (
            f"Write a professional follow-up email after an interview where the follow-up is overdue.\n"
            f"Company: {request.company}\n"
            f"Position: {request.position}\n"
            f"{'Recruiter: ' + request.recruiter_name if request.recruiter_name else ''}\n"
            f"{'Additional context: ' + request.additional_context if request.additional_context else ''}\n\n"
            f"Format: Start with 'Subject: ...' on the first line, then the email body.\n"
            f"Be polite and express continued interest. Keep under 150 words."
        ),
        "thank_you": (
            f"Write a professional thank-you email after a job interview.\n"
            f"Company: {request.company}\n"
            f"Position: {request.position}\n"
            f"{'Additional context: ' + request.additional_context if request.additional_context else ''}\n\n"
            f"Format: Start with 'Subject: ...' on the first line, then the email body.\n"
            f"Be genuine and specific. Reference the conversation. Keep under 200 words."
        ),
        "application_velocity": (
            f"Create a motivational action plan for increasing job application output this week.\n"
            f"{'Additional context: ' + request.additional_context if request.additional_context else ''}\n\n"
            f"Include:\n"
            f"1. A brief pep talk (2-3 sentences)\n"
            f"2. 5 specific, actionable steps to find and apply to more jobs today\n"
            f"3. Tips for efficient batch-applying\n"
            f"Format in markdown."
        ),
        "resume_freshness": (
            f"Create a resume improvement checklist.\n"
            f"{'Additional context: ' + request.additional_context if request.additional_context else ''}\n\n"
            f"Include:\n"
            f"1. Key sections to review and update\n"
            f"2. Modern resume best practices\n"
            f"3. Common mistakes to fix\n"
            f"4. Quick wins for immediate improvement\n"
            f"Format in markdown with checkboxes (- [ ])."
        ),
    }

    prompt = prompts.get(request.nudge_type)
    if not prompt:
        raise HTTPException(status_code=400, detail=f"Unknown nudge type: {request.nudge_type}")

    try:
        llm_service = get_llm_service()
        result = await asyncio.to_thread(llm_service._invoke, prompt)

        # Parse subject line for email-type drafts
        subject = None
        content = result
        email_types = {"stale_followup", "overdue_followup", "thank_you"}
        if request.nudge_type in email_types:
            lines = result.strip().split("\n")
            for i, line in enumerate(lines):
                if line.lower().startswith("subject:"):
                    subject = line[8:].strip()
                    content = "\n".join(lines[i + 1 :]).strip()
                    break

        tips_map = {
            "stale_followup": [
                "Personalize with a detail from the job posting",
                "Send between Tuesday and Thursday for best response rates",
            ],
            "interview_prep": [
                "Practice answers out loud before the interview",
                "Research recent company news",
            ],
            "overdue_followup": [
                "Keep it brief and professional",
                "Mention a specific topic from your interview",
            ],
            "thank_you": [
                "Send within 24 hours of the interview",
                "Reference something specific from the conversation",
            ],
            "application_velocity": [
                "Set a timer for focused application sessions",
                "Use your saved resumes to speed up the process",
            ],
            "resume_freshness": [
                "Quantify achievements wherever possible",
                "Tailor keywords to your target roles",
            ],
        }

        return DraftResponse(
            content=content,
            subject=subject,
            tips=tips_map.get(request.nudge_type, []),
        )
    except Exception as e:
        raise _handle_ai_error(e, "Failed to generate draft", int(current_user.id))
