import hashlib

def verify_password(plain_password, hashed_password):
    """Simple password verification for development"""
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password

def get_password_hash(password):
    """Simple password hashing for development"""
    return hashlib.sha256(password.encode()).hexdigest()