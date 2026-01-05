from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel

class Subject(BaseModel):
    __tablename__ = "subjects"
    
    user_id = Column(String, ForeignKey("users.uid"), nullable=False, index=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=True)  # Optional subject code
    
    # Relationship
    user = relationship("User", backref="subject_list")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "code": self.code,
        }

