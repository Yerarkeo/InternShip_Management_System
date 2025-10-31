# email_templates.py
class EmailTemplates:
    # Student Templates
    @staticmethod
    def application_submitted(student_name: str, internship_title: str):
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; }}
                .content {{ background: #f9f9f9; padding: 20px; }}
                .footer {{ text-align: center; padding: 20px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Application Submitted 🎉</h1>
                </div>
                <div class="content">
                    <h2>Hello {student_name},</h2>
                    <p>Your application for <strong>{internship_title}</strong> has been successfully submitted!</p>
                    <p>We will review your application and get back to you soon. You can check your application status in your dashboard.</p>
                    <p>Best of luck! 🚀</p>
                </div>
                <div class="footer">
                    <p>Internship Management System</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    @staticmethod
    def application_status_update(student_name: str, internship_title: str, status: str, notes: str = ""):
        status_emoji = {"approved": "✅", "rejected": "❌", "pending": "⏳"}
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: {'#4CAF50' if status == 'approved' else '#f44336' if status == 'rejected' else '#ff9800'}; color: white; padding: 20px; text-align: center; }}
                .content {{ background: #f9f9f9; padding: 20px; }}
                .notes {{ background: #e3f2fd; padding: 15px; border-left: 4px solid #2196F3; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{status_emoji.get(status, '📝')} Application Update</h1>
                </div>
                <div class="content">
                    <h2>Hello {student_name},</h2>
                    <p>Your application for <strong>{internship_title}</strong> has been <strong>{status}</strong>.</p>
                    {f'<div class="notes"><strong>Notes:</strong><br>{notes}</div>' if notes else ''}
                    {f'<p>🎉 Congratulations! The mentor will contact you shortly with next steps.</p>' if status == 'approved' else ''}
                    {f'<p>Thank you for your interest. We encourage you to apply for other opportunities.</p>' if status == 'rejected' else ''}
                </div>
            </div>
        </body>
        </html>
        """
    
    @staticmethod
    def task_assigned(student_name: str, task_title: str, due_date: str, mentor_name: str, task_description: str = ""):
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #2196F3; color: white; padding: 20px; text-align: center; }}
                .task-card {{ background: white; border: 1px solid #ddd; padding: 15px; margin: 15px 0; }}
                .deadline {{ color: #ff6b6b; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📋 New Task Assigned</h1>
                </div>
                <div class="content">
                    <h2>Hello {student_name},</h2>
                    <p>Your mentor <strong>{mentor_name}</strong> has assigned you a new task:</p>
                    
                    <div class="task-card">
                        <h3>{task_title}</h3>
                        {f'<p>{task_description}</p>' if task_description else ''}
                        <p class="deadline">📅 Deadline: {due_date}</p>
                    </div>
                    
                    <p>Please log in to your dashboard to view task details and submit your work.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    @staticmethod
    def deadline_reminder(student_name: str, task_title: str, days_left: int):
        color = "#ff6b6b" if days_left <= 1 else "#ffa726"
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: {color}; color: white; padding: 20px; text-align: center; }}
                .urgent {{ background: #ffebee; padding: 10px; border-left: 4px solid #f44336; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⏰ Deadline Reminder</h1>
                </div>
                <div class="content">
                    <h2>Hello {student_name},</h2>
                    <div class="urgent">
                        <h3>Task: {task_title}</h3>
                        <p>This task is due in <strong>{days_left} day(s)</strong>!</p>
                    </div>
                    <p>Please make sure to submit your work before the deadline.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    # Mentor Templates
    @staticmethod
    def new_application(mentor_name: str, student_name: str, internship_title: str, application_date: str):
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #9C27B0; color: white; padding: 20px; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📨 New Application Received</h1>
                </div>
                <div class="content">
                    <h2>Hello {mentor_name},</h2>
                    <p>You have received a new application for your internship:</p>
                    <div style="background: #f3e5f5; padding: 15px; margin: 15px 0;">
                        <p><strong>Internship:</strong> {internship_title}</p>
                        <p><strong>Student:</strong> {student_name}</p>
                        <p><strong>Applied on:</strong> {application_date}</p>
                    </div>
                    <p>Please review this application in your mentor dashboard.</p>
                </div>
            </div>
        </body>
        </html>
        """