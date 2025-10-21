from fastapi import FastAPI, Depends, HTTPException, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List  # ADD THIS IMPORT
import models
import schemas
from auth import get_current_active_user, create_access_token
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

# Authentication routes
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

# Frontend routes
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
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login")
    
    try:
        from auth import get_current_user
        user = await get_current_user(credentials=type('', (object,), {"credentials": token.replace("Bearer ", "")})(), db=db)
        
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
            # FIX: Ensure stats is defined and handle potential errors
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
            return templates.TemplateResponse("dashboard_mentor.html", {
                "request": request,
                "user": user,
                "internships": internships
            })
        else:
            print(f"❌ Unknown role: {user.role}")
            return RedirectResponse("/login?error=Unknown user role")
            
    except Exception as e:
        print(f"💥 Dashboard error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse("/login")

# Profile routes
@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login")
    
    try:
        from auth import get_current_user
        user = await get_current_user(credentials=type('', (object,), {"credentials": token.replace("Bearer ", "")})(), db=db)
        return templates.TemplateResponse("profile.html", {
            "request": request,
            "user": user
        })
    except Exception as e:
        return RedirectResponse("/login")

# Profile Picture Routes
@app.post("/api/users/me/profile-picture")
async def upload_profile_picture(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Upload and update profile picture"""
    try:
        # Save the uploaded file
        filename = save_profile_picture(file, current_user.id)
        
        # Update user's profile picture in database
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
        # Update user record to use default avatar
        user = crud.update_profile_picture(db, current_user.id, "default_avatar.png")
        return {"message": "Profile picture removed successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Serve profile pictures
@app.get("/uploads/profile_pictures/{filename}")
async def get_profile_picture(filename: str):
    """Serve profile picture files"""
    file_path = os.path.join("uploads/profile_pictures", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        # Return default avatar if file doesn't exist
        return FileResponse("static/images/default_avatar.svg")
    

# API Routes
@app.post("/api/register")
async def register(
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        form_data = await request.form()
        print(f"📝 Registration attempt for: {form_data.get('email')}")
        print(f"📝 Role selected: {form_data.get('role')}")
        print(f"📝 All form data: {dict(form_data)}")
        
        # Create UserCreate object from form data
        user_data = schemas.UserCreate(
            email=form_data.get("email"),
            full_name=form_data.get("full_name"),
            password=form_data.get("password"),
            role=form_data.get("role"),
            phone=form_data.get("phone", None),
            department=form_data.get("department", None)
        )
        
        print(f"🔍 User data created: {user_data}")
        print(f"🔍 User role value: {user_data.role}")
        print(f"🔍 User role type: {type(user_data.role)}")
        
        db_user = crud.get_user_by_email(db, email=user_data.email)
        
        if db_user:
            print(f"❌ User already exists: {user_data.email}")
            return RedirectResponse("/register?error=Email already registered", status_code=302)
        
        print(f"✅ Creating new user with role: {user_data.role}")
        user = crud.create_user(db=db, user=user_data)
        print(f"🎉 User created successfully: {user.id} - {user.email} - {user.role}")
        
        return RedirectResponse("/login?message=Registration successful", status_code=302)
        
    except Exception as e:
        print(f"💥 Registration error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse("/register?error=Registration failed: " + str(e), status_code=302)
    
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

@app.post("/api/internships")
def create_internship(
    internship: schemas.InternshipCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    if current_user.role not in ["admin", "mentor"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud.create_internship(db=db, internship=internship, user_id=current_user.id)

@app.get("/api/internships")
def read_internships(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    internships = crud.get_internships(db, skip=skip, limit=limit)
    return internships

@app.post("/api/applications")
def create_application(
    application: schemas.ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can apply for internships")
    return crud.create_application(db=db, application=application, student_id=current_user.id)

@app.get("/api/users/me")
def read_users_me(current_user: models.User = Depends(get_current_active_user)):
    return current_user

# Add a simple test endpoint
@app.get("/api/test")
def test_endpoint():
    return {"message": "Internship Management System is working!"}

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "Server is running"}


# Admin Management Routes
@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(request: Request, db: Session = Depends(get_db)):
    """Admin users management page"""
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login")
    
    try:
        from auth import get_current_user
        user = await get_current_user(credentials=type('', (object,), {"credentials": token.replace("Bearer ", "")})(), db=db)
        
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

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard_page(request: Request, db: Session = Depends(get_db)):
    """Admin system dashboard"""
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login")
    
    try:
        from auth import get_current_user
        user = await get_current_user(credentials=type('', (object,), {"credentials": token.replace("Bearer ", "")})(), db=db)
        
        if user.role != "admin":
            return RedirectResponse("/dashboard?error=Access denied")
        
        stats = crud.get_system_stats(db)
        recent_users = db.query(models.User).order_by(models.User.created_at.desc()).limit(5).all()
        recent_internships = db.query(models.Internship).order_by(models.Internship.created_at.desc()).limit(5).all()
        
        return templates.TemplateResponse("admin_dashboard.html", {
            "request": request,
            "user": user,
            "stats": stats,
            "recent_users": recent_users,
            "recent_internships": recent_internships
        })
    except Exception as e:
        return RedirectResponse("/login")

# Admin API Routes
@app.get("/api/admin/users", response_model=List[schemas.UserList])
def get_all_users_api(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get all users (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud.get_all_users(db, skip=skip, limit=limit)

@app.get("/api/admin/stats", response_model=schemas.SystemStats)
def get_system_stats_api(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get system statistics (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud.get_system_stats(db)

@app.get("/api/admin/users/{user_id}", response_model=schemas.UserList)
def get_user_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get any user by ID (admin only)"""
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
    """Update any user (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    user = crud.update_user_admin(db, user_id, user_update)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
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

@app.get("/api/admin/search/users")
def search_users_api(
    query: str,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Search users (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    if not query or len(query) < 2:
        raise HTTPException(status_code=400, detail="Query must be at least 2 characters")
    
    return crud.search_users(db, query, skip=skip, limit=limit)

@app.get("/api/admin/internships")
def get_all_internships_admin(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get all internships with creator info (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    internships = db.query(models.Internship).offset(skip).limit(limit).all()
    return internships

@app.get("/api/admin/applications")
def get_all_applications_admin(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get all applications with details (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    applications = db.query(models.InternshipApplication).offset(skip).limit(limit).all()
    return applications

@app.put("/api/admin/applications/{application_id}")
def update_application_status_admin(
    application_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Update application status (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    application = db.query(models.InternshipApplication).filter(
        models.InternshipApplication.id == application_id
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if status not in ["pending", "approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    application.status = status
    db.commit()
    db.refresh(application)
    
    return {"message": f"Application status updated to {status}", "application": application}

@app.delete("/api/admin/internships/{internship_id}")
def delete_internship_admin(
    internship_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Delete internship (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    internship = db.query(models.Internship).filter(models.Internship.id == internship_id).first()
    if not internship:
        raise HTTPException(status_code=404, detail="Internship not found")
    
    # Delete related applications first
    db.query(models.InternshipApplication).filter(
        models.InternshipApplication.internship_id == internship_id
    ).delete()
    
    # Delete related tasks
    db.query(models.Task).filter(models.Task.internship_id == internship_id).delete()
    
    # Delete the internship
    db.delete(internship)
    db.commit()
    
    return {"message": "Internship deleted successfully"}

@app.get("/api/admin/activity")
def get_recent_activity(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get recent system activity (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Get recent users (last 5)
    recent_users = db.query(models.User).order_by(models.User.created_at.desc()).limit(5).all()
    
    # Get recent internships (last 5)
    recent_internships = db.query(models.Internship).order_by(models.Internship.created_at.desc()).limit(5).all()
    
    # Get recent applications (last 10)
    recent_applications = db.query(models.InternshipApplication).order_by(
        models.InternshipApplication.application_date.desc()
    ).limit(10).all()
    
    return {
        "recent_users": recent_users,
        "recent_internships": recent_internships,
        "recent_applications": recent_applications
    }


# Add this route to app.py for system management page
@app.get("/admin/system", response_class=HTMLResponse)
async def admin_system_page(request: Request, db: Session = Depends(get_db)):
    """Admin system management page"""
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login")
    
    try:
        from auth import get_current_user
        user = await get_current_user(credentials=type('', (object,), {"credentials": token.replace("Bearer ", "")})(), db=db)
        
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
    
@app.get("/api/debug/user")
async def debug_user(request: Request, db: Session = Depends(get_db)):
    """Debug endpoint to check user authentication"""
    token = request.cookies.get("access_token")
    if not token:
        return {"error": "No token"}
    
    try:
        from auth import get_current_user
        user = await get_current_user(credentials=type('', (object,), {"credentials": token.replace("Bearer ", "")})(), db=db)
        return {
            "user_id": user.id,
            "email": user.email,
            "role": user.role,
            "name": user.full_name,
            "authenticated": True
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Internship Management System...")
    print("📊 Access the application at: http://localhost:8000")
    print("📚 API documentation at: http://localhost:8000/docs")
    print("🖼️  Profile pictures are now enabled!")
    print("👨‍💼 Admin panel available at: /admin/dashboard")
    print("⏹️  Press Ctrl+C to stop the server")
    print("-" * 50)
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)