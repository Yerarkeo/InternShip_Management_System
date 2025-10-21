from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
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
    hashed_password = Column(String(255), nullable=False)  # Make sure this column exists
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    phone = Column(String(20))
    department = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

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

class InternshipApplication(Base):
    __tablename__ = "internship_applications"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    internship_id = Column(Integer, ForeignKey("internships.id"), nullable=False)
    application_date = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(50), default="pending")
    cover_letter = Column(Text)
    resume_url = Column(String(500))

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    internship_id = Column(Integer, ForeignKey("internships.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_by = Column(Integer, ForeignKey("users.id"))
    due_date = Column(DateTime(timezone=True))
    status = Column(String(50), default="pending")
    progress = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    mentor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    internship_id = Column(Integer, ForeignKey("internships.id"), nullable=False)
    rating = Column(Integer)
    comments = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())