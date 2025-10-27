from sqlalchemy import Column, String, Text, Integer, ForeignKey, Enum, ARRAY
from sqlalchemy.orm import relationship
import enum
from .base import BaseModel  # Relative import

class QuestionType(str, enum.Enum):
    MCQ = "mcq"
    SHORT = "short"
    LONG = "long"
    ESSAY = "essay"

class DifficultyLevel(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class Question(BaseModel):
    __tablename__ = "questions"
    
    question_paper_id = Column(Integer, ForeignKey("questionpapers.id"))
    source_document_id = Column(Integer, ForeignKey("documents.id"))
    question_text = Column(Text, nullable=False)
    question_type = Column(Enum(QuestionType), nullable=False)
    options = Column(ARRAY(String))
    correct_answer = Column(Text, nullable=False)
    marks = Column(Integer, nullable=False)
    difficulty = Column(Enum(DifficultyLevel), nullable=False)
    generated_by = Column(String)
    
    # Relationships
    question_paper = relationship("QuestionPaper", back_populates="questions")
    source_document = relationship("Document", back_populates="questions")