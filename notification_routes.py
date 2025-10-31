from fastapi import APIRouter, Depends, Request, BackgroundTasks
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user_from_cookie
from notification_service import (
    send_application_submitted_email,
    send_application_status_email,
    send_task_assignment_email,
    send_new_application_notification
)
from email_service import email_service
from email_templates import EmailTemplates

router = APIRouter()

# ===== NOTIFICATION TEST ROUTES =====

@router.post("/api/notifications/send-test-email")
async def send_test_email(
    request: Request,
    db: Session = Depends(get_db)
):
    """Send test email to verify email configuration"""
    try:
        user = await get_current_user_from_cookie(request, db)
        
        subject = "Test Email - Internship Management System"
        html_content = EmailTemplates.system_notification(
            user.full_name,
            "Test Email Successful",
            "This is a test email to verify that your email notification system is working correctly."
        )
        
        await email_service.send_email_async(user.email, subject, html_content)
        
        return {"success": True, "message": "Test email sent successfully"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/api/notifications/email-status")
async def get_email_status():
    """Check email service status"""
    return {
        "enabled": email_service.enabled,
        "sender_email": email_service.sender_email,
        "smtp_server": email_service.smtp_server,
        "smtp_port": email_service.smtp_port
    }

# ===== NOTIFICATION WRAPPER FUNCTIONS =====

async def notify_application_submitted(db: Session, student_id: int, internship_id: int):
    """Wrapper for application submission notification"""
    await send_application_submitted_email(db, student_id, internship_id)

async def notify_application_status_change(db: Session, application_id: int, new_status: str, notes: str = ""):
    """Wrapper for application status change notification"""
    await send_application_status_email(db, application_id, new_status, notes)

async def notify_new_application(db: Session, application_id: int):
    """Wrapper for new application notification to mentor"""
    await send_new_application_notification(db, application_id)

async def notify_task_assignment(db: Session, task_id: int):
    """Wrapper for task assignment notification"""
    await send_task_assignment_email(db, task_id)