# email_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

class EmailService:
    def __init__(self):
        # For demo purposes, we'll use print logging
        # In production, configure these environment variables
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.sender_email = os.getenv("SENDER_EMAIL", "internship@university.edu")
        self.sender_password = os.getenv("SENDER_PASSWORD", "")
    
    def send_application_status_email(self, student_email: str, student_name: str, internship_title: str, company: str, status: str, admin_notes: str = ""):
        """Send email notification about application status change"""
        try:
            subject = f"Internship Application Update - {internship_title}"
            
            if status == "approved":
                body = f"""
                Dear {student_name},
                
                Congratulations! Your application for the {internship_title} position at {company} has been approved.
                
                Next Steps:
                - You will be contacted by the company within 3-5 business days
                - Prepare your documents for the onboarding process
                - Contact your internship coordinator if you have any questions
                
                {admin_notes if admin_notes else "Please check your dashboard for more details."}
                
                Best regards,
                Internship Management System
                University Career Center
                """
            else:  # rejected
                body = f"""
                Dear {student_name},
                
                Thank you for your application for the {internship_title} position at {company}. 
                After careful review, we regret to inform you that your application has not been approved at this time.
                
                Reason: {admin_notes if admin_notes else "The company has selected other candidates whose qualifications better match their current needs."}
                
                Don't be discouraged! We encourage you to:
                - Apply for other internship opportunities
                - Visit the career center for application review
                - Schedule an appointment with your academic advisor
                
                Best regards,
                Internship Management System
                University Career Center
                """
            
            # In a real implementation, you would send the actual email
            # For now, we'll simulate and log it
            print("=" * 60)
            print("📧 EMAIL NOTIFICATION SENT:")
            print(f"To: {student_email}")
            print(f"Subject: {subject}")
            print(f"Body:\n{body}")
            print("=" * 60)
            
            # Uncomment below to send actual emails (configure SMTP first)
            # return self._send_actual_email(student_email, subject, body)
            return True
            
        except Exception as e:
            print(f"❌ Failed to send email notification: {e}")
            return False
    
    def _send_actual_email(self, to_email: str, subject: str, body: str):
        """Actual email sending implementation"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            text = msg.as_string()
            server.sendmail(self.sender_email, to_email, text)
            server.quit()
            
            return True
        except Exception as e:
            print(f"❌ Email sending failed: {e}")
            return False

# Global instance
email_service = EmailService()
# Add to email_service.py
def send_application_status_email(student_email, student_name, internship_title, status, admin_notes=""):
    # Implementation for sending actual emails
    pass