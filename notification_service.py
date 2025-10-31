# notification_service.py
from sqlalchemy.orm import Session
from email_service import email_service
from email_templates import EmailTemplates
import asyncio

async def send_application_submitted_email(db: Session, student_id: int, internship_id: int):
    """Send email when student submits application"""
    from models import User, Internship
    
    student = db.query(User).filter(User.id == student_id).first()
    internship = db.query(Internship).filter(Internship.id == internship_id).first()
    
    if student and internship:
        subject = f"Application Submitted - {internship.title}"
        html_content = EmailTemplates.application_submitted(
            student.full_name, 
            internship.title
        )
        await email_service.send_email_async(student.email, subject, html_content)

async def send_application_status_email(db: Session, application_id: int, new_status: str, notes: str = ""):
    """Send email when application status changes"""
    from models import InternshipApplication, User, Internship
    
    application = db.query(InternshipApplication)\
        .join(User, InternshipApplication.student_id == User.id)\
        .join(Internship, InternshipApplication.internship_id == Internship.id)\
        .filter(InternshipApplication.id == application_id)\
        .first()
    
    if application:
        subject = f"Application Update - {application.internship.title}"
        html_content = EmailTemplates.application_status_update(
            application.student.full_name,
            application.internship.title,
            new_status,
            notes
        )
        await email_service.send_email_async(application.student.email, subject, html_content)

async def send_task_assignment_email(db: Session, task_id: int):
    """Send email when task is assigned to student"""
    from models import Task, User
    
    task = db.query(Task)\
        .join(User, Task.student_id == User.id)\
        .join(User, Task.assigned_by == User.id)\
        .filter(Task.id == task_id)\
        .first()
    
    if task and task.student:
        subject = f"New Task Assigned: {task.title}"
        due_date = task.due_date.strftime("%Y-%m-%d") if task.due_date else "Not specified"
        html_content = EmailTemplates.task_assigned(
            task.student.full_name,
            task.title,
            due_date,
            task.assigned_by_user.full_name,
            task.description
        )
        await email_service.send_email_async(task.student.email, subject, html_content)

async def send_new_application_notification(db: Session, application_id: int):
    """Send email to mentor when new application is received"""
    from models import InternshipApplication, Internship, User
    
    application = db.query(InternshipApplication)\
        .join(Internship, InternshipApplication.internship_id == Internship.id)\
        .join(User, Internship.created_by == User.id)\
        .join(User, InternshipApplication.student_id == User.id)\
        .filter(InternshipApplication.id == application_id)\
        .first()
    
    if application and application.internship.created_by_user:
        subject = f"New Application - {application.internship.title}"
        html_content = EmailTemplates.new_application(
            application.internship.created_by_user.full_name,
            application.student.full_name,
            application.internship.title,
            application.application_date.strftime("%Y-%m-%d")
        )
        await email_service.send_email_async(
            application.internship.created_by_user.email, 
            subject, 
            html_content
        )