"""
Resume model for storing resume versions.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Resume(Base):
    """Resume storage with versioning."""

    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    version_name = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    ats_score = Column(Integer, nullable=True)
    keywords = Column(Text, nullable=True)  # JSON string of extracted keywords
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    profile = relationship("Profile", back_populates="resumes")
