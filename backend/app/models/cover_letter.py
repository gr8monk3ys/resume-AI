"""
Cover letter model for storing generated cover letters.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from app.database import Base


class CoverLetter(Base):
    """Generated cover letters."""

    __tablename__ = "cover_letters"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    job_application_id = Column(
        Integer, ForeignKey("job_applications.id", ondelete="SET NULL"), nullable=True
    )
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    profile = relationship("Profile", back_populates="cover_letters")
    job_application = relationship("JobApplication", back_populates="cover_letters")
