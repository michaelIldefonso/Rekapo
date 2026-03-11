"""
Admin Authentication Module

Handles Google OAuth2 authentication for admin panel access.
Implements secure admin-only login flow with JWT token generation.

Endpoints:
- GET /admin/auth/login - Initiates OAuth flow
- GET /admin/auth/callback - Handles Google OAuth callback
- POST /admin/auth/verify - Validates stored JWT tokens
- POST /admin/auth/logout - Logout endpoint

Security:
- Only users with is_admin=True can access admin panel
- Disabled accounts are rejected
- JWT tokens for session management
- Clock skew tolerance for token verification
"""
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

# Allow HTTP for local development (OAuth requires HTTPS in production)
# Only enable this for localhost/127.0.0.1 URLs
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

router = APIRouter()
logger = get_logger(__name__)

# ============================================================================
# PKCE Code Verifier Storage
# TODO: Replace with Redis/Database for production multi-worker deployment
# ============================================================================
_code_verifiers = {}  # Temporary in-memory storage: {state: code_verifier}

# ============================================================================
# Google OAuth2 Configuration
# Set these environment variables in .env file
# GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET from Google Cloud Console
# ============================================================================
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("ADMIN_REDIRECT_URI", "http://localhost:8000/admin/auth/callback")
ADMIN_FRONTEND_URL = os.getenv("ADMIN_FRONTEND_URL", "http://localhost:3000")

# OAuth2 scopes - request email and profile information
SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

# ============================================================================
# Helper Functions
# ============================================================================

def create_oauth_flow():
    """
    Create and configure Google OAuth2 flow.
    Used by both login initiation and callback handling.
    """
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

# ============================================================================
# Admin Authentication Endpoints
# ============================================================================

@router.get("/admin/auth/login")
async def admin_login():
    """
    ADMIN ENDPOINT: Initiate Google OAuth2 login flow.
    
    Flow:
    1. Generate authorization URL with state parameter
    2. Frontend redirects user to Google consent screen
    3. User approves access
    4. Google redirects to /admin/auth/callback
    
    Returns:
        authorization_url: URL to redirect user to
        state: Security state parameter
    """
    logger.info("=== Admin login initiated ===")
    
    try:
        flow = create_oauth_flow()
        
        # Generate authorization URL with PKCE
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='select_account'
        )
        
        # Store code_verifier for later use in callback
        if hasattr(flow, 'code_verifier'):
            _code_verifiers[state] = flow.code_verifier
            logger.info("Stored code_verifier for state: %s", state[:10] + "...")
        
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
    ADMIN ENDPOINT: Handle OAuth2 callback from Google.
    
    Flow:
    1. Receive authorization code from Google
    2. Exchange code for ID token and access token
    3. Verify ID token signature and claims
    4. Check if user exists and is admin
    5. Generate JWT token for admin session
    6. Redirect to frontend with token
    
    Security checks:
    - Verifies user.is_admin=True
    - Rejects disabled accounts
    - Includes clock skew tolerance for token verification
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
        # Exchange authorization code for tokens from Google
        logger.info("Exchanging authorization code for tokens...")
        flow = create_oauth_flow()
        
        # Restore code_verifier if it was stored (PKCE support)
        if state and state in _code_verifiers:
            flow.code_verifier = _code_verifiers.pop(state)
            logger.info("Restored code_verifier for state: %s", state[:10] + "...")
        
        # Use the full authorization response URL
        authorization_response = str(request.url)
        flow.fetch_token(authorization_response=authorization_response)
        
        credentials = flow.credentials
        
        # Verify the ID token signature and claims
        # Add clock skew tolerance to handle time differences between servers
        logger.info("Verifying ID token...")
        idinfo = None
        verify_exception = None
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                idinfo = id_token.verify_oauth2_token(
                    credentials.id_token,
                    grequests.Request(),
                    GOOGLE_CLIENT_ID,
                    clock_skew_in_seconds=10  # Tolerate up to 10 seconds clock difference
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
                        wait = 3  # Increased from 2 to 3 seconds
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
        
        # Check if user exists in database
        user = db.query(User).filter_by(google_id=google_id).first()
        
        if not user:
            # First-time Google login - create new user account (non-admin by default)
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
        
        # Security check: Only admin users can access admin panel
        if not user.is_admin:
            logger.warning("⚠️ Non-admin user attempted admin login - ID: %s", user.id)
            return RedirectResponse(
                url=f"{ADMIN_FRONTEND_URL}/login?error=unauthorized"
            )
        
        # Security check: Reject disabled accounts
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
    ADMIN ENDPOINT: Verify admin JWT token and return user information.
    
    Used by frontend on page load to validate stored tokens.
    If token is valid, returns fresh token and user data.
    If token is invalid/expired, returns 401 error.
    
    Returns:
        access_token: Fresh JWT token
        user: Admin user information
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
    ADMIN ENDPOINT: Logout endpoint.
    
    Note: JWT tokens are stateless, so logout happens client-side.
    Frontend should discard the token from local storage.
    This endpoint just logs the event for audit purposes.
    """
    logger.info("Admin user logged out - ID: %s", current_user.id)
    return {"message": "Logged out successfully"}
