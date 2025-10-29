import dotenv
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
import jwt
import os
from db.db import get_db, User
from schemas.schemas import UserResponse
from datetime import datetime, timedelta

dotenv.load_dotenv()

router = APIRouter()

# JWT secret and algorithm (should be in env vars in production)
JWT_SECRET = os.getenv("JWT_SECRET", "your_jwt_secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

# Google client ID (should be in env vars)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "your_google_client_id")

class GoogleAuthRequest(BaseModel):
    id_token: str
    data_usage_consent: bool = False

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

@router.post("/auth/google-mobile", response_model=AuthResponse)
def google_mobile_auth(payload: GoogleAuthRequest, db: Session = Depends(get_db)):
    try:
        # Verify Google ID token
        idinfo = id_token.verify_oauth2_token(
            payload.id_token, grequests.Request(), GOOGLE_CLIENT_ID
        )
        if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
            raise ValueError("Wrong issuer.")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    # Extract user info
    google_id = idinfo["sub"]
    email = idinfo["email"]
    name = idinfo.get("name")
    picture = idinfo.get("picture")

    # Find or create user
    user = db.query(User).filter_by(google_id=google_id).first()
    if not user:
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
    else:
        # Update info if needed
        user.email = email
        user.name = name
        user.profile_picture_path = picture
        user.data_usage_consent = payload.data_usage_consent
        db.commit()
        db.refresh(user)

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
