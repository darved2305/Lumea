from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum

class UserBase(BaseModel):
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    user: UserResponse

# Patient Profile schemas
class PatientProfileCreate(BaseModel):
    full_name: Optional[str] = None
    age: Optional[int] = Field(None, ge=0, le=150)
    gender: Optional[str] = Field(None, pattern="^(male|female|other)$")
    height_cm: Optional[float] = Field(None, gt=0, le=300)
    weight_kg: Optional[float] = Field(None, gt=0, le=500)
    conditions: Optional[List[str]] = []
    last_blood_test_at: Optional[datetime] = None
    last_dental_at: Optional[datetime] = None
    last_eye_exam_at: Optional[datetime] = None

    @validator('conditions', pre=True, always=True)
    def validate_conditions(cls, v):
        if v is None:
            return []
        return v

class PatientProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    age: Optional[int] = Field(None, ge=0, le=150)
    gender: Optional[str] = Field(None, pattern="^(male|female|other)$")
    height_cm: Optional[float] = Field(None, gt=0, le=300)
    weight_kg: Optional[float] = Field(None, gt=0, le=500)
    conditions: Optional[List[str]] = None
    last_blood_test_at: Optional[datetime] = None
    last_dental_at: Optional[datetime] = None
    last_eye_exam_at: Optional[datetime] = None

class PatientProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    full_name: Optional[str]
    age: Optional[int]
    gender: Optional[str]
    height_cm: Optional[float]
    weight_kg: Optional[float]
    bmi: Optional[float]
    conditions: List[str]
    last_blood_test_at: Optional[datetime]
    last_dental_at: Optional[datetime]
    last_eye_exam_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Reminder schemas
class ReminderItem(BaseModel):
    title: str
    reason: str
    due_date: datetime
    urgency: str  # 'overdue', 'soon', 'ok'
    frequency_months: int

class RemindersResponse(BaseModel):
    reminders: List[ReminderItem]

# Chat schemas
class ChatMessageCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    guest_key: Optional[str] = None

class ChatMessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

class ChatSessionResponse(BaseModel):
    id: UUID
    messages: List[ChatMessageResponse]
    created_at: datetime


# ============================================================================
# NEW SCHEMAS FOR HEALTH PLATFORM
# ============================================================================

# ENUMS
class ReportStatusEnum(str, Enum):
    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    CONFIRMED = "confirmed"


class ObservationTypeEnum(str, Enum):
    LAB_VALUE = "lab_value"
    VITAL_SIGN = "vital_sign"
    PHYSICAL_MEASUREMENT = "physical_measurement"
    LIFESTYLE = "lifestyle"
    SYMPTOM = "symptom"


class TimeRange(str, Enum):
    ONE_DAY = "1d"
    ONE_DAY_UPPER = "1D"
    ONE_WEEK = "1w"
    ONE_WEEK_UPPER = "1W"
    ONE_MONTH = "1m"
    ONE_MONTH_UPPER = "1M"


class MetricType(str, Enum):
    HEALTH_INDEX = "health_index"
    SLEEP = "sleep"
    BLOOD_PRESSURE = "blood_pressure"  # Fixed: was "bloodPressure"
    BLOOD_PRESSURE_ALT = "bloodPressure"  # Also accept camelCase
    GLUCOSE = "glucose"
    ACTIVITY = "activity"
    STRESS = "stress"
    HYDRATION = "hydration"
    INDEX = "index"  # Alias for health_index


# BOOTSTRAP
class BootstrapResponse(BaseModel):
    user_id: UUID
    full_name: str
    email: str
    onboarding_completed: bool
    has_reports: bool
    report_count: int
    latest_health_index: Optional[float] = None
    health_index_confidence: Optional[float] = None
    last_report_date: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# DASHBOARD
class FactorContribution(BaseModel):
    key: str
    label: str
    value: float
    contribution: float
    status: str
    unit: Optional[str] = None


class DashboardSummary(BaseModel):
    health_index_score: float
    confidence: float
    trend: str
    last_updated: datetime
    factors: List[FactorContribution]
    
    class Config:
        from_attributes = True


class TimeSeriesPoint(BaseModel):
    timestamp: int
    value: float


class TrendsStats(BaseModel):
    current: float
    average: float
    minimum: float
    maximum: float
    change_percent: float


class TrendsResponse(BaseModel):
    metric: str
    range: str
    data: List[TimeSeriesPoint]
    stats: TrendsStats
    
    class Config:
        from_attributes = True


# REPORTS
class ReportListItem(BaseModel):
    id: UUID
    filename: str
    file_type: str
    file_size: int
    status: ReportStatusEnum
    report_date: Optional[datetime]
    uploaded_at: datetime
    processed_at: Optional[datetime]
    extraction_confidence: Optional[float]
    observation_count: int = 0
    
    class Config:
        from_attributes = True


class ReportDetail(BaseModel):
    id: UUID
    filename: str
    file_type: str
    file_size: int
    status: ReportStatusEnum
    report_date: Optional[datetime]
    uploaded_at: datetime
    processed_at: Optional[datetime]
    raw_text: Optional[str]
    extracted_data: Optional[Dict[str, Any]]
    extraction_confidence: Optional[float]
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


class ExtractedValue(BaseModel):
    metric_name: str
    value: float
    unit: str
    observation_type: ObservationTypeEnum
    observed_at: datetime
    confidence: Optional[float] = None


class ReportConfirmRequest(BaseModel):
    values: List[ExtractedValue]
    notes: Optional[str] = None


# OBSERVATIONS
class ObservationCreate(BaseModel):
    observation_type: ObservationTypeEnum
    metric_name: str
    value: float
    unit: str
    observed_at: datetime
    notes: Optional[str] = None


class ObservationResponse(BaseModel):
    id: UUID
    observation_type: ObservationTypeEnum
    metric_name: str
    value: float
    unit: str
    observed_at: datetime
    is_abnormal: bool
    notes: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ASSISTANT
class AssistantChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[UUID] = None


class Citation(BaseModel):
    # Optional fields must default to None in Pydantic v2, otherwise they are still required.
    report_id: Optional[UUID] = None
    report_name: Optional[str] = None
    report_date: Optional[datetime] = None
    observation_id: Optional[UUID] = None
    metric_name: Optional[str] = None
    value: Optional[str] = None
    excerpt: Optional[str] = None


class AssistantChatResponse(BaseModel):
    session_id: UUID
    message_id: UUID
    content: str
    citations: List[Citation]
    created_at: datetime
    
    class Config:
        from_attributes = True


# EVENTS (SSE)
class EventType(str, Enum):
    REPORT_STATUS_CHANGED = "report_status_changed"
    DASHBOARD_UPDATED = "dashboard_updated"
    METRICS_COMPUTED = "metrics_computed"
    RECOMMENDATIONS_UPDATED = "recommendations_updated"


class ServerEvent(BaseModel):
    event_type: EventType
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    def to_sse_format(self) -> str:
        return f"event: {self.event_type.value}\ndata: {self.json()}\n\n"


# ============================================================================
# HEALTH PROFILE SCHEMAS
# ============================================================================

# Answer data structure
class AnswerData(BaseModel):
    value: Optional[Any] = None
    unit: Optional[str] = None
    unknown: bool = False
    skipped: bool = False


class ProfileAnswerUpsert(BaseModel):
    question_id: str
    answer_data: AnswerData


class ProfileAnswerResponse(BaseModel):
    question_id: str
    answer_data: AnswerData
    updated_at: datetime

    class Config:
        from_attributes = True


# Condition schemas
class ProfileConditionCreate(BaseModel):
    condition_code: str
    condition_name: Optional[str] = None
    diagnosed_at: Optional[datetime] = None
    notes: Optional[str] = None


class ProfileConditionResponse(BaseModel):
    id: UUID
    condition_code: str
    condition_name: Optional[str]
    diagnosed_at: Optional[datetime]
    notes: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Symptom schemas
class ProfileSymptomCreate(BaseModel):
    symptom_code: str
    symptom_name: Optional[str] = None
    frequency: Optional[str] = None
    severity: Optional[str] = None
    notes: Optional[str] = None


class ProfileSymptomResponse(BaseModel):
    id: UUID
    symptom_code: str
    symptom_name: Optional[str]
    frequency: Optional[str]
    severity: Optional[str]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Medication schemas
class ProfileMedicationCreate(BaseModel):
    name: str
    dose: Optional[str] = None
    frequency: Optional[str] = None
    started_at: Optional[datetime] = None
    notes: Optional[str] = None


class ProfileMedicationResponse(BaseModel):
    id: UUID
    name: str
    dose: Optional[str]
    frequency: Optional[str]
    started_at: Optional[datetime]
    notes: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Supplement schemas
class ProfileSupplementCreate(BaseModel):
    name: str
    dose: Optional[str] = None
    frequency: Optional[str] = None


class ProfileSupplementResponse(BaseModel):
    id: UUID
    name: str
    dose: Optional[str]
    frequency: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Allergy schemas
class ProfileAllergyCreate(BaseModel):
    allergen: str
    allergy_type: Optional[str] = None
    reaction: Optional[str] = None
    severity: Optional[str] = None
    notes: Optional[str] = None


class ProfileAllergyResponse(BaseModel):
    id: UUID
    allergen: str
    allergy_type: Optional[str]
    reaction: Optional[str]
    severity: Optional[str]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Family history schemas
class ProfileFamilyHistoryCreate(BaseModel):
    relative_type: str
    condition_code: str
    condition_name: Optional[str] = None
    age_at_diagnosis: Optional[int] = None
    notes: Optional[str] = None


class ProfileFamilyHistoryResponse(BaseModel):
    id: UUID
    relative_type: str
    condition_code: str
    condition_name: Optional[str]
    age_at_diagnosis: Optional[int]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Genetic test schemas
class ProfileGeneticTestCreate(BaseModel):
    mutation_name: str
    result: Optional[str] = None
    test_date: Optional[datetime] = None
    lab_name: Optional[str] = None
    notes: Optional[str] = None


class ProfileGeneticTestResponse(BaseModel):
    id: UUID
    mutation_name: str
    result: Optional[str]
    test_date: Optional[datetime]
    lab_name: Optional[str]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Core profile update schema - tolerant validation for partial updates
class UserProfileUpdate(BaseModel):
    # Step 1: Basics
    full_name: Optional[str] = Field(None, max_length=255)
    date_of_birth: Optional[datetime] = None
    age_years: Optional[int] = Field(None, ge=0, le=150)
    sex_at_birth: Optional[str] = None  # Relaxed: any string or null
    gender: Optional[str] = Field(None, max_length=50)
    city: Optional[str] = Field(None, max_length=100)
    
    # Step 2: Body Measurements  
    height_cm: Optional[float] = Field(None, ge=20, le=300)  # Very relaxed bounds
    weight_kg: Optional[float] = Field(None, ge=1, le=500)   # Allow very low weight
    waist_cm: Optional[float] = Field(None, ge=10, le=250)   # Relaxed bounds
    activity_level: Optional[str] = None  # Relaxed: any string or null
    
    # Step 6: Lifestyle
    smoking: Optional[str] = None  # Relaxed: any string or null
    alcohol: Optional[str] = None  # Relaxed: any string or null
    sleep_hours_avg: Optional[float] = Field(None, ge=0, le=24)
    sleep_quality: Optional[str] = None  # Relaxed: any string or null
    exercise_minutes_per_week: Optional[int] = Field(None, ge=0, le=10080)
    diet_pattern: Optional[str] = None  # Relaxed: any string or null
    
    # Wizard state
    wizard_current_step: Optional[int] = Field(None, ge=1, le=10)
    wizard_completed: Optional[bool] = None
    
    class Config:
        extra = "ignore"  # Ignore extra fields not in schema


class DerivedFeatureResponse(BaseModel):
    feature_name: str
    feature_value: Dict[str, Any]
    computed_at: datetime

    class Config:
        from_attributes = True


class ProfileCompletionResponse(BaseModel):
    score: float  # 0-100
    missing_essentials: List[str]
    missing_optional: List[str]
    estimated_fields: List[str]
    completion_by_step: Dict[str, float]


class ProfileRecommendationResponse(BaseModel):
    id: UUID
    recommendation_type: str
    category: Optional[str]
    title: str
    description: Optional[str]
    priority: int
    evidence_jsonb: Optional[Dict[str, Any]]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Full profile response
class UserProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    
    # Basics
    full_name: Optional[str]
    date_of_birth: Optional[datetime]
    age_years: Optional[int]
    sex_at_birth: Optional[str]
    gender: Optional[str]
    city: Optional[str]
    
    # Body measurements
    height_cm: Optional[float]
    weight_kg: Optional[float]
    waist_cm: Optional[float]
    activity_level: Optional[str]
    
    # Lifestyle
    smoking: Optional[str]
    alcohol: Optional[str]
    sleep_hours_avg: Optional[float]
    sleep_quality: Optional[str]
    exercise_minutes_per_week: Optional[int]
    diet_pattern: Optional[str]
    
    # Wizard state
    wizard_current_step: int
    wizard_completed: bool
    wizard_last_saved_at: Optional[datetime]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FullProfileResponse(BaseModel):
    """Complete profile with all related data"""
    profile: Optional[UserProfileResponse]
    answers: List[ProfileAnswerResponse]
    conditions: List[ProfileConditionResponse]
    symptoms: List[ProfileSymptomResponse]
    medications: List[ProfileMedicationResponse]
    supplements: List[ProfileSupplementResponse]
    allergies: List[ProfileAllergyResponse]
    family_history: List[ProfileFamilyHistoryResponse]
    genetic_tests: List[ProfileGeneticTestResponse]
    derived_features: List[DerivedFeatureResponse]
    completion: ProfileCompletionResponse


# ============================================================================
# AI REPORT SUMMARY SCHEMAS
# ============================================================================

class KeyFinding(BaseModel):
    """A key finding from a report"""
    item: str
    evidence: str


class SummaryHighlights(BaseModel):
    """Summary highlights with categorized items"""
    positive: List[str] = []
    needs_attention: List[str] = []
    next_steps: List[str] = []


class ReportSummaryJSON(BaseModel):
    """AI-generated summary structure for a single report"""
    title: str
    highlights: SummaryHighlights
    plain_language_summary: str
    key_findings: List[KeyFinding] = []
    confidence: float = Field(ge=0, le=1)


class KeyDifference(BaseModel):
    """A key difference between reports"""
    metric: str
    from_value: Optional[str] = Field(None, alias="from")
    to_value: Optional[str] = Field(None, alias="to")
    evidence: str

    class Config:
        populate_by_name = True


class ReportComparisonJSON(BaseModel):
    """AI-generated comparison structure for multiple reports"""
    title: str
    overall_change: str
    improvements: List[str] = []
    worsened: List[str] = []
    stable: List[str] = []
    key_differences: List[KeyDifference] = []
    next_steps: List[str] = []
    confidence: float = Field(ge=0, le=1)


class GenerateSummaryRequest(BaseModel):
    """Request to generate AI summary for a report"""
    report_id: UUID
    force_regenerate: bool = False


class GenerateCompareRequest(BaseModel):
    """Request to generate AI comparison for multiple reports"""
    report_ids: List[UUID] = Field(..., min_length=2, max_length=6)
    force_regenerate: bool = False


class SummaryResponse(BaseModel):
    """Response containing AI summary"""
    summary_json: ReportSummaryJSON
    cached: bool
    generated_at: datetime
    model_name: str

    class Config:
        from_attributes = True


class ComparisonResponse(BaseModel):
    """Response containing AI comparison"""
    comparison_json: ReportComparisonJSON
    cached: bool
    generated_at: datetime
    model_name: str

    class Config:
        from_attributes = True


class ReportForSummary(BaseModel):
    """Report data for summary/comparison"""
    id: UUID
    filename: str
    category: Optional[str]
    doc_type: Optional[str]
    report_date: Optional[datetime]
    uploaded_at: datetime
    file_path: str
    file_type: str
    preview_url: Optional[str] = None

    class Config:
        from_attributes = True

