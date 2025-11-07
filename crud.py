from sqlalchemy.orm import Session, joinedload
import models
import schemas
from password import get_password_hash, verify_password
from file_utils import delete_old_profile_picture
import os
from sqlalchemy import func

# User CRUD
def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    print(f"🔧 Creating user: {user.email}")
    print(f"🔧 User role: {user.role} (type: {type(user.role)})")
    
    # Convert role to string if it's an enum
    role_value = user.role.value if hasattr(user.role, 'value') else user.role
    print(f"🔧 Role value to save: {role_value}")
    
    hashed_password = get_password_hash(user.password)
    
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        role=role_value,
        phone=user.phone,
        department=user.department
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    print(f"✅ User created: {db_user.id} - Role in DB: {db_user.role}")
    return db_user

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

# Application Stats
def get_application_stats(db: Session):
    total = db.query(models.InternshipApplication).count()
    pending = db.query(models.InternshipApplication).filter(models.InternshipApplication.status == "pending").count()
    approved = db.query(models.InternshipApplication).filter(models.InternshipApplication.status == "approved").count()
    rejected = db.query(models.InternshipApplication).filter(models.InternshipApplication.status == "rejected").count()
    
    return {
        "total_applications": total,
        "pending_applications": pending,
        "approved_applications": approved,
        "rejected_applications": rejected
    }

# Task CRUD Functions
def get_tasks_by_student(db: Session, student_id: int):
    """Get all tasks for a specific student"""
    return db.query(models.Task)\
        .filter(models.Task.student_id == student_id)\
        .options(
            joinedload(models.Task.internship),
            joinedload(models.Task.assigner)
        )\
        .order_by(models.Task.due_date.asc())\
        .all()

def get_all_tasks(db: Session, skip: int = 0, limit: int = 100):
    """Get all tasks in the system"""
    return db.query(models.Task)\
        .options(
            joinedload(models.Task.student),
            joinedload(models.Task.internship),
            joinedload(models.Task.assigner)
        )\
        .order_by(models.Task.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()

def get_tasks_by_internship(db: Session, internship_id: int):
    """Get all tasks for a specific internship"""
    return db.query(models.Task)\
        .filter(models.Task.internship_id == internship_id)\
        .options(
            joinedload(models.Task.student),
            joinedload(models.Task.assigner)
        )\
        .all()

def create_task(db: Session, task_data: dict):
    """Create a new task"""
    task = models.Task(**task_data)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

def update_task_progress(db: Session, task_id: int, progress: int, student_id: int):
    """Update task progress and status"""
    task = db.query(models.Task)\
        .filter(
            models.Task.id == task_id,
            models.Task.student_id == student_id
        )\
        .first()
    
    if task:
        task.progress = progress
        # Auto-update status based on progress
        if progress == 100:
            task.status = "completed"
        elif progress > 0:
            task.status = "in_progress"
        else:
            task.status = "pending"
        
        db.commit()
        db.refresh(task)
    
    return task

def update_task_status(db: Session, task_id: int, status: str):
    """Update task status (admin/mentor only)"""
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if task:
        task.status = status
        db.commit()
        db.refresh(task)
    return task

def delete_task(db: Session, task_id: int):
    """Delete a task"""
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if task:
        db.delete(task)
        db.commit()
    return task

# Internship CRUD
def create_internship(db: Session, internship: schemas.InternshipCreate, user_id: int):
    db_internship = models.Internship(**internship.dict(), created_by=user_id)
    db.add(db_internship)
    db.commit()
    db.refresh(db_internship)
    return db_internship

def get_internships(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Internship).filter(models.Internship.is_active == True).offset(skip).limit(limit).all()

def get_internship(db: Session, internship_id: int):
    return db.query(models.Internship).filter(models.Internship.id == internship_id).first()

# Application CRUD
def create_application(db: Session, application: schemas.ApplicationCreate, student_id: int):
    db_application = models.InternshipApplication(**application.dict(), student_id=student_id)
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    return db_application

def get_applications_by_student(db: Session, student_id: int):
    return db.query(models.InternshipApplication).filter(models.InternshipApplication.student_id == student_id).all()

def get_applications_by_internship(db: Session, internship_id: int):
    return db.query(models.InternshipApplication).filter(models.InternshipApplication.internship_id == internship_id).all()

# Authentication
def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

# Profile Management
def get_user_profile(db: Session, user_id: int):
    """Get user profile by ID"""
    return db.query(models.User).filter(models.User.id == user_id).first()

def update_user_profile(db: Session, user_id: int, profile_update: schemas.UserProfileUpdate):
    """Update user profile"""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        # Delete old profile picture if it's being updated
        if (profile_update.profile_picture and 
            profile_update.profile_picture != db_user.profile_picture and
            db_user.profile_picture != "default_avatar.png"):
            delete_old_profile_picture(db_user.profile_picture)
        
        update_data = profile_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_user, field, value)
        db.commit()
        db.refresh(db_user)
    return db_user

def update_profile_picture(db: Session, user_id: int, filename: str):
    """Update user's profile picture filename"""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        # Delete old profile picture
        if db_user.profile_picture and db_user.profile_picture != "default_avatar.png":
            delete_old_profile_picture(db_user.profile_picture)
        
        db_user.profile_picture = filename
        db.commit()
        db.refresh(db_user)
    return db_user

# Admin Management Functions
def get_all_users(db: Session, skip: int = 0, limit: int = 100):
    """Get all users (admin only)"""
    return db.query(models.User).order_by(models.User.created_at.desc()).offset(skip).limit(limit).all()

def get_user_by_id(db: Session, user_id: int):
    """Get user by ID"""
    return db.query(models.User).filter(models.User.id == user_id).first()

def update_user_admin(db: Session, user_id: int, user_update: schemas.UserUpdateAdmin):
    """Update any user (admin only)"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None
    
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    return user

def delete_user(db: Session, user_id: int):
    """Delete user (admin only) - FIXED WITH PROPER CASCADE HANDLING"""
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            return None
        
        print(f"🗑️ Attempting to delete user: {user.id} - {user.email}")
        
        # Delete user's applications
        applications = db.query(models.InternshipApplication).filter(
            models.InternshipApplication.student_id == user_id
        ).all()
        for application in applications:
            db.delete(application)
            print(f"🗑️ Deleted application: {application.id}")
        
        # If user is a mentor, handle their internships
        if user.role == "mentor":
            mentor_internships = db.query(models.Internship).filter(
                models.Internship.created_by == user_id
            ).all()
            
            for internship in mentor_internships:
                # Delete applications for this internship
                db.query(models.InternshipApplication).filter(
                    models.InternshipApplication.internship_id == internship.id
                ).delete()
                
                # Delete tasks for this internship
                db.query(models.Task).filter(
                    models.Task.internship_id == internship.id
                ).delete()
                
                # Delete the internship
                db.delete(internship)
                print(f"🗑️ Deleted mentor internship: {internship.id}")
        
        # Delete tasks assigned to this user
        tasks = db.query(models.Task).filter(models.Task.student_id == user_id).all()
        for task in tasks:
            db.delete(task)
            print(f"🗑️ Deleted task: {task.id}")
        
        # Delete tasks created by this user
        created_tasks = db.query(models.Task).filter(models.Task.assigned_by == user_id).all()
        for task in created_tasks:
            db.delete(task)
            print(f"🗑️ Deleted created task: {task.id}")
        
        # Delete user's profile picture if exists
        if user.profile_picture and user.profile_picture != "default_avatar.png":
            try:
                delete_old_profile_picture(user.profile_picture)
                print(f"🗑️ Deleted profile picture: {user.profile_picture}")
            except Exception as e:
                print(f"⚠️ Could not delete profile picture: {e}")
        
        # Finally delete the user
        db.delete(user)
        db.commit()
        print(f"✅ Successfully deleted user: {user_id}")
        return user
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error deleting user {user_id}: {e}")
        raise e

def get_system_stats(db: Session):
    """Get system statistics"""
    try:
        total_users = db.query(models.User).count()
        total_students = db.query(models.User).filter(models.User.role == "student").count()
        total_admins = db.query(models.User).filter(models.User.role == "admin").count()
        total_mentors = db.query(models.User).filter(models.User.role == "mentor").count()
        total_internships = db.query(models.Internship).count()
        total_applications = db.query(models.InternshipApplication).count()
        total_tasks = db.query(models.Task).count()
        
        return {
            "total_users": total_users,
            "total_students": total_students,
            "total_admins": total_admins,
            "total_mentors": total_mentors,
            "total_internships": total_internships,
            "total_applications": total_applications,
            "total_tasks": total_tasks
        }
    except Exception as e:
        print(f"❌ Error getting system stats: {e}")
        return {
            "total_users": 0,
            "total_students": 0,
            "total_admins": 0,
            "total_mentors": 0,
            "total_internships": 0,
            "total_applications": 0,
            "total_tasks": 0
        }

def search_users(db: Session, query: str, skip: int = 0, limit: int = 50):
    """Search users by name or email"""
    return db.query(models.User).filter(
        (models.User.full_name.ilike(f"%{query}%")) | 
        (models.User.email.ilike(f"%{query}%"))
    ).offset(skip).limit(limit).all()

# Mentor-specific Functions
def get_internships_by_mentor(db: Session, mentor_id: int, skip: int = 0, limit: int = 100):
    """Get internships created by a specific mentor"""
    return db.query(models.Internship)\
        .filter(models.Internship.created_by == mentor_id)\
        .offset(skip)\
        .limit(limit)\
        .all()

def get_applications_for_mentor(db: Session, mentor_id: int, skip: int = 0, limit: int = 100):
    """Get applications for internships created by a specific mentor"""
    return db.query(models.InternshipApplication)\
        .join(models.Internship, models.InternshipApplication.internship_id == models.Internship.id)\
        .filter(models.Internship.created_by == mentor_id)\
        .offset(skip)\
        .limit(limit)\
        .all()

def get_mentor_stats(db: Session, mentor_id: int):
    """Get statistics for a mentor"""
    total_internships = db.query(models.Internship)\
        .filter(models.Internship.created_by == mentor_id)\
        .count()
    
    total_applications = db.query(models.InternshipApplication)\
        .join(models.Internship, models.InternshipApplication.internship_id == models.Internship.id)\
        .filter(models.Internship.created_by == mentor_id)\
        .count()
    
    pending_applications = db.query(models.InternshipApplication)\
        .join(models.Internship, models.InternshipApplication.internship_id == models.Internship.id)\
        .filter(
            models.Internship.created_by == mentor_id,
            models.InternshipApplication.status == "pending"
        )\
        .count()
    
    return {
        "total_internships": total_internships,
        "total_applications": total_applications,
        "pending_applications": pending_applications
    }

def update_application_status(db: Session, application_id: int, status: str, mentor_id: int):
    """Update application status (mentor only for their internships)"""
    application = db.query(models.InternshipApplication)\
        .join(models.Internship, models.InternshipApplication.internship_id == models.Internship.id)\
        .filter(
            models.InternshipApplication.id == application_id,
            models.Internship.created_by == mentor_id
        )\
        .first()
    
    if application:
        application.status = status
        db.commit()
        db.refresh(application)
    
    return application

# Additional Functions
def get_internship_with_applications(db: Session, internship_id: int):
    """Get internship with its applications"""
    return db.query(models.Internship).filter(models.Internship.id == internship_id).first()

def get_application_with_details(db: Session, application_id: int):
    """Get application with student and internship details"""
    return db.query(models.InternshipApplication).filter(
        models.InternshipApplication.id == application_id
    ).first()

def get_student_applications_with_details(db: Session, student_id: int):
    """Get student applications with internship details"""
    return db.query(models.InternshipApplication).filter(
        models.InternshipApplication.student_id == student_id
    ).all()

def delete_internship(db: Session, internship_id: int):
    """Delete internship and its applications"""
    internship = db.query(models.Internship).filter(models.Internship.id == internship_id).first()
    if internship:
        # Delete related applications
        db.query(models.InternshipApplication).filter(
            models.InternshipApplication.internship_id == internship_id
        ).delete()
        
        # Delete related tasks
        db.query(models.Task).filter(models.Task.internship_id == internship_id).delete()
        
        # Delete internship
        db.delete(internship)
        db.commit()
    
    return internship

# =============================================
# MENTOR-SPECIFIC FUNCTIONS FOR STUDENT VIEWING
# =============================================

def get_mentor_students(db: Session, mentor_id: int):
    """Get all students assigned to a mentor"""
    try:
        # Get all active students (you might want to adjust this based on your mentor-student relationships)
        students = db.query(models.User).filter(
            models.User.role == "student",
            models.User.is_active == True
        ).all()
        return students
    except Exception as e:
        print(f"❌ Error getting mentor students: {e}")
        return []

def get_mentor_pending_tasks_count(db: Session, mentor_id: int):
    """Get count of pending tasks for mentor's students"""
    try:
        count = db.query(models.Task).filter(
            models.Task.assigned_by == mentor_id,
            models.Task.status.in_(["pending", "in_progress"])
        ).count()
        return count
    except Exception as e:
        print(f"❌ Error getting pending tasks count: {e}")
        return 0

def get_mentor_pending_feedback_count(db: Session, mentor_id: int):
    """Get count of pending feedback for mentor"""
    try:
        count = db.query(models.MentorFeedback).filter(
            models.MentorFeedback.mentor_id == mentor_id
        ).count()
        return count
    except Exception as e:
        print(f"❌ Error getting pending feedback count: {e}")
        return 0

def get_mentor_active_internships_count(db: Session, mentor_id: int):
    """Get count of active internships for mentor's students"""
    try:
        count = db.query(models.Internship).filter(
            models.Internship.created_by == mentor_id,
            models.Internship.is_active == True
        ).count()
        return count
    except Exception as e:
        print(f"❌ Error getting active internships count: {e}")
        return 0

def get_mentor_recent_tasks(db: Session, mentor_id: int, limit: int = 5):
    """Get recent tasks assigned by mentor"""
    try:
        tasks = db.query(models.Task).filter(
            models.Task.assigned_by == mentor_id
        ).options(
            joinedload(models.Task.student),
            joinedload(models.Task.internship)
        ).order_by(models.Task.created_at.desc()).limit(limit).all()
        return tasks
    except Exception as e:
        print(f"❌ Error getting recent tasks: {e}")
        return []

def get_mentor_recent_feedback(db: Session, mentor_id: int, limit: int = 5):
    """Get recent feedback given by mentor"""
    try:
        feedback = db.query(models.MentorFeedback).filter(
            models.MentorFeedback.mentor_id == mentor_id
        ).options(
            joinedload(models.MentorFeedback.student),
            joinedload(models.MentorFeedback.internship)
        ).order_by(models.MentorFeedback.feedback_date.desc()).limit(limit).all()
        return feedback
    except Exception as e:
        print(f"❌ Error getting recent feedback: {e}")
        return []

def get_student_progress(db: Session, student_id: int):
    """Calculate student progress based on completed tasks"""
    try:
        total_tasks = db.query(models.Task).filter(models.Task.student_id == student_id).count()
        completed_tasks = db.query(models.Task).filter(
            models.Task.student_id == student_id,
            models.Task.status == "completed"
        ).count()
        
        if total_tasks == 0:
            return 0
        return int((completed_tasks / total_tasks) * 100)
    except Exception as e:
        print(f"❌ Error calculating student progress: {e}")
        return 0

def get_student_current_internship(db: Session, student_id: int):
    """Get student's current internship"""
    try:
        application = db.query(models.InternshipApplication).filter(
            models.InternshipApplication.student_id == student_id,
            models.InternshipApplication.status == "approved"
        ).options(joinedload(models.InternshipApplication.internship)).first()
        
        if application:
            return application.internship
        return None
    except Exception as e:
        print(f"❌ Error getting student internship: {e}")
        return None

def get_mentor_active_tasks_count(db: Session, mentor_id: int):
    """Get count of active tasks for mentor's students"""
    try:
        count = db.query(models.Task).filter(
            models.Task.assigned_by == mentor_id,
            models.Task.status.in_(["pending", "in_progress"])
        ).count()
        return count
    except Exception as e:
        print(f"❌ Error getting active tasks count: {e}")
        return 0

def get_mentor_students_avg_rating(db: Session, mentor_id: int):
    """Get average rating of mentor's students"""
    try:
        avg_rating = db.query(func.avg(models.MentorFeedback.overall_rating)).filter(
            models.MentorFeedback.mentor_id == mentor_id
        ).scalar()
        return float(avg_rating) if avg_rating else 0.0
    except Exception as e:
        print(f"❌ Error getting average rating: {e}")
        return 0.0

def get_mentor_student(db: Session, mentor_id: int, student_id: int):
    """Verify and get a specific student for a mentor"""
    try:
        student = db.query(models.User).filter(
            models.User.id == student_id,
            models.User.role == "student",
            models.User.is_active == True
        ).first()
        return student
    except Exception as e:
        print(f"❌ Error getting mentor student: {e}")
        return None

def get_student_details(db: Session, student_id: int):
    """Get detailed information about a student"""
    try:
        student = db.query(models.User).filter(models.User.id == student_id).first()
        return student
    except Exception as e:
        print(f"❌ Error getting student details: {e}")
        return None

def get_student_tasks(db: Session, student_id: int):
    """Get all tasks for a student"""
    try:
        tasks = db.query(models.Task).filter(
            models.Task.student_id == student_id
        ).options(
            joinedload(models.Task.internship),
            joinedload(models.Task.assigner)
        ).all()
        return tasks
    except Exception as e:
        print(f"❌ Error getting student tasks: {e}")
        return []

def get_student_feedback(db: Session, student_id: int):
    """Get all feedback for a student"""
    try:
        feedback = db.query(models.MentorFeedback).filter(
            models.MentorFeedback.student_id == student_id
        ).options(
            joinedload(models.MentorFeedback.mentor),
            joinedload(models.MentorFeedback.internship)
        ).all()
        return feedback
    except Exception as e:
        print(f"❌ Error getting student feedback: {e}")
        return []

def get_students_with_internships_count(db: Session, mentor_id: int):
    """Get count of students with active internships"""
    try:
        # Get all students assigned to mentor
        students = get_mentor_students(db, mentor_id)
        count = 0
        
        for student in students:
            internship = get_student_current_internship(db, student.id)
            if internship:
                count += 1
        
        return count
    except Exception as e:
        print(f"❌ Error counting students with internships: {e}")
        return 0

def get_mentor_student_internships(db: Session, mentor_id: int):
    """Get internships for all mentor's students"""
    try:
        students = get_mentor_students(db, mentor_id)
        student_internships = {}
        
        for student in students:
            internship = get_student_current_internship(db, student.id)
            student_internships[student.id] = internship
        
        return student_internships
    except Exception as e:
        print(f"❌ Error getting student internships: {e}")
        return {}

def get_mentor_student_progress(db: Session, mentor_id: int):
    """Get progress for all mentor's students"""
    try:
        students = get_mentor_students(db, mentor_id)
        student_progress = {}
        
        for student in students:
            progress = get_student_progress(db, student.id)
            student_progress[student.id] = progress
        
        return student_progress
    except Exception as e:
        print(f"❌ Error getting student progress: {e}")
        return {}
    
