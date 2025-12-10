import os
import dotenv
from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
from datetime import datetime
import time
from db.db import get_db, User
from utils.utils import get_logger, mask_email
from schemas.schemas import UserResponse
from admin.schemas import AdminAuthResponse
from admin.utils import generate_admin_token, verify_admin_token, get_current_admin, security

dotenv.load_dotenv()

router = APIRouter()
logger = get_logger(__name__)

# Google OAuth2 configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("ADMIN_REDIRECT_URI", "http://localhost:8000/admin/auth/callback")
ADMIN_FRONTEND_URL = os.getenv("ADMIN_FRONTEND_URL", "http://localhost:3000")

# OAuth2 scopes
SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]


def create_oauth_flow():
    """Create and configure Google OAuth2 flow"""
    return Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI]
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )


@router.get("/admin/auth/login")
async def admin_login():
    """
    Initiate Google OAuth2 login flow for admin users.
    Redirects to Google's consent screen.
    """
    logger.info("=== Admin login initiated ===")
    
    try:
        flow = create_oauth_flow()
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='select_account'
        )
        
        logger.info("Generated authorization URL with state: %s", state[:10] + "...")
        return {
            "authorization_url": authorization_url,
            "state": state
        }
    except Exception as e:
        logger.error("Failed to create OAuth flow: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate authentication"
        )


@router.get("/admin/auth/callback")
async def admin_callback(request: Request, db: Session = Depends(get_db)):
    """
    Handle OAuth2 callback from Google.
    Exchanges authorization code for tokens and creates/updates admin user.
    """
    logger.info("=== Admin OAuth2 callback received ===")
    
    # Get the full callback URL
    code = request.query_params.get('code')
    state = request.query_params.get('state')
    error = request.query_params.get('error')
    
    if error:
        logger.warning("OAuth2 error received: %s", error)
        return RedirectResponse(
            url=f"{ADMIN_FRONTEND_URL}/login?error={error}"
        )
    
    if not code:
        logger.warning("No authorization code received")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code not provided"
        )
    
    try:
        # Exchange authorization code for tokens
        logger.info("Exchanging authorization code for tokens...")
        flow = create_oauth_flow()
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        
        # Verify the ID token and get user info
        # Add a short retry loop to tolerate small clock skew between machines
        logger.info("Verifying ID token...")
        idinfo = None
        verify_exception = None
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                idinfo = id_token.verify_oauth2_token(
                    credentials.id_token,
                    grequests.Request(),
                    GOOGLE_CLIENT_ID
                )
                verify_exception = None
                break
            except Exception as ex:
                verify_exception = ex
                msg = str(ex)
                logger.warning("ID token verification attempt %s failed: %s", attempt, msg)
                # If token is 'used too early' it's likely a small clock skew; retry briefly
                if "Token used too early" in msg or "token used too early" in msg.lower():
                    if attempt < max_attempts:
                        wait = 2
                        logger.info("Token appears from the future (clock skew). Waiting %s seconds before retry...", wait)
                        time.sleep(wait)
                        continue
                # For other errors, stop retrying
                break
        if idinfo is None:
            logger.error("ID token verification ultimately failed: %s", verify_exception)
            raise verify_exception
        
        if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
            raise ValueError("Wrong issuer")
        
        logger.info("✓ ID token verified - Email: %s", mask_email(idinfo.get("email")))
        
        # Extract user information
        google_id = idinfo["sub"]
        email = idinfo["email"]
        name = idinfo.get("name")
        picture = idinfo.get("picture")
        
        # Check if user exists
        user = db.query(User).filter_by(google_id=google_id).first()
        
        if not user:
            # Create new user (non-admin by default)
            logger.info("Creating new user account (non-admin)")
            user = User(
                google_id=google_id,
                email=email,
                name=name,
                profile_picture_path=picture,
                data_usage_consent=True,
                is_admin=False,  # Create as non-admin by default
                created_at=datetime.utcnow(),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info("✓ New user created - ID: %s (non-admin)", user.id)
        else:
            logger.info("Existing user found - ID: %s, Is Admin: %s", user.id, user.is_admin)
        
        # Check if user is admin
        if not user.is_admin:
            logger.warning("⚠️ Non-admin user attempted admin login - ID: %s", user.id)
            return RedirectResponse(
                url=f"{ADMIN_FRONTEND_URL}/login?error=unauthorized"
            )
        
        # Check if account is disabled
        if user.is_disabled:
            logger.warning("⚠️ Disabled admin attempted login - ID: %s", user.id)
            return RedirectResponse(
                url=f"{ADMIN_FRONTEND_URL}/login?error=account_disabled"
            )
        
        # Generate JWT token
        logger.info("Generating JWT token for admin user ID: %s", user.id)
        access_token = generate_admin_token(user)
        
        logger.info("✓ Admin authentication successful - Redirecting to frontend")
        
        # Redirect to frontend with token
        return RedirectResponse(
            url=f"{ADMIN_FRONTEND_URL}/auth/success?token={access_token}"
        )
        
    except Exception as e:
        logger.error("Admin authentication failed: %s", str(e))
        return RedirectResponse(
            url=f"{ADMIN_FRONTEND_URL}/login?error=auth_failed"
        )


@router.post("/admin/auth/verify", response_model=AdminAuthResponse)
async def verify_token(
    current_admin: User = Depends(get_current_admin)
):
    """
    Verify admin JWT token and return user information.
    Used by frontend to validate stored tokens.
    """
    logger.info("=== Admin token verified - User ID: %s ===", current_admin.id)
    
    # Generate a fresh token
    access_token = generate_admin_token(current_admin)
    
    return AdminAuthResponse(
        access_token=access_token,
        user=UserResponse.model_validate(current_admin)
    )


@router.post("/admin/auth/logout")
async def admin_logout(current_user: User = Depends(get_current_admin)):
    """
    Logout endpoint (client should discard token).
    """
    logger.info("Admin user logged out - ID: %s", current_user.id)
    return {"message": "Logged out successfully"}
