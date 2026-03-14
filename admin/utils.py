"""
Module: admin/utils.py.

This module contains admin-only endpoints, schemas, and service helpers.
"""

import os
import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from db.db import get_db, User
from utils.utils import get_logger

logger = get_logger(__name__)

# JWT configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your_jwt_secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 4  # 4 hours for admin sessions (security best practice)

security = HTTPBearer()


def generate_admin_token(user: User) -> str:
    """Generate JWT token for admin user"""
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "is_admin": True,
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(token_data, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_admin_token(token: str) -> dict:
    """Verify and decode admin JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        is_admin = payload.get("is_admin", False)
        
        if not user_id or not is_admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin token"
            )
        
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current admin user from JWT token.
    Validates that user is an admin and account is active.
    """
    token = credentials.credentials
    payload = verify_admin_token(token)
    user_id = payload.get("sub")
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    if user.is_disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    return user


def validate_user_operation(
    target_user_id: int,
    current_admin: User,
    operation: str = "modify"
) -> None:
    """
    Validate that an admin operation on a user is allowed.
    Prevents self-modification operations.
    """
    if target_user_id == current_admin.id:
        operations_map = {
            "disable": "disable your own account",
            "delete": "delete your own account",
            "demote": "change your own admin status",
            "modify": "modify your own account"
        }
        detail = f"You cannot {operations_map.get(operation, operations_map['modify'])}"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )

