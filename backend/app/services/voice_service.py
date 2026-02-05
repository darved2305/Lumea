"""
Voice Service - Lumea Health Companion voice agent with multilingual support
Handles personalized health context for Indian users (English/Hindi/Marathi/Gujarati)
"""
import logging
import json
import re
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.models import User, UserProfile, Report, Observation, ProfileCondition, ProfileMedication, ProfileAllergy
from app.services.llm_service import get_llm_service
from app.services.rag_service import get_rag_service

logger = logging.getLogger(__name__)

# Safety keywords that require emergency response (English + Hindi + common transliterations)
EMERGENCY_KEYWORDS = [
    # English
    "chest pain", "severe pain", "can't breathe", "cannot breathe", "suicide", 
    "heart attack", "stroke", "unconscious", "bleeding heavily", "overdose", 
    "emergency", "dying", "fainting", "paralysis", "seizure", "convulsion",
    # Hindi transliterations
    "seena dard", "dil ka daura", "saans nahi", "sans nahi", "behosh", 
    "khoon", "mirgi", "lakwa", "emergency", "hospital le jao",
    # Common urgent phrases
    "call 108", "call ambulance", "very serious", "bahut serious"
]

DOSAGE_KEYWORDS = [
    # English
    "how much", "dosage", "increase", "decrease", "should i take",
    "can i take more", "double dose", "extra dose", "missed dose",
    # Hindi transliterations  
    "kitna lena", "kitni goli", "dose badhao", "dose kam karo", "zyada le sakta"
]


class VoiceService:
    """Service for Lumea Health Companion voice agent with multilingual support"""
    
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
                # Detect language for emergency response
                detected_lang = self._detect_language(text)
                
                emergency_responses = {
                    "en": "I'm detecting words that suggest this might be an emergency. Please call 108 (ambulance) immediately or go to the nearest hospital. Do not delay - your safety comes first. If someone is with you, ask them to help.",
                    "hi": "Mujhe lag raha hai ye emergency ho sakti hai. Please turant 108 (ambulance) call karein ya nazdeeki hospital jayein. Der mat karein - aapki safety sabse pehle hai. Agar koi aapke saath hai, unse madad maangein.",
                    "mixed": "This seems like an emergency situation. Please immediately 108 call karein ya nearest hospital jayein. Don't delay - your safety is most important. Agar koi saath hai, unse help lein."
                }
                
                return {
                    "answer_text": emergency_responses.get(detected_lang, emergency_responses["en"]),
                    "language": detected_lang,
                    "safety_level": "urgent",
                    "followup_questions": [],
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

Remember: Return ONLY valid JSON with reply_text, language, safety_level, followup_questions, and used_context."""
            
            # Generate response using LLM
            raw_response = await self.llm_service.generate(
                user_message=enhanced_message,
                context="",  # Context is already in the message
                chat_history=None
            )
            
            # Parse JSON response from LLM
            parsed_response = self._parse_llm_response(raw_response, flags, context_data, summary, rag_context)
            
            return parsed_response
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}", exc_info=True)
            return {
                "answer_text": (
                    "I'm sorry, I'm having trouble processing your request right now. "
                    "Please try again, or consider speaking with your healthcare provider "
                    "for medical advice."
                ),
                "language": "en",
                "safety_level": "normal",
                "followup_questions": [],
                "flags": ["error"],
                "used_context": {},
                "error": str(e)
            }
    
    def _parse_llm_response(
        self, 
        raw_response: str, 
        flags: List[str],
        context_data: Dict[str, Any],
        summary: Dict[str, Any],
        rag_context: str
    ) -> Dict[str, Any]:
        """Parse JSON response from LLM, with fallback for non-JSON responses"""
        try:
            # Try to extract JSON from the response
            # Remove markdown code blocks if present
            cleaned = raw_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            # Try to find JSON object in the response
            json_match = re.search(r'\{[\s\S]*\}', cleaned)
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)
                
                # Validate required fields
                reply_text = parsed.get("reply_text", "")
                if not reply_text:
                    raise ValueError("Missing reply_text in response")
                
                return {
                    "answer_text": reply_text,
                    "language": parsed.get("language", "en"),
                    "safety_level": parsed.get("safety_level", "normal"),
                    "followup_questions": parsed.get("followup_questions", []),
                    "flags": flags,
                    "used_context": {
                        "has_profile": context_data.get("profile_complete", False),
                        "conditions_count": len(summary.get("conditions", [])),
                        "medications_count": len(summary.get("medications", [])),
                        "has_rag_context": bool(rag_context),
                        "llm_reported": parsed.get("used_context", [])
                    }
                }
            else:
                raise ValueError("No JSON found in response")
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse JSON response, using raw text: {e}")
            # Fallback: use raw response as answer_text
            return {
                "answer_text": raw_response,
                "language": self._detect_language(raw_response),
                "safety_level": "caution" if "emergency" in flags else "normal",
                "followup_questions": [],
                "flags": flags,
                "used_context": {
                    "has_profile": context_data.get("profile_complete", False),
                    "conditions_count": len(summary.get("conditions", [])),
                    "medications_count": len(summary.get("medications", [])),
                    "has_rag_context": bool(rag_context)
                }
            }
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection based on character patterns"""
        # Check for Devanagari script (Hindi/Marathi)
        if re.search(r'[\u0900-\u097F]', text):
            return "hi"  # Could be Hindi or Marathi
        # Check for Gujarati script
        if re.search(r'[\u0A80-\u0AFF]', text):
            return "gu"
        # Check for common Hindi/Hinglish transliterations
        hinglish_markers = ["hai", "hain", "kya", "aap", "mujhe", "kaise", "karna", "lena", "dena"]
        text_lower = text.lower()
        if any(marker in text_lower for marker in hinglish_markers):
            return "mixed"
        return "en"
    
    def _build_system_prompt(self, summary: Dict[str, Any], flags: list) -> str:
        """Build comprehensive multilingual system prompt for Lumea Health Companion"""
        base_prompt = """You are "Lumea Health Companion", a multilingual voice healthcare assistant for Indian users.
You are NOT a doctor. You provide supportive, practical guidance, safe home-care steps, and explain options clearly.
You must be helpful first, safe always, and avoid generic refusals.

========================
LANGUAGE (MULTILINGUAL)
========================
- Detect the user's language automatically: English / Hindi / Marathi / Gujarati.
- Reply in the SAME language as the user. If user mixes (Hinglish/Marathi-English/Gujarati-English), reply in the same mixed style.
- Understand imperfect speech-to-text, slang, short forms, and common Indian medicine brand names.
- If user's language is unclear, ask ONE short clarification in the language you think is most likely.
- Never reply in a different language unless user asks.

========================
RESPONSE STYLE (VOICE-FIRST)
========================
- Keep answers short and voice-friendly: 20–45 seconds when spoken.
- Use numbered steps (1,2,3…) for clarity.
- Be practical like a smart doctor-friend in India.
- Give actionable steps first. Do NOT start with "consult a doctor" unless red flags exist.
- Ask at most 1–2 follow-up questions only if needed for safety/dosage.

Standard structure:
1) Quick understanding (1 line)
2) What to do now (3–6 steps)
3) Medicine guidance (ONLY if appropriate + safe limits + who should avoid)
4) Red flags (when to seek urgent care)
5) One question (optional)

========================
SAFE MEDICINE RULES
========================
- You can suggest common OTC options for minor issues (fever/cold/acidity/body pain) with safety checks.
- Never prescribe antibiotics or controlled meds.
- Never claim cure or guarantee.
- For paracetamol: mention max daily limit and spacing, and caution for liver disease/alcohol use.
- Ask about pregnancy, child age, liver/kidney disease when medicine advice matters.
- If user has diabetes/BP/heart disease, tailor advice and avoid risky suggestions.

========================
WHEN TO ESCALATE (RED FLAGS)
========================
If any of these appear, advise urgent medical care:
- chest pain, breathing trouble, fainting, stroke signs
- severe dehydration, confusion
- very high fever or fever >3 days
- severe abdominal pain, blood in vomit/stool, severe allergic swelling
- suicidal thoughts/self-harm

========================
CONDITION-SPECIFIC GUIDANCE
========================
FEVER:
- hydration, rest, light food, temperature monitoring
- paracetamol guidance when safe
- avoid unnecessary antibiotics
- when to suspect dengue/flu (basic signs) and red flags

THROAT PAIN:
- warm fluids, salt gargle, steam, honey (not for infants), rest voice
- when to consider doctor (high fever, pus, trouble swallowing/breathing)

DIABETES:
- practical Indian plate method, meal timing, sugar swaps, walking, hydration
- safety: if on insulin/sulfonylureas, watch hypoglycemia signs
- if sugar extremely high with symptoms → urgent

========================
CONTEXT USE
========================
- If user_profile says diabetes, reflect it naturally in advice (diet/med caution).
- If allergies exist, avoid those meds/foods.
- If reports show high BP or high sugar, mention lifestyle steps and safe monitoring suggestions.
- If data is missing, say "If you can tell me X, I'll tailor it" and ask 1 question.

========================
OUTPUT FORMAT (STRICT JSON)
========================
You MUST return ONLY valid JSON in this exact format:
{
  "language": "en|hi|mr|gu|mixed",
  "reply_text": "Your voice-friendly answer in the user's language",
  "followup_questions": ["optional Q1", "optional Q2"],
  "safety_level": "normal|caution|urgent",
  "used_context": ["profile", "reports", "meds", "lifestyle"]
}

RULES:
- Do NOT include any text before or after the JSON
- Do NOT add markdown code blocks
- Do NOT include extra keys
- "reply_text" should be 20-45 seconds when spoken
- "followup_questions" can be empty array []
- "safety_level": "normal" (routine), "caution" (needs monitoring), "urgent" (seek care now)

"""
        
        if "dosage_inquiry" in flags:
            base_prompt += """
========================
DOSAGE INQUIRY DETECTED
========================
The user is asking about medication dosages. Respond with:
"Dosage changes depend on your specific health condition, weight, and other medications. 
Please consult your doctor or pharmacist before making any changes. I can help you understand 
what questions to ask your doctor about this medication."
"""
        
        if "emergency" in flags:
            base_prompt += """
========================
EMERGENCY DETECTED
========================
This appears to be an emergency situation. Immediately advise:
1) Call 108 (ambulance) or go to nearest hospital
2) Do not delay seeking medical care
3) If someone is with you, ask them to help
"""
        
        return base_prompt
    
    def _build_context_summary(self, summary: Dict[str, Any], rag_context: str) -> str:
        """Build structured context summary for Lumea Health Companion"""
        parts = ["========================", "USER PROFILE DATA", "========================"]
        
        # Basic demographics
        if summary.get("name"):
            parts.append(f"Name: {summary['name']}")
        
        if summary.get("age") and summary.get("gender"):
            parts.append(f"Age/Sex: {summary['age']} year old {summary['gender']}")
        
        if summary.get("height_cm") and summary.get("weight_kg"):
            parts.append(f"Height/Weight: {summary['height_cm']}cm, {summary['weight_kg']}kg")
        
        if summary.get("bmi"):
            bmi = summary['bmi']
            bmi_category = "Underweight" if bmi < 18.5 else "Normal" if bmi < 25 else "Overweight" if bmi < 30 else "Obese"
            parts.append(f"BMI: {bmi} ({bmi_category})")
        
        # Medical conditions (IMPORTANT for advice)
        if summary.get("conditions"):
            parts.append(f"\n⚕️ KNOWN CONDITIONS (tailor advice accordingly):")
            for condition in summary['conditions']:
                parts.append(f"  • {condition}")
        
        # Current medications (CRITICAL for interactions)
        if summary.get("medications"):
            parts.append(f"\n💊 CURRENT MEDICATIONS (check interactions):")
            for med in summary['medications']:
                parts.append(f"  • {med}")
        
        # Allergies (MUST AVOID in any suggestions)
        if summary.get("allergies"):
            parts.append(f"\n⚠️ ALLERGIES (DO NOT suggest these):")
            for allergy in summary['allergies']:
                parts.append(f"  • {allergy}")
        
        # Lifestyle factors
        lifestyle = []
        if summary.get("sleep_hours"):
            lifestyle.append(f"Sleep: {summary['sleep_hours']} hours/night")
        if summary.get("exercise_frequency"):
            lifestyle.append(f"Exercise: {summary['exercise_frequency']}")
        if summary.get("smoking_status"):
            lifestyle.append(f"Smoking: {summary['smoking_status']}")
        if summary.get("alcohol_frequency"):
            lifestyle.append(f"Alcohol: {summary['alcohol_frequency']}")
        if lifestyle:
            parts.append(f"\n🏃 LIFESTYLE:")
            for item in lifestyle:
                parts.append(f"  • {item}")
        
        # Recent health data from reports
        if rag_context:
            parts.append(f"\n========================")
            parts.append(f"RECENT LAB/REPORT DATA")
            parts.append(f"========================")
            parts.append(rag_context)
        
        # Reports count
        if summary.get("reports_count", 0) > 0:
            parts.append(f"\n📋 Total reports on file: {summary['reports_count']}")
        
        # Missing data warning
        if not summary.get("conditions") and not summary.get("medications") and summary.get("reports_count", 0) == 0:
            parts.append("\n📝 LIMITED DATA AVAILABLE:")
            parts.append("Profile is incomplete. Provide general guidance and ask minimal clarifying questions if needed.")

# Singleton instance
_voice_service: Optional[VoiceService] = None


def get_voice_service() -> VoiceService:
    """Get or create the voice service singleton"""
    global _voice_service
    if _voice_service is None:
        _voice_service = VoiceService()
    return _voice_service
