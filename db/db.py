from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Float,
    Text,
    ForeignKey,
    Date,
    Index,
    func,
    text,
)
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
    __table_args__ = (
        # Documentation comment
        {"comment": "Stores user account information with Google OAuth integration"},
    )
    
    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String(255), unique=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), comment="Full name from Google OAuth")
    username = Column(String(255), unique=True, comment="UC9: User customizable display name")
    profile_picture_path = Column(String(500), nullable=True, comment="UC9: Custom profile image path")
    data_usage_consent = Column(Boolean, nullable=False, server_default=text("TRUE"))
    is_admin = Column(Boolean, nullable=False, server_default=text("FALSE"))
    is_disabled = Column(Boolean, nullable=False, server_default=text("FALSE"), comment="UC8: Disable User Account")
    disabled_at = Column(DateTime, nullable=True)
    disabled_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    disabled_reason = Column(Text, nullable=True, comment="Reason for account disabling: policy violation, user request, inactivity, etc.")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    sessions = relationship(
        "Session",
        back_populates="user",
        foreign_keys="Session.user_id",
        passive_deletes=True,
    )
    disabled_users = relationship("User", remote_side=[id])

class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        Index("idx_sessions_user_id", "user_id"),
        Index("idx_sessions_status", "status"),
        Index("idx_sessions_start_time", "start_time"),
        {"comment": "Tracks meeting recording sessions"},
    )
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_title = Column(String(255), nullable=False, server_default=text("'Untitled Meeting'"))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), nullable=False, server_default=text("'recording'"), comment="Session status: recording, completed, or failed")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="sessions", foreign_keys=[user_id])
    recording_segments = relationship(
        "RecordingSegment",
        back_populates="session",
        passive_deletes=True,
        cascade="all, delete-orphan",
    )
    summaries = relationship(
        "Summary",
        back_populates="session",
        passive_deletes=True,
        cascade="all, delete-orphan",
    )

class RecordingSegment(Base):
    __tablename__ = "recording_segments"
    __table_args__ = (
        Index("idx_recording_segments_session_id", "session_id"),
        Index("idx_recording_segments_session_segment", "session_id", "segment_number"),
        {"comment": "Stores audio segments with transcription in Taglish and English"},
    )
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    segment_number = Column(Integer, nullable=False)
    audio_path = Column(String(500), nullable=False)
    transcript_text = Column(Text, comment="Original transcription in Taglish")
    english_translation = Column(Text, comment="English translation of the transcript")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    session = relationship("Session", back_populates="recording_segments")

class Summary(Base):
    __tablename__ = "summaries"
    __table_args__ = (
        Index("idx_summaries_session_id", "session_id"),
        Index("idx_summaries_session_chunk", "session_id", "chunk_range_start"),
        {"comment": "Contains AI-generated summaries for session chunks"},
    )
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    chunk_range_start = Column(Integer, nullable=False)
    chunk_range_end = Column(Integer, nullable=False)
    summary_text = Column(Text, nullable=False)
    generated_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    session = relationship("Session", back_populates="summaries")

class SystemStatistics(Base):
    __tablename__ = "system_statistics"
    __table_args__ = (
        {"comment": "Aggregated system metrics calculated daily"},
    )
    
    id = Column(Integer, primary_key=True, index=True)
    stat_date = Column(Date, nullable=False, unique=True)
    total_users = Column(Integer)
    active_users = Column(Integer)
    total_sessions = Column(Integer)
    average_session_duration = Column(Float)
    calculated_at = Column(DateTime, nullable=False, server_default=func.now())

# Create all tables
def init_db():
    # Create the uuid-ossp extension on PostgreSQL if available/needed
    try:
        if engine.url.get_backend_name() == "postgresql":
            with engine.connect() as conn:
                conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
                conn.commit()
    except Exception:
        # Non-fatal: extension may require superuser; continue without raising
        pass

    Base.metadata.create_all(bind=engine)