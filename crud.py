from sqlalchemy.orm import Session
import models
import schemas
from password import get_password_hash, verify_password  # Changed import

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