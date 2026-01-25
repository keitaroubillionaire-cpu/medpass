import os
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from database import get_db
from models import User

# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Get current user from cookie token."""
    token = request.cookies.get("access_token")
    print(f"DEBUG: Cookie token exists: {token is not None}")
    print(f"DEBUG: All cookies: {request.cookies}")

    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        print(f"DEBUG: Decoded user_id: {user_id_str}")
        if user_id_str is None:
            return None
        user_id = int(user_id_str)
    except (JWTError, ValueError) as e:
        print(f"DEBUG: JWT Error: {e}")
        return None

    user = db.query(User).filter(User.id == user_id).first()
    print(f"DEBUG: Found user: {user}")
    return user


def require_auth(request: Request, db: Session = Depends(get_db)) -> User:
    """Require authentication, redirect to login if not authenticated."""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/auth/login"}
        )
    return user


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Get user if authenticated, None otherwise."""
    return get_current_user(request, db)
