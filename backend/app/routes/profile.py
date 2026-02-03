"""
Health Profile API Routes

Provides endpoints for managing user health profiles, including:
- Core profile data (basics, measurements, lifestyle)
- Conditions, symptoms, medications, allergies
- Family history and genetic tests
- Completion tracking and derived features
- Recompute trigger
"""
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db import get_db, async_session_maker
from app.security import get_current_user
from app.models import User
from app.services.profile_service import ProfileService
from app.services.recompute_service import RecomputeService
from app.schemas import (
    UserProfileUpdate, UserProfileResponse, FullProfileResponse,
    ProfileAnswerUpsert, ProfileAnswerResponse, AnswerData,
    ProfileConditionCreate, ProfileConditionResponse,
    ProfileSymptomCreate, ProfileSymptomResponse,
    ProfileMedicationCreate, ProfileMedicationResponse,
    ProfileSupplementCreate, ProfileSupplementResponse,
    ProfileAllergyCreate, ProfileAllergyResponse,
    ProfileFamilyHistoryCreate, ProfileFamilyHistoryResponse,
    ProfileGeneticTestCreate, ProfileGeneticTestResponse,
    ProfileCompletionResponse, DerivedFeatureResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profile", tags=["profile"])


# ============================================================================
# HELPER CLASSES
# ============================================================================

class BatchAnswersRequest(BaseModel):
    answers: List[ProfileAnswerUpsert]


class BatchConditionsRequest(BaseModel):
    conditions: List[ProfileConditionCreate]


class BatchSymptomsRequest(BaseModel):
    symptoms: List[ProfileSymptomCreate]


class BatchMedicationsRequest(BaseModel):
    medications: List[ProfileMedicationCreate]


class BatchSupplementsRequest(BaseModel):
    supplements: List[ProfileSupplementCreate]


class BatchAllergiesRequest(BaseModel):
    allergies: List[ProfileAllergyCreate]


class BatchFamilyHistoryRequest(BaseModel):
    history: List[ProfileFamilyHistoryCreate]


class BatchGeneticTestsRequest(BaseModel):
    tests: List[ProfileGeneticTestCreate]


# ============================================================================
# MAIN PROFILE ENDPOINTS
# ============================================================================

@router.get("", response_model=FullProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get complete user profile with all related data.
    
    Returns profile, answers, conditions, medications, allergies,
    family history, genetic tests, derived features, and completion score.
    """
    service = ProfileService(db, current_user)
    data = await service.get_full_profile()
    
    # Convert answers to response format
    answers_response = []
    for answer in data["answers"]:
        answers_response.append(ProfileAnswerResponse(
            question_id=answer.question_id,
            answer_data=AnswerData(**answer.answer_data) if answer.answer_data else AnswerData(),
            updated_at=answer.updated_at
        ))
    
    return FullProfileResponse(
        profile=UserProfileResponse.model_validate(data["profile"]) if data["profile"] else None,
        answers=answers_response,
        conditions=[ProfileConditionResponse.model_validate(c) for c in data["conditions"]],
        symptoms=[ProfileSymptomResponse.model_validate(s) for s in data["symptoms"]],
        medications=[ProfileMedicationResponse.model_validate(m) for m in data["medications"]],
        supplements=[ProfileSupplementResponse.model_validate(s) for s in data["supplements"]],
        allergies=[ProfileAllergyResponse.model_validate(a) for a in data["allergies"]],
        family_history=[ProfileFamilyHistoryResponse.model_validate(f) for f in data["family_history"]],
        genetic_tests=[ProfileGeneticTestResponse.model_validate(g) for g in data["genetic_tests"]],
        derived_features=[DerivedFeatureResponse.model_validate(d) for d in data["derived_features"]],
        completion=data["completion"]
    )


@router.patch("", response_model=UserProfileResponse)
async def update_profile(
    data: UserProfileUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update core profile fields (basics, measurements, lifestyle).
    
    Triggers recompute of derived features and health index in background.
    """
    try:
        logger.info(f"Profile PATCH for user {current_user.id}: {data.model_dump(exclude_unset=True)}")
        
        service = ProfileService(db, current_user)
        profile = await service.update_profile(data)
        
        # Trigger recompute in background
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
        logger.error(f"Profile update failed for user {current_user.id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")


# ============================================================================
# ANSWERS ENDPOINTS
# ============================================================================

@router.get("/answers", response_model=List[ProfileAnswerResponse])
async def get_answers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all profile answers"""
    service = ProfileService(db, current_user)
    answers = await service.get_all_answers()
    
    return [
        ProfileAnswerResponse(
            question_id=a.question_id,
            answer_data=AnswerData(**a.answer_data) if a.answer_data else AnswerData(),
            updated_at=a.updated_at
        )
        for a in answers
    ]


@router.post("/answers", response_model=List[ProfileAnswerResponse])
async def upsert_answers(
    request: BatchAnswersRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Batch upsert profile answers.
    
    Each answer has:
    - question_id: unique identifier for the question
    - answer_data: { value, unit?, unknown, skipped }
    """
    try:
        logger.info(f"Upserting {len(request.answers)} answers for user {current_user.id}")
        
        service = ProfileService(db, current_user)
        answers = await service.upsert_answers(request.answers)
        
        # Trigger recompute
        async def bg_recompute():
            try:
                async with async_session_maker() as session:
                    recompute_service = RecomputeService(session, current_user)
                    await recompute_service.recompute_all(emit_events=True)
            except Exception as e:
                logger.error(f"Background recompute failed: {e}")
        
        background_tasks.add_task(bg_recompute)
        
        return [
            ProfileAnswerResponse(
                question_id=a.question_id,
                answer_data=AnswerData(**a.answer_data) if a.answer_data else AnswerData(),
                updated_at=a.updated_at
            )
            for a in answers
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upsert answers for user {current_user.id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save answers: {str(e)}")


# ============================================================================
# CONDITIONS ENDPOINTS
# ============================================================================

@router.get("/conditions", response_model=List[ProfileConditionResponse])
async def get_conditions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all user conditions"""
    service = ProfileService(db, current_user)
    conditions = await service.get_conditions()
    return [ProfileConditionResponse.model_validate(c) for c in conditions]


@router.post("/conditions", response_model=List[ProfileConditionResponse])
async def set_conditions(
    request: BatchConditionsRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Set user conditions (replaces existing)"""
    service = ProfileService(db, current_user)
    conditions = await service.set_conditions(request.conditions)
    
    # Mark as answered
    await service.upsert_answers([
        ProfileAnswerUpsert(
            question_id="diagnosed_conditions_answered",
            answer_data=AnswerData(value=True)
        )
    ])
    
    # Trigger recompute
    async def bg_recompute():
        try:
            async with async_session_maker() as session:
                recompute_service = RecomputeService(session, current_user)
                await recompute_service.recompute_all(emit_events=True)
        except Exception as e:
            logger.error(f"Background recompute failed: {e}")
    
    background_tasks.add_task(bg_recompute)
    
    return [ProfileConditionResponse.model_validate(c) for c in conditions]


# ============================================================================
# SYMPTOMS ENDPOINTS
# ============================================================================

@router.get("/symptoms", response_model=List[ProfileSymptomResponse])
async def get_symptoms(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all user symptoms"""
    service = ProfileService(db, current_user)
    symptoms = await service.get_symptoms()
    return [ProfileSymptomResponse.model_validate(s) for s in symptoms]


@router.post("/symptoms", response_model=List[ProfileSymptomResponse])
async def set_symptoms(
    request: BatchSymptomsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Set user symptoms (replaces existing)"""
    service = ProfileService(db, current_user)
    symptoms = await service.set_symptoms(request.symptoms)
    return [ProfileSymptomResponse.model_validate(s) for s in symptoms]


# ============================================================================
# MEDICATIONS ENDPOINTS
# ============================================================================

@router.get("/medications", response_model=List[ProfileMedicationResponse])
async def get_medications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all user medications"""
    service = ProfileService(db, current_user)
    medications = await service.get_medications()
    return [ProfileMedicationResponse.model_validate(m) for m in medications]


@router.post("/medications", response_model=List[ProfileMedicationResponse])
async def set_medications(
    request: BatchMedicationsRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Set user medications (replaces existing)"""
    service = ProfileService(db, current_user)
    medications = await service.set_medications(request.medications)
    
    # Mark as answered
    await service.upsert_answers([
        ProfileAnswerUpsert(
            question_id="taking_medications",
            answer_data=AnswerData(value=len(medications) > 0)
        )
    ])
    
    # Trigger recompute
    async def bg_recompute():
        try:
            async with async_session_maker() as session:
                recompute_service = RecomputeService(session, current_user)
                await recompute_service.recompute_all(emit_events=True)
        except Exception as e:
            logger.error(f"Background recompute failed: {e}")
    
    background_tasks.add_task(bg_recompute)
    
    return [ProfileMedicationResponse.model_validate(m) for m in medications]


# ============================================================================
# SUPPLEMENTS ENDPOINTS
# ============================================================================

@router.get("/supplements", response_model=List[ProfileSupplementResponse])
async def get_supplements(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all user supplements"""
    service = ProfileService(db, current_user)
    supplements = await service.get_supplements()
    return [ProfileSupplementResponse.model_validate(s) for s in supplements]


@router.post("/supplements", response_model=List[ProfileSupplementResponse])
async def set_supplements(
    request: BatchSupplementsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Set user supplements (replaces existing)"""
    service = ProfileService(db, current_user)
    supplements = await service.set_supplements(request.supplements)
    
    # Mark as answered
    await service.upsert_answers([
        ProfileAnswerUpsert(
            question_id="supplements",
            answer_data=AnswerData(value=len(supplements) > 0)
        )
    ])
    
    return [ProfileSupplementResponse.model_validate(s) for s in supplements]


# ============================================================================
# ALLERGIES ENDPOINTS
# ============================================================================

@router.get("/allergies", response_model=List[ProfileAllergyResponse])
async def get_allergies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all user allergies"""
    service = ProfileService(db, current_user)
    allergies = await service.get_allergies()
    return [ProfileAllergyResponse.model_validate(a) for a in allergies]


@router.post("/allergies", response_model=List[ProfileAllergyResponse])
async def set_allergies(
    request: BatchAllergiesRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Set user allergies (replaces existing)"""
    service = ProfileService(db, current_user)
    allergies = await service.set_allergies(request.allergies)
    
    # Mark as answered
    await service.upsert_answers([
        ProfileAnswerUpsert(
            question_id="has_allergies",
            answer_data=AnswerData(value=len(allergies) > 0)
        )
    ])
    
    # Trigger recompute
    async def bg_recompute():
        try:
            async with async_session_maker() as session:
                recompute_service = RecomputeService(session, current_user)
                await recompute_service.recompute_all(emit_events=True)
        except Exception as e:
            logger.error(f"Background recompute failed: {e}")
    
    background_tasks.add_task(bg_recompute)
    
    return [ProfileAllergyResponse.model_validate(a) for a in allergies]


# ============================================================================
# FAMILY HISTORY ENDPOINTS
# ============================================================================

@router.get("/family-history", response_model=List[ProfileFamilyHistoryResponse])
async def get_family_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all family history entries"""
    service = ProfileService(db, current_user)
    history = await service.get_family_history()
    return [ProfileFamilyHistoryResponse.model_validate(h) for h in history]


@router.post("/family-history", response_model=List[ProfileFamilyHistoryResponse])
async def set_family_history(
    request: BatchFamilyHistoryRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Set family history (replaces existing)"""
    service = ProfileService(db, current_user)
    history = await service.set_family_history(request.history)
    
    # Mark as answered
    await service.upsert_answers([
        ProfileAnswerUpsert(
            question_id="family_history_any",
            answer_data=AnswerData(value=len(history) > 0)
        )
    ])
    
    # Trigger recompute
    async def bg_recompute():
        try:
            async with async_session_maker() as session:
                recompute_service = RecomputeService(session, current_user)
                await recompute_service.recompute_all(emit_events=True)
        except Exception as e:
            logger.error(f"Background recompute failed: {e}")
    
    background_tasks.add_task(bg_recompute)
    
    return [ProfileFamilyHistoryResponse.model_validate(h) for h in history]


# ============================================================================
# GENETIC TESTS ENDPOINTS
# ============================================================================

@router.get("/genetic-tests", response_model=List[ProfileGeneticTestResponse])
async def get_genetic_tests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all genetic test results"""
    service = ProfileService(db, current_user)
    tests = await service.get_genetic_tests()
    return [ProfileGeneticTestResponse.model_validate(t) for t in tests]


@router.post("/genetic-tests", response_model=List[ProfileGeneticTestResponse])
async def set_genetic_tests(
    request: BatchGeneticTestsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Set genetic test results (replaces existing)"""
    service = ProfileService(db, current_user)
    tests = await service.set_genetic_tests(request.tests)
    
    # Mark as answered
    await service.upsert_answers([
        ProfileAnswerUpsert(
            question_id="genetic_tests_any",
            answer_data=AnswerData(value=len(tests) > 0)
        )
    ])
    
    return [ProfileGeneticTestResponse.model_validate(t) for t in tests]


# ============================================================================
# COMPLETION & DERIVED FEATURES
# ============================================================================

@router.get("/completion", response_model=ProfileCompletionResponse)
async def get_completion(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get profile completion score and missing fields"""
    service = ProfileService(db, current_user)
    return await service.compute_completion()


@router.get("/derived", response_model=List[DerivedFeatureResponse])
async def get_derived_features(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get computed derived features (BMI, age, risk flags)"""
    service = ProfileService(db, current_user)
    features = await service.get_derived_features()
    return [DerivedFeatureResponse.model_validate(f) for f in features]


@router.post("/recompute")
async def trigger_recompute(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger full recompute of derived features, health index,
    recommendations, and trends. Emits WebSocket events.
    """
    recompute_service = RecomputeService(db, current_user)
    result = await recompute_service.recompute_all(emit_events=True)
    return result


# ============================================================================
# WIZARD STATE
# ============================================================================

class WizardStateUpdate(BaseModel):
    current_step: int
    completed: Optional[bool] = None


@router.patch("/wizard-state")
async def update_wizard_state(
    data: WizardStateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update wizard progress state"""
    service = ProfileService(db, current_user)
    profile = await service.get_or_create_profile()
    
    profile.wizard_current_step = data.current_step
    if data.completed is not None:
        profile.wizard_completed = data.completed
    profile.wizard_last_saved_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(profile)
    
    return {
        "wizard_current_step": profile.wizard_current_step,
        "wizard_completed": profile.wizard_completed,
        "wizard_last_saved_at": profile.wizard_last_saved_at.isoformat() if profile.wizard_last_saved_at else None
    }
