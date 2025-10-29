from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database URL - use environment variable or default to SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./rekapo.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String, unique=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String)
    username = Column(String, unique=True)
    profile_picture_path = Column(String, nullable=True)
    data_usage_consent = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    is_disabled = Column(Boolean, default=False)
    disabled_at = Column(DateTime, nullable=True)
    disabled_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    disabled_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sessions = relationship("Session", back_populates="user", foreign_keys="Session.user_id")
    disabled_users = relationship("User", remote_side=[id])

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_title = Column(String, default="Untitled Meeting")
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String, default="recording")  # recording, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="sessions", foreign_keys=[user_id])
    recording_segments = relationship("RecordingSegment", back_populates="session")
    summaries = relationship("Summary", back_populates="session")

class RecordingSegment(Base):
    __tablename__ = "recording_segments"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    segment_number = Column(Integer, nullable=False)
    audio_path = Column(String, nullable=False)
    transcript_text = Column(Text)  # Taglish transcript
    english_translation = Column(Text)  # English translation
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="recording_segments")

class Summary(Base):
    __tablename__ = "summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    chunk_range_start = Column(Integer, nullable=False)
    chunk_range_end = Column(Integer, nullable=False)
    summary_text = Column(Text, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="summaries")

class SystemStatistics(Base):
    __tablename__ = "system_statistics"
    
    id = Column(Integer, primary_key=True, index=True)
    stat_date = Column(Date, unique=True)
    total_users = Column(Integer)
    active_users = Column(Integer)
    total_sessions = Column(Integer)
    average_session_duration = Column(Float)
    calculated_at = Column(DateTime, default=datetime.utcnow)

# Create all tables
def init_db():
    Base.metadata.create_all(bind=engine)