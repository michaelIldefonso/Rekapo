from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    username: Optional[str] = None

class UserCreate(UserBase):
    google_id: str
    data_usage_consent: bool = False

class UserUpdate(BaseModel):
    username: Optional[str] = None
    profile_picture_path: Optional[str] = None

class UserResponse(UserBase):
    id: int
    google_id: str
    profile_picture_path: Optional[str] = None
    is_admin: bool
    is_disabled: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Session Schemas
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
    
    class Config:
        from_attributes = True

# Recording Segment Schemas
class RecordingSegmentCreate(BaseModel):
    session_id: int
    segment_number: int
    audio_path: str
    transcript_text: Optional[str] = None
    english_translation: Optional[str] = None

class RecordingSegmentResponse(BaseModel):
    id: int
    session_id: int
    segment_number: int
    audio_path: str
    transcript_text: Optional[str] = None
    english_translation: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Summary Schemas
class SummaryCreate(BaseModel):
    session_id: int
    chunk_range_start: int
    chunk_range_end: int
    summary_text: str

class SummaryResponse(BaseModel):
    id: int
    session_id: int
    chunk_range_start: int
    chunk_range_end: int
    summary_text: str
    generated_at: datetime
    
    class Config:
        from_attributes = True

# WebSocket Message Schemas
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
