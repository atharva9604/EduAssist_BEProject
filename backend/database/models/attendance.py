from sqlalchemy import Column, Integer, String, ForeignKey, Date
from sqlalchemy.orm import relationship
from .base import BaseModel


class Teacher(BaseModel):
    """Teacher information - can be linked to User or standalone"""
    __tablename__ = "attendance_teachers"
    
    user_id = Column(String, ForeignKey("users.uid"), nullable=True, index=True)  # Optional link to User
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=True)
    
    # Relationships
    classes = relationship("AttendanceClass", back_populates="teacher")
    sessions = relationship("AttendanceSession", back_populates="teacher")


class DepartmentSemester(BaseModel):
    """Department and semester information"""
    __tablename__ = "attendance_dept_semesters"
    
    department = Column(String, nullable=False)  # e.g., "AI-DS"
    semester = Column(Integer, nullable=False)  # e.g., 5
    
    # Relationships
    subjects = relationship("AttendanceSubject", back_populates="dept_semester")
    classes = relationship("AttendanceClass", back_populates="dept_semester")


class AttendanceClass(BaseModel):
    """Class divisions (A, B, C, etc.)"""
    __tablename__ = "attendance_classes"
    
    division = Column(String, nullable=False)  # e.g., A, B, C
    teacher_id = Column(Integer, ForeignKey("attendance_teachers.id"), nullable=False)
    dept_sem_id = Column(Integer, ForeignKey("attendance_dept_semesters.id"), nullable=False)
    
    # Relationships
    teacher = relationship("Teacher", back_populates="classes")
    dept_semester = relationship("DepartmentSemester", back_populates="classes")
    students = relationship("AttendanceStudent", back_populates="class_", cascade="all, delete-orphan")
    sessions = relationship("AttendanceSession", back_populates="class_", cascade="all, delete-orphan")


class AttendanceSubject(BaseModel):
    """Course subjects for attendance tracking"""
    __tablename__ = "attendance_subjects"
    
    name = Column(String, nullable=False)
    dept_sem_id = Column(Integer, ForeignKey("attendance_dept_semesters.id"), nullable=False)
    
    # Relationships
    dept_semester = relationship("DepartmentSemester", back_populates="subjects")
    sessions = relationship("AttendanceSession", back_populates="subject")


class AttendanceStudent(BaseModel):
    """Student roster per class"""
    __tablename__ = "attendance_students"
    
    roll_no = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    class_id = Column(Integer, ForeignKey("attendance_classes.id"), nullable=False)
    
    # Relationships
    class_ = relationship("AttendanceClass", back_populates="students")
    attendance_records = relationship("AttendanceRecord", back_populates="student", cascade="all, delete-orphan")


class AttendanceSession(BaseModel):
    """Class sessions (teacher + class + subject + date)"""
    __tablename__ = "attendance_sessions"
    
    date = Column(Date, nullable=False)
    subject_id = Column(Integer, ForeignKey("attendance_subjects.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("attendance_teachers.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("attendance_classes.id"), nullable=False)
    
    # Relationships
    class_ = relationship("AttendanceClass", back_populates="sessions")
    subject = relationship("AttendanceSubject", back_populates="sessions")
    teacher = relationship("Teacher", back_populates="sessions")
    attendance = relationship("AttendanceRecord", back_populates="session", cascade="all, delete-orphan")


class AttendanceRecord(BaseModel):
    """Attendance records per session"""
    __tablename__ = "attendance_records"
    
    session_id = Column(Integer, ForeignKey("attendance_sessions.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("attendance_students.id"), nullable=False)
    status = Column(String, nullable=False)  # Present / Absent / Late
    
    # Relationships
    session = relationship("AttendanceSession", back_populates="attendance")
    student = relationship("AttendanceStudent", back_populates="attendance_records")
