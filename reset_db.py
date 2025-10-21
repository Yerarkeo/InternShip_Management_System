# reset_db.py
import os
from database import engine, Base
import models

def reset_database():
    # Delete existing database file
    db_file = "internship.db"
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"🗑️  Deleted existing database: {db_file}")
    else:
        print("ℹ️  No existing database file found")
    
    # Create all tables
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
        
        # Test the database
        from sqlalchemy.orm import Session
        from database import SessionLocal
        
        db = SessionLocal()
        try:
            user_count = db.query(models.User).count()
            print(f"📊 Users in database: {user_count}")
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Database creation failed: {e}")

if __name__ == "__main__":
    reset_database()