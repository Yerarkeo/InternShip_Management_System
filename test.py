# test_fixed.py
import os
import smtplib
from dotenv import load_dotenv

load_dotenv()

def test_email_config():
    print("🔍 Checking email configuration...")
    
    # Check which configuration is being used
    email = os.getenv("EMAIL_USERNAME") or os.getenv("SENDER_EMAIL")
    password = os.getenv("EMAIL_PASSWORD") or os.getenv("SENDER_PASSWORD")
    
    print(f"📧 Email: {email}")
    print(f"🔑 Password: {'*' * len(password) if password else 'NOT FOUND'}")
    print(f"📏 Password length: {len(password) if password else 0}")
    
    if not email or not password:
        print("❌ Email or password not found in .env file")
        return False
    
    # Remove spaces from password (common mistake)
    password = password.replace(" ", "")
    print(f"🔑 Password (no spaces): {'*' * len(password)}")
    print(f"📏 Password length (no spaces): {len(password)}")
    
    if len(password) != 16:
        print(f"❌ Password should be 16 characters, but got {len(password)}")
        print("💡 Make sure you're using an App Password, not your regular Gmail password")
        return False
    
    try:
        print("🔄 Testing SMTP connection...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.ehlo()
        print("✅ TLS started successfully")
        
        print("🔐 Attempting login...")
        server.login(email, password)
        print("✅ Login successful!")
        
        server.quit()
        print("🎉 Email configuration is working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n🔧 Troubleshooting steps:")
        print("1. Make sure 2-Step Verification is ENABLED in Google Account")
        print("2. Generate a new App Password for 'Mail'")
        print("3. Copy the 16-character password WITHOUT spaces")
        print("4. Make sure .env file is in the same directory as your script")
        return False

if __name__ == "__main__":
    test_email_config()