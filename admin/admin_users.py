import os
import dotenv
from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from db.db import get_db, User
from utils.utils import get_logger, mask_email, safe_user_log_dict
from schemas.schemas import UserResponse
from admin.schemas import UserListResponse, DisableUserRequest, UpdateAdminStatusRequest, UserAnalyticsResponse
from admin.utils import get_current_admin, validate_user_operation
from admin.services import AdminUserService

dotenv.load_dotenv()

router = APIRouter()
logger = get_logger(__name__)


@router.get("/admin/users", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by user ID (numeric), email, name, or username"),
    is_admin: Optional[bool] = Query(None, description="Filter by admin status"),
    is_disabled: Optional[bool] = Query(None, description="Filter by disabled status"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of users with optional filters.
    Admin-only endpoint - powers User Management screen with search and filters.
    
    Search:
    - Numeric input: Search by exact user ID
    - Text input: Search by email, name, or username (partial match, case-insensitive)
    
    Admin access required.
    """
    logger.info("=== Admin listing users - Admin ID: %s ===", current_admin.id)
    
    users, total = AdminUserService.get_users_paginated(
        db=db,
        page=page,
        page_size=page_size,
        search=search,
        is_admin=is_admin,
        is_disabled=is_disabled
    )
    
    logger.info("✓ Retrieved %d users (page %d of ~%d)", 
                len(users), page, (total + page_size - 1) // page_size)
    
    return UserListResponse(
        total=total,
        page=page,
        page_size=page_size,
        users=[UserResponse.model_validate(user) for user in users]
    )


@router.get("/admin/users/{user_id}", response_model=UserResponse)
async def get_user_details(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific user.
    Admin-only endpoint - retrieves full user profile and metadata.
    """
    logger.info("=== Admin viewing user details - Admin ID: %s, User ID: %s ===", 
                current_admin.id, user_id)
    
    user = AdminUserService.get_user_by_id(db, user_id)
    
    if not user:
        logger.warning("User not found: %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    logger.info("✓ Retrieved user details: %s", safe_user_log_dict(user))
    return UserResponse.model_validate(user)


@router.post("/admin/users/{user_id}/disable", response_model=UserResponse)
async def disable_user(
    user_id: int,
    request: DisableUserRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Disable a user account.
    Admin-only endpoint - prevents user login and marks account as disabled.
    """
    logger.info("=== Admin disabling user - Admin ID: %s, Target User ID: %s ===", 
                current_admin.id, user_id)
    
    # Prevent self-disable
    validate_user_operation(user_id, current_admin, "disable")
    
    user = AdminUserService.get_user_by_id(db, user_id)
    
    if not user:
        logger.warning("User not found: %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.is_disabled:
        logger.warning("User already disabled: %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is already disabled"
        )
    
    # Disable the user
    user = AdminUserService.disable_user(db, user, current_admin.id, request.reason)
    
    logger.info("✓ User disabled - ID: %s, Email: %s, Reason: %s", 
                user.id, mask_email(user.email), request.reason)
    
    return UserResponse.model_validate(user)


@router.post("/admin/users/{user_id}/enable", response_model=UserResponse)
async def enable_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Enable a previously disabled user account.
    Admin access required.
    """
    logger.info("=== Admin enabling user - Admin ID: %s, Target User ID: %s ===", 
                current_admin.id, user_id)
    
    user = AdminUserService.get_user_by_id(db, user_id)
    
    if not user:
        logger.warning("User not found: %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_disabled:
        logger.warning("User is not disabled: %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is not disabled"
        )
    
    # Enable the user
    user = AdminUserService.enable_user(db, user)
    
    logger.info("✓ User enabled - ID: %s, Email: %s", 
                user.id, mask_email(user.email))
    
    return UserResponse.model_validate(user)


@router.patch("/admin/users/{user_id}/admin-status", response_model=UserResponse)
async def update_admin_status(
    user_id: int,
    request: UpdateAdminStatusRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update admin status of a user (promote/demote).
    Admin access required.
    """
    logger.info("=== Admin updating admin status - Admin ID: %s, Target User ID: %s, New Status: %s ===", 
                current_admin.id, user_id, request.is_admin)
    
    # Prevent self-demotion
    validate_user_operation(user_id, current_admin, "demote")
    
    user = AdminUserService.get_user_by_id(db, user_id)
    
    if not user:
        logger.warning("User not found: %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.is_admin == request.is_admin:
        logger.warning("User already has admin status: %s", request.is_admin)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User is already {'an admin' if request.is_admin else 'not an admin'}"
        )
    
    # Update admin status
    user = AdminUserService.update_admin_status(db, user, request.is_admin)
    
    action = "promoted to admin" if request.is_admin else "demoted from admin"
    logger.info("✓ User %s - ID: %s, Email: %s", 
                action, user.id, mask_email(user.email))
    
    return UserResponse.model_validate(user)


@router.get("/admin/users/{user_id}/analytics", response_model=UserAnalyticsResponse)
async def get_user_analytics(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive analytics and statistics for a specific user.
    Includes session counts, duration statistics, segments, and activity metrics.
    Admin access required.
    """
    logger.info("=== Admin viewing user analytics - Admin ID: %s, User ID: %s ===", 
                current_admin.id, user_id)
    
    analytics = AdminUserService.get_user_analytics(db, user_id)
    
    if not analytics:
        logger.warning("User not found: %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    logger.info("✓ Retrieved analytics for user: %s (Sessions: %s, Segments: %s)", 
                user_id, analytics['total_sessions'], analytics['total_recording_segments'])
    
    return UserAnalyticsResponse(**analytics)


@router.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Permanently delete a user account and all associated data.
    Admin access required. Use with caution.
    """
    logger.info("=== Admin deleting user - Admin ID: %s, Target User ID: %s ===", 
                current_admin.id, user_id)
    
    # Prevent self-deletion
    validate_user_operation(user_id, current_admin, "delete")
    
    user = AdminUserService.get_user_by_id(db, user_id)
    
    if not user:
        logger.warning("User not found: %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user_email = user.email
    
    # Delete user (cascade will handle related records)
    AdminUserService.delete_user(db, user)
    
    logger.info("✓ User permanently deleted - ID: %s, Email: %s", 
                user_id, mask_email(user_email))
    
    return {"message": "User deleted successfully", "user_id": user_id}
