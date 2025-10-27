from sqlalchemy import Column, String, Text, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum
from .base import BaseModel

class DocumentType(str, enum.Enum):
    PDF = "pdf"
    PPT = "ppt"
    SYLLABUS = "syllabus"
    PYQS = "pyqs"

class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"

class Document(BaseModel):
    __tablename__ = "documents"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Changed to Integer
    file_name = Column(String, nullable=False)
    file_url = Column(String, nullable=False)
    file_type = Column(Enum(DocumentType), nullable=False)
    processed_content = Column(Text)
    extracted_text = Column(Text)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.UPLOADED)
    
    # Relationships
    user = relationship("User", back_populates="documents")
    questions = relationship("Question", back_populates="source_document")