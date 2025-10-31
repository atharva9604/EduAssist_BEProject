from sqlalchemy import Column, String, Text, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum
from .base import BaseModel  # Relative import

class AgentType(str, enum.Enum):
    DOCUMENT_PROCESSOR = "document_processor"
    CONTENT_ANALYZER = "content_analyzer"
    QUESTION_GENERATOR = "question_generator"
    QUALITY_VALIDATOR = "quality_validator"
    PPT_GENERATOR = "ppt_generator"

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class AgentTask(BaseModel):
    __tablename__ = "agent_tasks"
    
    question_paper_id = Column(Integer, ForeignKey("questionpapers.id"))
    agent_type = Column(Enum(AgentType), nullable=False)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    input_data = Column(Text)
    output_data = Column(Text)
    error_message = Column(Text)
    
    # Relationships
    question_paper = relationship("QuestionPaper")