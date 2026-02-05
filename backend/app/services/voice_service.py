"""
Voice Service - Handles voice agent logic with personalized health context
"""
import logging
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.models import User, UserProfile, Report, Observation, ProfileCondition, ProfileMedication, ProfileAllergy
from app.services.llm_service import get_llm_service
from app.services.rag_service import get_rag_service

logger = logging.getLogger(__name__)

# Safety keywords that require emergency response
EMERGENCY_KEYWORDS = [
    "chest pain", "severe pain", "can't breathe", "suicide", "heart attack",
    "stroke", "unconscious", "bleeding heavily", "overdose", "emergency"
]

DOSAGE_KEYWORDS = [
    "how much", "dosage", "increase", "decrease", "should i take",
    "can i take more", "double dose"
]


class VoiceService:
    """Service for voice agent interactions with personalized health context"""
    
    def __init__(self):
        self.llm_service = get_llm_service()
        self.rag_service = get_rag_service()
    
    async def get_user_context(self, db: AsyncSession, user_id: UUID) -> Dict[str, Any]:
        """
        Retrieve comprehensive user health context for voice interactions.
        
        Returns:
            Dictionary with profile_complete status and summary data
        """
        try:
            # Get user and profile
            user_result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                return {
                    "profile_complete": False,
                    "summary": {},
                    "error": "User not found"
                }
            
            profile_result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            profile = profile_result.scalar_one_or_none()
            
            # Get conditions
            conditions_result = await db.execute(
                select(ProfileCondition).where(ProfileCondition.user_id == user_id)
            )
            conditions = [c.condition_name for c in conditions_result.scalars().all()]
            
            # Get medications
            meds_result = await db.execute(
                select(ProfileMedication).where(ProfileMedication.user_id == user_id)
            )
            medications = [m.name for m in meds_result.scalars().all()]
            
            # Get allergies
            allergies_result = await db.execute(
                select(ProfileAllergy).where(ProfileAllergy.user_id == user_id)
            )
            allergies = [a.allergen for a in allergies_result.scalars().all()]
            
            # Get recent reports count
            reports_result = await db.execute(
                select(Report).where(Report.user_id == user_id)
            )
            reports_count = len(reports_result.scalars().all())
            
            # Build summary
            summary = {
                "name": user.full_name,
                "age": profile.age if profile else None,
                "gender": profile.gender if profile else None,
                "height_cm": profile.height_cm if profile else None,
                "weight_kg": profile.weight_kg if profile else None,
                "bmi": None,
                "conditions": conditions,
                "medications": medications,
                "allergies": allergies,
                "reports_count": reports_count,
                "sleep_hours": profile.sleep_hours_per_night if profile else None,
                "exercise_frequency": profile.exercise_frequency if profile else None,
                "smoking_status": profile.smoking_status if profile else None,
                "alcohol_frequency": profile.alcohol_frequency if profile else None,
            }
            
            # Calculate BMI if we have height and weight
            if profile and profile.height_cm and profile.weight_kg:
                height_m = profile.height_cm / 100
                summary["bmi"] = round(profile.weight_kg / (height_m ** 2), 1)
            
            # Determine if profile is reasonably complete
            profile_complete = bool(
                profile and
                profile.age and
                profile.gender and
                (conditions or medications or reports_count > 0)
            )
            
            return {
                "profile_complete": profile_complete,
                "summary": summary
            }
            
        except Exception as e:
            logger.error(f"Error getting user context: {e}", exc_info=True)
            return {
                "profile_complete": False,
                "summary": {},
                "error": str(e)
            }
    
    async def generate_answer(
        self,
        db: AsyncSession,
        user_id: UUID,
        text: str
    ) -> Dict[str, Any]:
        """
        Generate a personalized answer to user's voice query.
        
        Args:
            db: Database session
            user_id: User UUID
            text: User's transcribed question/text
        
        Returns:
            Dictionary with answer_text, flags, and used_context
        """
        try:
            # Get user context
            context_data = await self.get_user_context(db, user_id)
            summary = context_data.get("summary", {})
            
            # Safety checks
            text_lower = text.lower()
            flags = []
            
            # Check for emergency keywords
            if any(keyword in text_lower for keyword in EMERGENCY_KEYWORDS):
                flags.append("emergency")
                return {
                    "answer_text": (
                        "I'm detecting words that suggest this might be an emergency situation. "
                        "Please call emergency services immediately (911) or go to the nearest "
                        "emergency room. I'm here to help with general health questions, but "
                        "emergencies require immediate medical attention."
                    ),
                    "flags": flags,
                    "used_context": {}
                }
            
            # Check for dosage change requests
            if any(keyword in text_lower for keyword in DOSAGE_KEYWORDS):
                flags.append("dosage_inquiry")
            
            # Get relevant context from RAG if available
            rag_context = ""
            try:
                retrieved_docs = await self.rag_service.query(
                    user_id=user_id,
                    query=text,
                    k=3
                )
                if retrieved_docs:
                    rag_context = "\n".join([doc.get("content", "") for doc in retrieved_docs])
            except Exception as e:
                logger.warning(f"RAG retrieval failed, continuing without: {e}")
            
            # Build system prompt with safety instructions
            system_prompt = self._build_system_prompt(summary, flags)
            
            # Build user context summary
            context_summary = self._build_context_summary(summary, rag_context)
            
            # Build the full user message with instructions
            enhanced_message = f"""{system_prompt}

{context_summary}

User question: {text}

Provide a concise, helpful response (2-3 sentences max, voice-friendly)."""
            
            # Generate response using LLM
            response = await self.llm_service.generate(
                user_message=enhanced_message,
                context="",  # Context is already in the message
                chat_history=None
            )
            
            return {
                "answer_text": response,
                "flags": flags,
                "used_context": {
                    "has_profile": context_data.get("profile_complete", False),
                    "conditions_count": len(summary.get("conditions", [])),
                    "medications_count": len(summary.get("medications", [])),
                    "has_rag_context": bool(rag_context)
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}", exc_info=True)
            return {
                "answer_text": (
                    "I'm sorry, I'm having trouble processing your request right now. "
                    "Please try again, or consider speaking with your healthcare provider "
                    "for medical advice."
                ),
                "flags": ["error"],
                "used_context": {},
                "error": str(e)
            }
    
    def _build_system_prompt(self, summary: Dict[str, Any], flags: list) -> str:
        """Build system prompt with safety instructions"""
        base_prompt = """You are a knowledgeable and empathetic AI health assistant providing voice responses.

CRITICAL SAFETY RULES:
- NEVER diagnose medical conditions
- NEVER provide specific medication dosages or suggest dosage changes
- ALWAYS recommend consulting a healthcare professional for medical decisions
- Be clear, concise, and conversational (voice responses should be 2-3 sentences)
- If you detect emergency situations, immediately direct to emergency services
- Focus on explaining what data shows, not making medical judgments

"""
        
        if "dosage_inquiry" in flags:
            base_prompt += """
IMPORTANT: The user is asking about medication dosages. You MUST respond with:
"I cannot provide specific dosage recommendations. Please consult your doctor or pharmacist 
before making any changes to your medications, as dosages are personalized based on many factors."
"""
        
        return base_prompt
    
    def _build_context_summary(self, summary: Dict[str, Any], rag_context: str) -> str:
        """Build context summary for the LLM"""
        parts = ["PATIENT CONTEXT:"]
        
        if summary.get("name"):
            parts.append(f"- Name: {summary['name']}")
        
        if summary.get("age") and summary.get("gender"):
            parts.append(f"- Demographics: {summary['age']} year old {summary['gender']}")
        
        if summary.get("bmi"):
            parts.append(f"- BMI: {summary['bmi']}")
        
        if summary.get("conditions"):
            parts.append(f"- Known Conditions: {', '.join(summary['conditions'])}")
        
        if summary.get("medications"):
            parts.append(f"- Current Medications: {', '.join(summary['medications'])}")
        
        if summary.get("allergies"):
            parts.append(f"- Allergies: {', '.join(summary['allergies'])}")
        
        lifestyle = []
        if summary.get("sleep_hours"):
            lifestyle.append(f"sleeps {summary['sleep_hours']} hours/night")
        if summary.get("exercise_frequency"):
            lifestyle.append(f"exercises {summary['exercise_frequency']}")
        if summary.get("smoking_status"):
            lifestyle.append(f"smoking: {summary['smoking_status']}")
        if lifestyle:
            parts.append(f"- Lifestyle: {', '.join(lifestyle)}")
        
        if rag_context:
            parts.append(f"\nRECENT HEALTH DATA:\n{rag_context}")
        
        if not summary.get("conditions") and not summary.get("medications") and summary.get("reports_count", 0) == 0:
            parts.append("\n⚠️ LIMITED DATA: Profile incomplete. Recommend general guidance and suggest completing health profile.")
        
        return "\n".join(parts)


# Singleton instance
_voice_service: Optional[VoiceService] = None


def get_voice_service() -> VoiceService:
    """Get or create the voice service singleton"""
    global _voice_service
    if _voice_service is None:
        _voice_service = VoiceService()
    return _voice_service
