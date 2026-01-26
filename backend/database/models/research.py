from sqlalchemy import Column, String, ForeignKey, Date, Text, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel

class FDP(BaseModel):
    __tablename__ = "fdps"
    
    user_id = Column(String, ForeignKey("users.uid"), nullable=False, index=True)
    title = Column(String, nullable=False)
    organization = Column(String, nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    certificate_path = Column(String, nullable=True)  # Optional: path to certificate
    
    user = relationship("User", backref="fdps")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "title": self.title,
            "organization": self.organization,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "certificate_path": self.certificate_path,
        }

class Lecture(BaseModel):
    __tablename__ = "lectures"
    
    user_id = Column(String, ForeignKey("users.uid"), nullable=False, index=True)
    title = Column(String, nullable=False)
    venue = Column(String, nullable=True)
    date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)
    
    user = relationship("User", backref="lectures")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "title": self.title,
            "venue": self.venue,
            "date": self.date.isoformat() if self.date else None,
            "description": self.description,
        }

class Certification(BaseModel):
    __tablename__ = "certifications"
    
    user_id = Column(String, ForeignKey("users.uid"), nullable=False, index=True)
    name = Column(String, nullable=False)
    issuing_organization = Column(String, nullable=False)
    issue_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    certificate_path = Column(String, nullable=True)
    
    user = relationship("User", backref="certifications")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "issuing_organization": self.issuing_organization,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "certificate_path": self.certificate_path,
        }

class CurrentProject(BaseModel):
    __tablename__ = "current_projects"
    
    user_id = Column(String, ForeignKey("users.uid"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=True)
    status = Column(String, default="ongoing")  # ongoing, completed, on-hold
    
    user = relationship("User", backref="current_projects")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "status": self.status,
        }

class ResearchProposal(BaseModel):
    __tablename__ = "research_proposals"
    
    user_id = Column(String, ForeignKey("users.uid"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    submission_date = Column(Date, nullable=True)
    status = Column(String, default="draft")  # draft, submitted, approved, rejected
    proposal_file_path = Column(String, nullable=True)
    
    user = relationship("User", backref="research_proposals")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "submission_date": self.submission_date.isoformat() if self.submission_date else None,
            "status": self.status,
            "proposal_file_path": self.proposal_file_path,
        }