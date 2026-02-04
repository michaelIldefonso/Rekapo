from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from db.db import get_db, Session as DBSession, User, RecordingSegment, Summary
from routes.auth import get_current_user
from schemas.schemas import (
    CreateSessionRequest,
    SessionResponse,
    SessionUpdate,
    SessionDetailResponse,
    SessionRecordingSegmentResponse,
    SessionSummaryResponse
)
from utils.utils import get_logger
from ai_models.summarizer.inference import summarize_transcriptions, clear_summarizer_cache

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
    
    # Fix sessions with missing created_at
    for session in sessions:
        if session.created_at is None:
            session.created_at = datetime.now()
    db.commit()
    
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
    - **end_time**: Set the end time (automatically set to now if status changes to "completed" or "failed")
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


@router.get("/sessions/{session_id}/details", response_model=SessionDetailResponse)
async def get_session_details(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get complete session details including all recording segments, transcriptions, 
    translations, and summaries.
    
    Returns:
    - Session basic information (title, start/end time, status)
    - All recording segments with transcription and translation
    - All generated summaries
    - Statistics (total segments, total duration)
    
    Users can only access their own sessions.
    """
    # Fetch session with relationships
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
    
    # Fix missing created_at
    if session.created_at is None:
        session.created_at = datetime.now()
        db.commit()
    
    # Fetch all recording segments ordered by segment_number
    recording_segments = db.query(RecordingSegment).filter(
        RecordingSegment.session_id == session_id
    ).order_by(RecordingSegment.segment_number).all()
    
    # Fix segments with missing created_at
    for segment in recording_segments:
        if segment.created_at is None:
            segment.created_at = datetime.now()
    
    # Fetch all summaries ordered by chunk_range_start
    summaries = db.query(Summary).filter(
        Summary.session_id == session_id
    ).order_by(Summary.chunk_range_start).all()
    
    # Commit any timestamp fixes
    db.commit()
    
    # Calculate total duration from segments (if available)
    total_duration = None
    # Note: Duration is not stored in RecordingSegment, so we'll leave it as None
    # If you want to add duration tracking, add a 'duration' column to RecordingSegment
    
    # Build response
    response_data = {
        "id": session.id,
        "user_id": session.user_id,
        "session_title": session.session_title,
        "start_time": session.start_time,
        "end_time": session.end_time,
        "status": session.status,
        "created_at": session.created_at,
        "recording_segments": [
            SessionRecordingSegmentResponse.model_validate(segment)
            for segment in recording_segments
        ],
        "summaries": [
            SessionSummaryResponse.model_validate(summary)
            for summary in summaries
        ],
        "total_segments": len(recording_segments),
        "total_duration": total_duration
    }
    
    logger.info(f"User {current_user.id} accessed details for session {session_id}")
    
    return SessionDetailResponse(**response_data)


@router.post("/sessions/{session_id}/generate-summary")
async def generate_full_session_summary(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a full session summary from ALL segments.
    
    This should be called when the session is marked as "completed".
    Unlike the periodic 10-segment summaries, this creates a comprehensive
    summary of the entire meeting by processing all recording segments.
    
    Returns the generated summary with metadata.
    """
    # Verify session exists and belongs to user
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
        # Fetch all recording segments with translations
        segments = db.query(RecordingSegment).filter(
            RecordingSegment.session_id == session_id
        ).order_by(RecordingSegment.segment_number).all()
        
        if not segments:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No segments found for this session"
            )
        
        logger.info(f"Generating full session summary for session {session_id} with {len(segments)} segments")
        
        # Prepare transcriptions for summarization
        transcriptions = [
            {
                "segment_number": seg.segment_number,
                "transcription": seg.transcript_text,
                "english_translation": seg.english_translation or seg.transcript_text
            }
            for seg in segments
        ]
        
        # Generate comprehensive summary of ALL segments
        summary_result = summarize_transcriptions(
            transcriptions=transcriptions,
            device="cuda",
            max_length=400,  # Longer summary for full session
            min_length=100
        )
        
        # Save the full session summary to database
        # Use special markers: chunk_range_start=0, chunk_range_end=-1 to indicate full session summary
        full_summary = Summary(
            session_id=session_id,
            chunk_range_start=0,
            chunk_range_end=len(segments),
            summary_text=summary_result["summary"]
        )
        db.add(full_summary)
        db.commit()
        db.refresh(full_summary)
        
        logger.info(f"Full session summary generated and saved for session {session_id}")
        
        return {
            "success": True,
            "message": "Full session summary generated successfully",
            "summary": {
                "id": full_summary.id,
                "session_id": session_id,
                "chunk_range_start": 0,
                "chunk_range_end": len(segments),
                "summary_text": summary_result["summary"],
                "generated_at": full_summary.generated_at,
                "is_full_session_summary": True
            },
            "metadata": {
                "total_segments": len(segments),
                "original_length": summary_result["original_length"]
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error generating full session summary for session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate session summary: {str(e)}"
        )
    finally:
        # Always clear Qwen cache after summarization to free GPU memory
        logger.info("Clearing summarizer cache to free GPU memory...")
        clear_summarizer_cache()
