from fastapi import FastAPI, Depends, HTTPException, Request, Form, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from typing import List
import models
import schemas
from auth import get_current_active_user, create_access_token, get_current_user_from_cookie
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

# ===== EMAIL NOTIFICATION SYSTEM =====

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.sender_email = os.getenv("SENDER_EMAIL", "your-email@gmail.com")
        self.sender_password = os.getenv("SENDER_PASSWORD", "your-app-password")
        self.enabled = bool(self.sender_email and self.sender_password)
    
    def send_email(self, to_email: str, subject: str, html_content: str):
        """Send email synchronously"""
        if not self.enabled:
            print(f"📧 Email disabled - would send to {to_email}: {subject}")
            return
        
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
            
            print(f"✅ Email sent to {to_email}: {subject}")
            
        except Exception as e:
            print(f"❌ Failed to send email to {to_email}: {str(e)}")
    
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
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: {'#4CAF50' if status == 'approved' else '#f44336' if status == 'rejected' else '#ff9800'}; color: white; padding: 20px; text-align: center; }}
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
    
    @staticmethod
    def new_application(mentor_name: str, student_name: str, internship_title: str):
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #9C27B0; color: white; padding: 20px; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>New Application Received</h1>
                </div>
                <div class="content">
                    <h2>Hello {mentor_name},</h2>
                    <p>You have a new application for <strong>{internship_title}</strong> from <strong>{student_name}</strong>.</p>
                </div>
            </div>
        </body>
        </html>
        """

async def send_application_submitted_email(db: Session, student_id: int, internship_id: int):
    """Send email when student submits application"""
    student = db.query(models.User).filter(models.User.id == student_id).first()
    internship = db.query(models.Internship).filter(models.Internship.id == internship_id).first()
    
    if student and internship:
        subject = f"Application Submitted - {internship.title}"
        html_content = EmailTemplates.application_submitted(student.full_name, internship.title)
        await email_service.send_email_async(student.email, subject, html_content)

async def send_application_status_email(db: Session, application_id: int, new_status: str, notes: str = ""):
    """Send email when application status changes"""
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

async def send_task_assignment_email(db: Session, task_id: int):
    """Send email when task is assigned to student"""
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

async def send_new_application_notification(db: Session, application_id: int):
    """Send email to mentor when new application is received"""
    application = db.query(models.InternshipApplication)\
        .join(models.Internship, models.InternshipApplication.internship_id == models.Internship.id)\
        .join(models.User, models.Internship.created_by == models.User.id)\
        .join(models.User, models.InternshipApplication.student_id == models.User.id)\
        .filter(models.InternshipApplication.id == application_id)\
        .first()
    
    if application and application.internship.created_by_user:
        subject = f"New Application - {application.internship.title}"
        html_content = EmailTemplates.new_application(
            application.internship.created_by_user.full_name,
            application.student.full_name,
            application.internship.title
        )
        await email_service.send_email_async(
            application.internship.created_by_user.email, 
            subject, 
            html_content
        )

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
                print(f"📧 Sent deadline reminder for task '{task.title}'")
                
    except Exception as e:
        print(f"❌ Error in deadline reminder: {e}")
    finally:
        db.close()

async def start_background_tasks():
    """Start background tasks"""
    while True:
        try:
            await check_deadlines_and_send_reminders()
        except Exception as e:
            print(f"❌ Background task error: {e}")
        await asyncio.sleep(3600)  # Check every hour

# ===== END EMAIL NOTIFICATION SYSTEM =====

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Internship Management System")

# Create directories if they don't exist
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)
os.makedirs("uploads/profile_pictures", exist_ok=True)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
templates = Jinja2Templates(directory="templates")

# ===== AUTHENTICATION ROUTES =====
@app.post("/api/login")
async def login(request: Request, db: Session = Depends(get_db)):
    form_data = await request.form()
    email = form_data.get("email")
    password = form_data.get("password")
    
    user = crud.authenticate_user(db, email, password)
    if not user:
        return RedirectResponse("/login?error=Invalid credentials", status_code=302)
    
    access_token = create_access_token(data={"sub": user.email})
    response = RedirectResponse("/dashboard", status_code=302)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response

@app.get("/logout")
async def logout():
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
    try:
        user = await get_current_user_from_cookie(request, db)
        
        print(f"🎯 Dashboard access - User: {user.email}, Role: {user.role}")
        
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
                print(f"⚠️  Could not get system stats: {e}")
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
            print(f"❌ Unknown role: {user.role}")
            return RedirectResponse("/login?error=Unknown user role")
            
    except Exception as e:
        print(f"💥 Dashboard error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse("/login")

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: Session = Depends(get_db)):
    try:
        user = await get_current_user_from_cookie(request, db)
        return templates.TemplateResponse("profile.html", {
            "request": request,
            "user": user
        })
    except Exception as e:
        print(f"Profile page error: {e}")
        return RedirectResponse("/login")

# ===== ADMIN MANAGEMENT ROUTES =====
@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(request: Request, db: Session = Depends(get_db)):
    """Admin users management page"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "admin":
            return RedirectResponse("/dashboard?error=Access denied")
        
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
            return RedirectResponse("/dashboard?error=Access denied")
        
        internships = db.query(models.Internship).all()
        stats = crud.get_system_stats(db)
        
        return templates.TemplateResponse("admin_internships.html", {
            "request": request,
            "user": user,
            "internships": internships,
            "stats": stats
        })
    except Exception as e:
        print(f"Admin internships page error: {e}")
        return RedirectResponse("/login")

@app.get("/admin/system", response_class=HTMLResponse)
async def admin_system_page(request: Request, db: Session = Depends(get_db)):
    """Admin system management page"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "admin":
            return RedirectResponse("/dashboard?error=Access denied")
        
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
            return RedirectResponse("/dashboard?error=Access denied")
        
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
        print(f"Admin applications page error: {e}")
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
        
        print(f"📝 Application {application_id} status changed from {old_status} to {new_status}")
        print(f"📝 Student: {application.student.email}, Internship: {application.internship.title}")
        print(f"📝 Admin Notes: {admin_notes}")
        
        return {
            "success": True, 
            "message": f"Application {new_status} successfully", 
            "student_email": application.student.email
        }
        
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}

@app.get("/api/admin/applications")
async def get_applications_admin(
    request: Request,
    status: str = None,
    db: Session = Depends(get_db)
):
    """Get applications for admin review (API endpoint)"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "admin":
            return {"success": False, "error": "Access denied"}
        
        query = db.query(models.InternshipApplication)\
            .join(models.User, models.InternshipApplication.student_id == models.User.id)\
            .join(models.Internship, models.InternshipApplication.internship_id == models.Internship.id)\
            .options(
                joinedload(models.InternshipApplication.student),
                joinedload(models.InternshipApplication.internship)
            )
        
        # Filter by status if provided
        if status and status in ["pending", "approved", "rejected"]:
            query = query.filter(models.InternshipApplication.status == status)
        
        applications = query.order_by(models.InternshipApplication.application_date.desc()).all()
        
        # Convert to JSON-serializable format
        applications_data = []
        for app in applications:
            applications_data.append({
                "id": app.id,
                "application_date": app.application_date.isoformat(),
                "status": app.status,
                "cover_letter": app.cover_letter,
                "student": {
                    "id": app.student.id,
                    "full_name": app.student.full_name,
                    "email": app.student.email,
                    "department": app.student.department
                },
                "internship": {
                    "id": app.internship.id,
                    "title": app.internship.title,
                    "company": app.internship.company,
                    "location": app.internship.location
                }
            })
        
        return {"success": True, "applications": applications_data}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

# ===== MENTOR ROUTES =====
@app.get("/mentor/internships", response_class=HTMLResponse)
async def mentor_internships_page(request: Request, db: Session = Depends(get_db)):
    """Mentor internships management page"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "mentor":
            return RedirectResponse("/dashboard?error=Access denied")
        
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
            return RedirectResponse("/dashboard?error=Access denied")
        
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
            return RedirectResponse("/dashboard?error=Access denied")
        
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
            return RedirectResponse("/dashboard?error=Access denied")
        
        applications = crud.get_student_applications_with_details(db, user.id)
        return templates.TemplateResponse("my_applications.html", {
            "request": request,
            "user": user,
            "applications": applications
        })
    except Exception as e:
        return RedirectResponse("/login")

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
        print(f"📝 Registration attempt for: {form_data.get('email')}")
        
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
            return RedirectResponse("/register?error=Email already registered", status_code=302)
        
        user = crud.create_user(db=db, user=user_data)
        return RedirectResponse("/login?message=Registration successful", status_code=302)
        
    except Exception as e:
        print(f"💥 Registration error: {e}")
        return RedirectResponse("/register?error=Registration failed: " + str(e), status_code=302)

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
    """Create internship - FIXED WITH COOKIE AUTH"""
    try:
        # Get user from cookie instead of Bearer token
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "admin":
            return {"success": False, "error": "Not enough permissions"}
        
        form_data = await request.form()
        print(f"CREATE INTERNSHIP: {dict(form_data)}")
        
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
    """Update internship - FIXED WITH COOKIE AUTH"""
    try:
        # Get user from cookie instead of Bearer token
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "admin":
            return {"success": False, "error": "Not enough permissions"}
        
        form_data = await request.form()
        print(f"UPDATE INTERNSHIP {internship_id}: {dict(form_data)}")
        
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
    """Delete internship - FIXED WITH COOKIE AUTH"""
    try:
        # Get user from cookie instead of Bearer token
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "admin":
            return {"success": False, "error": "Not enough permissions"}
        
        print(f"DELETE INTERNSHIP {internship_id}")
        
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
    """Create internship application - FIXED WITH COOKIE AUTH"""
    try:
        # Get user from cookie instead of Bearer token
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
        background_tasks.add_task(send_new_application_notification, db, application.id)
        
        return {"success": True, "message": "Application submitted successfully"}
        
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}

@app.delete("/api/applications/{application_id}")
async def delete_application(
    application_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Withdraw application (student only) - FIXED WITH COOKIE AUTH"""
    try:
        # Get user from cookie instead of Bearer token
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "student":
            return {"success": False, "error": "Only students can withdraw applications"}
        
        application = db.query(models.InternshipApplication).filter(
            models.InternshipApplication.id == application_id,
            models.InternshipApplication.student_id == user.id
        ).first()
        
        if not application:
            return {"success": False, "error": "Application not found"}
        
        db.delete(application)
        db.commit()
        
        return {"success": True, "message": "Application withdrawn successfully"}
        
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}

# ===== MENTOR APPLICATION APPROVAL ROUTES =====
@app.put("/api/mentor/applications/{application_id}")
async def update_application_status(
    background_tasks: BackgroundTasks,
    application_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Mentor updates application status"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "mentor":
            return {"success": False, "error": "Only mentors can update application status"}
        
        form_data = await request.form()
        new_status = form_data.get("status")
        mentor_notes = form_data.get("mentor_notes", "")
        
        if new_status not in ["approved", "rejected"]:
            return {"success": False, "error": "Invalid status"}
        
        # Check if application belongs to mentor's internship
        application = db.query(models.InternshipApplication)\
            .join(models.Internship, models.InternshipApplication.internship_id == models.Internship.id)\
            .filter(
                models.InternshipApplication.id == application_id,
                models.Internship.created_by == user.id
            )\
            .first()
        
        if not application:
            return {"success": False, "error": "Application not found or access denied"}
        
        application.status = new_status
        db.commit()
        db.refresh(application)
        
        # Send email notification
        background_tasks.add_task(send_application_status_email, db, application_id, new_status, mentor_notes)
        
        return {"success": True, "message": f"Application {new_status} successfully"}
        
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}

# ===== FEEDBACK API ROUTES =====
@app.post("/api/feedback")
async def create_feedback(
    request: Request,
    db: Session = Depends(get_db)
):
    """Create feedback (mentor only)"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "mentor":
            return {"success": False, "error": "Only mentors can provide feedback"}
        
        form_data = await request.form()
        
        feedback = models.Feedback(
            student_id=form_data.get('student_id'),
            mentor_id=user.id,
            internship_id=form_data.get('internship_id'),
            rating=form_data.get('rating'),
            comments=form_data.get('comments', '')
        )
        
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        
        return {"success": True, "message": "Feedback submitted successfully"}
        
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}

@app.get("/api/feedback/student/{student_id}")
async def get_student_feedback(
    student_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Get feedback for a student"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        # Students can only see their own feedback, mentors/admins can see all
        if user.role == "student" and user.id != student_id:
            return {"success": False, "error": "Access denied"}
        
        feedback = db.query(models.Feedback)\
            .filter(models.Feedback.student_id == student_id)\
            .all()
        
        return {"success": True, "feedback": feedback}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

# ===== TASK PROGRESS ROUTES =====
@app.put("/api/tasks/{task_id}/progress")
async def update_task_progress(
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
        
        task = crud.update_task_progress(db, task_id, progress, user.id)
        if not task:
            return {"success": False, "error": "Task not found or access denied"}
        
        return {"success": True, "message": "Progress updated successfully"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

# ===== REPORT GENERATION ROUTES =====
@app.post("/api/reports/generate")
async def generate_report(
    request: Request,
    db: Session = Depends(get_db)
):
    """Generate reports (admin/mentor only)"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role not in ["admin", "mentor"]:
            return {"success": False, "error": "Access denied"}
        
        form_data = await request.form()
        report_type = form_data.get('report_type')
        target_id = form_data.get('target_id')
        format_type = form_data.get('format', 'pdf')
        
        from report_generator import generate_internship_report_pdf, generate_student_report_excel
        
        if report_type == 'internship' and target_id:
            if format_type == 'pdf':
                filename = generate_internship_report_pdf(db, int(target_id))
            else:
                filename = generate_student_report_excel(db, int(target_id))
        elif report_type == 'student' and target_id:
            filename = generate_student_report_excel(db, int(target_id))
        else:
            return {"success": False, "error": "Invalid report type or target"}
        
        if filename:
            return {
                "success": True, 
                "message": "Report generated successfully", 
                "filename": filename,
                "download_url": f"/static/reports/{filename}"
            }
        else:
            return {"success": False, "error": "Failed to generate report"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/static/reports/{filename}")
async def download_report(filename: str):
    """Download generated reports"""
    file_path = os.path.join("static/reports", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    else:
        raise HTTPException(status_code=404, detail="File not found")

# ===== ADMIN API ROUTES - FIXED WITH COOKIE AUTH =====
@app.get("/api/admin/users", response_model=List[schemas.UserList])
async def get_all_users_api(
    request: Request,  # Add request parameter
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all users (admin only) - FIXED WITH COOKIE AUTH"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Not enough permissions")
        
        return crud.get_all_users(db, skip=skip, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Not authenticated")

@app.get("/api/admin/users/{user_id}", response_model=schemas.UserList)
async def get_user_admin(
    user_id: int,
    request: Request,  # Add request parameter
    db: Session = Depends(get_db)
):
    """Get user by ID (admin only) - FIXED WITH COOKIE AUTH"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Not enough permissions")
        
        user_data = crud.get_user_by_id(db, user_id)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        return user_data
    except Exception as e:
        raise HTTPException(status_code=401, detail="Not authenticated")

@app.put("/api/admin/users/{user_id}", response_model=schemas.UserList)
async def update_user_admin(
    user_id: int,
    request: Request,  # Add request parameter
    db: Session = Depends(get_db)
):
    """Update user (admin only) - FIXED WITH COOKIE AUTH"""
    try:
        current_user = await get_current_user_from_cookie(request, db)
        
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Not enough permissions")
        
        # Get the update data from request body
        update_data = await request.json()
        
        user = crud.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update user fields
        for field, value in update_data.items():
            if hasattr(user, field) and field not in ['id', 'email', 'created_at']:
                setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        
        return user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/admin/users/{user_id}")
async def delete_user_admin(
    user_id: int,
    request: Request,  # Add request parameter
    db: Session = Depends(get_db)
):
    """Delete user (admin only) - FIXED WITH COOKIE AUTH"""
    try:
        current_user = await get_current_user_from_cookie(request, db)
        
        if current_user.role != "admin":
            return {"success": False, "error": "Not enough permissions"}
        
        if user_id == current_user.id:
            return {"success": False, "error": "Cannot delete your own account"}
        
        print(f"🗑️ Attempting to delete user ID: {user_id}")
        
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}
        
        # Delete related records first to maintain referential integrity
        # Delete applications
        db.query(models.InternshipApplication).filter(
            models.InternshipApplication.student_id == user_id
        ).delete()
        
        # Delete tasks where user is student
        db.query(models.Task).filter(models.Task.student_id == user_id).delete()
        
        # Delete tasks where user is assigner
        db.query(models.Task).filter(models.Task.assigned_by == user_id).delete()
        
        # Delete feedback
        db.query(models.Feedback).filter(
            (models.Feedback.student_id == user_id) | 
            (models.Feedback.mentor_id == user_id)
        ).delete()
        
        # Delete internships created by user
        internships = db.query(models.Internship).filter(models.Internship.created_by == user_id).all()
        for internship in internships:
            # Delete applications for these internships
            db.query(models.InternshipApplication).filter(
                models.InternshipApplication.internship_id == internship.id
            ).delete()
            # Delete tasks for these internships
            db.query(models.Task).filter(models.Task.internship_id == internship.id).delete()
            db.delete(internship)
        
        # Finally delete the user
        db.delete(user)
        db.commit()
        
        print(f"✅ Successfully deleted user: {user.email}")
        return {"success": True, "message": "User deleted successfully"}
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error deleting user: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/admin/stats", response_model=schemas.SystemStats)
async def get_system_stats_api(
    request: Request,  # Add request parameter
    db: Session = Depends(get_db)
):
    """Get system statistics (admin only) - FIXED WITH COOKIE AUTH"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Not enough permissions")
        
        return crud.get_system_stats(db)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Not authenticated")

# ===== ADMIN SEARCH & UTILITY ROUTES =====
@app.get("/api/admin/search/users")
async def search_users(
    request: Request,
    query: str,
    db: Session = Depends(get_db)
):
    """Search users by name or email"""
    try:
        user = await get_current_user_from_cookie(request, db)
        if user.role != "admin":
            return {"success": False, "error": "Access denied"}
        
        users = db.query(models.User).filter(
            (models.User.full_name.ilike(f"%{query}%")) | 
            (models.User.email.ilike(f"%{query}%"))
        ).all()
        
        return users
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/admin/activity")
async def get_recent_activity(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get recent system activity"""
    try:
        user = await get_current_user_from_cookie(request, db)
        if user.role != "admin":
            return {"success": False, "error": "Access denied"}
        
        # Get recent users (last 5)
        recent_users = db.query(models.User).order_by(models.User.created_at.desc()).limit(5).all()
        
        # Get recent applications (last 5)
        recent_applications = db.query(models.InternshipApplication)\
            .order_by(models.InternshipApplication.application_date.desc())\
            .limit(5).all()
        
        # Get recent internships (last 5)
        recent_internships = db.query(models.Internship)\
            .order_by(models.Internship.created_at.desc())\
            .limit(5).all()
        
        return {
            "recent_users": recent_users,
            "recent_applications": recent_applications,
            "recent_internships": recent_internships
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

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

@app.get("/api/debug/internships")
def debug_internships(db: Session = Depends(get_db)):
    """Debug endpoint to check internships"""
    internships = db.query(models.Internship).all()
    return {
        "total_internships": len(internships),
        "internships": [
            {
                "id": i.id,
                "title": i.title,
                "company": i.company,
                "created_by": i.created_by
            }
            for i in internships
        ]
    }

# Mount static files for images
app.mount("/images", StaticFiles(directory="static/images"), name="images")

# ===== ADMIN DASHBOARD ROUTE =====
@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard_page(request: Request, db: Session = Depends(get_db)):
    """Admin dashboard page"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role != "admin":
            return RedirectResponse("/dashboard?error=Access denied")
        
        # Get statistics
        try:
            stats = crud.get_system_stats(db)
        except Exception as e:
            print(f"⚠️  Could not get system stats: {e}")
            stats = {
                "total_users": 0,
                "total_students": 0,
                "total_admins": 0,
                "total_mentors": 0,
                "total_internships": 0,
                "total_applications": 0,
                "total_tasks": 0
            }
        
        # Get internships for the admin
        internships = crud.get_internships(db)
        
        return templates.TemplateResponse("dashboard_admin.html", {
            "request": request,
            "user": user,
            "stats": stats,
            "internships": internships
        })
        
    except Exception as e:
        print(f"Admin dashboard error: {e}")
        return RedirectResponse("/login")

# ===== TASK MANAGEMENT ROUTES =====

@app.get("/tasks")
async def tasks_page(request: Request, db: Session = Depends(get_db)):
    """Tasks page for students"""
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
            students = crud.get_all_users(db)
            internships = crud.get_internships(db)
            return templates.TemplateResponse("tasks_management.html", {
                "request": request,
                "user": user,
                "tasks": tasks,
                "students": students,
                "internships": internships
            })
        else:
            return RedirectResponse("/dashboard?error=Access denied")
            
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
                from datetime import datetime
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
            except ValueError:
                return {"success": False, "error": "Invalid date format. Use YYYY-MM-DD"}
        
        # Convert string IDs to integers (they come as strings from form)
        internship_id = form_data.get('internship_id')
        student_id = form_data.get('student_id')
        
        task = models.Task(
            title=form_data.get('title'),
            description=form_data.get('description'),
            internship_id=int(internship_id) if internship_id else None,
            student_id=int(student_id) if student_id else None,
            assigned_by=user.id,
            due_date=due_date,
            status=models.TaskStatus.PENDING,  # Use Enum instead of string
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
        print(f"❌ Error creating task: {e}")
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

@app.put("/api/tasks/{task_id}/status")
async def update_task_status_api(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Update task status (admin/mentor only)"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role not in ["admin", "mentor"]:
            return {"success": False, "error": "Access denied"}
        
        form_data = await request.form()
        new_status = form_data.get('status')
        
        if new_status not in ["pending", "in_progress", "completed", "cancelled"]:
            return {"success": False, "error": "Invalid status"}
        
        task = db.query(models.Task).filter(models.Task.id == task_id).first()
        if not task:
            return {"success": False, "error": "Task not found"}
        
        task.status = new_status
        db.commit()
        
        return {"success": True, "message": "Task status updated successfully"}
        
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}

@app.get("/api/tasks/student/{student_id}")
async def get_student_tasks_api(
    student_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Get tasks for a specific student"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        # Students can only see their own tasks, admins/mentors can see all
        if user.role == "student" and user.id != student_id:
            return {"success": False, "error": "Access denied"}
        
        tasks = crud.get_tasks_by_student(db, student_id)
        return {"success": True, "tasks": tasks}
        
    except Exception as e:
        return {"success": False, "error": str(e)}
    
# ===== DEBUG ROUTES =====
@app.get("/debug/current-user")
async def debug_current_user(request: Request, db: Session = Depends(get_db)):
    """Debug endpoint to check current user"""
    try:
        user = await get_current_user_from_cookie(request, db)
        return {
            "user_id": user.id,
            "email": user.email,
            "role": user.role,
            "authenticated": True
        }
    except Exception as e:
        return {"authenticated": False, "error": str(e)}

@app.get("/debug/students")
async def debug_students(db: Session = Depends(get_db)):
    """Debug endpoint to check available students"""
    students = db.query(models.User).filter(models.User.role == "student").all()
    return {
        "total_students": len(students),
        "students": [{"id": s.id, "name": s.full_name, "email": s.email} for s in students]
    }

@app.get("/debug/tasks")
async def debug_tasks(db: Session = Depends(get_db)):
    """Debug endpoint to check tasks"""
    tasks = db.query(models.Task).all()
    return {
        "total_tasks": len(tasks),
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "student_id": t.student_id,
                "status": t.status,
                "progress": t.progress
            } for t in tasks
        ]
    }

@app.get("/debug/test-task-creation")
async def debug_test_task_creation(request: Request, db: Session = Depends(get_db)):
    """Test task creation manually"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        if user.role not in ["admin", "mentor"]:
            return {"success": False, "error": "Not authorized"}
        
        # Create a test task
        task = models.Task(
            title="Test Task - Debug",
            description="This is a test task created via debug",
            student_id=2,  # Change this to an actual student ID
            assigned_by=user.id,
            status=models.TaskStatus.PENDING,
            progress=0
        )
        
        db.add(task)
        db.commit()
        db.refresh(task)
        
        return {"success": True, "message": "Test task created", "task_id": task.id}
        
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}

# ===== EMAIL NOTIFICATION TEST ROUTES =====
@app.post("/api/notifications/send-test-email")
async def send_test_email(
    request: Request,
    db: Session = Depends(get_db)
):
    """Send test email to verify email configuration"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        subject = "Test Email - Internship Management System"
        html_content = f"""
        <html>
        <body>
            <h2>Hello {user.full_name},</h2>
            <p>This is a test email to verify that your email notification system is working correctly.</p>
            <p>If you received this email, everything is configured properly! ✅</p>
        </body>
        </html>
        """
        
        await email_service.send_email_async(user.email, subject, html_content)
        
        return {"success": True, "message": "Test email sent successfully"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/notifications/email-status")
async def get_email_status():
    """Check email service status"""
    return {
        "enabled": email_service.enabled,
        "sender_email": email_service.sender_email,
        "smtp_server": email_service.smtp_server,
        "smtp_port": email_service.smtp_port
    }

# ===== STARTUP EVENT =====
@app.on_event("startup")
async def startup_event():
    """Start background tasks on startup"""
    asyncio.create_task(start_background_tasks())
    print("🚀 Email notification system started!")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Internship Management System with Email Notifications...")
    print("📧 Email notifications: " + ("ENABLED" if email_service.enabled else "DISABLED - configure SMTP settings"))
    print("📊 Access the application at: http://localhost:8000")
    print("📚 API documentation at: http://localhost:8000/docs")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)