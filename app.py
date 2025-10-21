from fastapi import FastAPI, Depends, HTTPException, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
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
        else:
            internships = crud.get_internships(db)
            return templates.TemplateResponse("dashboard_admin.html", {
                "request": request,
                "user": user,
                "internships": internships
            })
    except Exception as e:
        print(f"Dashboard error: {e}")
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
        
        # Create UserCreate object from form data
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
        print(f"Registration error: {e}")
        return RedirectResponse("/register?error=Registration failed", status_code=302)

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

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Internship Management System...")
    print("📊 Access the application at: http://localhost:8000")
    print("📚 API documentation at: http://localhost:8000/docs")
    print("🖼️  Profile pictures are now enabled!")
    print("⏹️  Press Ctrl+C to stop the server")
    print("-" * 50)
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)