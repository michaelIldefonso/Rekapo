import os
import dotenv
from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
from db.db import get_db, User
from utils.utils import get_logger
from admin.schemas import (
    SystemStatisticsResponse,
    SystemStatisticsListResponse,
    CreateSystemStatisticsRequest,
    UpdateSystemStatisticsRequest
)
from admin.utils import get_current_admin
from admin.services import SystemStatisticsService

dotenv.load_dotenv()

router = APIRouter()
logger = get_logger(__name__)


@router.get("/admin/statistics", response_model=SystemStatisticsListResponse)
async def list_statistics(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of system statistics with optional date filters.
    Admin access required.
    """
    logger.info("=== Admin listing system statistics - Admin ID: %s ===", current_admin.id)
    
    statistics, total = SystemStatisticsService.get_statistics_paginated(
        db=db,
        page=page,
        page_size=page_size,
        start_date=start_date,
        end_date=end_date
    )
    
    logger.info("✓ Retrieved %d statistics (page %d of ~%d)", 
                len(statistics), page, (total + page_size - 1) // page_size)
    
    return SystemStatisticsListResponse(
        total=total,
        page=page,
        page_size=page_size,
        statistics=[SystemStatisticsResponse.model_validate(stat) for stat in statistics]
    )


@router.get("/admin/statistics/{stat_id}", response_model=SystemStatisticsResponse)
async def get_statistics_by_id(
    stat_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get system statistics by ID.
    Admin access required.
    """
    logger.info("=== Admin viewing statistics - Admin ID: %s, Stat ID: %s ===", 
                current_admin.id, stat_id)
    
    stat = SystemStatisticsService.get_statistics_by_id(db, stat_id)
    
    if not stat:
        logger.warning("Statistics not found: %s", stat_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Statistics not found"
        )
    
    logger.info("✓ Retrieved statistics for date: %s", stat.stat_date)
    return SystemStatisticsResponse.model_validate(stat)


@router.get("/admin/statistics/date/{stat_date}", response_model=SystemStatisticsResponse)
async def get_statistics_by_date(
    stat_date: date,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get system statistics for a specific date.
    Admin access required.
    """
    logger.info("=== Admin viewing statistics for date - Admin ID: %s, Date: %s ===", 
                current_admin.id, stat_date)
    
    stat = SystemStatisticsService.get_statistics_by_date(db, stat_date)
    
    if not stat:
        logger.warning("Statistics not found for date: %s", stat_date)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Statistics not found for date: {stat_date}"
        )
    
    logger.info("✓ Retrieved statistics for date: %s", stat_date)
    return SystemStatisticsResponse.model_validate(stat)


@router.post("/admin/statistics", response_model=SystemStatisticsResponse, status_code=status.HTTP_201_CREATED)
async def create_statistics(
    request: CreateSystemStatisticsRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Create new system statistics entry.
    Admin access required.
    """
    logger.info("=== Admin creating statistics - Admin ID: %s, Date: %s ===", 
                current_admin.id, request.stat_date)
    
    # Check if statistics already exist for this date
    existing_stat = SystemStatisticsService.get_statistics_by_date(db, request.stat_date)
    
    if existing_stat:
        logger.warning("Statistics already exist for date: %s", request.stat_date)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Statistics already exist for date: {request.stat_date}"
        )
    
    # Create new statistics
    stat = SystemStatisticsService.create_statistics(
        db=db,
        stat_date=request.stat_date,
        total_users=request.total_users,
        active_users=request.active_users,
        total_sessions=request.total_sessions,
        average_session_duration=request.average_session_duration
    )
    
    logger.info("✓ Statistics created for date: %s", stat.stat_date)
    return SystemStatisticsResponse.model_validate(stat)


@router.put("/admin/statistics/{stat_id}", response_model=SystemStatisticsResponse)
async def update_statistics(
    stat_id: int,
    request: UpdateSystemStatisticsRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update existing system statistics entry.
    Admin access required.
    """
    logger.info("=== Admin updating statistics - Admin ID: %s, Stat ID: %s ===", 
                current_admin.id, stat_id)
    
    stat = SystemStatisticsService.get_statistics_by_id(db, stat_id)
    
    if not stat:
        logger.warning("Statistics not found: %s", stat_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Statistics not found"
        )
    
    # Update statistics
    stat = SystemStatisticsService.update_statistics(
        db=db,
        stat=stat,
        total_users=request.total_users,
        active_users=request.active_users,
        total_sessions=request.total_sessions,
        average_session_duration=request.average_session_duration
    )
    
    logger.info("✓ Statistics updated for date: %s", stat.stat_date)
    return SystemStatisticsResponse.model_validate(stat)


@router.delete("/admin/statistics/{stat_id}")
async def delete_statistics(
    stat_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Delete system statistics entry.
    Admin access required.
    """
    logger.info("=== Admin deleting statistics - Admin ID: %s, Stat ID: %s ===", 
                current_admin.id, stat_id)
    
    stat = SystemStatisticsService.get_statistics_by_id(db, stat_id)
    
    if not stat:
        logger.warning("Statistics not found: %s", stat_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Statistics not found"
        )
    
    stat_date = stat.stat_date
    
    # Delete statistics
    SystemStatisticsService.delete_statistics(db, stat)
    
    logger.info("✓ Statistics deleted for date: %s", stat_date)
    
    return {"message": "Statistics deleted successfully", "stat_id": stat_id, "stat_date": str(stat_date)}


@router.post("/admin/statistics/calculate/{stat_date}", response_model=SystemStatisticsResponse)
async def calculate_statistics(
    stat_date: date,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Calculate and store system statistics for a specific date based on actual data.
    This will compute metrics from the database for the given date.
    If statistics already exist for the date, they will be updated.
    Admin access required.
    """
    logger.info("=== Admin calculating statistics - Admin ID: %s, Date: %s ===", 
                current_admin.id, stat_date)
    
    # Calculate statistics
    stat = SystemStatisticsService.calculate_statistics_for_date(db, stat_date)
    
    logger.info("✓ Statistics calculated for date: %s - Total Users: %s, Active Users: %s, Sessions: %s, Avg Duration: %s", 
                stat.stat_date, stat.total_users, stat.active_users, stat.total_sessions, stat.average_session_duration)
    
    return SystemStatisticsResponse.model_validate(stat)
