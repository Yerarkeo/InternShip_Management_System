# create_test_user.py
from database import SessionLocal
import crud
import schemas
import models  # ADD THIS IMPORT

def create_test_users():
    db = SessionLocal()
    try:
        print("🔧 Creating test users...")
        
        # Create test admin user
        admin_user = schemas.UserCreate(
            email="admin@example.com",
            full_name="System Administrator",
            password="admin123",
            role="admin"
        )
        
        # Create test student user
        student_user = schemas.UserCreate(
            email="student@example.com", 
            full_name="Test Student",
            password="student123",
            role="student"
        )
        
        # Check if users exist
        existing_admin = crud.get_user_by_email(db, admin_user.email)
        existing_student = crud.get_user_by_email(db, student_user.email)
        
        if not existing_admin:
            admin = crud.create_user(db, admin_user)
            print(f"✅ Admin user created: {admin.email} (ID: {admin.id})")
        else:
            print(f"ℹ️  Admin user already exists: {existing_admin.email}")
            
        if not existing_student:
            student = crud.create_user(db, student_user)
            print(f"✅ Student user created: {student.email} (ID: {student.id})")
        else:
            print(f"ℹ️  Student user already exists: {existing_student.email}")
            
        # Verify users were created
        user_count = db.query(models.User).count()
        print(f"📊 Total users in database: {user_count}")
            
    except Exception as e:
        print(f"❌ Error creating test users: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_users()