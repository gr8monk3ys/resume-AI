"""
STAR story model for tracking behavioral interview stories.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class StarStory(Base):
    """STAR story for behavioral interview preparation."""

    __tablename__ = "star_stories"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    title = Column(String, nullable=False)
    situation = Column(Text, nullable=True)
    task = Column(Text, nullable=True)
    action = Column(Text, nullable=True)
    result = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)  # JSON array
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    profile = relationship("Profile", back_populates="star_stories")
