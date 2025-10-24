from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
import enum

class UserRole(str, enum.Enum):
    STUDENT = "student"
    ADMIN = "admin" 
    MENTOR = "mentor"

class ApplicationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.STUDENT)
    phone = Column(String(20))
    department = Column(String(255))
    profile_picture = Column(String(500), default="default_avatar.png")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    created_internships = relationship("Internship", back_populates="creator")
    applications = relationship("InternshipApplication", back_populates="student")
    assigned_tasks = relationship("Task", foreign_keys="Task.student_id", back_populates="student")
    assigned_by_tasks = relationship("Task", foreign_keys="Task.assigned_by", back_populates="assigner")
    student_feedback = relationship("Feedback", foreign_keys="Feedback.student_id", back_populates="student")
    mentor_feedback = relationship("Feedback", foreign_keys="Feedback.mentor_id", back_populates="mentor")

class Internship(Base):
    __tablename__ = "internships"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    company = Column(String(255), nullable=False)
    location = Column(String(255))
    duration = Column(String(100))
    stipend = Column(String(100))
    requirements = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    deadline = Column(DateTime(timezone=True))

    # Relationships
    creator = relationship("User", back_populates="created_internships")
    applications = relationship("InternshipApplication", back_populates="internship")
    tasks = relationship("Task", back_populates="internship")
    feedback = relationship("Feedback", back_populates="internship")

class InternshipApplication(Base):
    __tablename__ = "internship_applications"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    internship_id = Column(Integer, ForeignKey("internships.id"), nullable=False)
    application_date = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.PENDING)
    cover_letter = Column(Text)
    resume_url = Column(String(500))

    # Relationships
    student = relationship("User", back_populates="applications")
    internship = relationship("Internship", back_populates="applications")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    internship_id = Column(Integer, ForeignKey("internships.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_by = Column(Integer, ForeignKey("users.id"))
    due_date = Column(DateTime(timezone=True))
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    progress = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    internship = relationship("Internship", back_populates="tasks")
    student = relationship("User", foreign_keys=[student_id], back_populates="assigned_tasks")
    assigner = relationship("User", foreign_keys=[assigned_by], back_populates="assigned_by_tasks")

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    mentor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    internship_id = Column(Integer, ForeignKey("internships.id"), nullable=False)
    rating = Column(Integer)
    comments = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    student = relationship("User", foreign_keys=[student_id], back_populates="student_feedback")
    mentor = relationship("User", foreign_keys=[mentor_id], back_populates="mentor_feedback")
    internship = relationship("Internship", back_populates="feedback")