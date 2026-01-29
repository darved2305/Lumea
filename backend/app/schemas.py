from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
from typing import Optional, List
from uuid import UUID

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

