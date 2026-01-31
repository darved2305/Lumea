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
    report_id: Optional[UUID]
    report_name: Optional[str]
    report_date: Optional[datetime]
    observation_id: Optional[UUID]
    metric_name: Optional[str]
    value: Optional[str]
    excerpt: Optional[str]


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


