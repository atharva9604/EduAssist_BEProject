from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel

class CalendarEvent(BaseModel):
    __tablename__ = "calendar_events"

    user_id = Column(String, ForeignKey("users.uid"), nullable=False, index=True)
    title = Column(String, nullable=False)
    start = Column(DateTime, nullable=False, index=True)
    end = Column(DateTime, nullable=False)
    location = Column(String, nullable=True)
    description = Column(String, nullable=True)
    all_day = Column(Boolean, default=False)

    # Relationship
    user = relationship("User", backref="calendar_events")

    def to_dict(self):
        return {
            "id": str(self.id),
            "title": self.title,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "location": self.location,
            "description": self.description,
            "allDay": self.all_day  # Match API format
        }
