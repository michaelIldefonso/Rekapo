from pydantic import BaseModel
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
    
    class Config:
        from_attributes = True


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
    
    class Config:
        from_attributes = True


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
