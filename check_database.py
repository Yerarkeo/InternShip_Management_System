# check_database.py
from database import SessionLocal
import models

def check_database():
    db = SessionLocal()
    try:
        print("🔍 Checking database state...")
        
        # Count all users
        user_count = db.query(models.User).count()
        print(f"📊 Total users: {user_count}")
        
        # List all users
        users = db.query(models.User).all()
        for user in users:
            print(f"👤 User: {user.id} | {user.email} | {user.full_name} | {user.role}")
            
    except Exception as e:
        print(f"❌ Error checking database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_database()