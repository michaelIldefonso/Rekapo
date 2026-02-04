from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import date, datetime
from schemas.schemas import UserResponse


class AdminAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    users: List[UserResponse]


class DisableUserRequest(BaseModel):
    reason: str


class EnableUserRequest(BaseModel):
    pass


class UpdateAdminStatusRequest(BaseModel):
    is_admin: bool


class UserAnalyticsResponse(BaseModel):
    user_id: int
    email: str
    name: Optional[str] = None
    username: Optional[str] = None
    is_admin: bool
    is_disabled: bool
    created_at: datetime
    
    # Session statistics
    total_sessions: int
    completed_sessions: int
    failed_sessions: int
    deleted_sessions: int
    active_sessions: int
    
    # Duration statistics (in minutes)
    average_session_duration: Optional[float] = None
    total_recording_time: Optional[float] = None
    longest_session_duration: Optional[float] = None
    
    # Segment statistics
    total_recording_segments: int
    total_transcribed_words: Optional[int] = None
    
    # Activity statistics
    last_session_date: Optional[datetime] = None
    days_since_last_session: Optional[int] = None
    account_age_days: int


class SessionUserInfo(BaseModel):
    user_id: int
    email: str
    name: Optional[str] = None
    username: Optional[str] = None
    data_usage_consent: bool


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


class SummaryResponse(BaseModel):
    id: int
    session_id: int
    chunk_range_start: int
    chunk_range_end: int
    summary_text: str
    is_final_summary: bool
    generated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class SessionDetailedResponse(BaseModel):
    id: int
    user_id: int
    session_title: str
    start_time: datetime
    end_time: Optional[datetime] = None
    is_deleted: bool
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[int] = None
    status: str
    created_at: datetime
    user: SessionUserInfo
    recording_segments: List[RecordingSegmentResponse]
    summaries: List[SummaryResponse]
    
    # Computed fields
    total_segments: int
    total_summaries: int
    session_duration_minutes: Optional[float] = None


class SessionResponse(BaseModel):
    id: int
    user_id: int
    session_title: str
    start_time: datetime
    end_time: Optional[datetime] = None
    is_deleted: bool
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[int] = None
    status: str
    created_at: datetime
    user: SessionUserInfo
    
    model_config = ConfigDict(from_attributes=True)


class SessionListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    sessions: List[SessionResponse]


class SystemStatisticsResponse(BaseModel):
    id: int
    stat_date: date
    total_users: Optional[int] = None
    active_users: Optional[int] = None
    total_sessions: Optional[int] = None
    average_session_duration: Optional[float] = None
    calculated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class SystemStatisticsListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    statistics: List[SystemStatisticsResponse]


class CreateSystemStatisticsRequest(BaseModel):
    stat_date: date
    total_users: Optional[int] = None
    active_users: Optional[int] = None
    total_sessions: Optional[int] = None
    average_session_duration: Optional[float] = None


class UpdateSystemStatisticsRequest(BaseModel):
    total_users: Optional[int] = None
    active_users: Optional[int] = None
    total_sessions: Optional[int] = None
    average_session_duration: Optional[float] = None
