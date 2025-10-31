# email_config.py
import os
from dotenv import load_dotenv

load_dotenv()

class EmailConfig:
    # Use App Password instead of regular Gmail password
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    EMAIL_USERNAME = os.getenv("EMAIL_USERNAME", "your-email@gmail.com")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "your-app-password")  # Use App Password!
    FROM_EMAIL = os.getenv("FROM_EMAIL", "your-email@gmail.com")
    
    @classmethod
    def is_configured(cls):
        return all([cls.EMAIL_USERNAME, cls.EMAIL_PASSWORD, cls.FROM_EMAIL])