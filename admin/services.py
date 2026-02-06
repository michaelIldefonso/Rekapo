import os
from sqlalchemy.orm import Session
from sqlalchemy import func, Date
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime, date, timedelta
from db.db import User, SystemStatistics, Session as SessionModel, RecordingSegment, Summary
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
        is_deleted: Optional[bool] = None,
        session_title: Optional[str] = None,
        training_consent: Optional[bool] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get paginated list of sessions with optional filters and user info.
        Returns tuple of (sessions list with user data, total count)
        """
        query = db.query(SessionModel, User).join(
            User, SessionModel.user_id == User.id
        )
        
        # Apply filters
        if user_id is not None:
            query = query.filter(SessionModel.user_id == user_id)
        
        if status is not None:
            query = query.filter(SessionModel.status == status)
        
        if is_deleted is not None:
            query = query.filter(SessionModel.is_deleted == is_deleted)
        
        if session_title is not None:
            query = query.filter(SessionModel.session_title.ilike(f"%{session_title}%"))
        
        if training_consent is not None:
            query = query.filter(User.data_usage_consent == training_consent)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        results = query.order_by(SessionModel.created_at.desc()).offset(offset).limit(page_size).all()
        
        # Format results with user info
        sessions = []
        for session, user in results:
            # Fix missing created_at
            if session.created_at is None:
                session.created_at = datetime.utcnow()
            
            session_dict = {
                'id': session.id,
                'user_id': session.user_id,
                'session_title': session.session_title,
                'start_time': session.start_time,
                'end_time': session.end_time,
                'is_deleted': session.is_deleted,
                'deleted_at': session.deleted_at,
                'deleted_by': session.deleted_by,
                'status': session.status,
                'created_at': session.created_at,
                'user': {
                    'user_id': user.id,
                    'email': user.email,
                    'name': user.name,
                    'username': user.username,
                    'data_usage_consent': bool(user.data_usage_consent) if user.data_usage_consent is not None else True
                }
            }
            sessions.append(session_dict)
        
        # Commit any timestamp fixes
        db.commit()
        
        return sessions, total
    
    @staticmethod
    def get_session_by_id(db: Session, session_id: int) -> Optional[Dict[str, Any]]:
        """Get session by ID with user info"""
        result = db.query(SessionModel, User).join(
            User, SessionModel.user_id == User.id
        ).filter(SessionModel.id == session_id).first()
        
        if not result:
            return None
        
        session, user = result
        
        # Fix missing created_at
        if session.created_at is None:
            session.created_at = datetime.utcnow()
            db.commit()
        
        return {
            'id': session.id,
            'user_id': session.user_id,
            'session_title': session.session_title,
            'start_time': session.start_time,
            'end_time': session.end_time,
            'is_deleted': session.is_deleted,
            'deleted_at': session.deleted_at,
            'deleted_by': session.deleted_by,
            'status': session.status,
            'created_at': session.created_at,
            'user': {
                'user_id': user.id,
                'email': user.email,
                'name': user.name,
                'username': user.username,
                'data_usage_consent': bool(user.data_usage_consent) if user.data_usage_consent is not None else True
            }
        }
    
    @staticmethod
    def get_session_detailed(db: Session, session_id: int) -> Optional[Dict[str, Any]]:
        """Get comprehensive session details including segments and summaries"""
        result = db.query(SessionModel, User).join(
            User, SessionModel.user_id == User.id
        ).filter(SessionModel.id == session_id).first()
        
        if not result:
            return None
        
        session, user = result
        
        # Fix missing created_at
        if session.created_at is None:
            session.created_at = datetime.utcnow()
        
        # Get all recording segments for this session
        segments = db.query(RecordingSegment).filter(
            RecordingSegment.session_id == session_id
        ).order_by(RecordingSegment.segment_number).all()
        
        # Fix segments with missing created_at
        for segment in segments:
            if segment.created_at is None:
                segment.created_at = datetime.utcnow()
        
        # Get all summaries for this session
        summaries = db.query(Summary).filter(
            Summary.session_id == session_id
        ).order_by(Summary.chunk_range_start).all()
        
        # Fix summaries with missing generated_at
        for summary in summaries:
            if summary.generated_at is None:
                summary.generated_at = datetime.utcnow()
            if summary.is_final_summary is None:
                summary.is_final_summary = False
        
        # Commit all timestamp fixes
        db.commit()
        
        # Calculate session duration
        session_duration = None
        if session.end_time and session.start_time:
            duration_seconds = (session.end_time - session.start_time).total_seconds()
            session_duration = duration_seconds / 60  # Convert to minutes
        
        return {
            'id': session.id,
            'user_id': session.user_id,
            'session_title': session.session_title,
            'start_time': session.start_time,
            'end_time': session.end_time,
            'is_deleted': session.is_deleted,
            'deleted_at': session.deleted_at,
            'deleted_by': session.deleted_by,
            'status': session.status,
            'created_at': session.created_at,
            'user': {
                'user_id': user.id,
                'email': user.email,
                'name': user.name,
                'username': user.username,
                'data_usage_consent': bool(user.data_usage_consent) if user.data_usage_consent is not None else True
            },
            'recording_segments': segments,
            'summaries': summaries,
            'total_segments': len(segments),
            'total_summaries': len(summaries),
            'session_duration_minutes': session_duration
        }
    
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
            # Check if search is numeric (user ID)
            if search.isdigit():
                query = query.filter(User.id == int(search))
            else:
                # Search by email, name, or username
                search_pattern = f"%{search}%"
                query = query.filter(
                    (User.email.ilike(search_pattern)) | 
                    (User.name.ilike(search_pattern)) |
                    (User.username.ilike(search_pattern))
                )
        
        if is_admin is not None:
            if is_admin:
                query = query.filter(User.is_admin == True)
            else:
                # Include both False and NULL as "not admin"
                query = query.filter((User.is_admin == False) | (User.is_admin.is_(None)))
        
        if is_disabled is not None:
            if is_disabled:
                query = query.filter(User.is_disabled == True)
            else:
                # Include both False and NULL as "not disabled"
                query = query.filter((User.is_disabled == False) | (User.is_disabled.is_(None)))
        
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
    
    @staticmethod
    def get_user_analytics(db: Session, user_id: int) -> Optional[Dict[str, Any]]:
        """Get comprehensive analytics for a specific user"""
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return None
        
        # Total sessions by status
        total_sessions = db.query(func.count(SessionModel.id)).filter(
            SessionModel.user_id == user_id
        ).scalar() or 0
        
        completed_sessions = db.query(func.count(SessionModel.id)).filter(
            SessionModel.user_id == user_id,
            SessionModel.status == 'completed'
        ).scalar() or 0
        
        failed_sessions = db.query(func.count(SessionModel.id)).filter(
            SessionModel.user_id == user_id,
            SessionModel.status == 'failed'
        ).scalar() or 0
        
        deleted_sessions = db.query(func.count(SessionModel.id)).filter(
            SessionModel.user_id == user_id,
            SessionModel.is_deleted == True
        ).scalar() or 0
        
        active_sessions = db.query(func.count(SessionModel.id)).filter(
            SessionModel.user_id == user_id,
            SessionModel.status == 'recording'
        ).scalar() or 0
        
        # Duration statistics (in minutes)
        avg_duration_minutes = db.query(
            func.avg(
                func.extract('epoch', SessionModel.end_time - SessionModel.start_time) / 60
            )
        ).filter(
            SessionModel.user_id == user_id,
            SessionModel.end_time.isnot(None),
            SessionModel.status == 'completed'
        ).scalar()
        
        total_duration_minutes = db.query(
            func.sum(
                func.extract('epoch', SessionModel.end_time - SessionModel.start_time) / 60
            )
        ).filter(
            SessionModel.user_id == user_id,
            SessionModel.end_time.isnot(None),
            SessionModel.status == 'completed'
        ).scalar()
        
        longest_duration_minutes = db.query(
            func.max(
                func.extract('epoch', SessionModel.end_time - SessionModel.start_time) / 60
            )
        ).filter(
            SessionModel.user_id == user_id,
            SessionModel.end_time.isnot(None),
            SessionModel.status == 'completed'
        ).scalar()
        
        # Recording segments statistics
        total_segments = db.query(func.count(RecordingSegment.id)).join(
            SessionModel, SessionModel.id == RecordingSegment.session_id
        ).filter(
            SessionModel.user_id == user_id
        ).scalar() or 0
        
        # Count total words in transcripts (approximate)
        total_words = db.query(
            func.sum(
                func.coalesce(
                    func.length(RecordingSegment.transcript_text) - 
                    func.length(func.replace(RecordingSegment.transcript_text, ' ', '')) + 1,
                    0
                )
            )
        ).join(
            SessionModel, SessionModel.id == RecordingSegment.session_id
        ).filter(
            SessionModel.user_id == user_id,
            RecordingSegment.transcript_text.isnot(None),
            RecordingSegment.transcript_text != ''
        ).scalar()
        
        # Last session date
        last_session = db.query(SessionModel.start_time).filter(
            SessionModel.user_id == user_id
        ).order_by(SessionModel.start_time.desc()).first()
        
        last_session_date = last_session[0] if last_session else None
        
        # Calculate days since last session
        days_since_last = None
        if last_session_date:
            days_since_last = (datetime.utcnow() - last_session_date).days
        
        # Account age in days
        account_age_days = (datetime.utcnow() - user.created_at).days
        
        return {
            'user_id': user.id,
            'email': user.email,
            'name': user.name,
            'username': user.username,
            'is_admin': bool(user.is_admin) if user.is_admin is not None else False,
            'is_disabled': bool(user.is_disabled) if user.is_disabled is not None else False,
            'created_at': user.created_at,
            'total_sessions': total_sessions,
            'completed_sessions': completed_sessions,
            'failed_sessions': failed_sessions,
            'deleted_sessions': deleted_sessions,
            'active_sessions': active_sessions,
            'average_session_duration': float(avg_duration_minutes) if avg_duration_minutes else None,
            'total_recording_time': float(total_duration_minutes) if total_duration_minutes else None,
            'longest_session_duration': float(longest_duration_minutes) if longest_duration_minutes else None,
            'total_recording_segments': total_segments,
            'total_transcribed_words': int(total_words) if total_words else None,
            'last_session_date': last_session_date,
            'days_since_last_session': days_since_last,
            'account_age_days': account_age_days
        }
    
    @staticmethod
    def get_all_users_analytics(
        db: Session,
        page: int,
        page_size: int,
        time_period_days: Optional[int] = None,
        search: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get analytics for all users with optional time period filtering and search.
        
        Args:
            db: Database session
            page: Page number for pagination
            page_size: Number of items per page
            time_period_days: Filter sessions by time period (1, 7, 30, 90 days). 
                            None means all time.
            search: Search by user ID, email, name, or username
        
        Returns:
            Tuple of (analytics list, total user count)
        """
        # Get all users
        users_query = db.query(User)
        
        # Apply search filter
        if search:
            # Check if search is numeric (user ID)
            if search.isdigit():
                users_query = users_query.filter(User.id == int(search))
            else:
                # Search by email, name, or username
                search_pattern = f"%{search}%"
                users_query = users_query.filter(
                    (User.email.ilike(search_pattern)) |
                    (User.name.ilike(search_pattern)) |
                    (User.username.ilike(search_pattern))
                )
        
        total_users = users_query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        users = users_query.order_by(User.created_at.desc()).offset(offset).limit(page_size).all()
        
        # Calculate the cutoff date for time period filtering
        cutoff_date = None
        if time_period_days is not None:
            cutoff_date = datetime.utcnow() - timedelta(days=time_period_days)
        
        analytics_list = []
        
        for user in users:
            # Base session query
            session_query = db.query(SessionModel).filter(SessionModel.user_id == user.id)
            
            # Apply time period filter if specified
            if cutoff_date:
                session_query = session_query.filter(SessionModel.start_time >= cutoff_date)
            
            # Total sessions
            total_sessions = session_query.count()
            
            # Sessions by status
            completed_sessions = session_query.filter(
                SessionModel.status == 'completed'
            ).count()
            
            failed_sessions = session_query.filter(
                SessionModel.status == 'failed'
            ).count()
            
            deleted_sessions = session_query.filter(
                SessionModel.is_deleted == True
            ).count()
            
            active_sessions = session_query.filter(
                SessionModel.status == 'recording'
            ).count()
            
            # Duration statistics query (only completed sessions with end_time)
            duration_query = db.query(
                func.avg(
                    func.extract('epoch', SessionModel.end_time - SessionModel.start_time) / 60
                ).label('avg_duration'),
                func.sum(
                    func.extract('epoch', SessionModel.end_time - SessionModel.start_time) / 60
                ).label('total_duration'),
                func.max(
                    func.extract('epoch', SessionModel.end_time - SessionModel.start_time) / 60
                ).label('max_duration')
            ).filter(
                SessionModel.user_id == user.id,
                SessionModel.end_time.isnot(None),
                SessionModel.status == 'completed'
            )
            
            # Apply time period filter to duration query
            if cutoff_date:
                duration_query = duration_query.filter(SessionModel.start_time >= cutoff_date)
            
            duration_stats = duration_query.first()
            avg_duration = duration_stats.avg_duration if duration_stats else None
            total_duration = duration_stats.total_duration if duration_stats else None
            max_duration = duration_stats.max_duration if duration_stats else None
            
            # Recording segments statistics
            segments_query = db.query(func.count(RecordingSegment.id)).join(
                SessionModel, SessionModel.id == RecordingSegment.session_id
            ).filter(SessionModel.user_id == user.id)
            
            # Apply time period filter to segments
            if cutoff_date:
                segments_query = segments_query.filter(SessionModel.start_time >= cutoff_date)
            
            total_segments = segments_query.scalar() or 0
            
            # Count total words in transcripts
            words_query = db.query(
                func.sum(
                    func.coalesce(
                        func.length(RecordingSegment.transcript_text) - 
                        func.length(func.replace(RecordingSegment.transcript_text, ' ', '')) + 1,
                        0
                    )
                )
            ).join(
                SessionModel, SessionModel.id == RecordingSegment.session_id
            ).filter(
                SessionModel.user_id == user.id,
                RecordingSegment.transcript_text.isnot(None),
                RecordingSegment.transcript_text != ''
            )
            
            # Apply time period filter to words count
            if cutoff_date:
                words_query = words_query.filter(SessionModel.start_time >= cutoff_date)
            
            total_words = words_query.scalar()
            
            # Last session date in the time period
            last_session_query = db.query(SessionModel.start_time).filter(
                SessionModel.user_id == user.id
            )
            
            # Apply time period filter to last session
            if cutoff_date:
                last_session_query = last_session_query.filter(SessionModel.start_time >= cutoff_date)
            
            last_session = last_session_query.order_by(SessionModel.start_time.desc()).first()
            last_session_date = last_session[0] if last_session else None
            
            # Calculate days since last session
            days_since_last = None
            if last_session_date:
                days_since_last = (datetime.utcnow() - last_session_date).days
            
            # Account age in days
            account_age_days = (datetime.utcnow() - user.created_at).days
            
            analytics_list.append({
                'user_id': user.id,
                'email': user.email,
                'name': user.name,
                'username': user.username,
                'is_admin': bool(user.is_admin) if user.is_admin is not None else False,
                'is_disabled': bool(user.is_disabled) if user.is_disabled is not None else False,
                'created_at': user.created_at,
                'total_sessions': total_sessions,
                'completed_sessions': completed_sessions,
                'failed_sessions': failed_sessions,
                'deleted_sessions': deleted_sessions,
                'active_sessions': active_sessions,
                'average_session_duration': float(avg_duration) if avg_duration else None,
                'total_recording_time': float(total_duration) if total_duration else None,
                'longest_session_duration': float(max_duration) if max_duration else None,
                'total_recording_segments': total_segments,
                'total_transcribed_words': int(total_words) if total_words else None,
                'last_session_date': last_session_date,
                'days_since_last_session': days_since_last,
                'account_age_days': account_age_days
            })
        
        return analytics_list, total_users


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
