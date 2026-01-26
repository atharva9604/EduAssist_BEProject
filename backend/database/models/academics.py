from sqlalchemy import Column, String, ForeignKey, Integer, Date, Text
from sqlalchemy.orm import relationship
from datetime import date
from .base import BaseModel

class ContinuousAssessment(BaseModel):
    __tablename__ = "continuous_assessments"

    user_id = Column(String, ForeignKey("users.uid"),nullable=False,index=True)
    subject_name = Column(String,nullable=False)
    assessment_type =  Column(String, nullable=False)
    marks=Column(Integer,nullable=False)
    total_marks=Column(Integer,nullable=False)
    assessment_date= Column(Date,nullable=True)

    user = relationship("User", backref="continuous_assessments")

    def to_dict(self):
        return{
            "id":str(self.id),
            "subject_name": str(self.subject_name),
            "assessment_type":str(self.assessment_type),
            "marks":self.marks,
            "total_marks":self.total_marks,
            "assessment_date":self.assessment_date.isoformat() if self.assessment_date else None,
        }


class LabManual(BaseModel):
    __tablename__ = "lab_manuals"
    
    user_id = Column(String, ForeignKey("users.uid"), nullable=False, index=True)
    subject = Column(String, nullable=False)
    course_code = Column(String, nullable=True)
    prerequisites = Column(Text, nullable=True)
    lab_objectives = Column(Text, nullable=True)  # JSON string
    lab_outcomes = Column(Text, nullable=True)   # JSON string
    manual_content = Column(Text, nullable=False)  # JSON string of the full manual structure
    created_at = Column(Date, nullable=False, default=date.today)
    
    user = relationship("User", backref="lab_manuals")
    
    def to_dict(self):
        import json
        return {
            "id": str(self.id),
            "subject": self.subject,
            "course_code": self.course_code,
            "prerequisites": self.prerequisites,
            "lab_objectives": json.loads(self.lab_objectives) if self.lab_objectives else [],
            "lab_outcomes": json.loads(self.lab_outcomes) if self.lab_outcomes else [],
            "manual_content": json.loads(self.manual_content) if self.manual_content else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

