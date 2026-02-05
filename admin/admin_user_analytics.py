import os
import dotenv
from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session
from typing import Optional, Literal
from db.db import get_db, User
from utils.utils import get_logger
from admin.schemas import UserAnalyticsListResponse, UserAnalyticsResponse
from admin.utils import get_current_admin
from admin.services import AdminUserService

dotenv.load_dotenv()

router = APIRouter()
logger = get_logger(__name__)


@router.get("/admin/analytics/users", response_model=UserAnalyticsListResponse)
async def get_users_analytics(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    time_period: Literal["24h", "7d", "30d", "90d", "all"] = Query("all", description="Time period for analytics"),
    search: Optional[str] = Query(None, description="Search by user ID, email, name, or username"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive analytics for all users with optional time period filtering and search.
    
    Search:
    - Numeric input: Search by user ID
    - Text input: Search by email, name, or username (partial match, case-insensitive)
    
    Time periods:
    - 24h: Last 24 hours
    - 7d: Last 7 days
    - 30d: Last 30 days
    - 90d: Last 90 days
    - all: All time (default)
    
    Metrics calculated on backend:
    - Total sessions, completed, failed, active, deleted
    - Average session duration
    - Total recording time
    - Longest session duration
    - Total recording segments
    - Total transcribed words
    - Last session date
    - Days since last session
    - Account age
    
    Admin access required.
    """
    logger.info("=== Admin requesting users analytics - Admin ID: %s, Time Period: %s, Search: %s ===", 
                current_admin.id, time_period, search)
    
    # Map time period string to days
    time_period_map = {
        "24h": 1,
        "7d": 7,
        "30d": 30,
        "90d": 90,
        "all": None
    }
    
    time_period_days = time_period_map[time_period]
    
    # Get analytics for all users
    analytics_list, total = AdminUserService.get_all_users_analytics(
        db=db,
        page=page,
        page_size=page_size,
        time_period_days=time_period_days,
        search=search
    )
    
    logger.info("✓ Retrieved analytics for %d users (page %d of ~%d, period: %s)", 
                len(analytics_list), page, (total + page_size - 1) // page_size, time_period)
    
    return UserAnalyticsListResponse(
        total=total,
        page=page,
        page_size=page_size,
        time_period=time_period,
        analytics=[UserAnalyticsResponse(**analytics) for analytics in analytics_list]
    )
