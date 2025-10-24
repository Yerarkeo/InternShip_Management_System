# final_test.py
import requests
import time

def test_complete_flow():
    print("🎯 Testing Complete User Management Flow")
    print("=" * 50)
    
    # Test backend first
    print("1. Testing Backend API...")
    session = requests.Session()
    session.post("http://localhost:8000/api/login", 
                 data={"email": "admin@example.com", "password": "admin123"})
    
    # Create a test user
    test_user_data = {
        "email": "frontend_test@example.com",
        "password": "test123",
        "full_name": "Frontend Test User",
        "role": "student"
    }
    
    session.post("http://localhost:8000/api/register", data=test_user_data)
    time.sleep(1)  # Wait for user creation
    
    # Get the new user
    users = session.get("http://localhost:8000/api/admin/users").json()
    test_user = next((u for u in users if u['email'] == 'frontend_test@example.com'), None)
    
    if test_user:
        print(f"✅ Test user created: {test_user['email']} (ID: {test_user['id']})")
        
        # Test delete via API (backend)
        delete_response = session.delete(f"http://localhost:8000/api/admin/users/{test_user['id']}")
        if delete_response.json().get('success'):
            print("✅ Backend delete functionality: WORKING")
        else:
            print("❌ Backend delete functionality: BROKEN")
    else:
        print("❌ Could not create test user")
    
    print("\n2. Frontend Testing Instructions:")
    print("   • Go to: http://localhost:8000/admin/users")
    print("   • Login as: admin@example.com / admin123")
    print("   • Try to delete a user")
    print("   • Check browser console for errors (F12)")
    print("   • If it works, you should see a success message")
    print("   • If not, check the console for error details")

if __name__ == "__main__":
    test_complete_flow()