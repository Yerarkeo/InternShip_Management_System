from datetime import datetime, timedelta
from typing import Optional
import jwt
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from config import settings
import crud
from database import get_db
import logging

logger = logging.getLogger(__name__)
security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT token with extended expiration"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Extend token expiration to 7 days instead of short time
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 24 * 7)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """Get current user from Authorization header"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError as e:
        logger.error(f"JWT Error in get_current_user: {e}")
        raise credentials_exception
    
    user = crud.get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user

async def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)):
    """Get current user from cookie - FIXED VERSION WITH PROPER REDIRECTS"""
    token = request.cookies.get("access_token")
    if not token:
        # Return RedirectResponse directly instead of raising exception
        return RedirectResponse(url="/login", status_code=302)
    
    # Remove "Bearer " prefix if present
    if token.startswith("Bearer "):
        token = token.replace("Bearer ", "")
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            # Return RedirectResponse directly
            return RedirectResponse(url="/login", status_code=302)
    except jwt.ExpiredSignatureError:
        # Clear expired token and redirect to login
        response = RedirectResponse(url="/login", status_code=302)
        response.delete_cookie("access_token")
        return response
    except jwt.JWTError as e:
        logger.error(f"JWT Error in cookie auth: {e}")
        # Clear invalid token and redirect to login
        response = RedirectResponse(url="/login", status_code=302)
        response.delete_cookie("access_token")
        return response
    
    user = crud.get_user_by_email(db, email=email)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)
    return user

async def get_current_user_optional(request: Request, db: Session = Depends(get_db)):
    """Get current user but don't raise exception if not authenticated - FIXED VERSION"""
    try:
        token = request.cookies.get("access_token")
        if not token:
            return None
        
        # Remove "Bearer " prefix if present
        if token.startswith("Bearer "):
            token = token.replace("Bearer ", "")
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            return None
        
        user = crud.get_user_by_email(db, email=email)
        return user
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired in optional auth")
        return None
    except jwt.JWTError as e:
        logger.warning(f"JWT error in optional auth: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in optional auth: {e}")
        return None

async def get_current_active_user(current_user = Depends(get_current_user)):
    """Get current active user from header"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_active_user_from_cookie(current_user = Depends(get_current_user_from_cookie)):
    """Get current active user from cookie - FIXED VERSION"""
    # Handle the case where current_user might be a RedirectResponse
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def create_login_response(user, db: Session):
    """Create login response with proper token and cookies"""
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 24 * 7)  # 7 days
    access_token = create_access_token(
        data={"sub": user.email}, 
        expires_delta=access_token_expires
    )
    
    response = RedirectResponse(url="/dashboard", status_code=302)
    
    # Set cookie with longer expiration
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=7 * 24 * 60 * 60,  # 7 days in seconds
        expires=7 * 24 * 60 * 60,   # 7 days in seconds
        secure=False,  # Set to True in production with HTTPS
        samesite="lax"
    )
    
    # Log the login
    logger.info(f"User logged in: {user.email}, Role: {user.role}")
    
    return response

def clear_auth_cookie():
    """Clear authentication cookie"""
    response = RedirectResponse(url="/login")
    response.delete_cookie("access_token")
    return response

# Token verification utility
def verify_token(token: str) -> Optional[dict]:
    """Verify token and return payload if valid"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired during verification")
        return None
    except jwt.JWTError as e:
        logger.warning(f"Token verification failed: {e}")
        return None

# Role-based access control
async def require_role(required_role: str, user = Depends(get_current_user_from_cookie)):
    """Check if user has required role"""
    # Handle the case where user might be a RedirectResponse
    if isinstance(user, RedirectResponse):
        return user
    
    # Extract role value if it's an enum, otherwise use as is
    user_role = user.role.value if hasattr(user.role, 'value') else user.role
    
    if user_role != required_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires {required_role} role"
        )
    return user

async def require_admin(user = Depends(get_current_user_from_cookie)):
    """Require admin role"""
    return await require_role("admin", user)

async def require_mentor(user = Depends(get_current_user_from_cookie)):
    """Require mentor role"""
    return await require_role("mentor", user)

async def require_student(user = Depends(get_current_user_from_cookie)):
    """Require student role"""
    return await require_role("student", user)