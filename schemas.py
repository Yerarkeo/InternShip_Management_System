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
    CANCELLED = "cancelled"

# Enhanced Feedback & Evaluation Enums
class FeedbackStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"

class EvaluationStatus(str, Enum):
    DRAFT = "draft"
    FINAL = "final"

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

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    progress: Optional[int] = None
    due_date: Optional[datetime] = None

    @field_validator('status')
    def validate_status(cls, v):
        if v is not None:
            valid_statuses = ['pending', 'in_progress', 'completed', 'cancelled']
            if v not in valid_statuses:
                raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v

    @field_validator('progress')
    def validate_progress(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Progress must be between 0 and 100')
        return v

class TaskStatusUpdate(BaseModel):
    status: TaskStatus

class TaskProgressUpdate(BaseModel):
    progress: int

    @field_validator('progress')
    def validate_progress(cls, v):
        if v < 0 or v > 100:
            raise ValueError('Progress must be between 0 and 100')
        return v

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

# Task Statistics Schema
class TaskStats(BaseModel):
    total_tasks: int
    pending_tasks: int
    in_progress_tasks: int
    completed_tasks: int
    cancelled_tasks: int

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

class TaskWithDetails(Task):
    student: Optional[User] = None
    internship: Optional[Internship] = None
    assigner: Optional[User] = None

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

# Success Response Schema
class SuccessResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

# Error Response Schema
class ErrorResponse(BaseModel):
    success: bool
    error: str

# Bulk Operations
class BulkTaskUpdate(BaseModel):
    task_ids: List[int]
    status: Optional[TaskStatus] = None
    progress: Optional[int] = None

# Search and Filter Schemas
class TaskFilter(BaseModel):
    status: Optional[TaskStatus] = None
    internship_id: Optional[int] = None
    student_id: Optional[int] = None
    assigned_by: Optional[int] = None

class TaskSearch(BaseModel):
    query: str
    status_filter: Optional[TaskStatus] = None

# Dashboard Stats
class DashboardStats(BaseModel):
    system_stats: SystemStats
    task_stats: TaskStats
    application_stats: dict

    class Config:
        from_attributes = True

# ==============================
# ENHANCED FEEDBACK & EVALUATION SCHEMAS
# ==============================

# Enhanced Mentor Feedback Schemas
class MentorFeedbackBase(BaseModel):
    technical_skills: Optional[str] = None
    communication_skills: Optional[str] = None
    teamwork: Optional[str] = None
    problem_solving: Optional[str] = None
    overall_feedback: str
    technical_rating: Optional[int] = None
    communication_rating: Optional[int] = None
    teamwork_rating: Optional[int] = None
    problem_solving_rating: Optional[int] = None

    @field_validator('technical_rating', 'communication_rating', 'teamwork_rating', 'problem_solving_rating')
    def validate_ratings(cls, v):
        if v is not None and (v < 1 or v > 5):
            raise ValueError('Ratings must be between 1 and 5')
        return v

class MentorFeedbackCreate(MentorFeedbackBase):
    application_id: int
    student_id: int
    internship_id: int

class MentorFeedbackUpdate(BaseModel):
    technical_skills: Optional[str] = None
    communication_skills: Optional[str] = None
    teamwork: Optional[str] = None
    problem_solving: Optional[str] = None
    overall_feedback: Optional[str] = None
    technical_rating: Optional[int] = None
    communication_rating: Optional[int] = None
    teamwork_rating: Optional[int] = None
    problem_solving_rating: Optional[int] = None
    status: Optional[FeedbackStatus] = None

class MentorFeedback(MentorFeedbackBase):
    id: int
    application_id: int
    mentor_id: int
    student_id: int
    internship_id: int
    overall_rating: Optional[float]
    feedback_date: datetime
    status: FeedbackStatus

    class Config:
        from_attributes = True

# Evaluation Schemas
class EvaluationBase(BaseModel):
    technical_competence: int
    task_completion: int
    communication_skills: int
    professionalism: int
    initiative: int
    strengths: Optional[str] = None
    areas_for_improvement: Optional[str] = None
    final_comments: str

    @field_validator('technical_competence', 'task_completion', 'communication_skills', 'professionalism', 'initiative')
    def validate_scores(cls, v):
        if v < 1 or v > 10:
            raise ValueError('Scores must be between 1 and 10')
        return v

class EvaluationCreate(EvaluationBase):
    application_id: int
    student_id: int
    internship_id: int

class EvaluationUpdate(BaseModel):
    technical_competence: Optional[int] = None
    task_completion: Optional[int] = None
    communication_skills: Optional[int] = None
    professionalism: Optional[int] = None
    initiative: Optional[int] = None
    strengths: Optional[str] = None
    areas_for_improvement: Optional[str] = None
    final_comments: Optional[str] = None
    status: Optional[EvaluationStatus] = None

class Evaluation(EvaluationBase):
    id: int
    application_id: int
    admin_id: int
    student_id: int
    internship_id: int
    overall_score: float
    evaluation_date: datetime
    status: EvaluationStatus

    class Config:
        from_attributes = True

# Response schemas with related data
class MentorFeedbackWithRelations(MentorFeedback):
    mentor_name: str
    student_name: str
    internship_title: str

    class Config:
        from_attributes = True

class EvaluationWithRelations(Evaluation):
    admin_name: str
    student_name: str
    internship_title: str

    class Config:
        from_attributes = True

# Feedback Statistics
class FeedbackStats(BaseModel):
    total_feedbacks: int
    average_rating: float
    feedbacks_by_mentor: dict

class EvaluationStats(BaseModel):
    total_evaluations: int
    average_score: float
    evaluations_by_admin: dict

# Combined Feedback & Evaluation Response
class StudentFeedbackEvaluationResponse(BaseModel):
    mentor_feedbacks: List[MentorFeedbackWithRelations]
    admin_evaluations: List[EvaluationWithRelations]
    feedback_stats: Optional[FeedbackStats] = None
    evaluation_stats: Optional[EvaluationStats] = None

# Feedback Summary for Dashboards
class FeedbackSummary(BaseModel):
    total_given: int
    total_received: int
    average_rating: float
    recent_feedbacks: List[MentorFeedbackWithRelations]

class EvaluationSummary(BaseModel):
    total_given: int
    total_received: int
    average_score: float
    recent_evaluations: List[EvaluationWithRelations]

# Enhanced Dashboard Stats with Feedback
class EnhancedDashboardStats(DashboardStats):
    feedback_summary: Optional[FeedbackSummary] = None
    evaluation_summary: Optional[EvaluationSummary] = None

# Search and Filter for Feedback
class FeedbackFilter(BaseModel):
    student_id: Optional[int] = None
    mentor_id: Optional[int] = None
    internship_id: Optional[int] = None
    status: Optional[FeedbackStatus] = None
    min_rating: Optional[float] = None
    max_rating: Optional[float] = None

class EvaluationFilter(BaseModel):
    student_id: Optional[int] = None
    admin_id: Optional[int] = None
    internship_id: Optional[int] = None
    status: Optional[EvaluationStatus] = None
    min_score: Optional[float] = None
    max_score: Optional[float] = None

# Bulk Feedback Operations
class BulkFeedbackStatusUpdate(BaseModel):
    feedback_ids: List[int]
    status: FeedbackStatus

class BulkEvaluationStatusUpdate(BaseModel):
    evaluation_ids: List[int]
    status: EvaluationStatus

# Report Generation for Feedback & Evaluation
class FeedbackReportRequest(BaseModel):
    report_type: str  # 'mentor', 'student', 'internship'
    target_id: int
    include_ratings: bool = True
    include_comments: bool = True

class EvaluationReportRequest(BaseModel):
    report_type: str  # 'student', 'admin', 'internship'
    target_id: int
    include_scores: bool = True
    include_comments: bool = True

# Notification Schemas for Feedback & Evaluation
class FeedbackNotification(BaseModel):
    feedback_id: int
    student_name: str
    mentor_name: str
    internship_title: str
    rating: Optional[float]
    feedback_date: datetime

class EvaluationNotification(BaseModel):
    evaluation_id: int
    student_name: str
    admin_name: str
    internship_title: str
    overall_score: float
    evaluation_date: datetime