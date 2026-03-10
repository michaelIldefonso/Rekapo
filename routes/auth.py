import dotenv
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
import jwt
import os
from db.db import get_db, User
from utils.utils import get_logger, mask_email, safe_user_log_dict
from schemas.schemas import UserResponse
from datetime import datetime, timedelta

dotenv.load_dotenv()

router = APIRouter()
logger = get_logger(__name__)

# JWT secret and algorithm (should be in env vars in production)
JWT_SECRET = os.getenv("JWT_SECRET", "your_jwt_secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

# Google client ID (should be in env vars)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "your_google_client_id")

# Bearer token security scheme
security = HTTPBearer()

class GoogleAuthRequest(BaseModel):
    id_token: str
    data_usage_consent: bool = False

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

@router.post("/auth/google-mobile", response_model=AuthResponse)
def google_mobile_auth(payload: GoogleAuthRequest, db: Session = Depends(get_db)):
    """
    Google OAuth2 authentication for mobile app.
    
    Mobile app endpoint - handles Google Sign-In flow:
    - Verifies Google ID token
    - Creates new user on first login OR returns existing user
    - Generates JWT token for subsequent API requests
    - Checks if account is disabled before allowing login
    
    Returns JWT access token and user profile.
    """
    try:
        # Verify Google ID token
        idinfo = id_token.verify_oauth2_token(
            payload.id_token, grequests.Request(), GOOGLE_CLIENT_ID
        )
        if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
            raise ValueError("Wrong issuer.")
    except Exception as e:
        logger.warning("Google token verification failed: %s", str(e))
        raise HTTPException(status_code=401, detail="Invalid Google token")

    # Extract user info
    google_id = idinfo["sub"]
    email = idinfo["email"]
    name = idinfo.get("name")
    picture = idinfo.get("picture")

    # Find or create user
    user = db.query(User).filter_by(google_id=google_id).first()
    
    is_new_user = user is None
    
    if not user:
        # First login: Create user with Google info
        logger.info("NEW USER SIGNUP - Email: %s", mask_email(email))
        user = User(
            google_id=google_id,
            email=email,
            name=name,
            profile_picture_path=picture,
            data_usage_consent=payload.data_usage_consent,
            created_at=datetime.utcnow(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Check if user account is disabled
    if user.is_disabled:
        logger.warning("DISABLED USER LOGIN ATTEMPT - User ID: %s", user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been disabled. Please contact support."
        )

    # Generate JWT
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    access_token = jwt.encode(token_data, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return AuthResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )

# Dependency to get current user from JWT token
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to extract and validate JWT token, returning the current user.
    Raises HTTPException if token is invalid or user not found.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    if user.is_disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    return user

