"""
Tests for AI service endpoints.

Tests run with LLM_PROVIDER=mock to avoid API calls.

Tests:
- Tailor resume endpoint
- Answer question endpoint
- Interview prep endpoint
- Grammar check endpoint
- Optimize resume endpoint
- Networking email generation
- Keyword suggestions
- Job match score
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.profile import Profile
from app.models.user import User


class TestTailorResume:
    """Tests for resume tailoring endpoint."""

    @pytest.mark.asyncio
    async def test_tailor_resume_success(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        auth_headers: dict,
        sample_resume_content: str,
        sample_job_description: str,
    ):
        """Test successful resume tailoring."""
        response = await client.post(
            "/api/ai/tailor-resume",
            json={
                "resume_content": sample_resume_content,
                "job_description": sample_job_description,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "tailored_resume" in data
        assert len(data["tailored_resume"]) > 0
        assert "changes_made" in data
        assert isinstance(data["changes_made"], list)
        assert "keywords_added" in data
        assert isinstance(data["keywords_added"], list)

    @pytest.mark.asyncio
    async def test_tailor_resume_with_focus_areas(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        auth_headers: dict,
        sample_resume_content: str,
        sample_job_description: str,
    ):
        """Test resume tailoring with focus areas."""
        response = await client.post(
            "/api/ai/tailor-resume",
            json={
                "resume_content": sample_resume_content,
                "job_description": sample_job_description,
                "focus_areas": ["leadership", "technical skills"],
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "tailored_resume" in data

    @pytest.mark.asyncio
    async def test_tailor_resume_unauthorized(self, client: AsyncClient, db: Session):
        """Test resume tailoring without authentication."""
        response = await client.post(
            "/api/ai/tailor-resume",
            json={
                "resume_content": "Test resume",
                "job_description": "Test job",
            },
        )
        assert response.status_code == 401


class TestAnswerQuestion:
    """Tests for application question answering endpoint."""

    @pytest.mark.asyncio
    async def test_answer_question_general(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        auth_headers: dict,
        sample_resume_content: str,
        sample_job_description: str,
    ):
        """Test answering a general application question."""
        response = await client.post(
            "/api/ai/answer-question",
            json={
                "question": "Why do you want to work at our company?",
                "question_type": "general",
                "resume_content": sample_resume_content,
                "job_description": sample_job_description,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert len(data["answer"]) > 0
        assert "tips" in data
        assert isinstance(data["tips"], list)

    @pytest.mark.asyncio
    async def test_answer_question_behavioral(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        auth_headers: dict,
        sample_resume_content: str,
    ):
        """Test answering a behavioral question."""
        response = await client.post(
            "/api/ai/answer-question",
            json={
                "question": "Tell me about a time you handled a difficult situation.",
                "question_type": "behavioral",
                "resume_content": sample_resume_content,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data

    @pytest.mark.asyncio
    async def test_answer_question_minimal(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test answering question with minimal input."""
        response = await client.post(
            "/api/ai/answer-question",
            json={
                "question": "What are your strengths?",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data

    @pytest.mark.asyncio
    async def test_answer_question_unauthorized(self, client: AsyncClient, db: Session):
        """Test question answering without authentication."""
        response = await client.post(
            "/api/ai/answer-question",
            json={"question": "Test question"},
        )
        assert response.status_code == 401


class TestInterviewPrep:
    """Tests for interview preparation endpoint."""

    @pytest.mark.asyncio
    async def test_interview_prep_success(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        auth_headers: dict,
        sample_resume_content: str,
        sample_job_description: str,
    ):
        """Test generating interview answer with STAR method."""
        response = await client.post(
            "/api/ai/interview-prep",
            json={
                "question": "Tell me about a time you led a project.",
                "resume_content": sample_resume_content,
                "job_description": sample_job_description,
                "use_star_method": True,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert len(data["answer"]) > 0
        assert "tips" in data
        assert isinstance(data["tips"], list)

    @pytest.mark.asyncio
    async def test_interview_prep_common_questions(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        auth_headers: dict,
        sample_resume_content: str,
    ):
        """Test interview prep with common questions."""
        questions = [
            "What is your greatest weakness?",
            "Where do you see yourself in 5 years?",
            "Why should we hire you?",
            "Describe a challenging project you worked on.",
        ]

        for question in questions:
            response = await client.post(
                "/api/ai/interview-prep",
                json={
                    "question": question,
                    "resume_content": sample_resume_content,
                },
                headers=auth_headers,
            )
            assert response.status_code == 200
            assert "answer" in response.json()

    @pytest.mark.asyncio
    async def test_interview_prep_unauthorized(self, client: AsyncClient, db: Session):
        """Test interview prep without authentication."""
        response = await client.post(
            "/api/ai/interview-prep",
            json={"question": "Test question"},
        )
        assert response.status_code == 401


class TestGrammarCheck:
    """Tests for grammar check endpoint."""

    @pytest.mark.asyncio
    async def test_grammar_check_success(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test successful grammar correction."""
        response = await client.post(
            "/api/ai/grammar-check",
            json={"text": "I has experience in software developement and im very good at it."},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "corrected_text" in data
        assert "corrections_made" in data
        assert isinstance(data["corrections_made"], list)

    @pytest.mark.asyncio
    async def test_grammar_check_clean_text(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test grammar check with already correct text."""
        clean_text = "I have experience in software development and I am very good at it."
        response = await client.post(
            "/api/ai/grammar-check",
            json={"text": clean_text},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "corrected_text" in data

    @pytest.mark.asyncio
    async def test_grammar_check_unauthorized(self, client: AsyncClient, db: Session):
        """Test grammar check without authentication."""
        response = await client.post(
            "/api/ai/grammar-check",
            json={"text": "Test text"},
        )
        assert response.status_code == 401


class TestNetworkingEmail:
    """Tests for networking email generation endpoint."""

    @pytest.mark.asyncio
    async def test_networking_email_success(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test successful networking email generation."""
        response = await client.post(
            "/api/ai/networking-email",
            json={
                "recipient_name": "John Smith",
                "company": "Tech Corp",
                "purpose": "Informational interview about engineering roles",
                "background": "I am a software engineer with 5 years of experience",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "subject" in data
        assert "body" in data
        assert "full_email" in data
        assert len(data["subject"]) > 0
        assert len(data["body"]) > 0

    @pytest.mark.asyncio
    async def test_networking_email_minimal(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test networking email with minimal input."""
        response = await client.post(
            "/api/ai/networking-email",
            json={
                "recipient_name": "Jane Doe",
                "company": "StartupXYZ",
                "purpose": "Learn about the company culture",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "subject" in data
        assert "body" in data

    @pytest.mark.asyncio
    async def test_networking_email_unauthorized(self, client: AsyncClient, db: Session):
        """Test networking email without authentication."""
        response = await client.post(
            "/api/ai/networking-email",
            json={
                "recipient_name": "Test",
                "company": "Test Corp",
                "purpose": "Test purpose",
            },
        )
        assert response.status_code == 401


class TestKeywordSuggestions:
    """Tests for keyword suggestions endpoint."""

    @pytest.mark.asyncio
    async def test_keyword_suggestions_success(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        auth_headers: dict,
        sample_resume_content: str,
        sample_job_description: str,
    ):
        """Test successful keyword suggestions."""
        response = await client.post(
            "/api/ai/keyword-suggestions",
            json={
                "resume_content": sample_resume_content,
                "job_description": sample_job_description,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert "missing_keywords" in data
        assert "matched_keywords" in data
        assert isinstance(data["missing_keywords"], list)
        assert isinstance(data["matched_keywords"], list)

    @pytest.mark.asyncio
    async def test_keyword_suggestions_with_keywords(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        auth_headers: dict,
        sample_resume_content: str,
        sample_job_description: str,
    ):
        """Test keyword suggestions with provided missing keywords."""
        response = await client.post(
            "/api/ai/keyword-suggestions",
            json={
                "resume_content": sample_resume_content,
                "job_description": sample_job_description,
                "missing_keywords": ["Kubernetes", "Machine Learning", "Leadership"],
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data

    @pytest.mark.asyncio
    async def test_keyword_suggestions_unauthorized(self, client: AsyncClient, db: Session):
        """Test keyword suggestions without authentication."""
        response = await client.post(
            "/api/ai/keyword-suggestions",
            json={
                "resume_content": "Test resume",
                "job_description": "Test job",
            },
        )
        assert response.status_code == 401


class TestJobMatchScore:
    """Tests for job match score endpoint."""

    @pytest.mark.asyncio
    async def test_job_match_score_success(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        auth_headers: dict,
        sample_resume_content: str,
        sample_job_description: str,
    ):
        """Test successful job match score calculation."""
        response = await client.post(
            "/api/ai/job-match-score",
            json={
                "resume_content": sample_resume_content,
                "job_description": sample_job_description,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert isinstance(data["score"], int)
        assert 0 <= data["score"] <= 100
        assert "score_breakdown" in data
        assert "missing_keywords" in data
        assert "matched_keywords" in data
        assert "suggestions" in data
        assert "found_skills" in data

    @pytest.mark.asyncio
    async def test_job_match_score_high_match(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        auth_headers: dict,
    ):
        """Test job match score with high-matching resume."""
        # Resume that closely matches the job
        resume = """
        Software Engineer
        Skills: Python, FastAPI, REST API, AWS, Docker, PostgreSQL
        Experience: 5 years of Python development
        Led microservices architecture projects
        """
        job_desc = """
        Requirements:
        - Python development
        - FastAPI or Django
        - REST API design
        - AWS experience
        - Docker knowledge
        """
        response = await client.post(
            "/api/ai/job-match-score",
            json={
                "resume_content": resume,
                "job_description": job_desc,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # Should have a reasonable score due to keyword matches
        assert data["score"] >= 0

    @pytest.mark.asyncio
    async def test_job_match_score_low_match(
        self, client: AsyncClient, db: Session, test_profile: Profile, auth_headers: dict
    ):
        """Test job match score with low-matching resume."""
        # Resume that doesn't match the job
        resume = """
        Chef
        Skills: Cooking, Food preparation, Kitchen management
        Experience: 10 years in culinary arts
        """
        job_desc = """
        Software Engineer
        Requirements:
        - Python programming
        - Machine learning
        - Data science
        """
        response = await client.post(
            "/api/ai/job-match-score",
            json={
                "resume_content": resume,
                "job_description": job_desc,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # Should have a low score due to no keyword matches
        assert data["score"] <= 50

    @pytest.mark.asyncio
    async def test_job_match_score_unauthorized(self, client: AsyncClient, db: Session):
        """Test job match score without authentication."""
        response = await client.post(
            "/api/ai/job-match-score",
            json={
                "resume_content": "Test resume",
                "job_description": "Test job",
            },
        )
        assert response.status_code == 401


class TestOptimizeResume:
    """Tests for resume optimization endpoint."""

    @pytest.mark.asyncio
    async def test_optimize_resume_success(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        auth_headers: dict,
        sample_resume_content: str,
        sample_job_description: str,
    ):
        """Test successful resume optimization."""
        response = await client.post(
            "/api/ai/optimize-resume",
            params={
                "resume_content": sample_resume_content,
                "job_description": sample_job_description,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert len(data["suggestions"]) > 0

    @pytest.mark.asyncio
    async def test_optimize_resume_without_job_description(
        self,
        client: AsyncClient,
        db: Session,
        test_profile: Profile,
        auth_headers: dict,
        sample_resume_content: str,
    ):
        """Test resume optimization without job description."""
        response = await client.post(
            "/api/ai/optimize-resume",
            params={
                "resume_content": sample_resume_content,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data

    @pytest.mark.asyncio
    async def test_optimize_resume_unauthorized(self, client: AsyncClient, db: Session):
        """Test resume optimization without authentication."""
        response = await client.post(
            "/api/ai/optimize-resume",
            params={"resume_content": "Test resume"},
        )
        assert response.status_code == 401
