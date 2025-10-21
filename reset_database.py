# reset_database.py
import os
from database import engine, Base
import models

def reset_database():
    # Delete existing database file
    db_file = "internship.db"
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"🗑️  Deleted existing database: {db_file}")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")
    print("📊 Available tables:")
    for table in Base.metadata.tables:
        print(f"   - {table}")

if __name__ == "__main__":
    reset_database()