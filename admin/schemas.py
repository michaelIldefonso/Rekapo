from pydantic import BaseModel
from typing import Optional, List
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
