import os
import dotenv
from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from db.db import get_db, User, Session as SessionModel
from utils.utils import get_logger
from admin.schemas import SessionResponse, SessionListResponse, SessionDetailedResponse
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
    session_title: Optional[str] = Query(None, description="Search by session title"),
    training_consent: Optional[bool] = Query(None, description="Filter by user's training consent"),
    require_consent: bool = Query(False, description="If true, ONLY return sessions with training consent=true"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of sessions with optional filters.
    Set require_consent=true to enforce training consent (cannot be bypassed).
    Admin access required.
    """
    logger.info("=== Admin listing sessions - Admin ID: %s ===", current_admin.id)
    
    # If require_consent is True, force training_consent to True and exclude deleted
    if require_consent:
        training_consent = True
        is_deleted = False
        logger.info("Training consent enforcement enabled - only returning consented sessions")
    
    sessions, total = AdminSessionService.get_sessions_paginated(
        db=db,
        page=page,
        page_size=page_size,
        user_id=user_id,
        status=status,
        is_deleted=is_deleted,
        session_title=session_title,
        training_consent=training_consent
    )
    
    logger.info("✓ Retrieved %d sessions (page %d of ~%d)", 
                len(sessions), page, (total + page_size - 1) // page_size)
    
    return SessionListResponse(
        total=total,
        page=page,
        page_size=page_size,
        sessions=[SessionResponse(**session) for session in sessions]
    )


@router.get("/admin/sessions/{session_id}/detailed", response_model=SessionDetailedResponse)
async def get_session_detailed(
    session_id: int,
    require_consent: bool = Query(False, description="If true, return 403 if user hasn't consented to training"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive session details including all recording segments,
    transcriptions, translations, audio paths, and summaries.
    Set require_consent=true to enforce training consent check (returns 403 if not consented).
    Admin access required.
    """
    logger.info("=== Admin viewing detailed session - Admin ID: %s, Session ID: %s ===", 
                current_admin.id, session_id)
    
    session = AdminSessionService.get_session_detailed(db, session_id)
    
    if not session:
        logger.warning("Session not found: %s", session_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # If require_consent is True, enforce training consent check
    if require_consent and not session['user']['data_usage_consent']:
        logger.warning("Access denied - User has not consented to training data usage - Session ID: %s", session_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: User has not consented to training data usage"
        )
    
    logger.info("✓ Retrieved detailed session - ID: %s, Segments: %s, Summaries: %s", 
                session['id'], session['total_segments'], session['total_summaries'])
    
    return SessionDetailedResponse(**session)


@router.get("/admin/training-data/sessions/{session_id}", response_model=SessionDetailedResponse)
async def get_training_session_data(
    session_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get complete session data for AI training purposes.
    Returns all recording segments, audio paths, transcriptions, translations, and summaries.
    
    SECURITY: This endpoint ALWAYS enforces training consent check.
    Returns 403 Forbidden if user has not consented to training data usage.
    Cannot be bypassed.
    
    Admin access required.
    """
    logger.info("=== Admin accessing training data - Admin ID: %s, Session ID: %s ===", 
                current_admin.id, session_id)
    
    session = AdminSessionService.get_session_detailed(db, session_id)
    
    if not session:
        logger.warning("Session not found: %s", session_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # ALWAYS enforce training consent check - cannot be bypassed
    if not session['user']['data_usage_consent']:
        logger.warning("Training data access denied - User has not consented - Session ID: %s, User ID: %s", 
                      session_id, session['user_id'])
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: User has not consented to training data usage"
        )
    
    # Note: Deleted sessions ARE allowed for training if user has consented
    # Soft delete is for UI cleanup, doesn't revoke training consent
    logger.info("✓ Training data access granted - Session ID: %s, Segments: %s, Summaries: %s, Deleted: %s", 
                session['id'], session['total_segments'], session['total_summaries'], session['is_deleted'])
    
    return SessionDetailedResponse(**session)


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
    
    session_data = AdminSessionService.get_session_by_id(db, session_id)
    
    if not session_data:
        logger.warning("Session not found: %s", session_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if session_data['is_deleted']:
        logger.warning("Session already deleted: %s", session_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is already deleted"
        )
    
    # Get the actual session object for deletion
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    
    # Soft delete the session
    session = AdminSessionService.delete_session(db, session, current_admin.id)
    
    logger.info("✓ Session soft deleted - ID: %s, User ID: %s", 
                session.id, session.user_id)
    
    return {"message": "Session deleted successfully", "session_id": session_id}
