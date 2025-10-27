import pandas as pd
from sqlalchemy.orm import Session
import models
from fpdf import FPDF
import os
from datetime import datetime

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Internship Management System Report', 0, 1, 'C')
        self.set_font('Arial', 'I', 12)
        self.cell(0, 10, f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 1, 'C')
        self.ln(10)

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(5)

    def chapter_body(self, body):
        self.set_font('Arial', '', 12)
        self.multi_cell(0, 10, body)
        self.ln()

def generate_internship_report_pdf(db: Session, internship_id: int):
    internship = db.query(models.Internship).filter(models.Internship.id == internship_id).first()
    if not internship:
        return None
    
    applications = db.query(models.InternshipApplication).filter(
        models.InternshipApplication.internship_id == internship_id
    ).all()
    
    pdf = PDFReport()
    pdf.add_page()
    
    # Internship Details
    pdf.chapter_title('Internship Details')
    pdf.chapter_body(f"""
    Title: {internship.title}
    Company: {internship.company}
    Location: {internship.location}
    Duration: {internship.duration}
    Stipend: {internship.stipend}
    Requirements: {internship.requirements}
    """)
    
    # Applications Summary
    pdf.chapter_title('Applications Summary')
    total_apps = len(applications)
    pending = len([app for app in applications if app.status == 'pending'])
    approved = len([app for app in applications if app.status == 'approved'])
    rejected = len([app for app in applications if app.status == 'rejected'])
    
    pdf.chapter_body(f"""
    Total Applications: {total_apps}
    Pending: {pending}
    Approved: {approved}
    Rejected: {rejected}
    """)
    
    # Save PDF
    filename = f"internship_report_{internship_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join("static/reports", filename)
    os.makedirs("static/reports", exist_ok=True)
    pdf.output(filepath)
    
    return filename

def generate_student_report_excel(db: Session, student_id: int):
    student = db.query(models.User).filter(models.User.id == student_id).first()
    if not student:
        return None
    
    applications = db.query(models.InternshipApplication).filter(
        models.InternshipApplication.student_id == student_id
    ).all()
    
    tasks = db.query(models.Task).filter(models.Task.student_id == student_id).all()
    
    # Create Excel file
    filename = f"student_report_{student_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = os.path.join("static/reports", filename)
    os.makedirs("static/reports", exist_ok=True)
    
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        # Applications sheet
        apps_data = []
        for app in applications:
            internship = db.query(models.Internship).filter(models.Internship.id == app.internship_id).first()
            apps_data.append({
                'Internship': internship.title if internship else 'N/A',
                'Company': internship.company if internship else 'N/A',
                'Applied Date': app.application_date,
                'Status': app.status,
                'Cover Letter': app.cover_letter[:100] + '...' if app.cover_letter else 'None'
            })
        
        if apps_data:
            pd.DataFrame(apps_data).to_excel(writer, sheet_name='Applications', index=False)
        
        # Tasks sheet
        tasks_data = []
        for task in tasks:
            internship = db.query(models.Internship).filter(models.Internship.id == task.internship_id).first()
            tasks_data.append({
                'Task Title': task.title,
                'Description': task.description,
                'Internship': internship.title if internship else 'N/A',
                'Status': task.status,
                'Progress': f"{task.progress}%",
                'Due Date': task.due_date,
                'Created Date': task.created_at
            })
        
        if tasks_data:
            pd.DataFrame(tasks_data).to_excel(writer, sheet_name='Tasks', index=False)
    
    return filename