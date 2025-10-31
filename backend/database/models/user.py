from sqlalchemy import Column, String, ARRAY
from sqlalchemy.orm import relationship
from .base import BaseModel

class User(BaseModel):
    __tablename__ = "users"
    
    uid = Column(String, unique=True, nullable=False)  # Firebase UID
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    photo_url = Column(String)
    role = Column(String, default="teacher")
    department_id = Column(String)
    subjects = Column(ARRAY(String))  # Array of subject names
    
    # Relationships
    documents = relationship("Document", back_populates="user")
    question_papers = relationship("QuestionPaper", back_populates="user")
    presentations = relationship("Presentation", back_populates="user")