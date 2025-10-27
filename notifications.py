from email_service import get_email_service
from sqlalchemy.orm import Session
import models

class NotificationService:
    def __init__(self, db: Session):
        self.db = db
        self.email_service = get_email_service()
    
    def send_application_submitted_notification(self, application: models.InternshipApplication):
        """Send notification when student submits application"""
        try:
            student = application.student
            internship = application.internship
            
            subject = "Internship Application Submitted"
            body = f"""
            Dear {student.full_name},
            
            Your application for the {internship.title} position at {internship.company} has been submitted successfully.
            
            Application Details:
            - Position: {internship.title}
            - Company: {internship.company}
            - Application Date: {application.application_date}
            
            We will review your application and get back to you soon.
            
            Best regards,
            Internship Management System
            """
            
            # In a real system, you would send to student's email
            # For now, just log it
            print(f"📧 Application submitted notification for {student.email}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send application notification: {e}")
            return False
    
    def send_application_status_notification(self, application: models.InternshipApplication):
        """Send notification when application status changes"""
        try:
            student = application.student
            internship = application.internship
            
            subject = f"Application Status Update - {internship.title}"
            body = f"""
            Dear {student.full_name},
            
            Your application for the {internship.title} position at {internship.company} has been {application.status}.
            
            Application Details:
            - Position: {internship.title}
            - Company: {internship.company}
            - Status: {application.status.title()}
            
            Thank you for your interest in our internship program.
            
            Best regards,
            Internship Management System
            """
            
            print(f"📧 Application status notification for {student.email}: {application.status}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send status notification: {e}")
            return False
    
    def send_task_assigned_notification(self, task: models.Task):
        """Send notification when task is assigned to student"""
        try:
            student = task.student
            
            subject = f"New Task Assigned: {task.title}"
            body = f"""
            Dear {student.full_name},
            
            A new task has been assigned to you:
            
            Task Details:
            - Title: {task.title}
            - Description: {task.description}
            - Due Date: {task.due_date}
            - Internship: {task.internship.title}
            
            Please complete this task by the due date.
            
            Best regards,
            Internship Management System
            """
            
            print(f"📧 Task assigned notification for {student.email}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send task notification: {e}")
            return False

def get_notification_service(db: Session):
    return NotificationService(db)