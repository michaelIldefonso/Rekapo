import os
from sqlalchemy.orm import Session
from sqlalchemy import func, Date
from typing import Optional, Tuple, List
from datetime import datetime, date
from db.db import User, SystemStatistics, Session as SessionModel
from utils.utils import get_logger

logger = get_logger(__name__)


class AdminSessionService:
    """Service layer for admin session management operations"""
    
    @staticmethod
    def get_sessions_paginated(
        db: Session,
        page: int,
        page_size: int,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        is_deleted: Optional[bool] = None
    ) -> Tuple[List[SessionModel], int]:
        """
        Get paginated list of sessions with optional filters.
        Returns tuple of (sessions list, total count)
        """
        query = db.query(SessionModel)
        
        # Apply filters
        if user_id is not None:
            query = query.filter(SessionModel.user_id == user_id)
        
        if status is not None:
            query = query.filter(SessionModel.status == status)
        
        if is_deleted is not None:
            query = query.filter(SessionModel.is_deleted == is_deleted)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        sessions = query.order_by(SessionModel.created_at.desc()).offset(offset).limit(page_size).all()
        
        return sessions, total
    
    @staticmethod
    def get_session_by_id(db: Session, session_id: int) -> Optional[SessionModel]:
        """Get session by ID"""
        return db.query(SessionModel).filter(SessionModel.id == session_id).first()
    
    @staticmethod
    def delete_session(
        db: Session,
        session: SessionModel,
        admin_id: int
    ) -> SessionModel:
        """Soft delete a session"""
        session.is_deleted = True
        session.deleted_at = datetime.utcnow()
        session.deleted_by = admin_id
        
        db.commit()
        db.refresh(session)
        
        return session


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


class SystemStatisticsService:
    """Service layer for system statistics operations"""
    
    @staticmethod
    def get_statistics_paginated(
        db: Session,
        page: int,
        page_size: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Tuple[List[SystemStatistics], int]:
        """
        Get paginated list of system statistics with optional date filters.
        Returns tuple of (statistics list, total count)
        """
        query = db.query(SystemStatistics)
        
        # Apply date filters
        if start_date:
            query = query.filter(SystemStatistics.stat_date >= start_date)
        
        if end_date:
            query = query.filter(SystemStatistics.stat_date <= end_date)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        statistics = query.order_by(SystemStatistics.stat_date.desc()).offset(offset).limit(page_size).all()
        
        return statistics, total
    
    @staticmethod
    def get_statistics_by_id(db: Session, stat_id: int) -> Optional[SystemStatistics]:
        """Get system statistics by ID"""
        return db.query(SystemStatistics).filter(SystemStatistics.id == stat_id).first()
    
    @staticmethod
    def get_statistics_by_date(db: Session, stat_date: date) -> Optional[SystemStatistics]:
        """Get system statistics by date"""
        return db.query(SystemStatistics).filter(SystemStatistics.stat_date == stat_date).first()
    
    @staticmethod
    def create_statistics(
        db: Session,
        stat_date: date,
        total_users: Optional[int] = None,
        active_users: Optional[int] = None,
        total_sessions: Optional[int] = None,
        average_session_duration: Optional[float] = None
    ) -> SystemStatistics:
        """Create new system statistics entry"""
        stat = SystemStatistics(
            stat_date=stat_date,
            total_users=total_users,
            active_users=active_users,
            total_sessions=total_sessions,
            average_session_duration=average_session_duration,
            calculated_at=datetime.utcnow()
        )
        
        db.add(stat)
        db.commit()
        db.refresh(stat)
        
        return stat
    
    @staticmethod
    def update_statistics(
        db: Session,
        stat: SystemStatistics,
        total_users: Optional[int] = None,
        active_users: Optional[int] = None,
        total_sessions: Optional[int] = None,
        average_session_duration: Optional[float] = None
    ) -> SystemStatistics:
        """Update existing system statistics entry"""
        if total_users is not None:
            stat.total_users = total_users
        if active_users is not None:
            stat.active_users = active_users
        if total_sessions is not None:
            stat.total_sessions = total_sessions
        if average_session_duration is not None:
            stat.average_session_duration = average_session_duration
        
        stat.calculated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(stat)
        
        return stat
    
    @staticmethod
    def delete_statistics(db: Session, stat: SystemStatistics) -> None:
        """Delete system statistics entry"""
        db.delete(stat)
        db.commit()
    
    @staticmethod
    def calculate_statistics_for_date(db: Session, stat_date: date) -> SystemStatistics:
        """
        Calculate and store system statistics for a specific date.
        This computes actual metrics from the database.
        """
        # Calculate total users (all users created up to that date)
        total_users = db.query(func.count(User.id)).filter(
            User.created_at <= datetime.combine(stat_date, datetime.max.time())
        ).scalar()
        
        # Calculate active users (users who created at least one session on that date)
        from sqlalchemy import cast
        active_users = db.query(func.count(func.distinct(SessionModel.user_id))).filter(
            cast(SessionModel.start_time, Date) == stat_date,
            SessionModel.is_deleted == False
        ).scalar()
        
        # Calculate total sessions (all sessions created up to that date)
        total_sessions = db.query(func.count(SessionModel.id)).filter(
            SessionModel.start_time <= datetime.combine(stat_date, datetime.max.time()),
            SessionModel.is_deleted == False
        ).scalar()
        
        # Calculate average session duration (in minutes) for all completed sessions up to that date
        # PostgreSQL: EXTRACT(EPOCH FROM (end_time - start_time)) / 60 = minutes
        avg_duration_minutes = db.query(
            func.avg(
                func.extract('epoch', SessionModel.end_time - SessionModel.start_time) / 60
            )
        ).filter(
            SessionModel.start_time <= datetime.combine(stat_date, datetime.max.time()),
            SessionModel.end_time.isnot(None),
            SessionModel.status == 'completed',
            SessionModel.is_deleted == False
        ).scalar()
        
        # Check if statistics already exist for this date
        existing_stat = db.query(SystemStatistics).filter(
            SystemStatistics.stat_date == stat_date
        ).first()
        
        if existing_stat:
            # Update existing statistics
            return SystemStatisticsService.update_statistics(
                db=db,
                stat=existing_stat,
                total_users=total_users,
                active_users=active_users,
                total_sessions=total_sessions,
                average_session_duration=float(avg_duration_minutes) if avg_duration_minutes else None
            )
        else:
            # Create new statistics
            return SystemStatisticsService.create_statistics(
                db=db,
                stat_date=stat_date,
                total_users=total_users,
                active_users=active_users,
                total_sessions=total_sessions,
                average_session_duration=float(avg_duration_minutes) if avg_duration_minutes else None
            )
