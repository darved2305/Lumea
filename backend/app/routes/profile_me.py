"""
Profile Me & Reminders API Routes

Simplified endpoints for:
- GET /api/profile/me - Check profile existence and completion status
- PUT /api/profile/me - Upsert health profile (create or update)
- PATCH /api/profile/me - Partial update for settings page

Reminder endpoints:
- GET /api/reminders/me - Get user's reminders
- POST /api/reminders - Create reminder
- PATCH /api/reminders/{id} - Update reminder
- DELETE /api/reminders/{id} - Delete reminder
- POST /api/reminders/generate-default - Generate default reminders

SMS endpoints:
- POST /api/sms/test - Send test SMS (uses env test number)
"""
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db import get_db, async_session_maker
from app.security import get_current_user
from app.models import User, UserProfile, Reminder, ReminderEvent
from app.services.profile_service import ProfileService
from app.services.recompute_service import RecomputeService
from app.services.reminder_service import (
    ReminderService, 
    check_profile_completion, 
    compute_bmi
)
from app.services.sms_sender import get_sms_sender
from app.schemas import (
    UserProfileUpdate, 
    UserProfileResponse,
    ProfileMeResponse,
    ProfileCompletionResponse,
    ReminderCreate,
    ReminderUpdate,
    ReminderResponse,
    ReminderEventResponse,
    SMSTestRequest,
    SMSTestResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["profile-me", "reminders", "sms"])


# ============================================================================
# PROFILE /ME ENDPOINTS
# ============================================================================

@router.get("/api/profile/me", response_model=ProfileMeResponse)
async def get_profile_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's profile status.
    
    Returns:
    - exists: bool - whether profile record exists
    - is_completed: bool - whether all required fields are filled
    - profile: full profile data if exists
    - completion: completion score and missing fields
    """
    try:
        # Get profile
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == current_user.id)
        )
        profile = result.scalar_one_or_none()
        
        if not profile:
            logger.info(f"No profile found for user {current_user.id}")
            return ProfileMeResponse(
                exists=False,
                is_completed=False,
                profile=None,
                completion=ProfileCompletionResponse(
                    score=0,
                    missing_essentials=["full_name", "age", "gender", "height", "weight"],
                    missing_optional=[],
                    estimated_fields=[],
                    completion_by_step={}
                )
            )
        
        # Get completion info via ProfileService
        service = ProfileService(db, current_user)
        full_data = await service.get_full_profile()
        
        return ProfileMeResponse(
            exists=True,
            is_completed=profile.is_completed,
            profile=UserProfileResponse.model_validate(profile),
            completion=full_data["completion"]
        )
        
    except Exception as e:
        logger.error(f"Error getting profile/me for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/profile/me", response_model=UserProfileResponse)
async def upsert_profile_me(
    data: UserProfileUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create or update user's health profile (UPSERT).
    
    - Creates profile if not exists
    - Updates if exists
    - Computes BMI if height & weight provided
    - Sets is_completed=true and completed_at when all required fields present
    """
    try:
        logger.info(f"Profile PUT (upsert) for user {current_user.id}")
        
        # Check if profile exists
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == current_user.id)
        )
        profile = result.scalar_one_or_none()
        
        update_data = data.model_dump(exclude_unset=True)
        
        if not profile:
            # Create new profile
            logger.info(f"Creating new profile for user {current_user.id}")
            profile = UserProfile(
                user_id=current_user.id,
                **update_data
            )
            db.add(profile)
        else:
            # Update existing
            logger.info(f"Updating existing profile for user {current_user.id}")
            for field, value in update_data.items():
                if hasattr(profile, field):
                    setattr(profile, field, value)
        
        # Compute BMI if height and weight available
        height = update_data.get("height_cm") or profile.height_cm
        weight = update_data.get("weight_kg") or profile.weight_kg
        
        # Store BMI in derived_features (via recompute service)
        # For now just log it
        if height and weight:
            bmi = compute_bmi(height, weight)
            logger.info(f"Computed BMI for user {current_user.id}: {bmi}")
        
        # Check completion status
        profile.updated_at = datetime.utcnow()
        
        # Need to flush to check completion with updated values
        await db.flush()
        await db.refresh(profile)
        
        is_now_complete = check_profile_completion(profile)
        
        if is_now_complete and not profile.is_completed:
            # First time completing profile
            profile.is_completed = True
            profile.completed_at = datetime.utcnow()
            profile.wizard_completed = True
            logger.info(f"Profile marked as completed for user {current_user.id}")
        elif is_now_complete:
            # Already complete, keep it
            profile.is_completed = True
        else:
            # Not complete
            profile.is_completed = False
        
        await db.commit()
        await db.refresh(profile)
        
        # Trigger recompute in background
        async def bg_recompute():
            try:
                async with async_session_maker() as session:
                    recompute_service = RecomputeService(session, current_user)
                    await recompute_service.recompute_all(emit_events=True)
            except Exception as e:
                logger.error(f"Background recompute failed: {e}")
        
        background_tasks.add_task(bg_recompute)
        
        logger.info(f"Profile upsert successful for user {current_user.id}, is_completed={profile.is_completed}")
        return UserProfileResponse.model_validate(profile)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile upsert failed for user {current_user.id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save profile: {str(e)}")


@router.patch("/api/profile/me", response_model=UserProfileResponse)
async def patch_profile_me(
    data: UserProfileUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Partial update for profile (used by Settings page).
    
    Same as PUT but only updates provided fields.
    Profile must exist (use PUT for initial creation).
    """
    try:
        logger.info(f"Profile PATCH for user {current_user.id}")
        
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == current_user.id)
        )
        profile = result.scalar_one_or_none()
        
        if not profile:
            raise HTTPException(
                status_code=404,
                detail="Profile not found. Use PUT /api/profile/me to create."
            )
        
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(profile, field):
                setattr(profile, field, value)
        
        profile.updated_at = datetime.utcnow()
        
        # Recheck completion
        await db.flush()
        await db.refresh(profile)
        
        is_now_complete = check_profile_completion(profile)
        
        if is_now_complete and not profile.is_completed:
            profile.is_completed = True
            profile.completed_at = datetime.utcnow()
            profile.wizard_completed = True
        elif is_now_complete:
            profile.is_completed = True
        else:
            profile.is_completed = False
        
        await db.commit()
        await db.refresh(profile)
        
        # Background recompute
        async def bg_recompute():
            try:
                async with async_session_maker() as session:
                    recompute_service = RecomputeService(session, current_user)
                    await recompute_service.recompute_all(emit_events=True)
            except Exception as e:
                logger.error(f"Background recompute failed: {e}")
        
        background_tasks.add_task(bg_recompute)
        
        return UserProfileResponse.model_validate(profile)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile PATCH failed for user {current_user.id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")


# ============================================================================
# REMINDER ENDPOINTS
# ============================================================================

@router.get("/api/reminders/me", response_model=List[ReminderResponse])
async def get_my_reminders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all reminders for the current user."""
    service = ReminderService(db, current_user)
    reminders = await service.get_all()
    return [ReminderResponse.model_validate(r) for r in reminders]


@router.post("/api/reminders", response_model=ReminderResponse)
async def create_reminder(
    data: ReminderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new reminder."""
    service = ReminderService(db, current_user)
    reminder = await service.create(data.model_dump())
    return ReminderResponse.model_validate(reminder)


@router.patch("/api/reminders/{reminder_id}", response_model=ReminderResponse)
async def update_reminder(
    reminder_id: UUID,
    data: ReminderUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an existing reminder."""
    service = ReminderService(db, current_user)
    reminder = await service.update(reminder_id, data.model_dump(exclude_unset=True))
    
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    
    return ReminderResponse.model_validate(reminder)


@router.delete("/api/reminders/{reminder_id}")
async def delete_reminder(
    reminder_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a reminder."""
    service = ReminderService(db, current_user)
    deleted = await service.delete(reminder_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Reminder not found")
    
    return {"status": "deleted", "id": str(reminder_id)}


@router.post("/api/reminders/generate-default", response_model=List[ReminderResponse])
async def generate_default_reminders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate default reminders based on user profile.
    
    Creates hydration, sleep, and exercise reminders (if applicable).
    Skips reminders that already exist.
    """
    service = ReminderService(db, current_user)
    reminders = await service.generate_default_reminders()
    return [ReminderResponse.model_validate(r) for r in reminders]


@router.get("/api/reminders/{reminder_id}/events", response_model=List[ReminderEventResponse])
async def get_reminder_events(
    reminder_id: UUID,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get delivery events for a specific reminder."""
    # Verify reminder belongs to user
    service = ReminderService(db, current_user)
    reminder = await service.get_by_id(reminder_id)
    
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    
    # Get events
    result = await db.execute(
        select(ReminderEvent)
        .where(ReminderEvent.reminder_id == reminder_id)
        .order_by(ReminderEvent.sent_at.desc())
        .limit(limit)
    )
    events = list(result.scalars().all())
    
    return [ReminderEventResponse.model_validate(e) for e in events]


# ============================================================================
# SMS ENDPOINTS
# ============================================================================

@router.post("/api/sms/test", response_model=SMSTestResponse)
async def send_test_sms(
    request: SMSTestRequest = SMSTestRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a test SMS to the configured test number (from SMS_TEST_TO_NUMBER env).
    
    This is for testing only - does NOT send to user's phone number.
    """
    sms_sender = get_sms_sender()
    result = await sms_sender.send_test(request.message)
    
    # Log the test event
    event = ReminderEvent(
        reminder_id=None,  # No associated reminder
        user_id=current_user.id,
        status=result["status"],
        provider=result["provider"],
        provider_response=result.get("provider_response"),
        message_sent=request.message,
        error_message=result.get("error")
    )
    
    # Note: Can't save without reminder_id FK, so just log
    logger.info(f"SMS test by user {current_user.id}: {result['status']}")
    
    return SMSTestResponse(
        success=result["success"],
        status=result["status"],
        provider=result["provider"],
        message=f"Test SMS {'sent' if result['success'] else 'failed'}",
        provider_response=result.get("provider_response")
    )
