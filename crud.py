from sqlalchemy.orm import Session
import models
import schemas
from password import get_password_hash, verify_password
from file_utils import delete_old_profile_picture  # NEW
import os

# User CRUD
def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        role=user.role.value,
        phone=user.phone,
        department=user.department
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

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

# Task CRUD
def create_task(db: Session, task: schemas.TaskCreate, assigned_by: int):
    db_task = models.Task(**task.dict(), assigned_by=assigned_by)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def get_tasks_by_student(db: Session, student_id: int):
    return db.query(models.Task).filter(models.Task.student_id == student_id).all()

# Password verification function
def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

# Add these functions to your existing crud.py

def get_user_profile(db: Session, user_id: int):
    """Get user profile by ID"""
    return db.query(models.User).filter(models.User.id == user_id).first()

def update_user_profile(db: Session, user_id: int, profile_update: schemas.UserProfileUpdate):
    """Update user profile"""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        update_data = profile_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_user, field, value)
        db.commit()
        db.refresh(db_user)
    return db_user


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


# Add these functions to your existing crud.py

# Admin Management Functions
def get_all_users(db: Session, skip: int = 0, limit: int = 100):
    """Get all users (admin only)"""
    return db.query(models.User).offset(skip).limit(limit).all()

def get_user_by_id(db: Session, user_id: int):
    """Get user by ID"""
    return db.query(models.User).filter(models.User.id == user_id).first()

def update_user_admin(db: Session, user_id: int, user_update: schemas.UserUpdateAdmin):
    """Update any user (admin only)"""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        update_data = user_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_user, field, value)
        db.commit()
        db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int):
    """Delete user (admin only)"""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        # Delete user's profile picture if exists
        if db_user.profile_picture and db_user.profile_picture != "default_avatar.png":
            from file_utils import delete_old_profile_picture
            delete_old_profile_picture(db_user.profile_picture)
        
        db.delete(db_user)
        db.commit()
    return db_user

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
        # Return default stats if there's an error
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
        role=role_value,  # Save as string
        phone=user.phone,
        department=user.department
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    print(f"✅ User created: {db_user.id} - Role in DB: {db_user.role}")
    return db_user