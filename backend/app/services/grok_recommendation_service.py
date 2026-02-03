"""
Enhanced Recommendations Service with Grok API Integration

Generates personalized health recommendations using:
- Rule-based analysis (existing)
- Grok API for intelligent recommendations (new)
- Fallback to basic recommendations if Grok unavailable
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import httpx

from app.models import (
    User, ProfileRecommendation, Observation, HealthMetric, 
    UserProfile, ProfileCondition, ProfileAnswer, HealthIndexSnapshot
)
from app.settings import settings
from app.services.recommendation_service import get_user_recommendations

logger = logging.getLogger(__name__)


async def generate_grok_recommendations(
    user_id: str,
    db: AsyncSession,
    context_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Generate recommendations using Grok API.
    
    Args:
        user_id: User ID
        db: Database session
        context_data: Health profile, metrics, observations data
        
    Returns:
        List of recommendation dictionaries
    """
    # Check if any LLM API key is configured (Groq, Grok, or OpenAI)
    api_key = settings.groq_api_key or settings.grok_api_key or settings.xai_api_key or settings.openai_api_key
    
    if not api_key:
        logger.warning("No LLM API key configured, falling back to rule-based recommendations")
        return []
    
    # Determine which API to use
    if settings.groq_api_key:
        api_base = settings.groq_api_base
        model = settings.groq_model
        logger.info("Using Groq API for recommendations")
    elif settings.grok_api_key or settings.xai_api_key:
        api_base = settings.xai_api_base
        model = settings.grok_model
        api_key = settings.grok_api_key or settings.xai_api_key
        logger.info("Using xAI Grok API for recommendations")
    elif settings.openai_api_key:
        api_base = settings.openai_api_base
        model = settings.openai_model
        api_key = settings.openai_api_key
        logger.info("Using OpenAI API for recommendations")
    else:
        api_base = settings.groq_api_base
        model = settings.groq_model
    
    # Build context for Grok
    prompt = _build_grok_prompt(context_data)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a health advisory AI. Provide actionable, evidence-based health recommendations in structured JSON format. Be specific, prioritize safety, and always recommend consulting healthcare providers for serious concerns."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000,
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # Parse Grok response to extract recommendations
                recommendations = _parse_grok_response(content)
                logger.info(f"Generated {len(recommendations)} recommendations via Grok API")
                return recommendations
            else:
                logger.error(f"Grok API error: {response.status_code} - {response.text}")
                return []
                
    except Exception as e:
        logger.error(f"Error calling Grok API: {e}")
        return []


def _build_grok_prompt(context: Dict[str, Any]) -> str:
    """Build prompt for Grok API based on user health data."""
    
    prompt_parts = [
        "Analyze the following health profile and generate personalized recommendations.",
        "",
        "**Health Profile:**"
    ]
    
    # User profile info
    profile = context.get("profile", {})
    if profile:
        prompt_parts.append(f"- Age: {profile.get('age_years', 'N/A')}")
        prompt_parts.append(f"- Sex: {profile.get('sex_at_birth', 'N/A')}")
        prompt_parts.append(f"- BMI: {context.get('bmi', 'N/A')}")
        prompt_parts.append(f"- Activity Level: {profile.get('activity_level', 'N/A')}")
        prompt_parts.append(f"- Smoking: {profile.get('smoking', 'never')}")
        prompt_parts.append(f"- Alcohol: {profile.get('alcohol', 'none')}")
        prompt_parts.append(f"- Sleep: {profile.get('sleep_hours_avg', 'N/A')} hours, quality: {profile.get('sleep_quality', 'N/A')}")
    
    # Health conditions
    conditions = context.get("conditions", [])
    if conditions:
        prompt_parts.append("")
        prompt_parts.append("**Medical Conditions:**")
        for cond in conditions:
            prompt_parts.append(f"- {cond.get('condition_name', cond.get('condition_code', 'Unknown'))}")
    
    # Recent lab observations
    observations = context.get("observations", [])
    if observations:
        prompt_parts.append("")
        prompt_parts.append("**Recent Lab Results:**")
        for obs in observations[:10]:  # Limit to most recent 10
            flag = obs.get("flag", "")
            flag_text = f" ({flag})" if flag and flag != "Normal" else ""
            prompt_parts.append(
                f"- {obs.get('display_name', obs.get('metric_name'))}: "
                f"{obs.get('value')} {obs.get('unit')}{flag_text}"
            )
    
    # Health index
    health_index = context.get("health_index")
    if health_index:
        prompt_parts.append("")
        prompt_parts.append(f"**Current Health Index:** {health_index.get('score', 'N/A')}/100")
        contributions = health_index.get("contributions", {})
        if contributions:
            prompt_parts.append("**Contributing Factors:**")
            for factor, score in sorted(contributions.items(), key=lambda x: x[1], reverse=True)[:5]:
                prompt_parts.append(f"- {factor}: {score}")
    
    prompt_parts.append("")
    prompt_parts.append("**Required Output Format:**")
    prompt_parts.append("Generate 3-7 recommendations in this JSON array format:")
    prompt_parts.append("```json")
    prompt_parts.append("[")
    prompt_parts.append("  {")
    prompt_parts.append('    "title": "Brief recommendation title",')
    prompt_parts.append('    "priority": "high|medium|low",')
    prompt_parts.append('    "category": "lifestyle|checkup|nutrition|medical_followup",')
    prompt_parts.append('    "summary": "Detailed explanation",')
    prompt_parts.append('    "actions": ["Specific action 1", "Specific action 2"],')
    prompt_parts.append('    "evidence": ["Why this matters", "Supporting reason"]')
    prompt_parts.append("  }")
    prompt_parts.append("]")
    prompt_parts.append("```")
    
    return "\n".join(prompt_parts)


def _parse_grok_response(content: str) -> List[Dict[str, Any]]:
    """Parse Grok API response to extract recommendations."""
    import json
    import re
    
    # Try to extract JSON from markdown code blocks
    json_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", content, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Try to find JSON array directly
        json_match = re.search(r"(\[.*\])", content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            logger.warning("Could not extract JSON from Grok response")
            return []
    
    try:
        recommendations = json.loads(json_str)
        # Validate structure
        valid_recs = []
        for rec in recommendations:
            if isinstance(rec, dict) and "title" in rec and "priority" in rec:
                valid_recs.append({
                    "title": rec.get("title", ""),
                    "priority": rec.get("priority", "medium"),
                    "category": rec.get("category", "lifestyle"),
                    "summary": rec.get("summary", rec.get("description", "")),
                    "actions": rec.get("actions", []),
                    "evidence": rec.get("evidence", [])
                })
        return valid_recs
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Grok JSON: {e}")
        return []


async def save_recommendations_to_db(
    user_id: str,
    recommendations: List[Dict[str, Any]],
    db: AsyncSession
) -> None:
    """Save generated recommendations to database."""
    
    # Deactivate old recommendations
    result = await db.execute(
        select(ProfileRecommendation)
        .where(ProfileRecommendation.user_id == user_id)
        .where(ProfileRecommendation.is_active == True)
    )
    old_recs = result.scalars().all()
    for rec in old_recs:
        rec.is_active = False
    
    # Add new recommendations
    priority_map = {"high": 1, "medium": 5, "low": 8}
    
    for rec_data in recommendations:
        new_rec = ProfileRecommendation(
            user_id=user_id,
            recommendation_type=rec_data.get("category", "lifestyle"),
            category=rec_data.get("category", "lifestyle"),
            title=rec_data["title"],
            description=rec_data.get("summary", ""),
            priority=priority_map.get(rec_data.get("priority", "medium"), 5),
            evidence_jsonb={
                "actions": rec_data.get("actions", []),
                "evidence": rec_data.get("evidence", []),
                "source": "grok_api"
            },
            is_active=True
        )
        db.add(new_rec)
    
    await db.commit()
    logger.info(f"Saved {len(recommendations)} recommendations for user {user_id}")


async def generate_and_save_recommendations(
    user_id: str,
    db: AsyncSession,
    user: User
) -> Dict[str, Any]:
    """
    Main function to generate recommendations using Grok + fallback rules.
    
    Returns:
        Summary of generated recommendations
    """
    # Gather context data
    context = await _gather_user_context(user_id, db)
    
    # Try Grok API first
    grok_recommendations = await generate_grok_recommendations(user_id, db, context)
    
    # If Grok failed or returned no recommendations, use rule-based fallback
    if not grok_recommendations:
        logger.info("Using rule-based recommendations as fallback")
        rule_recommendations = await get_user_recommendations(db, user, include_low_severity=True)
        # Convert to our format for storage
        grok_recommendations = _convert_rule_recommendations(rule_recommendations)
    
    # Save to database
    if grok_recommendations:
        await save_recommendations_to_db(user_id, grok_recommendations, db)
    
    return {
        "count": len(grok_recommendations),
        "source": "grok_api" if settings.grok_api_key or settings.xai_api_key else "rule_based",
        "timestamp": datetime.utcnow().isoformat()
    }


async def _gather_user_context(user_id: str, db: AsyncSession) -> Dict[str, Any]:
    """Gather all relevant user health data for recommendation generation."""
    
    context = {}
    
    # Get profile
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if profile:
        context["profile"] = {
            "age_years": profile.age_years,
            "sex_at_birth": profile.sex_at_birth,
            "activity_level": profile.activity_level,
            "smoking": profile.smoking,
            "alcohol": profile.alcohol,
            "sleep_hours_avg": profile.sleep_hours_avg,
            "sleep_quality": profile.sleep_quality,
            "height_cm": profile.height_cm,
            "weight_kg": profile.weight_kg,
        }
        
        # Calculate BMI if available
        if profile.height_cm and profile.weight_kg:
            height_m = profile.height_cm / 100
            bmi = profile.weight_kg / (height_m ** 2)
            context["bmi"] = round(bmi, 1)
    
    # Get conditions
    result = await db.execute(
        select(ProfileCondition).where(ProfileCondition.user_id == user_id)
    )
    conditions = result.scalars().all()
    context["conditions"] = [
        {"condition_code": c.condition_code, "condition_name": c.condition_name}
        for c in conditions
    ]
    
    # Get recent observations
    result = await db.execute(
        select(Observation)
        .where(Observation.user_id == user_id)
        .order_by(desc(Observation.observed_at))
        .limit(20)
    )
    observations = result.scalars().all()
    context["observations"] = [
        {
            "metric_name": obs.metric_name,
            "display_name": obs.display_name,
            "value": float(obs.value) if obs.value else None,
            "unit": obs.unit,
            "flag": obs.flag,
            "is_abnormal": obs.is_abnormal,
            "observed_at": obs.observed_at.isoformat() if obs.observed_at else None
        }
        for obs in observations
    ]
    
    # Get latest health index
    result = await db.execute(
        select(HealthIndexSnapshot)
        .where(HealthIndexSnapshot.user_id == user_id)
        .order_by(desc(HealthIndexSnapshot.created_at))
        .limit(1)
    )
    health_index = result.scalar_one_or_none()
    if health_index:
        context["health_index"] = {
            "score": health_index.score,
            "confidence": health_index.confidence,
            "contributions": health_index.contributions or {}
        }
    
    return context


def _convert_rule_recommendations(rule_recs: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert rule-based recommendations to our storage format."""
    converted = []
    
    for item in rule_recs.get("items", []):
        converted.append({
            "title": item.get("title", ""),
            "priority": item.get("severity", "medium").lower(),
            "category": item.get("category", "lifestyle"),
            "summary": item.get("description", ""),
            "actions": [item.get("action", "")] if item.get("action") else [],
            "evidence": [item.get("rationale", "")] if item.get("rationale") else []
        })
    
    return converted
