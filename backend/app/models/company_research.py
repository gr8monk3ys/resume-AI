"""
Company research model for tracking interview preparation notes.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class CompanyResearch(Base):
    """Company research for interview preparation."""

    __tablename__ = "company_research"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    company_name = Column(String, nullable=False)
    talking_points = Column(Text, nullable=True)  # JSON array of strings
    notes = Column(Text, nullable=True)
    checklist = Column(Text, nullable=True)  # JSON array of {text, done}
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    profile = relationship("Profile", back_populates="company_research")
