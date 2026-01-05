from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel

class SimpleTodo(BaseModel):
    __tablename__ = "simple_todos"
    
    user_id = Column(String, ForeignKey("users.uid"), nullable=False, index=True)
    text = Column(String, nullable=False)
    done = Column(Boolean, default=False)
    
    # Relationship
    user = relationship("User", backref="simple_todos")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "text": self.text,
            "done": self.done,
        }

