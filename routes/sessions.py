from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from db.db import get_db, SessionLocal, Session as DBSession, User, RecordingSegment, Summary
from routes.auth import get_current_user
from schemas.schemas import (
    CreateSessionRequest,
    SessionResponse,
    SessionUpdate,
    SessionDetailResponse,
    SessionRecordingSegmentResponse,
    SessionSummaryResponse,
    RateSegmentRequest,
    RateSegmentResponse
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
    background_tasks: BackgroundTasks,
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
    
    # Fix summaries with missing generated_at and is_final_summary
    for summary in summaries:
        if summary.generated_at is None:
            summary.generated_at = datetime.now()
        # Fix missing is_final_summary for old summaries (set default for NULL values)
        if summary.is_final_summary is None:
            summary.is_final_summary = False  # Default old summaries to intermediate
    
    # Commit any timestamp fixes
    db.commit()
    
    # Check if completed session needs a final summary (for old recordings)
    has_final_summary = any(s.is_final_summary for s in summaries)
    if session.status == "completed" and not has_final_summary and len(recording_segments) > 0:
        logger.info(f"Session {session_id} completed but has no final summary - triggering generation")
        
        # Define background task function
        def generate_summary_background():
            try:
                print(f"📝 Generating missing final summary for old session {session_id}...")
                generate_session_summary_logic(session_id)
                print(f"✅ Final summary generated for old session {session_id}")
            except Exception as e:
                print(f"❌ Failed to generate final summary for session {session_id}: {e}")
        
        # Add to FastAPI background tasks (runs after response is sent)
        background_tasks.add_task(generate_summary_background)
        logger.info(f"⚡ Final summary generation queued for old session {session_id}")
    
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


@router.patch("/sessions/{session_id}/segments/{segment_id}/rate", response_model=RateSegmentResponse)
async def rate_segment(
    session_id: int,
    segment_id: int,
    request: RateSegmentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Rate a recording segment for transcription quality.
    
    - **session_id**: The session ID that contains the segment
    - **segment_id**: The segment ID to rate
    - **rating**: Quality rating from 1 (poor) to 5 (excellent)
    
    Users can only rate segments from their own sessions.
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
    
    # Fetch the segment
    segment = db.query(RecordingSegment).filter(
        RecordingSegment.id == segment_id,
        RecordingSegment.session_id == session_id
    ).first()
    
    if not segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Segment not found"
        )
    
    # Update the rating
    segment.rating = request.rating
    db.commit()
    
    logger.info(f"User {current_user.id} rated segment {segment_id} (session {session_id}) with {request.rating} stars")
    
    return RateSegmentResponse(
        success=True,
        message=f"Segment rated successfully",
        segment_id=segment_id,
        rating=request.rating
    )


def generate_session_summary_logic(session_id: int):
    """
    Core logic to generate final session summary.
    Can be called from API endpoint or background task.
    
    Returns dict with summary result or raises exception.
    """
    db = SessionLocal()
    try:
        # Check if final summary already exists
        existing_final = db.query(Summary).filter(
            Summary.session_id == session_id,
            Summary.is_final_summary == True
        ).first()
        
        if existing_final:
            logger.info(f"Final summary already exists for session {session_id}, returning cached version")
            return {
                "success": True,
                "message": "Final summary retrieved (cached)",
                "summary": {
                    "id": existing_final.id,
                    "session_id": session_id,
                    "chunk_range_start": existing_final.chunk_range_start,
                    "chunk_range_end": existing_final.chunk_range_end,
                    "summary_text": existing_final.summary_text,
                    "generated_at": existing_final.generated_at,
                    "is_final_summary": True
                },
                "metadata": {
                    "was_cached": True
                }
            }
        
        # Fetch all recording segments
        segments = db.query(RecordingSegment).filter(
            RecordingSegment.session_id == session_id
        ).order_by(RecordingSegment.segment_number).all()
        
        if not segments:
            raise ValueError("No segments found for this session")
        
        segment_count = len(segments)
        
        # Check minimum thresholds before generating summary
        # Calculate total content length
        total_text = " ".join([seg.transcript_text or "" for seg in segments])
        total_length = len(total_text.strip())
        
        # Minimum thresholds to justify loading heavy Qwen model
        MIN_SEGMENTS = 5
        MIN_TEXT_LENGTH = 200
        
        if segment_count < MIN_SEGMENTS or total_length < MIN_TEXT_LENGTH:
            logger.info(f"Skipping final summary for session {session_id}: insufficient content (segments={segment_count}, length={total_length})")
            # Create a simple concatenated summary instead of using AI
            simple_summary = " ".join([
                seg.english_translation or seg.transcript_text or ""
                for seg in segments
            ]).strip()
            
            if not simple_summary:
                simple_summary = "Session too short to generate summary."
            
            # Save minimal summary to database
            full_summary = Summary(
                session_id=session_id,
                chunk_range_start=1,
                chunk_range_end=segment_count,
                summary_text=simple_summary[:500],  # Limit to 500 chars
                is_final_summary=True
            )
            db.add(full_summary)
            db.commit()
            db.refresh(full_summary)
            
            return {
                "success": True,
                "message": "Session too short for AI summary, using simple concatenation",
                "summary": {
                    "id": full_summary.id,
                    "session_id": session_id,
                    "chunk_range_start": full_summary.chunk_range_start,
                    "chunk_range_end": full_summary.chunk_range_end,
                    "summary_text": full_summary.summary_text,
                    "generated_at": full_summary.generated_at,
                    "is_final_summary": True
                },
                "metadata": {
                    "total_segments": segment_count,
                    "total_length": total_length,
                    "summary_source": "simple_concatenation",
                    "was_cached": False,
                    "skipped_ai": True
                }
            }
        
        logger.info(f"Generating final summary for session {session_id} with {segment_count} segments")
        
        # Smart branching: Direct from segments (<100) or from intermediate summaries (>=100)
        if segment_count < 100:
            logger.info(f"Using direct summarization (segments < 100)")
            # Prepare transcriptions for summarization
            transcriptions = [
                {
                    "segment_number": seg.segment_number,
                    "transcription": seg.transcript_text,
                    "english_translation": seg.english_translation or seg.transcript_text
                }
                for seg in segments
            ]
            
            # Generate comprehensive summary directly from ALL segments
            summary_result = summarize_transcriptions(
                transcriptions=transcriptions,
                device="cuda",
                max_length=500,  # Longer summary for full session
                min_length=150
            )
            summary_source = "segments"
        else:
            logger.info(f"Using hierarchical summarization (segments >= 100, using intermediate summaries)")
            # Get all intermediate summaries
            intermediate_summaries = db.query(Summary).filter(
                Summary.session_id == session_id,
                Summary.is_final_summary == False
            ).order_by(Summary.chunk_range_start).all()
            
            if not intermediate_summaries:
                logger.warning(f"No intermediate summaries found for session {session_id}, falling back to direct summarization")
                # Fallback: summarize segments directly (risky with >100 segments but better than nothing)
                transcriptions = [
                    {
                        "segment_number": seg.segment_number,
                        "transcription": seg.transcript_text,
                        "english_translation": seg.english_translation or seg.transcript_text
                    }
                    for seg in segments
                ]
                summary_result = summarize_transcriptions(
                    transcriptions=transcriptions,
                    device="cuda",
                    max_length=500,
                    min_length=150
                )
                summary_source = "segments_fallback"
            else:
                # Prepare intermediate summaries as "transcriptions"
                summary_transcriptions = [
                    {
                        "segment_number": f"{summ.chunk_range_start}-{summ.chunk_range_end}",
                        "transcription": summ.summary_text,
                        "english_translation": summ.summary_text
                    }
                    for summ in intermediate_summaries
                ]
                
                # Generate final comprehensive summary from intermediate summaries
                summary_result = summarize_transcriptions(
                    transcriptions=summary_transcriptions,
                    device="cuda",
                    max_length=600,  # Longer for hierarchical summary
                    min_length=200
                )
                summary_source = f"intermediates ({len(intermediate_summaries)} summaries)"
        
        # Save the final summary to database
        full_summary = Summary(
            session_id=session_id,
            chunk_range_start=1,  # First segment
            chunk_range_end=segment_count,  # Last segment
            summary_text=summary_result["summary"],
            is_final_summary=True  # Mark as final comprehensive summary
        )
        db.add(full_summary)
        db.commit()
        db.refresh(full_summary)
        
        logger.info(f"Final summary generated and saved for session {session_id} (source: {summary_source})")
        
        return {
            "success": True,
            "message": "Final session summary generated successfully",
            "summary": {
                "id": full_summary.id,
                "session_id": session_id,
                "chunk_range_start": full_summary.chunk_range_start,
                "chunk_range_end": full_summary.chunk_range_end,
                "summary_text": summary_result["summary"],
                "generated_at": full_summary.generated_at,
                "is_final_summary": True
            },
            "metadata": {
                "total_segments": segment_count,
                "original_length": summary_result["original_length"],
                "summary_source": summary_source,
                "was_cached": False
            }
        }
    finally:
        # Always clear Qwen cache and close DB
        clear_summarizer_cache()
        db.close()


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
        # Call the core logic function
        result = generate_session_summary_logic(session_id)
        return result
    
    except ValueError as e:
        # No segments found
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating full session summary for session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate session summary: {str(e)}"
        )

