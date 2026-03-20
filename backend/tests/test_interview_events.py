"""
Tests for interview event endpoints.

Tests:
- CRUD operations for interview events (create, read, list, update, delete)
- Search and event type filtering
- User data isolation (can't access others' events)
- Validation and error handling
- Edge cases (special characters, unicode, date handling, duration values)
"""

import json

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.interview_event import InterviewEvent
from app.models.job_application import JobApplication
from app.models.profile import Profile
from app.models.user import User


def _create_interview_event(
    db: Session,
    profile_id: int,
    company: str = "Stripe",
    position: str = "Senior Backend Engineer",
    event_type: str = "Technical Interview",
    scheduled_date: str = "2026-04-15",
    scheduled_time: str | None = "10:00",
    duration_minutes: int | None = 60,
    location: str | None = None,
    meeting_link: str | None = "https://zoom.us/j/123456789",
    interviewer_names: list | None = None,
    notes: str | None = None,
    is_completed: bool = False,
    follow_up_date: str | None = None,
    follow_up_done: bool = False,
    job_application_id: int | None = None,
) -> InterviewEvent:
    """Helper to create an interview event directly via ORM."""
    entry = InterviewEvent(
        profile_id=profile_id,
        job_application_id=job_application_id,
        company=company,
        position=position,
        event_type=event_type,
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
        duration_minutes=duration_minutes,
        location=location,
        meeting_link=meeting_link,
        interviewer_names=json.dumps(interviewer_names) if interviewer_names is not None else None,
        notes=notes,
        is_completed=is_completed,
        follow_up_date=follow_up_date,
        follow_up_done=follow_up_done,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


class TestInterviewEventList:
    """Tests for listing interview events."""

    @pytest.mark.asyncio
    async def test_list_events_empty(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test listing interview events when none exist."""
        response = await client.get("/api/interview-events", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data == []

    @pytest.mark.asyncio
    async def test_list_events_with_items(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test listing interview events when they exist."""
        event = _create_interview_event(db, test_profile.id)

        response = await client.get("/api/interview-events", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["company"] == event.company
        assert data[0]["id"] == event.id

    @pytest.mark.asyncio
    async def test_list_events_multiple_ordered_by_date_desc(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test that multiple events are returned ordered by scheduled_date descending."""
        _create_interview_event(db, test_profile.id, company="Airbnb", scheduled_date="2026-03-01")
        _create_interview_event(
            db, test_profile.id, company="Coinbase", scheduled_date="2026-05-20"
        )
        _create_interview_event(db, test_profile.id, company="Figma", scheduled_date="2026-04-10")

        response = await client.get("/api/interview-events", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        # Most recent date should be first (desc order)
        assert data[0]["company"] == "Coinbase"
        assert data[1]["company"] == "Figma"
        assert data[2]["company"] == "Airbnb"

    @pytest.mark.asyncio
    async def test_list_events_unauthorized(self, client: AsyncClient, db: Session):
        """Test listing interview events without authentication."""
        response = await client.get("/api/interview-events")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_events_filter_by_event_type(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test filtering events by event type."""
        _create_interview_event(db, test_profile.id, company="Meta", event_type="Phone Screen")
        _create_interview_event(db, test_profile.id, company="Apple", event_type="System Design")
        _create_interview_event(db, test_profile.id, company="Google", event_type="Phone Screen")

        response = await client.get(
            "/api/interview-events",
            params={"event_type": "Phone Screen"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        for item in data:
            assert item["event_type"] == "Phone Screen"

    @pytest.mark.asyncio
    async def test_list_events_search_by_company(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test searching events by company name."""
        _create_interview_event(db, test_profile.id, company="Netflix")
        _create_interview_event(db, test_profile.id, company="Databricks")

        response = await client.get(
            "/api/interview-events",
            params={"search": "netflix"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["company"] == "Netflix"


class TestInterviewEventCreate:
    """Tests for creating interview events."""

    @pytest.mark.asyncio
    async def test_create_event_minimal_fields(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating an interview event with only required fields."""
        event_data = {
            "company": "Vercel",
            "position": "Full-Stack Engineer",
            "event_type": "Recruiter Call",
            "scheduled_date": "2026-04-22",
        }
        response = await client.post("/api/interview-events", json=event_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["company"] == "Vercel"
        assert data["position"] == "Full-Stack Engineer"
        assert data["event_type"] == "Recruiter Call"
        assert data["scheduled_date"] == "2026-04-22"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert data["profile_id"] == test_profile.id
        assert data["is_completed"] is False
        assert data["follow_up_done"] is False
        assert data["scheduled_time"] is None
        assert data["interviewer_names"] is None

    @pytest.mark.asyncio
    async def test_create_event_all_fields(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating an interview event with all fields populated."""
        event_data = {
            "company": "Anthropic",
            "position": "ML Infrastructure Engineer",
            "event_type": "On-Site Panel",
            "scheduled_date": "2026-05-10",
            "scheduled_time": "09:30",
            "duration_minutes": 240,
            "location": "548 Market St, San Francisco, CA 94104",
            "meeting_link": "https://meet.google.com/abc-defg-hij",
            "interviewer_names": ["Sarah Chen", "Michael Torres", "Priya Kapoor"],
            "notes": "Four back-to-back sessions: system design, coding, ML fundamentals, and team fit",
            "is_completed": False,
            "follow_up_date": "2026-05-12",
            "follow_up_done": False,
        }
        response = await client.post("/api/interview-events", json=event_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["company"] == "Anthropic"
        assert data["duration_minutes"] == 240
        assert data["location"] == "548 Market St, San Francisco, CA 94104"
        assert data["interviewer_names"] == ["Sarah Chen", "Michael Torres", "Priya Kapoor"]
        assert data["follow_up_date"] == "2026-05-12"
        assert data["notes"].startswith("Four back-to-back")

    @pytest.mark.asyncio
    async def test_create_event_unauthorized(self, client: AsyncClient, db: Session):
        """Test creating an interview event without authentication."""
        response = await client.post(
            "/api/interview-events",
            json={
                "company": "Unauthorized Corp",
                "position": "Engineer",
                "event_type": "Phone Screen",
                "scheduled_date": "2026-04-01",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_event_missing_required_fields(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating an interview event without required fields."""
        # Missing company, position, event_type, and scheduled_date
        response = await client.post(
            "/api/interview-events",
            json={"notes": "No required fields provided"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_event_empty_required_fields(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating an interview event with empty required fields."""
        response = await client.post(
            "/api/interview-events",
            json={
                "company": "",
                "position": "Engineer",
                "event_type": "Phone Screen",
                "scheduled_date": "2026-04-01",
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_event_with_interviewer_names(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating an interview event with a list of interviewer names."""
        event_data = {
            "company": "Spotify",
            "position": "Data Engineer",
            "event_type": "Technical Interview",
            "scheduled_date": "2026-04-18",
            "interviewer_names": ["Elena Rodriguez", "Jakub Nowak"],
        }
        response = await client.post("/api/interview-events", json=event_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["interviewer_names"] == ["Elena Rodriguez", "Jakub Nowak"]

    @pytest.mark.asyncio
    async def test_create_event_with_job_application_link(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        test_job: JobApplication,
        auth_headers: dict,
    ):
        """Test creating an interview event linked to a job application."""
        event_data = {
            "company": "Tech Company",
            "position": "Senior Developer",
            "event_type": "Hiring Manager Interview",
            "scheduled_date": "2026-04-25",
            "job_application_id": test_job.id,
        }
        response = await client.post("/api/interview-events", json=event_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["job_application_id"] == test_job.id


class TestInterviewEventGet:
    """Tests for reading individual interview events."""

    @pytest.mark.asyncio
    async def test_get_event_success(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test getting a specific interview event by ID."""
        event = _create_interview_event(
            db,
            test_profile.id,
            company="Datadog",
            position="Site Reliability Engineer",
            interviewer_names=["Alex Kim", "Jordan Lee"],
        )

        response = await client.get(f"/api/interview-events/{event.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == event.id
        assert data["company"] == "Datadog"
        assert data["position"] == "Site Reliability Engineer"
        assert data["interviewer_names"] == ["Alex Kim", "Jordan Lee"]

    @pytest.mark.asyncio
    async def test_get_event_unauthorized(
        self, client: AsyncClient, db: Session, test_profile: Profile
    ):
        """Test getting an interview event without authentication."""
        event = _create_interview_event(db, test_profile.id)
        response = await client.get(f"/api/interview-events/{event.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_event_not_found(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test getting a non-existent interview event."""
        response = await client.get("/api/interview-events/99999", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestInterviewEventUpdate:
    """Tests for updating interview events."""

    @pytest.mark.asyncio
    async def test_update_event_success(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test updating all fields of an interview event."""
        event = _create_interview_event(db, test_profile.id)

        update_data = {
            "company": "Stripe (Updated)",
            "position": "Staff Backend Engineer",
            "event_type": "Final Round Panel",
            "scheduled_date": "2026-05-01",
            "scheduled_time": "14:00",
            "duration_minutes": 180,
            "location": "Stripe HQ, South San Francisco",
            "notes": "Rescheduled from original date. Four sessions with lunch break.",
        }
        response = await client.put(
            f"/api/interview-events/{event.id}", json=update_data, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["company"] == "Stripe (Updated)"
        assert data["position"] == "Staff Backend Engineer"
        assert data["duration_minutes"] == 180
        assert data["location"] == "Stripe HQ, South San Francisco"

    @pytest.mark.asyncio
    async def test_update_event_partial(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test updating only a subset of fields leaves other fields unchanged."""
        event = _create_interview_event(
            db,
            test_profile.id,
            company="Plaid",
            position="Platform Engineer",
            notes="Initial round with engineering manager",
        )

        response = await client.put(
            f"/api/interview-events/{event.id}",
            json={"notes": "Rescheduled to include a second interviewer"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["company"] == "Plaid"
        assert data["position"] == "Platform Engineer"
        assert data["notes"] == "Rescheduled to include a second interviewer"

    @pytest.mark.asyncio
    async def test_update_event_unauthorized(
        self, client: AsyncClient, db: Session, test_profile: Profile
    ):
        """Test updating an interview event without authentication."""
        event = _create_interview_event(db, test_profile.id)
        response = await client.put(
            f"/api/interview-events/{event.id}",
            json={"company": "Unauthorized Update"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_event_not_found(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test updating a non-existent interview event."""
        response = await client.put(
            "/api/interview-events/99999",
            json={"company": "Ghost Corp"},
            headers=auth_headers,
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_event_mark_complete(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test marking an interview event as completed."""
        event = _create_interview_event(db, test_profile.id, is_completed=False)

        response = await client.put(
            f"/api/interview-events/{event.id}",
            json={"is_completed": True},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_completed"] is True

    @pytest.mark.asyncio
    async def test_update_event_toggle_follow_up(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test toggling follow-up status and setting follow-up date."""
        event = _create_interview_event(
            db, test_profile.id, follow_up_done=False, follow_up_date=None
        )

        response = await client.put(
            f"/api/interview-events/{event.id}",
            json={"follow_up_date": "2026-04-20", "follow_up_done": True},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["follow_up_date"] == "2026-04-20"
        assert data["follow_up_done"] is True

    @pytest.mark.asyncio
    async def test_update_event_interviewer_names(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test updating interviewer names list."""
        event = _create_interview_event(
            db,
            test_profile.id,
            interviewer_names=["Original Interviewer"],
        )

        response = await client.put(
            f"/api/interview-events/{event.id}",
            json={"interviewer_names": ["Maria Santos", "David Park", "Aisha Johnson"]},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["interviewer_names"] == ["Maria Santos", "David Park", "Aisha Johnson"]


class TestInterviewEventDelete:
    """Tests for deleting interview events."""

    @pytest.mark.asyncio
    async def test_delete_event_success(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test successful interview event deletion."""
        event = _create_interview_event(db, test_profile.id, company="Dropbox")
        event_id = event.id

        response = await client.delete(f"/api/interview-events/{event_id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify it is deleted
        get_response = await client.get(f"/api/interview-events/{event_id}", headers=auth_headers)
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_event_unauthorized(
        self, client: AsyncClient, db: Session, test_profile: Profile
    ):
        """Test deleting an interview event without authentication."""
        event = _create_interview_event(db, test_profile.id)
        response = await client.delete(f"/api/interview-events/{event.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_event_not_found(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test deleting a non-existent interview event."""
        response = await client.delete("/api/interview-events/99999", headers=auth_headers)
        assert response.status_code == 404


class TestInterviewEventIsolation:
    """Tests for user data isolation."""

    @pytest.mark.asyncio
    async def test_user_cannot_read_other_users_event(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        admin_user: User,
        admin_auth_headers: dict,
    ):
        """Test that a user cannot access another user's interview event."""
        event = _create_interview_event(
            db, test_profile.id, company="Confidential Interview Target"
        )

        response = await client.get(f"/api/interview-events/{event.id}", headers=admin_auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_update_other_users_event(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        admin_user: User,
        admin_auth_headers: dict,
    ):
        """Test that a user cannot update another user's interview event."""
        event = _create_interview_event(db, test_profile.id)

        response = await client.put(
            f"/api/interview-events/{event.id}",
            json={"company": "Hijacked Company"},
            headers=admin_auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_delete_other_users_event(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        admin_user: User,
        admin_auth_headers: dict,
    ):
        """Test that a user cannot delete another user's interview event."""
        event = _create_interview_event(db, test_profile.id)

        response = await client.delete(
            f"/api/interview-events/{event.id}", headers=admin_auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_only_sees_own_events(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        admin_user: User,
        admin_auth_headers: dict,
        auth_headers: dict,
    ):
        """Test that listing events only returns the user's own entries."""
        _create_interview_event(db, test_profile.id, company="Test User's Secret Interview")

        # Admin lists events - should see nothing
        response = await client.get("/api/interview-events", headers=admin_auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 0

        # Test user lists events - should see their own
        response = await client.get("/api/interview-events", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestInterviewEventEdgeCases:
    """Tests for edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_event_with_special_characters(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating an event with special characters in text fields."""
        event_data = {
            "company": "Ernst & Young (EY)",
            "position": "Senior Consultant <Technology>",
            "event_type": "Case Study",
            "scheduled_date": "2026-04-30",
            "notes": "They'll ask about O'Reilly's framework & \"digital transformation\" strategy",
        }
        response = await client.post("/api/interview-events", json=event_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["company"] == "Ernst & Young (EY)"
        assert "O'Reilly" in data["notes"]

    @pytest.mark.asyncio
    async def test_event_with_unicode_content(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating an event with unicode and multilingual content."""
        event_data = {
            "company": "Mercado Libre",
            "position": "Ingeniero de Software S\u00e9nior",
            "event_type": "Entrevista T\u00e9cnica",
            "scheduled_date": "2026-05-05",
            "notes": "Interview conducted in Spanish and English. \u00a1Buena suerte!",
        }
        response = await client.post("/api/interview-events", json=event_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert "S\u00e9nior" in data["position"]
        assert "\u00a1Buena suerte!" in data["notes"]

    @pytest.mark.asyncio
    async def test_event_with_past_date(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating an event with a past date (recording historical interviews)."""
        event_data = {
            "company": "Amazon",
            "position": "Software Development Engineer II",
            "event_type": "Loop Interview",
            "scheduled_date": "2025-11-15",
            "is_completed": True,
            "notes": "Completed all 5 sessions. Strong positive signals from bar raiser.",
        }
        response = await client.post("/api/interview-events", json=event_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["scheduled_date"] == "2025-11-15"
        assert data["is_completed"] is True

    @pytest.mark.asyncio
    async def test_event_with_future_date(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating an event with a far-future date."""
        event_data = {
            "company": "SpaceX",
            "position": "Avionics Software Engineer",
            "event_type": "On-Site Interview",
            "scheduled_date": "2027-01-15",
            "notes": "Hawthorne campus visit scheduled well in advance",
        }
        response = await client.post("/api/interview-events", json=event_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["scheduled_date"] == "2027-01-15"

    @pytest.mark.asyncio
    async def test_event_with_duration_edge_values(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating events with various duration values."""
        # Very short duration (15-minute recruiter screen)
        event_data = {
            "company": "Twilio",
            "position": "Developer Evangelist",
            "event_type": "Quick Intro Call",
            "scheduled_date": "2026-04-08",
            "duration_minutes": 15,
        }
        response = await client.post("/api/interview-events", json=event_data, headers=auth_headers)
        assert response.status_code == 201
        assert response.json()["duration_minutes"] == 15

        # Full day on-site (480 minutes = 8 hours)
        event_data_long = {
            "company": "Bloomberg",
            "position": "Senior Software Engineer",
            "event_type": "Super Day",
            "scheduled_date": "2026-04-22",
            "duration_minutes": 480,
        }
        response = await client.post(
            "/api/interview-events", json=event_data_long, headers=auth_headers
        )
        assert response.status_code == 201
        assert response.json()["duration_minutes"] == 480

    @pytest.mark.asyncio
    async def test_event_with_various_meeting_link_formats(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test creating events with different meeting link formats."""
        links = [
            "https://zoom.us/j/98765432100?pwd=abc123",
            "https://meet.google.com/xyz-abcd-efg",
            "https://teams.microsoft.com/l/meetup-join/19%3ameeting_abc",
        ]
        for i, link in enumerate(links):
            event_data = {
                "company": f"Company {i + 1}",
                "position": "Engineer",
                "event_type": "Video Interview",
                "scheduled_date": f"2026-04-{10 + i:02d}",
                "meeting_link": link,
            }
            response = await client.post(
                "/api/interview-events", json=event_data, headers=auth_headers
            )
            assert response.status_code == 201
            assert response.json()["meeting_link"] == link
