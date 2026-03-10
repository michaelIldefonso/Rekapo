"""
Pydantic Schemas for Rekapo API

Defines request/response models for data validation and serialization.
Organized by feature:
- User schemas: Authentication, profile management
- Session schemas: Meeting lifecycle
- Recording schemas: Audio segments and transcriptions
- Summary schemas: AI-generated meeting summaries
- WebSocket schemas: Real-time transcription messages
- Admin schemas: Dashboard and analytics

All schemas use Pydantic v2 with model_config for ORM compatibility.
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

# ============================================================================
# User Schemas
# Used for authentication, profile management, and consent tracking
# ============================================================================
class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    username: Optional[str] = None

class UserCreate(UserBase):
    google_id: str
    data_usage_consent: bool = True

class UserUpdate(BaseModel):
    username: Optional[str] = None
    profile_picture_path: Optional[str] = None

class UserResponse(UserBase):
    id: int
    google_id: str
    profile_picture_path: Optional[str] = None
    data_usage_consent: bool
    is_admin: Optional[bool] = None
    is_disabled: Optional[bool] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# ============================================================================
# Session Schemas
# Manages meeting lifecycle from creation to completion
# ============================================================================
class CreateSessionRequest(BaseModel):
    session_title: Optional[str] = Field(default="Untitled Meeting", max_length=255, description="Title for the meeting session")

class SessionCreate(BaseModel):
    session_title: Optional[str] = "Untitled Meeting"
    user_id: int

class SessionUpdate(BaseModel):
    session_title: Optional[str] = None
    status: Optional[str] = None
    end_time: Optional[datetime] = None

class SessionResponse(BaseModel):
    id: int
    user_id: int
    session_title: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# ============================================================================
# Recording Segment Schemas
# Handles individual audio chunks from WebSocket transcription
# Each segment has transcript (Taglish) and translation (English)
# ============================================================================
class RecordingSegmentCreate(BaseModel):
    session_id: int
    segment_number: int
    audio_path: str
    transcript_text: Optional[str] = None
    english_translation: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating 1-5")

class RecordingSegmentResponse(BaseModel):
    id: int
    session_id: int
    segment_number: int
    audio_path: str
    transcript_text: Optional[str] = None
    english_translation: Optional[str] = None
    rating: Optional[int] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class RateSegmentRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")

class RateSegmentResponse(BaseModel):
    success: bool
    message: str
    segment_id: int
    rating: int

# ============================================================================
# Summary Schemas
# AI-generated summaries produced every 10 segments or at session end
# ============================================================================
class SummaryCreate(BaseModel):
    session_id: int
    chunk_range_start: int
    chunk_range_end: int
    summary_text: str
    is_final_summary: bool = False

class SummaryResponse(BaseModel):
    id: int
    session_id: int
    chunk_range_start: int
    chunk_range_end: int
    summary_text: str
    is_final_summary: bool
    generated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# ============================================================================
# WebSocket Message Schemas
# Real-time communication between mobile app and transcription service
# ============================================================================
class AudioChunkMessage(BaseModel):
    session_id: int
    segment_number: int
    audio: str  # base64 encoded
    filename: Optional[str] = "chunk.wav"
    language: Optional[str] = None  # Auto-detect or specify
    model: Optional[str] = "small"

class TranscriptionResponse(BaseModel):
    status: str  # processing, success, error
    message: str
    session_id: Optional[int] = None
    segment_number: Optional[int] = None
    transcription: Optional[str] = None  # Taglish
    english_translation: Optional[str] = None
    language: Optional[str] = None
    language_probability: Optional[float] = None
    duration: Optional[float] = None
    segments: Optional[List[dict]] = None

# ============================================================================
# User Profile Update Schemas
# Mobile API schemas for profile customization
# ============================================================================
class ChangeUsernameRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="New username (3-50 characters)")

class ChangeUsernameResponse(BaseModel):
    success: bool
    message: str
    username: str

class UploadProfilePhotoResponse(BaseModel):
    success: bool
    message: str
    profile_picture_path: str

class DataUsageConsentRequest(BaseModel):
    data_usage_consent: bool = Field(..., description="Whether user consents to data usage")

class DataUsageConsentResponse(BaseModel):
    success: bool
    message: str
    data_usage_consent: bool

# ============================================================================
# Session History Detail Schemas
# Fetch complete session data with segments, transcriptions, and summaries
# Used by mobile app's session history screen
# ============================================================================
class SessionRecordingSegmentResponse(BaseModel):
    id: int
    segment_number: int
    audio_path: str
    transcript_text: Optional[str] = None
    english_translation: Optional[str] = None
    rating: Optional[int] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class SessionSummaryResponse(BaseModel):
    id: int
    chunk_range_start: int
    chunk_range_end: int
    summary_text: str
    is_final_summary: bool
    generated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class SessionDetailResponse(BaseModel):
    # Session info
    id: int
    user_id: int
    session_title: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str
    created_at: datetime
    
    # Related data
    recording_segments: List[SessionRecordingSegmentResponse] = []
    summaries: List[SessionSummaryResponse] = []
    
    # Statistics
    total_segments: int = 0
    total_duration: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)
