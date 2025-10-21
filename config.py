import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./internship.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # File upload settings
    UPLOAD_DIR: str = "uploads"
    PROFILE_PICTURES_DIR: str = "uploads/profile_pictures"
    MAX_FILE_SIZE: int = 5 * 1024 * 1024  # 5MB
    ALLOWED_EXTENSIONS: set = {'.png', '.jpg', '.jpeg', '.gif', '.svg'}

settings = Settings()