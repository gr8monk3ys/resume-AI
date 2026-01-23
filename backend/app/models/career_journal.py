"""
Career journal model for tracking achievements.
"""

from datetime import date, datetime

from app.database import Base
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship


class CareerJournalEntry(Base):
    """Career journal for tracking achievements and milestones."""

    __tablename__ = "career_journal"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    achievement_date = Column(Date, nullable=True)
    tags = Column(Text, nullable=True)  # JSON string or comma-separated
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    profile = relationship("Profile", back_populates="journal_entries")
