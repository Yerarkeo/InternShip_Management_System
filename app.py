from fastapi import FastAPI, Depends, HTTPException, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List
import models
import schemas
from auth import get_current_active_user, create_access_token, get_current_user_from_cookie
from database import SessionLocal, engine, get_db
import crud
from password import verify_password
from file_utils import save_profile_picture, delete_old_profile_picture
import os

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
        
        applications = crud.get_applications_for_mentor(db, user.id)
        
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Create internship application"""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can apply for internships")
    
    try:
        form_data = await request.form()
        internship_id = form_data.get("internship_id")
        cover_letter = form_data.get("cover_letter", "")
        
        if not internship_id:
            raise HTTPException(status_code=400, detail="Internship ID is required")
        
        # Check if already applied
        existing_application = db.query(models.InternshipApplication).filter(
            models.InternshipApplication.student_id == current_user.id,
            models.InternshipApplication.internship_id == internship_id
        ).first()
        
        if existing_application:
            raise HTTPException(status_code=400, detail="You have already applied for this internship")
        
        application = models.InternshipApplication(
            student_id=current_user.id,
            internship_id=int(internship_id),
            cover_letter=cover_letter,
            status="pending"
        )
        
        db.add(application)
        db.commit()
        db.refresh(application)
        
        return {"success": True, "message": "Application submitted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/applications/{application_id}")
def delete_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Withdraw application (student only)"""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can withdraw applications")
    
    application = db.query(models.InternshipApplication).filter(
        models.InternshipApplication.id == application_id,
        models.InternshipApplication.student_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    db.delete(application)
    db.commit()
    
    return {"message": "Application withdrawn successfully"}

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
        
@app.get("/api/admin/users/{user_id}", response_model=schemas.UserList)
def get_user_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get user by ID (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.put("/api/admin/users/{user_id}", response_model=schemas.UserList)
def update_user_admin(
    user_id: int,
    user_update: schemas.UserUpdateAdmin,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Update user (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user fields
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return user

@app.delete("/api/admin/users/{user_id}")
def delete_user_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Delete user (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    user = crud.delete_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}

@app.get("/api/admin/stats", response_model=schemas.SystemStats)
def get_system_stats_api(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get system statistics (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud.get_system_stats(db)

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
# Add this to your app.py after the existing static mounts
from fastapi.staticfiles import StaticFiles

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

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Internship Management System...")
    print("📊 Access the application at: http://localhost:8000")
    print("📚 API documentation at: http://localhost:8000/docs")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)