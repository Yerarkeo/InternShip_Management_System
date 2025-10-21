# test_all_roles.py
from database import SessionLocal
import crud
import schemas
import models  # ADD THIS IMPORT

def test_all_roles():
    db = SessionLocal()
    try:
        print("🧪 Testing all user roles...")
        
        test_users = [
            {
                "email": "test_student@example.com",
                "full_name": "Test Student", 
                "password": "test123",
                "role": "student"
            },
            {
                "email": "test_admin@example.com",
                "full_name": "Test Admin",
                "password": "test123", 
                "role": "admin"
            },
            {
                "email": "test_mentor@example.com",
                "full_name": "Test Mentor",
                "password": "test123",
                "role": "mentor"
            }
        ]
        
        for user_data in test_users:
            # Check if user exists
            existing_user = crud.get_user_by_email(db, user_data["email"])
            
            if existing_user:
                print(f"ℹ️  User already exists: {user_data['email']} (Role: {existing_user.role})")
            else:
                user_schema = schemas.UserCreate(**user_data)
                user = crud.create_user(db, user_schema)
                print(f"✅ Created: {user.email} (Role: {user.role})")
                
        # Verify all users
        users = db.query(models.User).all()
        print(f"\n📊 All users in database:")
        for user in users:
            print(f"   👤 {user.id}: {user.email} - {user.role}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_all_roles()