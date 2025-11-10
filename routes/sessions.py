from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from db.db import get_db, Session as DBSession, User
from routes.auth import get_current_user
from schemas.schemas import (
    CreateSessionRequest,
    SessionResponse,
    SessionUpdate
)
from utils.utils import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new meeting session.
    
    - **session_title**: Optional title for the meeting (defaults to "Untitled Meeting")
    
    Returns the created session with session_id and start_time.
    """
    try:
        new_session = DBSession(
            user_id=current_user.id,
            session_title=request.session_title or "Untitled Meeting",
            start_time=datetime.now(),
            status="recording",
            created_at=datetime.now()
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        
        logger.info(f"User {current_user.id} created session {new_session.id}: '{new_session.session_title}'")
        
        return SessionResponse.model_validate(new_session)
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating session for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create session"
        )


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific session.
    
    Users can only access their own sessions.
    """
    session = db.query(DBSession).filter(
        DBSession.id == session_id,
        DBSession.user_id == current_user.id,
        DBSession.is_deleted == False
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return SessionResponse.model_validate(session)


@router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50
):
    """
    List all sessions for the current user.
    
    - **skip**: Number of sessions to skip (for pagination)
    - **limit**: Maximum number of sessions to return (default 50, max 100)
    """
    if limit > 100:
        limit = 100
    
    sessions = db.query(DBSession).filter(
        DBSession.user_id == current_user.id,
        DBSession.is_deleted == False
    ).order_by(DBSession.start_time.desc()).offset(skip).limit(limit).all()
    
    return [SessionResponse.model_validate(session) for session in sessions]


@router.patch("/sessions/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: int,
    request: SessionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a session (title, status, or end_time).
    
    - **session_title**: Update the session title
    - **status**: Update status ("recording", "completed", "failed")
    - **end_time**: Set the end time (automatically set to now if status changes to "completed")
    """
    session = db.query(DBSession).filter(
        DBSession.id == session_id,
        DBSession.user_id == current_user.id,
        DBSession.is_deleted == False
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    try:
        if request.session_title is not None:
            session.session_title = request.session_title
        
        if request.status is not None:
            if request.status not in ["recording", "completed", "failed"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid status. Must be 'recording', 'completed', or 'failed'"
                )
            session.status = request.status
            
            # Auto-set end_time when marking as completed or failed
            if request.status in ["completed", "failed"] and not session.end_time:
                session.end_time = datetime.now()
        
        if request.end_time is not None:
            session.end_time = request.end_time
        
        db.commit()
        db.refresh(session)
        
        logger.info(f"User {current_user.id} updated session {session_id}")
        
        return SessionResponse.model_validate(session)
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update session"
        )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Soft delete a session (marks as deleted, doesn't actually delete from database).
    """
    session = db.query(DBSession).filter(
        DBSession.id == session_id,
        DBSession.user_id == current_user.id,
        DBSession.is_deleted == False
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    try:
        session.is_deleted = True
        session.deleted_at = datetime.now()
        session.deleted_by = current_user.id
        
        db.commit()
        
        logger.info(f"User {current_user.id} deleted session {session_id}")
        
        return {
            "success": True,
            "message": "Session deleted successfully"
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete session"
        )
