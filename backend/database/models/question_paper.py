from sqlalchemy import Column, String, Text, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum
from .base import BaseModel
from .question import DifficultyLevel

class QuestionPaperStatus(str, enum.Enum):
    GENERATING = "generating"
    COMPLETED = "completed"
    REVIEWED = "reviewed"

class QuestionPaper(BaseModel):
    __tablename__ = "questionpapers"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Changed to Integer
    title = Column(String, nullable=False)
    description = Column(Text)
    subject = Column(String, nullable=False)
    difficulty = Column(Enum(DifficultyLevel), nullable=False)
    total_marks = Column(Integer, nullable=False)
    duration = Column(Integer)
    status = Column(Enum(QuestionPaperStatus), default=QuestionPaperStatus.GENERATING)
    
    # Relationships
    user = relationship("User", back_populates="question_papers")
    questions = relationship("Question", back_populates="question_paper")