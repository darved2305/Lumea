from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, ARRAY, Text, Boolean, Enum, JSON, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, date
import uuid
import enum
from app.db import Base


class ReportStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    CONFIRMED = "confirmed"


class ObservationType(str, enum.Enum):
    LAB_VALUE = "lab_value"
    VITAL_SIGN = "vital_sign"
    PHYSICAL_MEASUREMENT = "physical_measurement"
    LIFESTYLE = "lifestyle"
    SYMPTOM = "symptom"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    onboarding_completed = Column(Boolean, default=False)
    
    # Relationships
    reports = relationship("Report", back_populates="user", cascade="all, delete-orphan")
    observations = relationship("Observation", back_populates="user", cascade="all, delete-orphan")
    health_metrics = relationship("HealthMetric", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")

class LoginEvent(Base):
    __tablename__ = "login_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    ip = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PatientProfile(Base):
    __tablename__ = "patient_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    height_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    bmi = Column(Float, nullable=True)
    conditions = Column(ARRAY(String), default=list)
    last_blood_test_at = Column(DateTime, nullable=True)
    last_dental_at = Column(DateTime, nullable=True)
    last_eye_exam_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Report(Base):
    """Medical report uploaded by user (PDF, image, etc.)"""
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    status = Column(Enum(ReportStatus), default=ReportStatus.UPLOADED, nullable=False, index=True)
    report_date = Column(DateTime, nullable=True)  # Date on the report itself
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    
    # Extraction results
    raw_text = Column(Text, nullable=True)  # Full OCR text
    extraction_method = Column(String, nullable=True)  # "text", "ocr", "hybrid", "failed"
    page_stats = Column(JSON, nullable=True)  # Per-page extraction statistics
    extracted_data = Column(JSON, nullable=True)  # Structured extraction
    extraction_confidence = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="reports")
    observations = relationship("Observation", back_populates="report", cascade="all, delete-orphan")


class Observation(Base):
    """Structured health data point extracted from reports or manually entered"""
    __tablename__ = "observations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id"), nullable=True, index=True)
    
    observation_type = Column(Enum(ObservationType), nullable=False, index=True)
    metric_name = Column(String, nullable=False, index=True)  # canonical key e.g., "hemoglobin", "glucose"
    display_name = Column(String, nullable=True)  # original test name from report
    value = Column(Numeric(10, 3), nullable=False)  # Numeric value
    unit = Column(String, nullable=False)  # e.g., "mg/dL", "mmHg", "hours"
    
    observed_at = Column(DateTime, nullable=False, index=True)  # When measurement was taken
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Reference ranges for scoring
    reference_min = Column(Numeric(10, 3), nullable=True)
    reference_max = Column(Numeric(10, 3), nullable=True)
    is_abnormal = Column(Boolean, default=False, index=True)
    flag = Column(String, nullable=True)  # "Low", "High", "Normal", "Critical"
    
    # Additional context
    notes = Column(Text, nullable=True)
    raw_line = Column(Text, nullable=True)  # Original line from report
    page_num = Column(Integer, nullable=True)  # Page number in report
    extra_data = Column(JSON, nullable=True)  # Additional structured info
    
    # Relationships
    user = relationship("User", back_populates="observations")
    report = relationship("Report", back_populates="observations")


class HealthMetric(Base):
    """Computed health metrics and scores"""
    __tablename__ = "health_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    metric_type = Column(String, nullable=False, index=True)  # "health_index", "sleep_score", etc.
    value = Column(Float, nullable=False)
    confidence = Column(Float, nullable=True)  # 0-1, how confident we are in this score
    
    computed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    valid_from = Column(DateTime, nullable=False)  # Period this metric represents
    valid_to = Column(DateTime, nullable=False)
    
    # Breakdown for UI
    contributions = Column(JSON, nullable=True)  # Factor contributions {"sleep": 0.25, "glucose": 0.18, ...}
    extra_metadata = Column(JSON, nullable=True)  # Additional details (renamed from metadata)
    
    # Relationships
    user = relationship("User", back_populates="health_metrics")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    guest_key = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON, nullable=True)  # Citations, context used, etc. (renamed from metadata)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("ChatSession", back_populates="messages")
