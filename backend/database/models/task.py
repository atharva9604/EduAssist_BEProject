from sqlalchemy import Column, String, Date, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel

class Task(BaseModel):
    __tablename__ = "tasks"

    user_id = Column(String, ForeignKey("users.uid"), nullable=False, index=True)
    title = Column(String, nullable=False)
    due_date = Column(Date, nullable=False, index=True)
    done = Column(Boolean, default=False)

    # Relationship
    user = relationship("User", backref="tasks")

    def to_dict(self):
        return {
            "id": str(self.id),
            "title": self.title,
            "due_date": self.due_date.isoformat(),
            "done": self.done,
        }
