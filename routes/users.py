from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from db.db import get_db, User
from routes.auth import get_current_user
from schemas.schemas import (
    ChangeUsernameRequest,
    ChangeUsernameResponse,
    UploadProfilePhotoResponse,
    UserResponse
)
from utils.utils import save_profile_photo, delete_profile_photo, get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.patch("/users/me/username", response_model=ChangeUsernameResponse)
async def change_username(
    request: ChangeUsernameRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change the current user's username.
    
    - **username**: New username (3-50 characters, must be unique)
    """
    # Validate username format (alphanumeric, underscore, hyphen)
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', request.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username can only contain letters, numbers, underscores, and hyphens"
        )
    
    # Check if username is already taken by another user
    existing_user = db.query(User).filter(
        User.username == request.username,
        User.id != current_user.id
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken"
        )
    
    # Update username
    old_username = current_user.username
    current_user.username = request.username
    
    try:
        db.commit()
        db.refresh(current_user)
        logger.info(
            f"User {current_user.id} changed username from '{old_username}' to '{request.username}'"
        )
        
        return ChangeUsernameResponse(
            success=True,
            message="Username updated successfully",
            username=current_user.username
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken"
        )


@router.patch("/users/me/photo", response_model=UploadProfilePhotoResponse)
async def upload_profile_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a new profile photo for the current user.
    
    - **file**: Image file (JPG, PNG, GIF, WebP, max 5MB)
    """
    # Delete old profile photo if it exists and is a local file
    if current_user.profile_picture_path and not current_user.profile_picture_path.startswith("http"):
        delete_profile_photo(current_user.profile_picture_path)
    
    # Save new profile photo
    try:
        file_path = await save_profile_photo(file, current_user.id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving profile photo for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save profile photo"
        )
    
    # Update user's profile picture path
    current_user.profile_picture_path = file_path
    db.commit()
    db.refresh(current_user)
    
    logger.info(f"User {current_user.id} updated profile photo to {file_path}")
    
    return UploadProfilePhotoResponse(
        success=True,
        message="Profile photo updated successfully",
        profile_picture_path=file_path
    )


@router.get("/users/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get the current user's profile information.
    """
    return UserResponse.model_validate(current_user)


@router.delete("/users/me/photo")
async def delete_current_user_photo(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete the current user's profile photo.
    """
    if not current_user.profile_picture_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No profile photo to delete"
        )
    
    # Don't delete Google profile photos (they start with http)
    if current_user.profile_picture_path.startswith("http"):
        current_user.profile_picture_path = None
        db.commit()
        return {"success": True, "message": "Profile photo reference removed"}
    
    # Delete local file
    deleted = delete_profile_photo(current_user.profile_picture_path)
    current_user.profile_picture_path = None
    db.commit()
    
    logger.info(f"User {current_user.id} deleted profile photo")
    
    return {
        "success": True,
        "message": "Profile photo deleted successfully"
    }
