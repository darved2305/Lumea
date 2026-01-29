from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from uuid import UUID
import uuid
from datetime import datetime

from app.db import get_db
from app.models import User, PatientProfile, ChatSession, ChatMessage
from app.schemas import (
    PatientProfileCreate, PatientProfileUpdate, PatientProfileResponse,
    RemindersResponse, ChatMessageCreate, ChatMessageResponse, ChatSessionResponse,
    UserResponse
)
from app.security import decode_access_token
from app.reminders import compute_reminders

router = APIRouter(prefix="/api", tags=["health"])

async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """Extract and verify JWT from httpOnly cookie"""
    token = request.cookies.get("auth_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user

# Get current user info
@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information"""
    return current_user

# Get patient profile
@router.get("/profile", response_model=PatientProfileResponse)
async def get_profile(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get patient profile for authenticated user"""
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return profile

# Create or update patient profile
@router.post("/profile", response_model=PatientProfileResponse)
@router.put("/profile", response_model=PatientProfileResponse)
async def upsert_profile(
    profile_data: PatientProfileUpdate,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create or update patient profile"""
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    
    # Check if profile exists
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    
    # Calculate BMI if height and weight provided
    bmi = None
    height_cm = profile_data.height_cm if profile_data.height_cm is not None else (profile.height_cm if profile else None)
    weight_kg = profile_data.weight_kg if profile_data.weight_kg is not None else (profile.weight_kg if profile else None)
    
    if height_cm and weight_kg and height_cm > 0:
        height_m = height_cm / 100
        bmi = round(weight_kg / (height_m * height_m), 1)
    
    if profile:
        # Update existing profile
        update_data = profile_data.dict(exclude_unset=True)
        update_data['bmi'] = bmi
        update_data['updated_at'] = datetime.utcnow()
        
        await db.execute(
            update(PatientProfile)
            .where(PatientProfile.user_id == current_user.id)
            .values(**update_data)
        )
        await db.commit()
        
        # Fetch updated profile
        result = await db.execute(
            select(PatientProfile).where(PatientProfile.user_id == current_user.id)
        )
        profile = result.scalar_one()
    else:
        # Create new profile
        profile = PatientProfile(
            id=uuid.uuid4(),
            user_id=current_user.id,
            **profile_data.dict(exclude_unset=True),
            bmi=bmi
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    
    return profile

# Get reminders
@router.get("/reminders", response_model=RemindersResponse)
async def get_reminders(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get computed health reminders based on patient profile"""
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        # Return empty reminders if no profile
        return RemindersResponse(reminders=[])
    
    # Convert profile to dict for reminders computation
    profile_dict = {
        'conditions': profile.conditions or [],
        'last_blood_test_at': profile.last_blood_test_at,
        'last_dental_at': profile.last_dental_at,
        'last_eye_exam_at': profile.last_eye_exam_at
    }
    
    reminders = compute_reminders(profile_dict)
    return RemindersResponse(reminders=reminders)

# Chat endpoint
@router.post("/chat", response_model=ChatMessageResponse)
async def chat(
    chat_request: ChatMessageCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle chat messages. Works for both authenticated users and guests.
    For guests, provide guest_key in request body.
    """
    user_id = None
    guest_key = chat_request.guest_key
    
    # Try to get authenticated user
    try:
        token = request.cookies.get("auth_token")
        if token:
            payload = decode_access_token(token)
            if payload:
                user_id = payload.get("sub")
    except:
        pass
    
    # Must have either user_id or guest_key
    if not user_id and not guest_key:
        raise HTTPException(status_code=400, detail="Must be authenticated or provide guest_key")
    
    # Find or create chat session
    if user_id:
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == UUID(user_id))
            .order_by(ChatSession.created_at.desc())
        )
        session = result.scalar_one_or_none()
        
        if not session:
            session = ChatSession(
                id=uuid.uuid4(),
                user_id=UUID(user_id),
                guest_key=None
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)
    else:
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.guest_key == guest_key)
            .order_by(ChatSession.created_at.desc())
        )
        session = result.scalar_one_or_none()
        
        if not session:
            session = ChatSession(
                id=uuid.uuid4(),
                user_id=None,
                guest_key=guest_key
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)
    
    # Save user message
    user_message = ChatMessage(
        id=uuid.uuid4(),
        session_id=session.id,
        role='user',
        content=chat_request.message
    )
    db.add(user_message)
    await db.commit()
    
    # Generate assistant response (MVP stub)
    # Get profile for personalization if authenticated
    profile_context = ""
    if user_id:
        result = await db.execute(
            select(PatientProfile).where(PatientProfile.user_id == UUID(user_id))
        )
        profile = result.scalar_one_or_none()
        if profile:
            profile_dict = {
                'conditions': profile.conditions or [],
                'last_blood_test_at': profile.last_blood_test_at,
                'last_dental_at': profile.last_dental_at,
                'last_eye_exam_at': profile.last_eye_exam_at
            }
            reminders = compute_reminders(profile_dict)
            if reminders:
                overdue = [r for r in reminders if r.urgency == 'overdue']
                if overdue:
                    profile_context = f"\n\nBased on your profile, you have {len(overdue)} overdue health checkup(s). Consider scheduling: " + ", ".join([r.title for r in overdue[:2]])
    
    assistant_content = f"Thank you for your message. I understand you're asking about: '{chat_request.message[:100]}...'\n\nAs your health companion, I'm here to help you track checkups and reminders.{profile_context}\n\n⚠️ **Important**: This is not medical advice. Always consult with qualified healthcare professionals for medical decisions."
    
    assistant_message = ChatMessage(
        id=uuid.uuid4(),
        session_id=session.id,
        role='assistant',
        content=assistant_content
    )
    db.add(assistant_message)
    await db.commit()
    await db.refresh(assistant_message)
    
    return assistant_message

# Get chat history
@router.get("/chat/history", response_model=ChatSessionResponse)
async def get_chat_history(
    request: Request,
    guest_key: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Get chat history for authenticated user or guest"""
    user_id = None
    
    # Try to get authenticated user
    try:
        token = request.cookies.get("auth_token")
        if token:
            payload = decode_access_token(token)
            if payload:
                user_id = payload.get("sub")
    except:
        pass
    
    if not user_id and not guest_key:
        raise HTTPException(status_code=400, detail="Must be authenticated or provide guest_key")
    
    # Find session
    if user_id:
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == UUID(user_id))
            .order_by(ChatSession.created_at.desc())
        )
    else:
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.guest_key == guest_key)
            .order_by(ChatSession.created_at.desc())
        )
    
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="No chat history found")
    
    # Get messages
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()
    
    return ChatSessionResponse(
        id=session.id,
        messages=messages,
        created_at=session.created_at
    )
