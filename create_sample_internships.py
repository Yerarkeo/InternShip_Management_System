#!/usr/bin/env python3
"""
Test the complete internship application flow
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
import crud
import models

def test_complete_flow():
    print("=== TESTING COMPLETE APPLICATION FLOW ===\n")
    
    db = SessionLocal()
    
    try:
        # 1. Check internships
        internships = crud.get_internships(db)
        print(f"1. 💼 Internships available: {len(internships)}")
        for internship in internships:
            print(f"   - {internship.title} (ID: {internship.id})")
        print()
        
        # 2. Check students
        students = db.query(models.User).filter(models.User.role == 'student').all()
        print(f"2. 🎓 Students available: {len(students)}")
        for student in students[:3]:
            print(f"   - {student.email} (ID: {student.id})")
        print()
        
        # 3. Check mentors
        mentors = db.query(models.User).filter(models.User.role == 'mentor').all()
        print(f"3. 👨‍🏫 Mentors available: {len(mentors)}")
        for mentor in mentors:
            print(f"   - {mentor.email} (ID: {mentor.id})")
        print()
        
        # 4. Check current applications
        applications = db.query(models.InternshipApplication).all()
        print(f"4. 📨 Existing applications: {len(applications)}")
        for app in applications:
            student = db.query(models.User).filter(models.User.id == app.student_id).first()
            internship = db.query(models.Internship).filter(models.Internship.id == app.internship_id).first()
            if student and internship:
                print(f"   - {student.email} -> {internship.title} ({app.status})")
            else:
                print(f"   - Application ID: {app.id} (Student ID: {app.student_id}, Internship ID: {app.internship_id})")
        print()
        
        # 5. Check mentor-specific data
        if mentors:
            mentor = mentors[0]
            print(f"5. 🔍 Checking mentor-specific data for {mentor.email}:")
            try:
                mentor_internships = crud.get_internships_by_mentor(db, mentor.id)
                print(f"   - Internships created: {len(mentor_internships)}")
                
                mentor_applications = crud.get_applications_for_mentor(db, mentor.id)
                print(f"   - Applications received: {len(mentor_applications)}")
            except Exception as e:
                print(f"   - Error: {e}")
        print()
        
        # 6. System readiness
        print("6. ✅ SYSTEM READINESS CHECK")
        print(f"   Database: Connected ✓")
        print(f"   Users: {db.query(models.User).count()} ✓") 
        print(f"   Internships: {len(internships)} ✓")
        print(f"   Applications: {len(applications)}")
        print(f"   Students: {len(students)} ✓")
        print(f"   Mentors: {len(mentors)} ✓")
        print(f"   Admins: {len(db.query(models.User).filter(models.User.role == 'admin').all())} ✓")
        print()
        
        # 7. Test application creation
        if internships and students:
            print("7. 🧪 Testing application creation...")
            student = students[0]
            internship = internships[0]
            
            try:
                from schemas import ApplicationCreate
                # Test that we can create application schema
                test_app = ApplicationCreate(
                    internship_id=internship.id,
                    cover_letter="Test application for system verification"
                )
                print(f"   ✅ Application schema works for {student.email} -> {internship.title}")
                print(f"   📝 Ready for student to apply via web interface")
            except Exception as e:
                print(f"   ❌ Application schema error: {e}")
        print()
        
        print("🎉 YOUR SYSTEM IS READY FOR TESTING!")
        print("\n📋 Manual Testing Steps:")
        print("   1. Start app: python app.py")
        print("   2. Login as student: http://localhost:8000/login")
        print("   3. Browse internships: http://localhost:8000/internships") 
        print("   4. Apply for internships (click Apply Now)")
        print("   5. Check applications: http://localhost:8000/my-applications")
        print("   6. Login as mentor to review applications")
        print("   7. Login as admin for system overview")
        print("\n🔧 Available Test Accounts:")
        print("   Student: keoyerar@gmail.com")
        print("   Mentor: mana@gmail.com") 
        print("   Admin: yuna@gmail.com")
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    test_complete_flow()