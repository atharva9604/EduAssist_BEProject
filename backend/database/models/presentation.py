from sqlalchemy import Column, String, Text, Integer, ForeignKey, Enum, DateTime, Boolean
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from .base import BaseModel

class PresentationStatus(str, enum.Enum):
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"

class PresentationType(str, enum.Enum):
    TOPIC_BASED = "topic_based"
    SYLLABUS_BASED = "syllabus_based"
    CUSTOM = "custom"

class Presentation(BaseModel):
    __tablename__ = "presentations"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    subtitle = Column(String)
    topic = Column(String, nullable=False)
    description = Column(Text)
    presentation_type = Column(Enum(PresentationType), default=PresentationType.TOPIC_BASED)
    
    # File information
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_url = Column(String)  # For download links
    file_size = Column(Integer)  # File size in bytes
    
    # Content information
    num_slides = Column(Integer, default=0)
    content_data = Column(Text)  # JSON string of slide content
    
    # Status and metadata
    status = Column(Enum(PresentationStatus), default=PresentationStatus.GENERATING)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="presentations")
    
    def to_dict(self):
        """Convert presentation to dictionary for API responses"""
        return {
            "id": self.id,
            "title": self.title,
            "subtitle": self.subtitle,
            "topic": self.topic,
            "description": self.description,
            "presentation_type": self.presentation_type.value,
            "filename": self.filename,
            "file_url": self.file_url,
            "file_size": self.file_size,
            "num_slides": self.num_slides,
            "status": self.status.value,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

