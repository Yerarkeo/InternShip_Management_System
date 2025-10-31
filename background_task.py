# background_tasks.py
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import SessionLocal
from email_service import email_service
from email_templates import EmailTemplates

async def check_deadlines_and_send_reminders():
    """Check for upcoming deadlines and send reminder emails"""
    db = SessionLocal()
    try:
        from models import Task, User
        
        # Get tasks due in the next 1-3 days
        upcoming_deadline = datetime.now() + timedelta(days=3)
        tasks = db.query(Task)\
            .join(User, Task.student_id == User.id)\
            .filter(
                Task.due_date <= upcoming_deadline,
                Task.due_date >= datetime.now(),
                Task.status.in_(["pending", "in_progress"])
            )\
            .all()
        
        for task in tasks:
            days_left = (task.due_date - datetime.now()).days
            if 1 <= days_left <= 3:  # Send reminders for tasks due in 1-3 days
                subject = f"Deadline Reminder: {task.title}"
                html_content = EmailTemplates.deadline_reminder(
                    task.student.full_name,
                    task.title,
                    days_left
                )
                await email_service.send_email_async(task.student.email, subject, html_content)
                print(f"📧 Sent deadline reminder for task '{task.title}' to {task.student.email}")
                
    except Exception as e:
        print(f"❌ Error in deadline reminder service: {e}")
    finally:
        db.close()

async def start_background_tasks():
    """Start all background tasks"""
    while True:
        try:
            await check_deadlines_and_send_reminders()
        except Exception as e:
            print(f"❌ Background task error: {e}")
        
        # Check every hour
        await asyncio.sleep(3600)