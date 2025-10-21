# file_utils.py
import os
import uuid
from fastapi import UploadFile, HTTPException
from config import settings

def save_profile_picture(file: UploadFile, user_id: int) -> str:
    """Save profile picture and return filename"""
    
    # Check file extension
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not allowed")
    
    # Generate unique filename
    filename = f"user_{user_id}_{uuid.uuid4().hex}{file_extension}"
    file_path = os.path.join(settings.PROFILE_PICTURES_DIR, filename)
    
    # Ensure directory exists
    os.makedirs(settings.PROFILE_PICTURES_DIR, exist_ok=True)
    
    try:
        # Read file content
        contents = file.file.read()
        if len(contents) > settings.MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(contents)
        
        return filename
        
    except Exception as e:
        # Clean up if error occurs
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Error saving file: {str(e)}")
    finally:
        file.file.close()

def delete_old_profile_picture(filename: str):
    """Delete old profile picture file"""
    if filename and filename != "default_avatar.png":
        file_path = os.path.join(settings.PROFILE_PICTURES_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)

def get_profile_picture_url(filename: str) -> str:
    """Get URL for profile picture"""
    if not filename or filename == "default_avatar.png":
        return "/static/images/default_avatar.svg"
    return f"/uploads/profile_pictures/{filename}"