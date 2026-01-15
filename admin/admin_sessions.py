import os
import dotenv
from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from db.db import get_db, User
from utils.utils import get_logger
from admin.schemas import SessionResponse, SessionListResponse
from admin.utils import get_current_admin
from admin.services import AdminSessionService

dotenv.load_dotenv()

router = APIRouter()
logger = get_logger(__name__)


@router.get("/admin/sessions", response_model=SessionListResponse)
async def list_sessions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    status: Optional[str] = Query(None, description="Filter by status (recording, completed, failed)"),
    is_deleted: Optional[bool] = Query(None, description="Filter by deleted status"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of sessions with optional filters.
    Admin access required.
    """
    logger.info("=== Admin listing sessions - Admin ID: %s ===", current_admin.id)
    
    sessions, total = AdminSessionService.get_sessions_paginated(
        db=db,
        page=page,
        page_size=page_size,
        user_id=user_id,
        status=status,
        is_deleted=is_deleted
    )
    
    logger.info("✓ Retrieved %d sessions (page %d of ~%d)", 
                len(sessions), page, (total + page_size - 1) // page_size)
    
    return SessionListResponse(
        total=total,
        page=page,
        page_size=page_size,
        sessions=[SessionResponse.model_validate(session) for session in sessions]
    )


@router.get("/admin/sessions/{session_id}", response_model=SessionResponse)
async def get_session_details(
    session_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific session.
    Admin access required.
    """
    logger.info("=== Admin viewing session details - Admin ID: %s, Session ID: %s ===", 
                current_admin.id, session_id)
    
    session = AdminSessionService.get_session_by_id(db, session_id)
    
    if not session:
        logger.warning("Session not found: %s", session_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    logger.info("✓ Retrieved session details - ID: %s, User ID: %s, Status: %s", 
                session.id, session.user_id, session.status)
    
    return SessionResponse.model_validate(session)


@router.delete("/admin/sessions/{session_id}")
async def delete_session(
    session_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Soft delete a session (mark as deleted).
    Admin access required.
    """
    logger.info("=== Admin deleting session - Admin ID: %s, Session ID: %s ===", 
                current_admin.id, session_id)
    
    session = AdminSessionService.get_session_by_id(db, session_id)
    
    if not session:
        logger.warning("Session not found: %s", session_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if session.is_deleted:
        logger.warning("Session already deleted: %s", session_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is already deleted"
        )
    
    # Soft delete the session
    session = AdminSessionService.delete_session(db, session, current_admin.id)
    
    logger.info("✓ Session soft deleted - ID: %s, User ID: %s", 
                session.id, session.user_id)
    
    return {"message": "Session deleted successfully", "session_id": session_id}
