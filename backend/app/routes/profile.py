"""
Health Profile API Routes

Provides endpoints for managing user health profiles, including:
- Core profile data (basics, measurements, lifestyle)
- Conditions, symptoms, medications, allergies
- Family history and genetic tests
- Completion tracking and derived features
- Recompute trigger
"""
import asyncio
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db import get_db, async_session_maker
from app.security import get_current_user
from app.models import User
from app.settings import settings
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
MEMORY_SYNC_TIMEOUT_SECONDS = 60.0
MEMORY_SYNC_MAX_RETRIES = 2
MEMORY_SYNC_RETRY_BASE_SECONDS = 3.0


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


# ============================================================================
# MEMORY & GRAPH SYNC
# ============================================================================

def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_fact(text: str) -> str:
    return " ".join(text.strip().split())


def _build_profile_sync_facts(profile_data: Dict[str, Any]) -> List[str]:
    """Build direct profile facts + lightweight inferred insights for memory/graph sync."""
    facts: List[str] = []

    profile = profile_data.get("profile")
    if profile:
        if profile.height_cm:
            facts.append(f"height is {profile.height_cm} cm")
        if profile.weight_kg:
            facts.append(f"weight is {profile.weight_kg} kg")
        if profile.sex_at_birth:
            facts.append(f"sex at birth is {profile.sex_at_birth}")
        if profile.activity_level:
            facts.append(f"activity level is {profile.activity_level}")
        if profile.sleep_hours_avg:
            facts.append(f"sleep is about {profile.sleep_hours_avg} hours per night")
        if profile.diet_pattern:
            facts.append(f"diet pattern is {profile.diet_pattern}")
        if profile.smoking:
            facts.append(f"smoking status is {profile.smoking}")
        if profile.alcohol:
            facts.append(f"alcohol use is {profile.alcohol}")

    # Conditions
    conditions = profile_data.get("conditions", []) or []
    for condition in conditions:
        if condition.condition_name:
            facts.append(f"has condition {condition.condition_name}")

    # Medications
    medications = profile_data.get("medications", []) or []
    for med in medications:
        if med.name:
            fact = f"takes medication {med.name}"
            if med.dose:
                fact += f" at dose {med.dose}"
            facts.append(fact)

    # Supplements
    supplements = profile_data.get("supplements", []) or []
    for supp in supplements:
        if supp.name:
            fact = f"takes supplement {supp.name}"
            if supp.dose:
                fact += f" at dose {supp.dose}"
            facts.append(fact)

    # Allergies
    allergies = profile_data.get("allergies", []) or []
    for allergy in allergies:
        if allergy.allergen:
            facts.append(f"is allergic to {allergy.allergen}")

    # Family history
    family_history = profile_data.get("family_history", []) or []
    for history in family_history:
        if history.condition_name and history.relative_type:
            facts.append(f"family history includes {history.relative_type} with {history.condition_name}")

    # Lightweight, deterministic inferences from questionnaire data.
    if profile:
        height_cm = _safe_float(profile.height_cm)
        weight_kg = _safe_float(profile.weight_kg)
        if height_cm and height_cm > 0 and weight_kg and weight_kg > 0:
            bmi = round(weight_kg / ((height_cm / 100.0) ** 2), 1)
            if bmi < 18.5:
                bmi_band = "underweight"
            elif bmi < 25:
                bmi_band = "normal"
            elif bmi < 30:
                bmi_band = "overweight"
            else:
                bmi_band = "obesity"
            facts.append(f"inference: bmi is {bmi} which falls in {bmi_band} range")

        exercise_minutes = _safe_float(profile.exercise_minutes_per_week)
        if exercise_minutes is not None:
            if exercise_minutes < 90:
                facts.append("inference: weekly activity is low and may increase cardiometabolic risk")
            elif exercise_minutes >= 150:
                facts.append("inference: weekly activity meets or exceeds recommended baseline")

        sleep_hours = _safe_float(profile.sleep_hours_avg)
        if sleep_hours is not None:
            if sleep_hours < 6:
                facts.append("inference: habitual short sleep may affect recovery and metabolic health")
            elif sleep_hours >= 7:
                facts.append("inference: sleep duration is within a generally healthy range")

        smoking_value = str(profile.smoking or "").strip().lower()
        if smoking_value in {"yes", "current", "daily", "sometimes"}:
            facts.append("inference: smoking status indicates elevated cardiovascular and respiratory risk")

        alcohol_value = str(profile.alcohol or "").strip().lower()
        if alcohol_value in {"heavy", "daily", "frequent"}:
            facts.append("inference: alcohol pattern may impact liver and cardiometabolic risk profile")

    if conditions and family_history:
        facts.append("inference: combined personal and family history increases value of preventive monitoring")
    if medications and allergies:
        facts.append("inference: medication planning should remain allergy-aware")

    # De-duplicate while preserving order and keeping text normalized.
    deduped: List[str] = []
    seen = set()
    for fact in facts:
        normalized = _normalize_fact(fact)
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)

    return deduped


@router.post("/sync-to-memory")
async def sync_profile_to_memory(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Sync user profile data to Memory (Mem0) and Knowledge Graph (Neo4j).
    
    Called after questionnaire completion to ensure all health data
    is available for the recommendation engine's provenance tracking.
    """
    from app.services.memory_service import get_memory_service
    from app.services.graph_service import get_graph_service
    
    service = ProfileService(db, current_user)
    profile_data = await service.get_full_profile()
    
    user_id = str(current_user.id)
    facts_to_sync = _build_profile_sync_facts(profile_data)
    synced = {
        "memory": False,
        "graph": False,
        "facts_attempted": len(facts_to_sync),
        "facts_synced": 0,
        "memory_facts_synced": 0,
        "graph_facts_synced": 0,
    }
    errors: List[str] = []

    if not facts_to_sync:
        return {
            "success": False,
            "synced": synced,
            "errors": ["No profile facts were available to sync yet."],
            "message": "No profile facts available to sync",
        }

    # Sync to Memory (Mem0)
    memory_service = get_memory_service()
    if not memory_service.is_available:
        errors.append("Memory service (Mem0) is not available.")
    else:
        batch_size = settings.MEM0_SYNC_BATCH_SIZE
        batch_delay = settings.MEM0_BATCH_DELAY_SECONDS
        memory_batches = [
            facts_to_sync[i : i + batch_size]
            for i in range(0, len(facts_to_sync), batch_size)
        ]

        async def _sync_batch(batch_index: int, batch: List[str]) -> bool:
            batch_content = "profile sync snapshot facts:\n" + "\n".join(f"- {fact}" for fact in batch)

            for attempt in range(1, MEMORY_SYNC_MAX_RETRIES + 1):
                try:
                    result = await asyncio.wait_for(
                        memory_service.add(
                            content=batch_content,
                            user_id=user_id,
                            metadata={
                                "source": "questionnaire_sync",
                                "kind": "profile_fact_batch",
                                "batch_index": batch_index,
                                "batch_size": len(batch),
                            },
                        ),
                        timeout=MEMORY_SYNC_TIMEOUT_SECONDS,
                    )
                except asyncio.TimeoutError:
                    logger.warning(
                        "Timed out syncing Mem0 batch %s for user %s after %.1fs (attempt %s/%s)",
                        batch_index,
                        user_id,
                        MEMORY_SYNC_TIMEOUT_SECONDS,
                        attempt,
                        MEMORY_SYNC_MAX_RETRIES,
                    )
                    if attempt < MEMORY_SYNC_MAX_RETRIES:
                        await asyncio.sleep(MEMORY_SYNC_RETRY_BASE_SECONDS * attempt)
                        continue
                    return False
                except Exception as exc:
                    logger.warning(
                        "Unexpected Mem0 batch sync error for user %s (batch %s, attempt %s/%s): %s",
                        user_id,
                        batch_index,
                        attempt,
                        MEMORY_SYNC_MAX_RETRIES,
                        exc,
                    )
                    if attempt < MEMORY_SYNC_MAX_RETRIES:
                        await asyncio.sleep(MEMORY_SYNC_RETRY_BASE_SECONDS * attempt)
                        continue
                    return False

                # memory_service.add() now self-retries on 429; a returned error
                # here means retries were exhausted or a non-429 failure occurred.
                if isinstance(result, dict) and result.get("error"):
                    err_text = str(result["error"])
                    logger.warning(
                        "Mem0 batch sync failed for user %s (batch %s, attempt %s/%s): %s",
                        user_id,
                        batch_index,
                        attempt,
                        MEMORY_SYNC_MAX_RETRIES,
                        err_text,
                    )
                    if attempt < MEMORY_SYNC_MAX_RETRIES:
                        await asyncio.sleep(MEMORY_SYNC_RETRY_BASE_SECONDS * attempt)
                        continue
                    return False

                return True

            return False

        memory_sync_count = 0
        for batch_index, batch in enumerate(memory_batches, start=1):
            batch_synced = await _sync_batch(batch_index, batch)
            if batch_synced:
                memory_sync_count += len(batch)
            # Proactive inter-batch delay to avoid Groq TPM exhaustion
            if batch_index < len(memory_batches) and batch_delay > 0:
                logger.debug(
                    "Mem0 sync: proactive %.1fs delay before batch %s/%s",
                    batch_delay, batch_index + 1, len(memory_batches),
                )
                await asyncio.sleep(batch_delay)

        if memory_sync_count < len(facts_to_sync):
            logger.info("Mem0 sync partial success for user %s: %s/%s facts", user_id, memory_sync_count, len(facts_to_sync))

        synced["memory_facts_synced"] = memory_sync_count
        synced["memory"] = memory_sync_count > 0
        if memory_sync_count > 0:
            logger.info("Synced %s facts to Mem0 for user %s", memory_sync_count, user_id)
        else:
            errors.append(memory_service.last_error or "Failed to sync questionnaire data to Mem0.")
    
    # Sync to Graph (Neo4j/Graphiti)
    graph_service = get_graph_service()
    if graph_service.client is not None:
        try:
            await graph_service.add_user_facts(
                user_id=user_id,
                facts=facts_to_sync,
                source="questionnaire_sync",
                timestamp=datetime.utcnow().isoformat(),
            )
            synced["graph"] = True
            synced["graph_facts_synced"] = len(facts_to_sync)
            logger.info("Synced %s facts to Neo4j for user %s", len(facts_to_sync), user_id)
        except Exception as e:
            logger.warning("Failed to sync to Neo4j: %s", e)
            errors.append(f"Graph sync failed: {e}")
    else:
        errors.append("Knowledge graph service is not available.")

    synced["facts_synced"] = max(synced["memory_facts_synced"], synced["graph_facts_synced"])
    overall_success = synced["memory"] or synced["graph"]

    return {
        "success": overall_success,
        "synced": synced,
        "errors": errors,
        "message": (
            f"Synced {synced['facts_synced']} profile facts to memory/graph layers"
            if overall_success
            else "Profile sync failed for both memory and graph layers"
        ),
    }
