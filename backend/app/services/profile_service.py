"""
Health Profile Service

Manages user health profiles, answers, and derived computations.
Triggers recompute pipeline on profile changes.
"""
import logging
import uuid
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert

from app.models import (
    User, UserProfile, ProfileAnswer, ProfileCondition, ProfileSymptom,
    ProfileMedication, ProfileSupplement, ProfileAllergy, ProfileFamilyHistory,
    ProfileGeneticTest, DerivedFeature, ProfileRecommendation
)
from app.schemas import (
    UserProfileUpdate, ProfileAnswerUpsert, AnswerData,
    ProfileConditionCreate, ProfileSymptomCreate, ProfileMedicationCreate,
    ProfileSupplementCreate, ProfileAllergyCreate, ProfileFamilyHistoryCreate,
    ProfileGeneticTestCreate, ProfileCompletionResponse
)

logger = logging.getLogger(__name__)


# Essential fields with their weights for completion score
ESSENTIAL_FIELDS = {
    "date_of_birth": 15,
    "age_years": 10,  # Alternative to DOB
    "sex_at_birth": 12,
    "height_cm": 10,
    "weight_kg": 10,
    "activity_level": 8,
    "smoking": 8,
    "alcohol": 5,
    "diagnosed_conditions": 12,  # At least responded to conditions question
    "taking_medications": 5,
    "allergies": 5,
}

OPTIONAL_FIELDS = {
    "full_name": 2,
    "gender": 1,
    "city": 1,
    "waist_cm": 3,
    "sleep_hours_avg": 3,
    "sleep_quality": 2,
    "exercise_minutes_per_week": 3,
    "diet_pattern": 2,
    "family_history": 5,
    "genetic_tests": 2,
    "supplements": 1,
}


class ProfileService:
    """Service for managing health profiles"""
    
    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user
    
    # ========================================================================
    # PROFILE CRUD
    # ========================================================================
    
    async def get_or_create_profile(self) -> UserProfile:
        """Get existing profile or create new one"""
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == self.user.id)
        )
        profile = result.scalar_one_or_none()
        
        if not profile:
            profile = UserProfile(
                id=uuid.uuid4(),
                user_id=self.user.id,
                wizard_current_step=1,
                wizard_completed=False
            )
            self.db.add(profile)
            await self.db.commit()
            await self.db.refresh(profile)
        
        return profile
    
    async def get_profile(self) -> Optional[UserProfile]:
        """Get user profile if exists"""
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == self.user.id)
        )
        return result.scalar_one_or_none()
    
    async def update_profile(self, data: UserProfileUpdate) -> UserProfile:
        """Update core profile fields"""
        profile = await self.get_or_create_profile()
        
        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(profile, field):
                setattr(profile, field, value)
        
        profile.wizard_last_saved_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(profile)
        
        return profile
    
    # ========================================================================
    # PROFILE ANSWERS
    # ========================================================================
    
    async def get_all_answers(self) -> List[ProfileAnswer]:
        """Get all profile answers for user"""
        result = await self.db.execute(
            select(ProfileAnswer).where(ProfileAnswer.user_id == self.user.id)
        )
        return result.scalars().all()
    
    async def upsert_answers(self, answers: List[ProfileAnswerUpsert]) -> List[ProfileAnswer]:
        """Batch upsert profile answers"""
        results = []
        
        for answer in answers:
            # Check if answer exists
            result = await self.db.execute(
                select(ProfileAnswer).where(
                    ProfileAnswer.user_id == self.user.id,
                    ProfileAnswer.question_id == answer.question_id
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                existing.answer_data = answer.answer_data.model_dump()
                existing.updated_at = datetime.utcnow()
                results.append(existing)
            else:
                new_answer = ProfileAnswer(
                    id=uuid.uuid4(),
                    user_id=self.user.id,
                    question_id=answer.question_id,
                    answer_data=answer.answer_data.model_dump()
                )
                self.db.add(new_answer)
                results.append(new_answer)
        
        await self.db.commit()
        for r in results:
            await self.db.refresh(r)
        
        return results
    
    # ========================================================================
    # CONDITIONS
    # ========================================================================
    
    async def get_conditions(self) -> List[ProfileCondition]:
        """Get all conditions for user"""
        result = await self.db.execute(
            select(ProfileCondition).where(
                ProfileCondition.user_id == self.user.id,
                ProfileCondition.is_active == True
            )
        )
        return result.scalars().all()
    
    async def set_conditions(self, conditions: List[ProfileConditionCreate]) -> List[ProfileCondition]:
        """Replace all conditions (delete existing, add new)"""
        # Delete existing
        await self.db.execute(
            delete(ProfileCondition).where(ProfileCondition.user_id == self.user.id)
        )
        
        # Add new
        results = []
        for cond in conditions:
            new_cond = ProfileCondition(
                id=uuid.uuid4(),
                user_id=self.user.id,
                **cond.model_dump()
            )
            self.db.add(new_cond)
            results.append(new_cond)
        
        await self.db.commit()
        return results
    
    # ========================================================================
    # SYMPTOMS
    # ========================================================================
    
    async def get_symptoms(self) -> List[ProfileSymptom]:
        """Get all symptoms for user"""
        result = await self.db.execute(
            select(ProfileSymptom).where(ProfileSymptom.user_id == self.user.id)
        )
        return result.scalars().all()
    
    async def set_symptoms(self, symptoms: List[ProfileSymptomCreate]) -> List[ProfileSymptom]:
        """Replace all symptoms"""
        await self.db.execute(
            delete(ProfileSymptom).where(ProfileSymptom.user_id == self.user.id)
        )
        
        results = []
        for symp in symptoms:
            new_symp = ProfileSymptom(
                id=uuid.uuid4(),
                user_id=self.user.id,
                **symp.model_dump()
            )
            self.db.add(new_symp)
            results.append(new_symp)
        
        await self.db.commit()
        return results
    
    # ========================================================================
    # MEDICATIONS
    # ========================================================================
    
    async def get_medications(self) -> List[ProfileMedication]:
        """Get all active medications"""
        result = await self.db.execute(
            select(ProfileMedication).where(
                ProfileMedication.user_id == self.user.id,
                ProfileMedication.is_active == True
            )
        )
        return result.scalars().all()
    
    async def set_medications(self, medications: List[ProfileMedicationCreate]) -> List[ProfileMedication]:
        """Replace all medications"""
        await self.db.execute(
            delete(ProfileMedication).where(ProfileMedication.user_id == self.user.id)
        )
        
        results = []
        for med in medications:
            new_med = ProfileMedication(
                id=uuid.uuid4(),
                user_id=self.user.id,
                **med.model_dump()
            )
            self.db.add(new_med)
            results.append(new_med)
        
        await self.db.commit()
        return results
    
    # ========================================================================
    # SUPPLEMENTS
    # ========================================================================
    
    async def get_supplements(self) -> List[ProfileSupplement]:
        """Get all active supplements"""
        result = await self.db.execute(
            select(ProfileSupplement).where(
                ProfileSupplement.user_id == self.user.id,
                ProfileSupplement.is_active == True
            )
        )
        return result.scalars().all()
    
    async def set_supplements(self, supplements: List[ProfileSupplementCreate]) -> List[ProfileSupplement]:
        """Replace all supplements"""
        await self.db.execute(
            delete(ProfileSupplement).where(ProfileSupplement.user_id == self.user.id)
        )
        
        results = []
        for supp in supplements:
            new_supp = ProfileSupplement(
                id=uuid.uuid4(),
                user_id=self.user.id,
                **supp.model_dump()
            )
            self.db.add(new_supp)
            results.append(new_supp)
        
        await self.db.commit()
        return results
    
    # ========================================================================
    # ALLERGIES
    # ========================================================================
    
    async def get_allergies(self) -> List[ProfileAllergy]:
        """Get all allergies"""
        result = await self.db.execute(
            select(ProfileAllergy).where(ProfileAllergy.user_id == self.user.id)
        )
        return result.scalars().all()
    
    async def set_allergies(self, allergies: List[ProfileAllergyCreate]) -> List[ProfileAllergy]:
        """Replace all allergies"""
        await self.db.execute(
            delete(ProfileAllergy).where(ProfileAllergy.user_id == self.user.id)
        )
        
        results = []
        for allergy in allergies:
            new_allergy = ProfileAllergy(
                id=uuid.uuid4(),
                user_id=self.user.id,
                **allergy.model_dump()
            )
            self.db.add(new_allergy)
            results.append(new_allergy)
        
        await self.db.commit()
        return results
    
    # ========================================================================
    # FAMILY HISTORY
    # ========================================================================
    
    async def get_family_history(self) -> List[ProfileFamilyHistory]:
        """Get all family history entries"""
        result = await self.db.execute(
            select(ProfileFamilyHistory).where(ProfileFamilyHistory.user_id == self.user.id)
        )
        return result.scalars().all()
    
    async def set_family_history(self, history: List[ProfileFamilyHistoryCreate]) -> List[ProfileFamilyHistory]:
        """Replace all family history"""
        await self.db.execute(
            delete(ProfileFamilyHistory).where(ProfileFamilyHistory.user_id == self.user.id)
        )
        
        results = []
        for entry in history:
            new_entry = ProfileFamilyHistory(
                id=uuid.uuid4(),
                user_id=self.user.id,
                **entry.model_dump()
            )
            self.db.add(new_entry)
            results.append(new_entry)
        
        await self.db.commit()
        return results
    
    # ========================================================================
    # GENETIC TESTS
    # ========================================================================
    
    async def get_genetic_tests(self) -> List[ProfileGeneticTest]:
        """Get all genetic tests"""
        result = await self.db.execute(
            select(ProfileGeneticTest).where(ProfileGeneticTest.user_id == self.user.id)
        )
        return result.scalars().all()
    
    async def set_genetic_tests(self, tests: List[ProfileGeneticTestCreate]) -> List[ProfileGeneticTest]:
        """Replace all genetic tests"""
        await self.db.execute(
            delete(ProfileGeneticTest).where(ProfileGeneticTest.user_id == self.user.id)
        )
        
        results = []
        for test in tests:
            new_test = ProfileGeneticTest(
                id=uuid.uuid4(),
                user_id=self.user.id,
                **test.model_dump()
            )
            self.db.add(new_test)
            results.append(new_test)
        
        await self.db.commit()
        return results
    
    # ========================================================================
    # DERIVED FEATURES
    # ========================================================================
    
    async def get_derived_features(self) -> List[DerivedFeature]:
        """Get all derived features"""
        result = await self.db.execute(
            select(DerivedFeature).where(DerivedFeature.user_id == self.user.id)
        )
        return result.scalars().all()
    
    async def compute_derived_features(self) -> List[DerivedFeature]:
        """Compute and store derived features"""
        profile = await self.get_profile()
        if not profile:
            return []
        
        features_to_upsert = []
        
        # Compute age from DOB
        if profile.date_of_birth:
            today = date.today()
            age = today.year - profile.date_of_birth.year
            if (today.month, today.day) < (profile.date_of_birth.month, profile.date_of_birth.day):
                age -= 1
            features_to_upsert.append(("age_computed", {"value": age, "source": "date_of_birth"}))
        elif profile.age_years:
            features_to_upsert.append(("age_computed", {"value": profile.age_years, "source": "age_years", "estimated": True}))
        
        # Compute BMI
        if profile.height_cm and profile.weight_kg and profile.height_cm > 0:
            height_m = profile.height_cm / 100
            bmi = profile.weight_kg / (height_m ** 2)
            bmi = round(bmi, 1)
            
            # BMI category
            if bmi < 18.5:
                bmi_category = "underweight"
            elif bmi < 25:
                bmi_category = "normal"
            elif bmi < 30:
                bmi_category = "overweight"
            else:
                bmi_category = "obese"
            
            features_to_upsert.append(("bmi", {"value": bmi}))
            features_to_upsert.append(("bmi_category", {"value": bmi_category}))
        
        # Compute completion score
        completion = await self.compute_completion()
        features_to_upsert.append(("completeness_score", {
            "score": completion.score,
            "missing_essentials": completion.missing_essentials,
            "missing_optional": completion.missing_optional
        }))
        
        # Risk flags based on conditions and lifestyle
        risk_flags = await self._compute_risk_flags(profile)
        if risk_flags:
            features_to_upsert.append(("risk_flags", {"flags": risk_flags}))
        
        # Upsert all features
        results = []
        for feature_name, feature_value in features_to_upsert:
            result = await self.db.execute(
                select(DerivedFeature).where(
                    DerivedFeature.user_id == self.user.id,
                    DerivedFeature.feature_name == feature_name
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                existing.feature_value = feature_value
                existing.computed_at = datetime.utcnow()
                results.append(existing)
            else:
                new_feature = DerivedFeature(
                    id=uuid.uuid4(),
                    user_id=self.user.id,
                    feature_name=feature_name,
                    feature_value=feature_value
                )
                self.db.add(new_feature)
                results.append(new_feature)
        
        await self.db.commit()
        return results
    
    async def _compute_risk_flags(self, profile: UserProfile) -> List[Dict[str, Any]]:
        """Compute risk flags based on profile data"""
        flags = []
        
        # Get conditions
        conditions = await self.get_conditions()
        condition_codes = {c.condition_code for c in conditions}
        
        # Smoking risk
        if profile.smoking == "current":
            flags.append({
                "flag": "smoking_current",
                "severity": "high",
                "message": "Current smoker - increased cardiovascular and cancer risk"
            })
        
        # Obesity risk
        derived = await self.get_derived_features()
        bmi_feature = next((f for f in derived if f.feature_name == "bmi"), None)
        if bmi_feature and bmi_feature.feature_value.get("value", 0) >= 30:
            flags.append({
                "flag": "obesity",
                "severity": "moderate",
                "message": "BMI indicates obesity - increased health risks"
            })
        
        # Diabetes risk
        if "diabetes" in condition_codes or "prediabetes" in condition_codes:
            flags.append({
                "flag": "diabetes_diagnosed",
                "severity": "moderate",
                "message": "Diabetes/prediabetes requires ongoing monitoring"
            })
        
        # Cardiovascular risk
        if "high_bp" in condition_codes or "heart_disease" in condition_codes:
            flags.append({
                "flag": "cardiovascular_risk",
                "severity": "high",
                "message": "Cardiovascular condition requires monitoring"
            })
        
        # Sedentary lifestyle
        if profile.activity_level == "sedentary":
            flags.append({
                "flag": "sedentary_lifestyle",
                "severity": "low",
                "message": "Sedentary lifestyle - consider increasing physical activity"
            })
        
        return flags
    
    # ========================================================================
    # COMPLETION SCORE
    # ========================================================================
    
    async def compute_completion(self) -> ProfileCompletionResponse:
        """Compute profile completion score"""
        profile = await self.get_profile()
        answers = await self.get_all_answers()
        conditions = await self.get_conditions()
        medications = await self.get_medications()
        allergies = await self.get_allergies()
        family_history = await self.get_family_history()
        
        # Build answered questions set
        answered_questions = set()
        for answer in answers:
            if answer.answer_data:
                data = answer.answer_data
                # Count as answered if has value or explicitly unknown/skipped
                if data.get("value") is not None or data.get("unknown") or data.get("skipped"):
                    answered_questions.add(answer.question_id)
        
        # Track scores
        total_weight = sum(ESSENTIAL_FIELDS.values()) + sum(OPTIONAL_FIELDS.values())
        earned_weight = 0
        missing_essentials = []
        missing_optional = []
        estimated_fields = []
        
        # Check essential fields
        for field, weight in ESSENTIAL_FIELDS.items():
            is_filled = False
            is_estimated = False
            
            if field == "date_of_birth":
                if profile and profile.date_of_birth:
                    is_filled = True
                elif profile and profile.age_years:
                    is_filled = True
                    is_estimated = True
            elif field == "age_years":
                # Already counted via date_of_birth
                if profile and (profile.date_of_birth or profile.age_years):
                    is_filled = True
            elif field == "diagnosed_conditions":
                # Check if user answered the conditions question (even if no conditions)
                is_filled = "diagnosed_conditions_answered" in answered_questions or len(conditions) > 0
            elif field == "taking_medications":
                is_filled = "taking_medications" in answered_questions or len(medications) > 0
            elif field == "allergies":
                is_filled = "has_allergies" in answered_questions or len(allergies) > 0
            elif profile and hasattr(profile, field):
                value = getattr(profile, field)
                is_filled = value is not None
            
            if is_filled:
                earned_weight += weight
                if is_estimated:
                    estimated_fields.append(field)
            else:
                missing_essentials.append(field)
        
        # Check optional fields
        for field, weight in OPTIONAL_FIELDS.items():
            is_filled = False
            
            if field == "family_history":
                is_filled = "family_history_any" in answered_questions or len(family_history) > 0
            elif field == "genetic_tests":
                is_filled = "genetic_tests_any" in answered_questions
            elif field == "supplements":
                is_filled = "supplements" in answered_questions
            elif profile and hasattr(profile, field):
                value = getattr(profile, field)
                is_filled = value is not None
            
            if is_filled:
                earned_weight += weight
            else:
                missing_optional.append(field)
        
        # Compute score
        score = (earned_weight / total_weight) * 100 if total_weight > 0 else 0
        
        # Compute by-step completion
        step_completion = {
            "basics": self._compute_step_completion(profile, ["full_name", "date_of_birth", "sex_at_birth", "gender", "city"]),
            "measurements": self._compute_step_completion(profile, ["height_cm", "weight_kg", "waist_cm", "activity_level"]),
            "conditions": 100 if ("diagnosed_conditions_answered" in answered_questions or len(conditions) > 0) else 0,
            "medications": 100 if ("taking_medications" in answered_questions or len(medications) > 0) else 0,
            "family_history": 100 if ("family_history_any" in answered_questions or len(family_history) > 0) else 0,
            "lifestyle": self._compute_step_completion(profile, ["smoking", "alcohol", "sleep_hours_avg", "exercise_minutes_per_week", "diet_pattern"]),
        }
        
        return ProfileCompletionResponse(
            score=round(score, 1),
            missing_essentials=missing_essentials,
            missing_optional=missing_optional,
            estimated_fields=estimated_fields,
            completion_by_step=step_completion
        )
    
    def _compute_step_completion(self, profile: Optional[UserProfile], fields: List[str]) -> float:
        """Compute completion percentage for a step"""
        if not profile:
            return 0
        
        filled = 0
        for field in fields:
            if hasattr(profile, field) and getattr(profile, field) is not None:
                filled += 1
        
        return (filled / len(fields)) * 100 if fields else 0
    
    # ========================================================================
    # FULL PROFILE FETCH
    # ========================================================================
    
    async def get_full_profile(self) -> Dict[str, Any]:
        """Get complete profile with all related data"""
        profile = await self.get_profile()
        answers = await self.get_all_answers()
        conditions = await self.get_conditions()
        symptoms = await self.get_symptoms()
        medications = await self.get_medications()
        supplements = await self.get_supplements()
        allergies = await self.get_allergies()
        family_history = await self.get_family_history()
        genetic_tests = await self.get_genetic_tests()
        derived = await self.get_derived_features()
        completion = await self.compute_completion()
        
        return {
            "profile": profile,
            "answers": answers,
            "conditions": conditions,
            "symptoms": symptoms,
            "medications": medications,
            "supplements": supplements,
            "allergies": allergies,
            "family_history": family_history,
            "genetic_tests": genetic_tests,
            "derived_features": derived,
            "completion": completion
        }
