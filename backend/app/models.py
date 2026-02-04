from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, ARRAY, Text, Boolean, Enum, JSON, Numeric, Date
from sqlalchemy.dialects.postgresql import UUID, JSONB
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
    # Health Profile relationships
    user_profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    profile_answers = relationship("ProfileAnswer", back_populates="user", cascade="all, delete-orphan")
    profile_conditions = relationship("ProfileCondition", back_populates="user", cascade="all, delete-orphan")
    profile_symptoms = relationship("ProfileSymptom", back_populates="user", cascade="all, delete-orphan")
    profile_medications = relationship("ProfileMedication", back_populates="user", cascade="all, delete-orphan")
    profile_supplements = relationship("ProfileSupplement", back_populates="user", cascade="all, delete-orphan")
    profile_allergies = relationship("ProfileAllergy", back_populates="user", cascade="all, delete-orphan")
    profile_family_history = relationship("ProfileFamilyHistory", back_populates="user", cascade="all, delete-orphan")
    profile_genetic_tests = relationship("ProfileGeneticTest", back_populates="user", cascade="all, delete-orphan")
    derived_features = relationship("DerivedFeature", back_populates="user", cascade="all, delete-orphan")
    profile_recommendations = relationship("ProfileRecommendation", back_populates="user", cascade="all, delete-orphan")

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
    
    # Classification results (regex-based)
    category = Column(String(50), nullable=True, index=True)  # lab/dental/mri/xray/prescription/sleep
    doc_type = Column(String(50), nullable=True, index=True)  # blood_panel/lipid_panel/checkup/etc.
    classification_confidence = Column(Float, nullable=True)  # 0-1
    classification_rules_matched = Column(JSONB, nullable=True)  # List of rules that matched
    
    # Extraction results
    raw_text = Column(Text, nullable=True)  # Full OCR text
    extraction_method = Column(String, nullable=True)  # "text", "ocr", "hybrid", "failed"
    extraction_source = Column(String(20), nullable=True)  # regex/grok/grok_fallback/manual
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
    
    # Extraction metadata
    source = Column(String(20), nullable=True)  # regex/grok/grok_fallback/manual
    confidence = Column(Float, nullable=True)  # 0-1 extraction confidence
    user_corrected = Column(Boolean, default=False, nullable=False)  # True if user manually entered/corrected
    
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


# ============================================================================
# HEALTH PROFILE MODELS
# ============================================================================

class SexAtBirth(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    INTERSEX = "intersex"
    PREFER_NOT = "prefer_not"


class ActivityLevel(str, enum.Enum):
    SEDENTARY = "sedentary"
    MODERATE = "moderate"
    ACTIVE = "active"


class SmokingStatus(str, enum.Enum):
    NEVER = "never"
    FORMER = "former"
    CURRENT = "current"
    PREFER_NOT = "prefer_not"
    UNKNOWN = "unknown"


class AlcoholConsumption(str, enum.Enum):
    NONE = "none"
    OCCASIONAL = "occasional"
    FREQUENT = "frequent"
    UNKNOWN = "unknown"


class SleepQuality(str, enum.Enum):
    GOOD = "good"
    OK = "ok"
    POOR = "poor"
    UNKNOWN = "unknown"


class DietPattern(str, enum.Enum):
    VEG = "veg"
    NONVEG = "nonveg"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class UserProfile(Base):
    """Core user health profile data - 1 row per user"""
    __tablename__ = "user_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    # Step 1: Basics
    full_name = Column(String(255), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    age_years = Column(Integer, nullable=True)  # fallback if DOB unknown
    sex_at_birth = Column(String(20), nullable=True)
    gender = Column(String(50), nullable=True)
    city = Column(String(100), nullable=True)
    
    # Step 2: Body Measurements
    height_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    waist_cm = Column(Float, nullable=True)
    activity_level = Column(String(20), nullable=True)
    
    # Step 6: Lifestyle
    smoking = Column(String(20), nullable=True)
    alcohol = Column(String(20), nullable=True)
    sleep_hours_avg = Column(Float, nullable=True)
    sleep_quality = Column(String(20), nullable=True)
    exercise_minutes_per_week = Column(Integer, nullable=True)
    diet_pattern = Column(String(20), nullable=True)
    
    # Wizard state
    wizard_current_step = Column(Integer, default=1)
    wizard_completed = Column(Boolean, default=False)
    wizard_last_saved_at = Column(DateTime, nullable=True)
    
    # Completion tracking (separate from wizard state for API simplicity)
    is_completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Contact for SMS reminders
    phone_number = Column(String(20), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="user_profile")
    reminders = relationship("Reminder", back_populates="user_profile", cascade="all, delete-orphan")


class ProfileAnswer(Base):
    """Flexible JSONB storage for any question answer"""
    __tablename__ = "profile_answers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(String(100), nullable=False, index=True)
    answer_data = Column(JSONB, nullable=False)  # { "value": any, "unit": str?, "unknown": bool, "skipped": bool }
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="profile_answers")


class ProfileCondition(Base):
    """User's diagnosed medical conditions"""
    __tablename__ = "profile_conditions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    condition_code = Column(String(50), nullable=False)
    condition_name = Column(String(200), nullable=True)
    diagnosed_at = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="profile_conditions")


class ProfileSymptom(Base):
    """User's recurring symptoms"""
    __tablename__ = "profile_symptoms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    symptom_code = Column(String(50), nullable=False)
    symptom_name = Column(String(200), nullable=True)
    frequency = Column(String(50), nullable=True)
    severity = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="profile_symptoms")


class ProfileMedication(Base):
    """User's current medications"""
    __tablename__ = "profile_medications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    dose = Column(String(100), nullable=True)
    frequency = Column(String(100), nullable=True)
    started_at = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="profile_medications")


class ProfileSupplement(Base):
    """User's supplements/vitamins"""
    __tablename__ = "profile_supplements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    dose = Column(String(100), nullable=True)
    frequency = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="profile_supplements")


class ProfileAllergy(Base):
    """User's allergies"""
    __tablename__ = "profile_allergies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    allergen = Column(String(200), nullable=False)
    allergy_type = Column(String(50), nullable=True)  # drug/food/environmental/other
    reaction = Column(String(500), nullable=True)
    severity = Column(String(20), nullable=True)  # mild/moderate/severe/life_threatening
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="profile_allergies")


class ProfileFamilyHistory(Base):
    """Family medical history"""
    __tablename__ = "profile_family_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    relative_type = Column(String(50), nullable=False)  # mother/father/sibling/grandparent_maternal/grandparent_paternal
    condition_code = Column(String(50), nullable=False)
    condition_name = Column(String(200), nullable=True)
    age_at_diagnosis = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="profile_family_history")


class ProfileGeneticTest(Base):
    """Genetic test results"""
    __tablename__ = "profile_genetic_tests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    mutation_name = Column(String(100), nullable=False)
    result = Column(String(50), nullable=True)  # positive/negative/variant_uncertain
    test_date = Column(Date, nullable=True)
    lab_name = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="profile_genetic_tests")


class DerivedFeature(Base):
    """Computed values like BMI, risk scores, completeness"""
    __tablename__ = "derived_features"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_name = Column(String(100), nullable=False, index=True)
    feature_value = Column(JSONB, nullable=False)
    computed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    valid_until = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="derived_features")


class ProfileRecommendation(Base):
    """Generated recommendations with evidence"""
    __tablename__ = "profile_recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    recommendation_type = Column(String(50), nullable=False)  # lifestyle/screening/followup/urgent
    category = Column(String(50), nullable=True)  # nutrition/exercise/sleep/medical
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(Integer, default=5)  # 1-10, 1 being highest
    evidence_jsonb = Column(JSONB, nullable=True)
    is_active = Column(Boolean, default=True)
    dismissed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="profile_recommendations")


# ============================================================================
# DOCUMENT OCR PIPELINE MODELS
# ============================================================================

class DocumentCategory(str, enum.Enum):
    LAB = "lab"
    DENTAL = "dental"
    MRI = "mri"
    XRAY = "xray"
    PRESCRIPTION = "prescription"
    SLEEP = "sleep"
    UNKNOWN = "unknown"


class DocumentType(str, enum.Enum):
    BLOOD_PANEL = "blood_panel"
    LIPID_PANEL = "lipid_panel"
    CHECKUP = "checkup"
    BRAIN_SCAN = "brain_scan"
    CHEST = "chest"
    DENTAL_EXAM = "dental_exam"
    PRESCRIPTION = "prescription"
    SLEEP_STUDY = "sleep_study"
    UNKNOWN = "unknown"


class ExtractionSource(str, enum.Enum):
    REGEX = "regex"
    GROK = "grok"
    GROK_FALLBACK = "grok_fallback"
    MANUAL = "manual"


class MissingDataStatus(str, enum.Enum):
    PENDING = "pending"
    RESOLVED = "resolved"
    SKIPPED = "skipped"


class DocumentOCR(Base):
    """Stores OCR extraction results for a document"""
    __tablename__ = "document_ocr"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    ocr_text = Column(Text, nullable=True)  # Full extracted text
    ocr_json = Column(JSONB, nullable=True)  # Page stats, confidence per page, method used
    extraction_method = Column(String(20), nullable=True)  # text/ocr/hybrid
    total_chars = Column(Integer, nullable=True)
    total_pages = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    document = relationship("Report", backref="ocr_data")


class MissingDataTask(Base):
    """Tracks required parameters not extracted from documents"""
    __tablename__ = "missing_data_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    
    metric_key = Column(String(100), nullable=False)  # Canonical metric key
    label = Column(String(200), nullable=False)  # Human-readable label for UI
    expected_unit = Column(String(50), nullable=True)  # Expected unit for this metric
    required = Column(Boolean, default=False, nullable=False)  # Is this critical?
    status = Column(String(20), default="pending", nullable=False)  # pending/resolved/skipped
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", backref="missing_data_tasks")
    document = relationship("Report", backref="missing_data_tasks")


class HealthIndexSnapshot(Base):
    """Stores computed health index scores over time"""
    __tablename__ = "health_index_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    score = Column(Float, nullable=False)  # 0-100
    confidence = Column(Float, nullable=True)  # 0-1
    contributions = Column(JSONB, nullable=True)  # Factor breakdown {"sleep": 0.25, "glucose": 0.18}
    missing_inputs = Column(JSONB, nullable=True)  # What data was missing ["hba1c", "ldl"]
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    user = relationship("User", backref="health_index_snapshots")


# ============================================================================
# AI REPORT SUMMARY MODELS
# ============================================================================

class ReportAISummary(Base):
    """Stores AI-generated summaries for individual reports"""
    __tablename__ = "report_ai_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    
    summary_json = Column(JSONB, nullable=False)  # AI summary output
    model_name = Column(String(100), nullable=False)  # e.g., "grok-beta"
    source_hash = Column(String(64), nullable=False, index=True)  # Hash of source text for cache invalidation
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="ai_summaries")
    report = relationship("Report", backref="ai_summaries")


class ReportAIComparison(Base):
    """Stores AI-generated comparisons between multiple reports"""
    __tablename__ = "report_ai_comparisons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    report_ids_json = Column(JSONB, nullable=False)  # List of report IDs being compared
    comparison_json = Column(JSONB, nullable=False)  # AI comparison output
    model_name = Column(String(100), nullable=False)  # e.g., "grok-beta"
    source_hash = Column(String(64), nullable=False, index=True)  # Hash of combined source texts
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="ai_comparisons")


# ============================================================================
# MEDICINES FEATURE MODELS
# ============================================================================

class GenericCatalog(Base):
    """Generic medicines catalog - seeded from Jan Aushadhi/PMBI data"""
    __tablename__ = "generic_catalog"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_name = Column(String(500), nullable=False)
    salt = Column(String(500), nullable=False, index=True)
    strength = Column(String(100), nullable=False)
    form = Column(String(100), nullable=False)  # tablet/capsule/syrup/injection
    release_type = Column(String(50), nullable=True)  # SR/ER/CR/Normal/null
    mrp = Column(Numeric(10, 2), nullable=True)
    manufacturer = Column(String(300), nullable=True)
    source = Column(String(50), nullable=False, default='jan_aushadhi')
    is_jan_aushadhi = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class UserSavedMedicine(Base):
    """User's saved medicines for quick access"""
    __tablename__ = "user_saved_medicines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    original_name = Column(String(500), nullable=True)
    salt = Column(String(500), nullable=False)
    strength = Column(String(100), nullable=False)
    form = Column(String(100), nullable=False)
    release_type = Column(String(50), nullable=True)
    schedule_json = Column(JSONB, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    user = relationship("User", backref="saved_medicines")


class SubstituteQuery(Base):
    """Tracks substitute search queries for analytics"""
    __tablename__ = "substitute_queries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    query_raw = Column(Text, nullable=False)
    normalized_json = Column(JSONB, nullable=True)
    results_json = Column(JSONB, nullable=True)
    results_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    user = relationship("User", backref="substitute_queries")


class PharmacyClick(Base):
    """Tracks pharmacy detail views for analytics"""
    __tablename__ = "pharmacy_clicks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    place_id = Column(String(300), nullable=False)
    place_name = Column(String(500), nullable=True)
    mode = Column(String(50), nullable=False)  # pharmacy/janaushadhi
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    user = relationship("User", backref="pharmacy_clicks")


class UserLocationConsent(Base):
    """Stores user consent for location services"""
    __tablename__ = "user_location_consent"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    consent = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    user = relationship("User", backref="location_consent", uselist=False)


# ============================================================================
# REMINDERS & SMS MODELS
# ============================================================================

class ReminderType(str, enum.Enum):
    MEDICINE = "medicine"
    HYDRATION = "hydration"
    SLEEP = "sleep"
    CHECKUP = "checkup"
    EXERCISE = "exercise"
    CUSTOM = "custom"


class ReminderScheduleType(str, enum.Enum):
    FIXED_TIMES = "fixed_times"
    INTERVAL = "interval"
    CRON = "cron"


class ReminderChannel(str, enum.Enum):
    SMS = "sms"
    IN_APP = "in_app"
    PUSH = "push"
    EMAIL = "email"


class ReminderEventStatus(str, enum.Enum):
    SENT = "sent"
    FAILED = "failed"
    MOCKED = "mocked"
    SKIPPED = "skipped"


class Reminder(Base):
    """User reminders for medicine, hydration, sleep, etc."""
    __tablename__ = "reminders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=True)
    
    # Reminder details
    type = Column(String(50), nullable=False)  # medicine|hydration|sleep|checkup|custom
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    
    # Schedule configuration
    schedule_type = Column(String(30), nullable=False)  # fixed_times|interval|cron
    schedule_json = Column(JSONB, nullable=False)
    # schedule_json examples:
    # fixed_times: {"times": ["08:00", "14:00", "20:00"]}
    # interval: {"interval_minutes": 120, "start_time": "08:00", "end_time": "22:00"}
    # cron: {"cron": "0 9 * * *"}
    
    # Timezone
    timezone = Column(String(50), default="Asia/Kolkata", nullable=False)
    
    # Execution tracking
    next_run_at = Column(DateTime, nullable=True, index=True)
    last_run_at = Column(DateTime, nullable=True)
    
    # Status
    is_enabled = Column(Boolean, default=True, nullable=False)
    
    # Delivery channel
    channel = Column(String(20), default="sms", nullable=False)
    
    # Medicine-specific fields (optional)
    medicine_id = Column(UUID(as_uuid=True), nullable=True)
    medicine_name = Column(String(200), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="reminders")
    user_profile = relationship("UserProfile", back_populates="reminders")
    events = relationship("ReminderEvent", back_populates="reminder", cascade="all, delete-orphan")


class ReminderEvent(Base):
    """Delivery log for reminders (SMS/push/in-app notifications)"""
    __tablename__ = "reminder_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reminder_id = Column(UUID(as_uuid=True), ForeignKey("reminders.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Delivery details
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(20), nullable=False)  # sent|failed|mocked|skipped
    provider = Column(String(30), nullable=False)  # twilio|mock|in_app
    provider_response = Column(JSONB, nullable=True)
    
    # Message content (for audit)
    message_sent = Column(Text, nullable=True)
    phone_number = Column(String(20), nullable=True)  # Masked for privacy
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    # Relationships
    reminder = relationship("Reminder", back_populates="events")
    user = relationship("User", backref="reminder_events")

