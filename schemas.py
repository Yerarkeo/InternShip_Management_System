from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

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

    @field_validator('email')
    def validate_email(cls, v):
        if not v or '@' not in v:
            raise ValueError('Invalid email format')
        return v

class UserCreate(UserBase):
    password: str

    @field_validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v

    @field_validator('role')
    def validate_role(cls, v):
        valid_roles = ['student', 'admin', 'mentor']
        if v not in valid_roles:
            raise ValueError(f'Role must be one of: {", ".join(valid_roles)}')
        return v

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

# User Profile Schemas
class UserProfile(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    phone: Optional[str] = None
    department: Optional[str] = None
    profile_picture: Optional[str] = "default_avatar.png"
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    profile_picture: Optional[str] = None

class ProfilePictureUpdate(BaseModel):
    profile_picture: str

# Admin Management Schemas
class UserUpdateAdmin(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None
    
    class Config:
        from_attributes = True

class UserList(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    phone: Optional[str] = None
    department: Optional[str] = None
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class SystemStats(BaseModel):
    total_users: int
    total_students: int
    total_admins: int
    total_mentors: int
    total_internships: int
    total_applications: int
    total_tasks: int

# Add these additional schemas for better functionality
class ApplicationWithInternship(Application):
    internship: Internship

    class Config:
        from_attributes = True

class InternshipWithApplications(Internship):
    applications: List[Application] = []

    class Config:
        from_attributes = True

class UserWithApplications(User):
    applications: List[Application] = []

    class Config:
        from_attributes = True

# Response schemas for API endpoints
class MessageResponse(BaseModel):
    message: str

class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus

class InternshipUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    duration: Optional[str] = None
    stipend: Optional[str] = None
    requirements: Optional[str] = None
    deadline: Optional[datetime] = None
    is_active: Optional[bool] = None

# Feedback Schemas
class FeedbackBase(BaseModel):
    student_id: int
    mentor_id: int
    internship_id: int
    rating: int
    comments: Optional[str] = None

class FeedbackCreate(FeedbackBase):
    pass

class FeedbackUpdate(BaseModel):
    rating: Optional[int] = None
    comments: Optional[str] = None

class Feedback(FeedbackBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Report Schemas
class ReportRequest(BaseModel):
    report_type: str  # 'internship', 'student', 'system'
    target_id: Optional[int] = None
    format: str = 'pdf'  # 'pdf', 'excel'

# Task Update Schemas
class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    progress: Optional[int] = None
    due_date: Optional[datetime] = None

# Success Response Schema
class SuccessResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

# Error Response Schema
class ErrorResponse(BaseModel):
    success: bool
    error: str