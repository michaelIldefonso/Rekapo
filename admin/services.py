import os
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, Tuple, List
from datetime import datetime
from db.db import User
from utils.utils import get_logger

logger = get_logger(__name__)


class AdminUserService:
    """Service layer for admin user management operations"""
    
    @staticmethod
    def get_users_paginated(
        db: Session,
        page: int,
        page_size: int,
        search: Optional[str] = None,
        is_admin: Optional[bool] = None,
        is_disabled: Optional[bool] = None
    ) -> Tuple[List[User], int]:
        """
        Get paginated list of users with optional filters.
        Returns tuple of (users list, total count)
        """
        query = db.query(User)
        
        # Apply filters
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (User.email.ilike(search_pattern)) | 
                (User.name.ilike(search_pattern)) |
                (User.username.ilike(search_pattern))
            )
        
        if is_admin is not None:
            query = query.filter(User.is_admin == is_admin)
        
        if is_disabled is not None:
            query = query.filter(User.is_disabled == is_disabled)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        users = query.order_by(User.created_at.desc()).offset(offset).limit(page_size).all()
        
        return users, total
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def disable_user(
        db: Session,
        user: User,
        admin_id: int,
        reason: str
    ) -> User:
        """Disable a user account"""
        user.is_disabled = True
        user.disabled_at = datetime.utcnow()
        user.disabled_by = admin_id
        user.disabled_reason = reason
        
        db.commit()
        db.refresh(user)
        
        return user
    
    @staticmethod
    def enable_user(db: Session, user: User) -> User:
        """Enable a previously disabled user account"""
        user.is_disabled = False
        user.disabled_at = None
        user.disabled_by = None
        user.disabled_reason = None
        
        db.commit()
        db.refresh(user)
        
        return user
    
    @staticmethod
    def update_admin_status(db: Session, user: User, is_admin: bool) -> User:
        """Update admin status of a user"""
        user.is_admin = is_admin
        
        db.commit()
        db.refresh(user)
        
        return user
    
    @staticmethod
    def delete_user(db: Session, user: User) -> None:
        """Permanently delete a user and all associated data"""
        db.delete(user)
        db.commit()
