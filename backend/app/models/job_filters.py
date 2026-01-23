"""
Job filtering models for company filters, keyword filters, and application questions.
"""

from datetime import datetime
from enum import Enum

from app.database import Base
from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship


class CompanyFilterType(str, Enum):
    """Company filter type."""

    BLACKLIST = "blacklist"
    WHITELIST = "whitelist"


class KeywordFilterType(str, Enum):
    """Keyword filter type."""

    EXCLUDE = "exclude"
    REQUIRE = "require"


class KeywordAppliesTo(str, Enum):
    """Where keyword filter applies."""

    TITLE = "title"
    DESCRIPTION = "description"
    BOTH = "both"


class QuestionType(str, Enum):
    """Application question type."""

    TEXT = "text"
    NUMBER = "number"
    SELECT = "select"
    BOOLEAN = "boolean"


class CompanyFilter(Base):
    """Company filter for blacklisting or whitelisting companies."""

    __tablename__ = "company_filters"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_name = Column(String(255), nullable=False, index=True)
    filter_type = Column(
        SQLEnum(CompanyFilterType), nullable=False, default=CompanyFilterType.BLACKLIST
    )
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    user = relationship("User", backref="company_filters")


class KeywordFilter(Base):
    """Keyword filter for excluding or requiring keywords in job listings."""

    __tablename__ = "keyword_filters"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    keyword = Column(String(255), nullable=False, index=True)
    filter_type = Column(
        SQLEnum(KeywordFilterType), nullable=False, default=KeywordFilterType.EXCLUDE
    )
    applies_to = Column(SQLEnum(KeywordAppliesTo), nullable=False, default=KeywordAppliesTo.BOTH)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    user = relationship("User", backref="keyword_filters")


class ApplicationQuestion(Base):
    """Template for common application questions with pre-filled answers."""

    __tablename__ = "application_questions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_pattern = Column(String(500), nullable=False, index=True)
    answer = Column(Text, nullable=False)
    question_type = Column(SQLEnum(QuestionType), nullable=False, default=QuestionType.TEXT)
    category = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = relationship("User", backref="application_questions")


# Default question templates
DEFAULT_QUESTION_TEMPLATES = [
    {
        "question_pattern": "years of experience",
        "answer": "",
        "question_type": QuestionType.NUMBER,
        "category": "experience",
    },
    {
        "question_pattern": "salary expectations|expected salary|desired salary|compensation expectations",
        "answer": "",
        "question_type": QuestionType.TEXT,
        "category": "compensation",
    },
    {
        "question_pattern": "notice period|how soon can you start|availability",
        "answer": "2 weeks",
        "question_type": QuestionType.TEXT,
        "category": "availability",
    },
    {
        "question_pattern": "work authorization|authorized to work|legally authorized|eligible to work",
        "answer": "Yes",
        "question_type": QuestionType.BOOLEAN,
        "category": "legal",
    },
    {
        "question_pattern": "willing to relocate|open to relocation|relocation",
        "answer": "Yes",
        "question_type": QuestionType.BOOLEAN,
        "category": "relocation",
    },
    {
        "question_pattern": "sponsorship|visa sponsorship|require sponsorship|need sponsorship",
        "answer": "No",
        "question_type": QuestionType.BOOLEAN,
        "category": "legal",
    },
    {
        "question_pattern": "remote work|work remotely|hybrid|on-site|work from home",
        "answer": "Open to all options",
        "question_type": QuestionType.SELECT,
        "category": "work_arrangement",
    },
    {
        "question_pattern": "start date|when can you start|earliest start date",
        "answer": "",
        "question_type": QuestionType.TEXT,
        "category": "availability",
    },
    {
        "question_pattern": "highest level of education|education level|degree",
        "answer": "",
        "question_type": QuestionType.SELECT,
        "category": "education",
    },
    {
        "question_pattern": "linkedin|linkedin profile|linkedin url",
        "answer": "",
        "question_type": QuestionType.TEXT,
        "category": "social",
    },
    {
        "question_pattern": "github|github profile|portfolio|personal website",
        "answer": "",
        "question_type": QuestionType.TEXT,
        "category": "social",
    },
    {
        "question_pattern": "phone number|contact number|mobile number",
        "answer": "",
        "question_type": QuestionType.TEXT,
        "category": "contact",
    },
    {
        "question_pattern": "cover letter|why.*interested|why.*company|why.*position",
        "answer": "",
        "question_type": QuestionType.TEXT,
        "category": "motivation",
    },
    {
        "question_pattern": "disability|veteran|gender|race|ethnicity",
        "answer": "Prefer not to answer",
        "question_type": QuestionType.SELECT,
        "category": "demographic",
    },
]
