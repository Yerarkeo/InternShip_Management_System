from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
import re

class UserRole(str, Enum):
    STUDENT = "student"
    ADMIN = "admin"
    MENTOR = "mentor"

class ApplicationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

# User Schemas
class UserBase(BaseModel):
    email: str
    full_name: str
    role: UserRole
    phone: Optional[str] = None
    department: Optional[str] = None

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: str
    password: str

# Internship Schemas
class InternshipBase(BaseModel):
    title: str
    description: Optional[str] = None
    company: str
    location: Optional[str] = None
    duration: Optional[str] = None
    stipend: Optional[str] = None
    requirements: Optional[str] = None
    deadline: Optional[datetime] = None

class InternshipCreate(InternshipBase):
    pass

class Internship(InternshipBase):
    id: int
    created_by: int
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True

# Application Schemas
class ApplicationBase(BaseModel):
    cover_letter: Optional[str] = None
    resume_url: Optional[str] = None

class ApplicationCreate(ApplicationBase):
    internship_id: int

class Application(ApplicationBase):
    id: int
    student_id: int
    internship_id: int
    application_date: datetime
    status: ApplicationStatus

    class Config:
        from_attributes = True

# Task Schemas
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None

class TaskCreate(TaskBase):
    internship_id: int
    student_id: int

class Task(TaskBase):
    id: int
    internship_id: int
    student_id: int
    assigned_by: Optional[int] = None
    status: TaskStatus
    progress: int
    created_at: datetime

    class Config:
        from_attributes = True

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# Add this to your existing schemas.py

class UserProfile(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    phone: Optional[str] = None
    department: Optional[str] = None
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None


class UserProfile(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    phone: Optional[str] = None
    department: Optional[str] = None
    profile_picture: Optional[str] = "default_avatar.png"  # NEW
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    profile_picture: Optional[str] = None  # NEW

class ProfilePictureUpdate(BaseModel):  # NEW: Separate schema for picture update
    profile_picture: str