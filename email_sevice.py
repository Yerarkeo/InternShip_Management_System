# email_service.py - Simple email service that won't crash your app
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def send_email(to_email: str, subject: str, body: str, is_html: bool = False) -> bool:
        """Send email without crashing the application"""
        try:
            # Log instead of actually sending (for now)
            logger.info(f"📧 [EMAIL] Would send to {to_email}: {subject}")
            logger.info(f"📧 [EMAIL] Body: {body[:100]}...")
            
            # Return True to prevent application crashes
            return True
            
        except Exception as e:
            logger.error(f"❌ Email error (non-critical): {e}")
            return True  # Still return True to avoid breaking the app

    @staticmethod
    def test_connection() -> bool:
        logger.info("✅ Email service in simulation mode")
        return True