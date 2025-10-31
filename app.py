from fastapi import FastAPI, Depends, HTTPException, Request, Form, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import models
import schemas
from auth import get_current_active_user, create_access_token, get_current_user_from_cookie, get_current_user_optional
from database import SessionLocal, engine, get_db
import crud
from password import verify_password
from file_utils import save_profile_picture, delete_old_profile_picture
import os
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== EMAIL NOTIFICATION SYSTEM =====

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.sender_email = os.getenv("SENDER_EMAIL", "")
        self.sender_password = os.getenv("SENDER_PASSWORD", "")
        self.enabled = bool(self.sender_email and self.sender_password)
    
    def send_email(self, to_email: str, subject: str, html_content: str):
        """Send email synchronously"""
        if not self.enabled:
            logger.info(f"📧 Email disabled - would send to {to_email}: {subject}")
            return True  # Return True to prevent app crashes
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add HTML body
            msg.attach(MIMEText(html_content, 'html'))
            
            # Create server connection and send
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"✅ Email sent to {to_email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send email to {to_email}: {str(e)}")
            return True  # Still return True to avoid breaking the app
    
    async def send_email_async(self, to_email: str, subject: str, html_content: str):
        """Send email asynchronously using thread pool"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.send_email, to_email, subject, html_content)

# Initialize email service
email_service = EmailService()

class EmailTemplates:
    @staticmethod
    def application_submitted(student_name: str, internship_title: str):
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; }}
                .content {{ background: #f9f9f9; padding: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Application Submitted 🎉</h1>
                </div>
                <div class="content">
                    <h2>Hello {student_name},</h2>
                    <p>Your application for <strong>{internship_title}</strong> has been successfully submitted!</p>
                    <p>We will review your application and get back to you soon.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    @staticmethod
    def application_status_update(student_name: str, internship_title: str, status: str, notes: str = ""):
        status_colors = {
            'approved': '#4CAF50',
            'rejected': '#f44336', 
            'pending': '#ff9800'
        }
        color = status_colors.get(status, '#ff9800')
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: {color}; color: white; padding: 20px; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Application {status.title()}</h1>
                </div>
                <div class="content">
                    <h2>Hello {student_name},</h2>
                    <p>Your application for <strong>{internship_title}</strong> has been <strong>{status}</strong>.</p>
                    {f'<p><strong>Notes:</strong> {notes}</p>' if notes else ''}
                </div>
            </div>
        </body>
        </html>
        """
    
    @staticmethod
    def task_assigned(student_name: str, task_title: str, due_date: str, mentor_name: str):
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #2196F3; color: white; padding: 20px; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>New Task Assigned</h1>
                </div>
                <div class="content">
                    <h2>Hello {student_name},</h2>
                    <p>Your mentor <strong>{mentor_name}</strong> assigned you a new task:</p>
                    <p><strong>Task:</strong> {task_title}</p>
                    <p><strong>Due Date:</strong> {due_date}</p>
                </div>
            </div>
        </body>
        </html>
        """

async def send_application_submitted_email(db: Session, student_id: int, internship_id: int):
    """Send email when student submits application"""
    try:
        student = db.query(models.User).filter(models.User.id == student_id).first()
        internship = db.query(models.Internship).filter(models.Internship.id == internship_id).first()
        
        if student and internship:
            subject = f"Application Submitted - {internship.title}"
            html_content = EmailTemplates.application_submitted(student.full_name, internship.title)
            await email_service.send_email_async(student.email, subject, html_content)
    except Exception as e:
        logger.error(f"Error sending application submitted email: {e}")

async def send_application_status_email(db: Session, application_id: int, new_status: str, notes: str = ""):
    """Send email when application status changes"""
    try:
        application = db.query(models.InternshipApplication)\
            .join(models.User, models.InternshipApplication.student_id == models.User.id)\
            .join(models.Internship, models.InternshipApplication.internship_id == models.Internship.id)\
            .filter(models.InternshipApplication.id == application_id)\
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
    except Exception as e:
        logger.error(f"Error sending application status email: {e}")

async def send_task_assignment_email(db: Session, task_id: int):
    """Send email when task is assigned to student"""
    try:
        task = db.query(models.Task)\
            .join(models.User, models.Task.student_id == models.User.id)\
            .join(models.User, models.Task.assigned_by == models.User.id)\
            .filter(models.Task.id == task_id)\
            .first()
        
        if task and task.student:
            subject = f"New Task: {task.title}"
            due_date = task.due_date.strftime("%Y-%m-%d") if task.due_date else "Not specified"
            html_content = EmailTemplates.task_assigned(
                task.student.full_name,
                task.title,
                due_date,
                task.assigned_by_user.full_name
            )
            await email_service.send_email_async(task.student.email, subject, html_content)
    except Exception as e:
        logger.error(f"Error sending task assignment email: {e}")

async def check_deadlines_and_send_reminders():
    """Check for upcoming deadlines and send reminder emails"""
    db = SessionLocal()
    try:
        upcoming_deadline = datetime.now() + timedelta(days=3)
        tasks = db.query(models.Task)\
            .join(models.User, models.Task.student_id == models.User.id)\
            .filter(
                models.Task.due_date <= upcoming_deadline,
                models.Task.due_date >= datetime.now(),
                models.Task.status.in_(["pending", "in_progress"])
            )\
            .all()
        
        for task in tasks:
            days_left = (task.due_date - datetime.now()).days
            if 1 <= days_left <= 3:
                subject = f"Deadline Reminder: {task.title}"
                html_content = f"""
                <html>
                <body>
                    <h2>Hello {task.student.full_name},</h2>
                    <p>Your task <strong>{task.title}</strong> is due in <strong>{days_left} day(s)</strong>.</p>
                    <p>Please submit your work before the deadline.</p>
                </body>
                </html>
                """
                await email_service.send_email_async(task.student.email, subject, html_content)
                logger.info(f"📧 Sent deadline reminder for task '{task.title}'")
                
    except Exception as e:
        logger.error(f"❌ Error in deadline reminder: {e}")
    finally:
        db.close()

async def start_background_tasks():
    """Start background tasks"""
    while True:
        try:
            await check_deadlines_and_send_reminders()
        except Exception as e:
            logger.error(f"❌ Background task error: {e}")
        await asyncio.sleep(3600)  # Check every hour

# ===== END EMAIL NOTIFICATION SYSTEM =====

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Internship Management System")

# Create directories if they don't exist
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)
os.makedirs("uploads/profile_pictures", exist_ok=True)
os.makedirs("static/reports", exist_ok=True)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
templates = Jinja2Templates(directory="templates")

# ===== AUTHENTICATION ROUTES =====
@app.post("/api/login")
async def login_user(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """User login with better error handling"""
    try:
        user = crud.authenticate_user(db, email, password)
        if not user:
            return RedirectResponse("/login?error=Invalid+credentials", status_code=302)
        
        # Create access token with longer expiration
        access_token_expires = timedelta(days=7)  # 7 days
        access_token = create_access_token(
            data={"sub": user.email}, 
            expires_delta=access_token_expires
        )
        
        response = RedirectResponse("/dashboard", status_code=302)
        response.set_cookie(
            key="access_token",
            value=access_token,  # Don't add "Bearer " prefix
            httponly=True,
            max_age=7 * 24 * 60 * 60,  # 7 days in seconds
            expires=7 * 24 * 60 * 60,   # 7 days in seconds
            secure=False,  # Set to True in production with HTTPS
            samesite="lax"
        )
        
        logger.info(f"🎯 Dashboard access - User: {user.email}, Role: {user.role}")
        return response
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return RedirectResponse("/login?error=Login+failed", status_code=302)

@app.get("/logout")
async def logout():
    """Logout user and clear cookie"""
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie("access_token")
    return response

# ===== FRONTEND ROUTES =====
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Main dashboard with improved error handling"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        logger.info(f"🎯 Dashboard access - User: {user.email}, Role: {user.role}")
        
        if user.role == "student":
            internships = crud.get_internships(db)
            applications = crud.get_applications_by_student(db, user.id)
            tasks = crud.get_tasks_by_student(db, user.id)
            return templates.TemplateResponse("dashboard_student.html", {
                "request": request,
                "user": user,
                "internships": internships,
                "applications": applications,
                "tasks": tasks
            })
        elif user.role == "admin":
            internships = crud.get_internships(db)
            try:
                stats = crud.get_system_stats(db)
            except Exception as e:
                logger.warning(f"⚠️ Could not get system stats: {e}")
                stats = {
                    "total_users": 0,
                    "total_students": 0,
                    "total_admins": 0,
                    "total_mentors": 0,
                    "total_internships": 0,
                    "total_applications": 0,
                    "total_tasks": 0
                }
            
            return templates.TemplateResponse("dashboard_admin.html", {
                "request": request,
                "user": user,
                "internships": internships,
                "stats": stats
            })
        elif user.role == "mentor":
            internships = crud.get_internships(db)
            mentor_internships = crud.get_internships_by_mentor(db, user.id)
            mentor_applications = crud.get_applications_for_mentor(db, user.id)
            
            return templates.TemplateResponse("dashboard_mentor.html", {
                "request": request,
                "user": user,
                "internships": internships,
                "mentor_internships": mentor_internships,
                "mentor_applications": mentor_applications
            })
        else:
            logger.error(f"❌ Unknown role: {user.role}")
            return RedirectResponse("/login?error=Unknown+user+role")
            
    except HTTPException as e:
        if e.status_code == 307:  # Temporary redirect
            return RedirectResponse("/login")
        raise e
    except Exception as e:
        logger.error(f"💥 Dashboard error: {e}")
        # Clear invalid token and redirect to login
        response = RedirectResponse("/login")
        response.delete_cookie("access_token")
        return response

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: Session = Depends(get_db)):
    try:
        user = await get_current_user_from_cookie(request, db)
        return templates.TemplateResponse("profile.html", {
            "request": request,
            "user": user
        })
    except Exception as e:
        logger.error(f"Profile page error: {e}")
        return RedirectResponse("/login")

# ===== ADMIN MANAGEMENT ROUTES =====
@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(request: Request, db: Session = Depends(get_db)):
    """Admin users management page"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "admin":
            return RedirectResponse("/dashboard?error=Access+denied")
        
        users = crud.get_all_users(db)
        stats = crud.get_system_stats(db)
        
        return templates.TemplateResponse("admin_users.html", {
            "request": request,
            "user": user,
            "users": users,
            "stats": stats
        })
    except Exception as e:
        return RedirectResponse("/login")

@app.get("/admin/internships", response_class=HTMLResponse)
async def admin_internships_page(request: Request, db: Session = Depends(get_db)):
    """Admin internships management page"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "admin":
            return RedirectResponse("/dashboard?error=Access+denied")
        
        internships = db.query(models.Internship).all()
        stats = crud.get_system_stats(db)
        
        return templates.TemplateResponse("admin_internships.html", {
            "request": request,
            "user": user,
            "internships": internships,
            "stats": stats
        })
    except Exception as e:
        logger.error(f"Admin internships page error: {e}")
        return RedirectResponse("/login")

@app.get("/admin/system", response_class=HTMLResponse)
async def admin_system_page(request: Request, db: Session = Depends(get_db)):
    """Admin system management page"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "admin":
            return RedirectResponse("/dashboard?error=Access+denied")
        
        stats = crud.get_system_stats(db)
        
        return templates.TemplateResponse("admin_system.html", {
            "request": request,
            "user": user,
            "stats": stats
        })
    except Exception as e:
        return RedirectResponse("/login")

# ===== ADMIN APPLICATION REVIEW ROUTES =====
@app.get("/admin/applications", response_class=HTMLResponse)
async def admin_applications_page(request: Request, db: Session = Depends(get_db)):
    """Admin applications review page"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "admin":
            return RedirectResponse("/dashboard?error=Access+denied")
        
        # Get all applications with student and internship details
        applications = db.query(models.InternshipApplication)\
            .join(models.User, models.InternshipApplication.student_id == models.User.id)\
            .join(models.Internship, models.InternshipApplication.internship_id == models.Internship.id)\
            .options(
                joinedload(models.InternshipApplication.student),
                joinedload(models.InternshipApplication.internship)
            )\
            .order_by(models.InternshipApplication.application_date.desc())\
            .all()
        
        stats = crud.get_system_stats(db)
        
        return templates.TemplateResponse("admin_applications.html", {
            "request": request,
            "user": user,
            "applications": applications,
            "stats": stats
        })
    except Exception as e:
        logger.error(f"Admin applications page error: {e}")
        return RedirectResponse("/login")

@app.put("/api/admin/applications/{application_id}/status")
async def update_application_status_admin(
    background_tasks: BackgroundTasks,
    application_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Admin updates application status"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "admin":
            return {"success": False, "error": "Only admins can update application status"}
        
        form_data = await request.form()
        new_status = form_data.get("status")
        admin_notes = form_data.get("admin_notes", "")
        
        if new_status not in ["approved", "rejected"]:
            return {"success": False, "error": "Invalid status. Must be 'approved' or 'rejected'"}
        
        # Get application with student and internship details
        application = db.query(models.InternshipApplication)\
            .join(models.User, models.InternshipApplication.student_id == models.User.id)\
            .join(models.Internship, models.InternshipApplication.internship_id == models.Internship.id)\
            .filter(models.InternshipApplication.id == application_id)\
            .first()
        
        if not application:
            return {"success": False, "error": "Application not found"}
        
        # Store old status for logging
        old_status = application.status
        
        # Update application status
        application.status = new_status
        db.commit()
        db.refresh(application)
        
        # Send email notification
        background_tasks.add_task(send_application_status_email, db, application_id, new_status, admin_notes)
        
        logger.info(f"📝 Application {application_id} status changed from {old_status} to {new_status}")
        logger.info(f"📝 Student: {application.student.email}, Internship: {application.internship.title}")
        logger.info(f"📝 Admin Notes: {admin_notes}")
        
        return {
            "success": True, 
            "message": f"Application {new_status} successfully", 
            "student_email": application.student.email
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating application status: {e}")
        return {"success": False, "error": str(e)}

# ===== MENTOR ROUTES =====
@app.get("/mentor/internships", response_class=HTMLResponse)
async def mentor_internships_page(request: Request, db: Session = Depends(get_db)):
    """Mentor internships management page"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "mentor":
            return RedirectResponse("/dashboard?error=Access+denied")
        
        mentor_internships = crud.get_internships_by_mentor(db, user.id)
        applications = crud.get_applications_for_mentor(db, user.id)
        
        return templates.TemplateResponse("mentor_internships.html", {
            "request": request,
            "user": user,
            "internships": mentor_internships,
            "applications": applications
        })
    except Exception as e:
        return RedirectResponse("/login")

@app.get("/mentor/applications", response_class=HTMLResponse)
async def mentor_applications_page(request: Request, db: Session = Depends(get_db)):
    """Mentor applications management page"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "mentor":
            return RedirectResponse("/dashboard?error=Access+denied")
        
        applications = db.query(models.InternshipApplication)\
            .join(models.Internship, models.InternshipApplication.internship_id == models.Internship.id)\
            .join(models.User, models.InternshipApplication.student_id == models.User.id)\
            .filter(models.Internship.created_by == user.id)\
            .all()
        
        return templates.TemplateResponse("mentor_applications.html", {
            "request": request,
            "user": user,
            "applications": applications
        })
    except Exception as e:
        return RedirectResponse("/login")

# ===== STUDENT ROUTES =====
@app.get("/internships", response_class=HTMLResponse)
async def internships_page(request: Request, db: Session = Depends(get_db)):
    """Internship listings page for students"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "student":
            return RedirectResponse("/dashboard?error=Access+denied")
        
        internships = crud.get_internships(db)
        return templates.TemplateResponse("internships.html", {
            "request": request,
            "user": user,
            "internships": internships
        })
    except Exception as e:
        return RedirectResponse("/login")

@app.get("/my-applications", response_class=HTMLResponse)
async def my_applications_page(request: Request, db: Session = Depends(get_db)):
    """Student applications tracking page"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "student":
            return RedirectResponse("/dashboard?error=Access+denied")
        
        applications = crud.get_student_applications_with_details(db, user.id)
        return templates.TemplateResponse("my_applications.html", {
            "request": request,
            "user": user,
            "applications": applications
        })
    except Exception as e:
        return RedirectResponse("/login")

# ===== TASK MANAGEMENT ROUTES =====
@app.get("/tasks", response_class=HTMLResponse)
async def tasks_page(request: Request, db: Session = Depends(get_db)):
    """Tasks page for all roles"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role == "student":
            tasks = crud.get_tasks_by_student(db, user.id)
            return templates.TemplateResponse("tasks_student.html", {
                "request": request,
                "user": user,
                "tasks": tasks
            })
        elif user.role in ["admin", "mentor"]:
            tasks = crud.get_all_tasks(db)
            students = db.query(models.User).filter(models.User.role == "student").all()
            internships = crud.get_internships(db)
            return templates.TemplateResponse("tasks_management.html", {
                "request": request,
                "user": user,
                "tasks": tasks,
                "students": students,
                "internships": internships
            })
        else:
            return RedirectResponse("/dashboard?error=Access+denied")
            
    except Exception as e:
        return RedirectResponse("/login")

@app.post("/api/tasks")
async def create_task_api(
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db)
):
    """Create new task (admin/mentor only)"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role not in ["admin", "mentor"]:
            return {"success": False, "error": "Only admins and mentors can create tasks"}
        
        form_data = await request.form()
        
        # Parse due_date from string to datetime
        due_date_str = form_data.get('due_date')
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
            except ValueError:
                return {"success": False, "error": "Invalid date format. Use YYYY-MM-DD"}
        
        # Convert string IDs to integers
        internship_id = form_data.get('internship_id')
        student_id = form_data.get('student_id')
        
        task = models.Task(
            title=form_data.get('title'),
            description=form_data.get('description'),
            internship_id=int(internship_id) if internship_id else None,
            student_id=int(student_id) if student_id else None,
            assigned_by=user.id,
            due_date=due_date,
            status="pending",
            progress=0
        )
        
        db.add(task)
        db.commit()
        db.refresh(task)
        
        # Send task assignment email
        if student_id:
            background_tasks.add_task(send_task_assignment_email, db, task.id)
        
        return {"success": True, "message": "Task created successfully", "task_id": task.id}
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error creating task: {e}")
        return {"success": False, "error": str(e)}

@app.put("/api/tasks/{task_id}/progress")
async def update_task_progress_api(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Update task progress (student only)"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "student":
            return {"success": False, "error": "Only students can update task progress"}
        
        form_data = await request.form()
        progress = int(form_data.get('progress', 0))
        
        if progress < 0 or progress > 100:
            return {"success": False, "error": "Progress must be between 0 and 100"}
        
        task = db.query(models.Task).filter(
            models.Task.id == task_id,
            models.Task.student_id == user.id
        ).first()
        
        if not task:
            return {"success": False, "error": "Task not found"}
        
        task.progress = progress
        if progress == 100:
            task.status = "completed"
        elif progress > 0:
            task.status = "in_progress"
        else:
            task.status = "pending"
        
        db.commit()
        
        return {"success": True, "message": "Progress updated successfully"}
        
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}

# ===== PROFILE PICTURE ROUTES =====
@app.post("/api/users/me/profile-picture")
async def upload_profile_picture(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Upload and update profile picture"""
    try:
        filename = save_profile_picture(file, current_user.id)
        user = crud.update_profile_picture(db, current_user.id, filename)
        return {"message": "Profile picture updated successfully", "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/users/me/profile-picture")
async def delete_profile_picture(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Delete user's profile picture"""
    try:
        user = crud.update_profile_picture(db, current_user.id, "default_avatar.png")
        return {"message": "Profile picture removed successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/uploads/profile_pictures/{filename}")
async def get_profile_picture(filename: str):
    """Serve profile picture files"""
    file_path = os.path.join("uploads/profile_pictures", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        return FileResponse("static/images/default_avatar.svg")

# ===== API ROUTES =====
@app.post("/api/register")
async def register(request: Request, db: Session = Depends(get_db)):
    try:
        form_data = await request.form()
        logger.info(f"📝 Registration attempt for: {form_data.get('email')}")
        
        user_data = schemas.UserCreate(
            email=form_data.get("email"),
            full_name=form_data.get("full_name"),
            password=form_data.get("password"),
            role=form_data.get("role"),
            phone=form_data.get("phone", None),
            department=form_data.get("department", None)
        )
        
        db_user = crud.get_user_by_email(db, email=user_data.email)
        if db_user:
            return RedirectResponse("/register?error=Email+already+registered", status_code=302)
        
        user = crud.create_user(db=db, user=user_data)
        return RedirectResponse("/login?message=Registration+successful", status_code=302)
        
    except Exception as e:
        logger.error(f"💥 Registration error: {e}")
        return RedirectResponse("/register?error=Registration+failed", status_code=302)

@app.get("/api/users/me")
def read_users_me(current_user: models.User = Depends(get_current_active_user)):
    return current_user

@app.get("/api/users/me/profile", response_model=schemas.UserProfile)
def get_my_profile(current_user: models.User = Depends(get_current_active_user)):
    """Get current user's profile"""
    return current_user

@app.put("/api/users/me/profile", response_model=schemas.UserProfile)
def update_my_profile(
    profile_update: schemas.UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Update current user's profile"""
    return crud.update_user_profile(db, current_user.id, profile_update)

# ===== INTERNSHIP API ROUTES =====
@app.post("/api/admin/internships")
async def create_internship_admin(
    request: Request,
    db: Session = Depends(get_db)
):
    """Create internship"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "admin":
            return {"success": False, "error": "Not enough permissions"}
        
        form_data = await request.form()
        logger.info(f"CREATE INTERNSHIP: {dict(form_data)}")
        
        internship = models.Internship(
            title=form_data.get('title', 'New Internship'),
            company=form_data.get('company', 'Unknown Company'),
            description=form_data.get('description', ''),
            location=form_data.get('location'),
            duration=form_data.get('duration'),
            stipend=form_data.get('stipend'),
            requirements=form_data.get('requirements'),
            created_by=user.id
        )
        
        db.add(internship)
        db.commit()
        db.refresh(internship)
        
        return {"success": True, "message": "Internship created successfully", "internship_id": internship.id}
        
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}

@app.put("/api/admin/internships/{internship_id}")
async def update_internship_admin(
    internship_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Update internship"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "admin":
            return {"success": False, "error": "Not enough permissions"}
        
        form_data = await request.form()
        logger.info(f"UPDATE INTERNSHIP {internship_id}: {dict(form_data)}")
        
        internship = db.query(models.Internship).filter(models.Internship.id == internship_id).first()
        if not internship:
            return {"success": False, "error": "Internship not found"}
        
        # Update fields
        for field in ['title', 'company', 'description', 'location', 'duration', 'stipend', 'requirements']:
            if field in form_data:
                setattr(internship, field, form_data[field])
        
        db.commit()
        return {"success": True, "message": "Internship updated successfully"}
        
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}

@app.delete("/api/admin/internships/{internship_id}")
async def delete_internship_admin(
    internship_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Delete internship"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "admin":
            return {"success": False, "error": "Not enough permissions"}
        
        logger.info(f"DELETE INTERNSHIP {internship_id}")
        
        internship = db.query(models.Internship).filter(models.Internship.id == internship_id).first()
        if not internship:
            return {"success": False, "error": "Internship not found"}
        
        # Delete related applications first
        db.query(models.InternshipApplication).filter(
            models.InternshipApplication.internship_id == internship_id
        ).delete()
        
        # Delete related tasks
        db.query(models.Task).filter(models.Task.internship_id == internship_id).delete()
        
        db.delete(internship)
        db.commit()
        
        return {"success": True, "message": "Internship deleted successfully"}
        
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}

@app.get("/api/internships")
def read_internships(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all internships (public)"""
    internships = crud.get_internships(db, skip=skip, limit=limit)
    return internships

# ===== APPLICATION API ROUTES =====
@app.post("/api/applications")
async def create_application(
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db)
):
    """Create internship application"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "student":
            return {"success": False, "error": "Only students can apply for internships"}
        
        form_data = await request.form()
        internship_id = form_data.get("internship_id")
        cover_letter = form_data.get("cover_letter", "")
        
        if not internship_id:
            return {"success": False, "error": "Internship ID is required"}
        
        # Check if already applied
        existing_application = db.query(models.InternshipApplication).filter(
            models.InternshipApplication.student_id == user.id,
            models.InternshipApplication.internship_id == internship_id
        ).first()
        
        if existing_application:
            return {"success": False, "error": "You have already applied for this internship"}
        
        application = models.InternshipApplication(
            student_id=user.id,
            internship_id=int(internship_id),
            cover_letter=cover_letter,
            status="pending"
        )
        
        db.add(application)
        db.commit()
        db.refresh(application)
        
        # Send email notifications
        background_tasks.add_task(send_application_submitted_email, db, user.id, internship_id)
        
        return {"success": True, "message": "Application submitted successfully"}
        
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}

# ===== ADMIN API ROUTES =====
@app.get("/api/admin/users", response_model=List[schemas.UserList])
async def get_all_users_api(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all users (admin only)"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Not enough permissions")
        
        return crud.get_all_users(db, skip=skip, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Not authenticated")

@app.delete("/api/admin/users/{user_id}")
async def delete_user_admin(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Delete user (admin only)"""
    try:
        current_user = await get_current_user_from_cookie(request, db)
        
        if current_user.role != "admin":
            return {"success": False, "error": "Not enough permissions"}
        
        if user_id == current_user.id:
            return {"success": False, "error": "Cannot delete your own account"}
        
        logger.info(f"🗑️ Attempting to delete user ID: {user_id}")
        
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}
        
        # Delete related records first
        db.query(models.InternshipApplication).filter(
            models.InternshipApplication.student_id == user_id
        ).delete()
        
        db.query(models.Task).filter(models.Task.student_id == user_id).delete()
        db.query(models.Task).filter(models.Task.assigned_by == user_id).delete()
        
        # Delete internships created by user
        internships = db.query(models.Internship).filter(models.Internship.created_by == user_id).all()
        for internship in internships:
            db.query(models.InternshipApplication).filter(
                models.InternshipApplication.internship_id == internship.id
            ).delete()
            db.query(models.Task).filter(models.Task.internship_id == internship.id).delete()
            db.delete(internship)
        
        # Finally delete the user
        db.delete(user)
        db.commit()
        
        logger.info(f"✅ Successfully deleted user: {user.email}")
        return {"success": True, "message": "User deleted successfully"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error deleting user: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/admin/stats", response_model=schemas.SystemStats)
async def get_system_stats_api(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get system statistics (admin only)"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Not enough permissions")
        
        return crud.get_system_stats(db)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Not authenticated")

# ===== DASHBOARD API ROUTES =====
@app.get("/api/admin/dashboard")
async def get_admin_dashboard_data(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get admin dashboard data"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        
        stats = crud.get_system_stats(db)
        
        # Get application status distribution
        application_status = db.query(
            models.InternshipApplication.status,
            models.func.count(models.InternshipApplication.id)
        ).group_by(models.InternshipApplication.status).all()
        
        # Get user distribution by role
        user_distribution = db.query(
            models.User.role,
            models.func.count(models.User.id)
        ).group_by(models.User.role).all()
        
        return {
            "stats": {
                "total_users": stats.total_users,
                "total_students": stats.total_students,
                "total_internships": stats.total_internships,
                "total_applications": stats.total_applications
            },
            "charts": {
                "application_status": {
                    "labels": [status[0] for status in application_status],
                    "data": [status[1] for status in application_status]
                },
                "user_distribution": {
                    "labels": [role[0] for role in user_distribution],
                    "data": [role[1] for role in user_distribution]
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting admin dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/student/dashboard")
async def get_student_dashboard_data(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get student dashboard data"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "student":
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get student's applications
        applications = crud.get_applications_by_student(db, user.id)
        
        # Get student's tasks
        tasks = crud.get_tasks_by_student(db, user.id)
        
        # Get available internships
        internships = crud.get_internships(db)
        
        # Calculate progress
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.status == "completed"])
        overall_progress = round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1)
        
        return {
            "user": {
                "full_name": user.full_name,
                "email": user.email
            },
            "stats": {
                "total_applications": len(applications),
                "completed_tasks": completed_tasks,
                "available_internships": len(internships),
                "progress_rate": overall_progress
            },
            "applications": [
                {
                    "id": app.id,
                    "internship_title": app.internship.title if app.internship else "Unknown",
                    "company": app.internship.company if app.internship else "Unknown",
                    "status": app.status,
                    "application_date": app.application_date.isoformat(),
                    "feedback": None
                }
                for app in applications
            ],
            "tasks": [
                {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "status": task.status,
                    "progress": task.progress or 0,
                    "due_date": task.due_date.isoformat() if task.due_date else None
                }
                for task in tasks
            ],
            "internships": [
                {
                    "id": internship.id,
                    "title": internship.title,
                    "company": internship.company,
                    "description": internship.description,
                    "location": internship.location,
                    "duration": internship.duration
                }
                for internship in internships[:5]  # Limit to 5 internships
            ],
            "feedback": []
        }
        
    except Exception as e:
        logger.error(f"Error getting student dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== DEBUG & TEST ROUTES =====
@app.get("/api/test")
def test_endpoint():
    return {"message": "Internship Management System is working!"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "Server is running"}

@app.get("/api/debug/user")
async def debug_user(request: Request, db: Session = Depends(get_db)):
    """Debug endpoint to check user authentication"""
    try:
        user = await get_current_user_from_cookie(request, db)
        return {
            "user_id": user.id,
            "email": user.email,
            "role": user.role,
            "name": user.full_name,
            "authenticated": True
        }
    except Exception as e:
        return {"error": str(e), "authenticated": False}

# Mount static files for images
app.mount("/images", StaticFiles(directory="static/images"), name="images")

# ===== STARTUP EVENT =====
@app.on_event("startup")
async def startup_event():
    """Start background tasks on startup"""
    asyncio.create_task(start_background_tasks())
    logger.info("🚀 Email notification system started!")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Internship Management System with Email Notifications...")
    print("📧 Email notifications: " + ("ENABLED" if email_service.enabled else "DISABLED - configure SMTP settings"))
    print("📊 Access the application at: http://localhost:8000")
    print("📚 API documentation at: http://localhost:8000/docs")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)