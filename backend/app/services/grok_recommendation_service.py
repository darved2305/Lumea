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
from app.services.memory_service import get_memory_service
from app.services.rag_service import get_rag_service
from app.services.graph_service import get_graph_service

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
    """Build prompt for Grok API based on user health data.
    
    Includes:
    - User profile and conditions (from PostgreSQL)
    - User preferences and facts (from Mem0)
    - Historical context (from RAG)
    - Medical relationships (from Neo4j/Graphiti)
    """
    
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
    
    # =========================================================================
    # NEW: User Preferences from Mem0
    # =========================================================================
    user_preferences = context.get("user_preferences", [])
    if user_preferences:
        prompt_parts.append("")
        prompt_parts.append("**User Preferences & Personal Context:** (IMPORTANT: Tailor recommendations to these)")
        for pref in user_preferences[:7]:  # Limit to avoid prompt bloat
            prompt_parts.append(f"- {pref}")
    
    # =========================================================================
    # NEW: Historical Context from RAG
    # =========================================================================
    historical_context = context.get("historical_context", [])
    if historical_context:
        prompt_parts.append("")
        prompt_parts.append("**Historical Health Data:**")
        for snippet in historical_context[:5]:  # Limit to avoid prompt bloat
            # Truncate long snippets
            display_snippet = snippet[:300] + "..." if len(snippet) > 300 else snippet
            prompt_parts.append(f"- {display_snippet}")
    
    # =========================================================================
    # NEW: Medical Relationships from Neo4j/Graphiti
    # =========================================================================
    medical_relationships = context.get("medical_relationships", [])
    if medical_relationships:
        prompt_parts.append("")
        prompt_parts.append("**Known Medical Relationships:**")
        for rel in medical_relationships[:8]:  # Limit to avoid prompt bloat
            prompt_parts.append(f"- {rel}")
    
    prompt_parts.append("")
    prompt_parts.append("**IMPORTANT INSTRUCTIONS:**")
    if user_preferences:
        prompt_parts.append("- PERSONALIZE recommendations based on the user's preferences above")
        prompt_parts.append("- Consider their lifestyle, dietary preferences, and stated concerns")
    prompt_parts.append("- Be specific and actionable")
    prompt_parts.append("- Prioritize based on health risk and user context")
    
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
        parsed = json.loads(json_str)
        if not isinstance(parsed, list):
            logger.warning("Grok response is not a list, got %s", type(parsed).__name__)
            return []
        recommendations = parsed
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
    db: AsyncSession,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """Save generated recommendations to database with provenance tracking."""
    
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
        # Build provenance info based on context
        provenance = {}
        if context:
            provenance = {
                "memory": bool(context.get("user_preferences")),
                "graph": bool(context.get("medical_relationships")),
                "metrics": bool(context.get("observations")),
                "profile": bool(context.get("profile")),
            }
        
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
                "source": "grok_api",
                "provenance": provenance,
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
    
    # Save to database with context for provenance
    if grok_recommendations:
        await save_recommendations_to_db(user_id, grok_recommendations, db, context)
    
    return {
        "count": len(grok_recommendations),
        "source": "grok_api" if settings.grok_api_key or settings.xai_api_key else "rule_based",
        "timestamp": datetime.utcnow().isoformat()
    }


async def _gather_user_context(user_id: str, db: AsyncSession) -> Dict[str, Any]:
    """Gather all relevant user health data for recommendation generation.
    
    Integrates data from:
    1. PostgreSQL (profile, conditions, observations, health index)
    2. Mem0 (user preferences and facts from conversations)
    3. RAG (historical report context)
    4. Neo4j/Graphiti (medical knowledge relationships)
    """
    import asyncio
    
    context = {}
    
    # =========================================================================
    # 1. POSTGRESQL DATA (existing functionality)
    # =========================================================================
    
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
    
    # =========================================================================
    # 2. MEMORY/KNOWLEDGE LAYER (NEW - parallel async queries)
    # =========================================================================
    
    # Define async tasks for each service
    async def get_memory_context():
        """Fetch user preferences from Mem0."""
        try:
            memory_service = get_memory_service()
            if not memory_service.is_available:
                return []
            
            # Search for preferences relevant to recommendations
            results = await memory_service.search(
                query="preferences diet exercise lifestyle medication health goals concerns",
                user_id=user_id,
                limit=10
            )
            
            # Extract memory text from results
            memories = []
            if isinstance(results, list):
                for item in results:
                    if isinstance(item, dict):
                        text = item.get("memory", item.get("text", item.get("content", "")))
                    else:
                        text = str(item)
                    if text:
                        memories.append(text)
            
            return memories
        except Exception as e:
            logger.warning(f"Failed to get memory context: {e}")
            return []
    
    async def get_rag_context():
        """Fetch relevant historical data from RAG."""
        try:
            rag_service = get_rag_service()
            
            # Query for historical health patterns
            results = await rag_service.query(
                user_id=user_id,
                query="health trends patterns previous recommendations lab results",
                k=5
            )
            
            # Extract relevant snippets
            snippets = []
            if results:
                for doc in results:
                    if isinstance(doc, dict):
                        content = doc.get("content", doc.get("text", ""))
                        if content:
                            # Truncate long snippets
                            snippets.append(content[:500] if len(content) > 500 else content)
            
            return snippets
        except Exception as e:
            logger.warning(f"Failed to get RAG context: {e}")
            return []
    
    async def get_graph_context():
        """Fetch medical relationships from Neo4j/Graphiti."""
        try:
            graph_service = get_graph_service()
            if graph_service.client is None:
                return []
            
            # Search for relevant medical knowledge
            results = await graph_service.search(
                query="health conditions medications recommendations risk factors",
                limit=10
            )
            
            return results if isinstance(results, list) else []
        except Exception as e:
            logger.warning(f"Failed to get graph context: {e}")
            return []
    
    # Execute all queries in parallel for performance
    try:
        memory_results, rag_results, graph_results = await asyncio.gather(
            get_memory_context(),
            get_rag_context(),
            get_graph_context(),
            return_exceptions=True
        )
        
        # Handle any exceptions from gather
        if isinstance(memory_results, Exception):
            logger.warning(f"Memory query failed: {memory_results}")
            memory_results = []
        if isinstance(rag_results, Exception):
            logger.warning(f"RAG query failed: {rag_results}")
            rag_results = []
        if isinstance(graph_results, Exception):
            logger.warning(f"Graph query failed: {graph_results}")
            graph_results = []
        
        # Add to context
        context["user_preferences"] = memory_results
        context["historical_context"] = rag_results
        context["medical_relationships"] = graph_results
        
        logger.info(
            f"Context enriched with {len(memory_results)} memories, "
            f"{len(rag_results)} RAG docs, {len(graph_results)} graph facts"
        )
        
    except Exception as e:
        logger.error(f"Failed to gather memory/knowledge context: {e}")
        context["user_preferences"] = []
        context["historical_context"] = []
        context["medical_relationships"] = []
    
    return context


def _convert_rule_recommendations(rule_recs: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert rule-based recommendations to our storage format.
    
    Maps RuleResult.to_dict() format to our storage/API format:
    - RuleResult has: id, title, severity, why, actions (list of {type, text}), 
      followup, sources, metric_name, metric_value, metric_unit, reference_min/max, trend
    - Storage format needs: title, priority, category, summary, actions (list of strings), evidence
    """
    converted = []
    
    for item in rule_recs.get("items", []):
        # Map severity to priority (rule results use 'severity' field)
        severity = item.get("severity", "info").lower()
        priority_map = {"urgent": "high", "warning": "medium", "info": "low"}
        priority = priority_map.get(severity, "medium")
        
        # Derive category from rule ID (e.g., "lipids_ldl_high" -> "lipids")
        rule_id = item.get("id", "")
        category = _derive_category_from_rule_id(rule_id)
        
        # Build dynamic summary with actual metric values
        summary = item.get("why", "")
        if item.get("metric_value") is not None:
            metric_info = f"{item.get('metric_name', 'Metric')}: {item.get('metric_value')} {item.get('metric_unit', '')}"
            if item.get("reference_max") is not None:
                metric_info += f" (ref max: {item.get('reference_max')})"
            elif item.get("reference_min") is not None:
                metric_info += f" (ref min: {item.get('reference_min')})"
            if item.get("trend"):
                metric_info += f" | Trend: {item.get('trend')}"
            summary = f"{summary}\n\n📊 {metric_info}"
        
        # Extract action text from list of {type, text} dicts
        actions = []
        for action in item.get("actions", []):
            if isinstance(action, dict):
                actions.append(action.get("text", ""))
            elif isinstance(action, str):
                actions.append(action)
        
        # Also include followup actions
        for followup in item.get("followup", []):
            if isinstance(followup, dict):
                text = followup.get("text", "")
                if text:
                    actions.append(f"📋 {text}")
            elif isinstance(followup, str) and followup:
                actions.append(f"📋 {followup}")
        
        # Build evidence from sources and rationale
        evidence = []
        for source in item.get("sources", []):
            if isinstance(source, dict):
                source_text = source.get("name", "")
                if source.get("url"):
                    source_text += f" ({source.get('url')})"
                if source_text:
                    evidence.append(source_text)
            elif isinstance(source, str):
                evidence.append(source)
        
        # Add the explanation as evidence if not already in summary
        if item.get("why") and not evidence:
            evidence.append(item.get("why"))
        
        converted.append({
            "title": item.get("title", "Health Recommendation"),
            "priority": priority,
            "category": category,
            "summary": summary.strip(),
            "actions": [a for a in actions if a],  # Filter empty strings
            "evidence": [e for e in evidence if e],
            # Preserve dynamic data for potential future use
            "metric_data": {
                "name": item.get("metric_name"),
                "value": item.get("metric_value"),
                "unit": item.get("metric_unit"),
                "reference_min": item.get("reference_min"),
                "reference_max": item.get("reference_max"),
                "trend": item.get("trend"),
            } if item.get("metric_value") is not None else None
        })
    
    return converted


def _derive_category_from_rule_id(rule_id: str) -> str:
    """Derive recommendation category from rule ID.
    
    Rule IDs follow patterns like:
    - lipids_ldl_high, lipids_hdl_low -> nutrition
    - glucose_hba1c_high -> medical_followup  
    - lifestyle_sleep_low -> lifestyle
    - cardiovascular_bp_high -> medical_followup
    - missing_tests -> checkup
    """
    if not rule_id:
        return "lifestyle"
    
    rule_id = rule_id.lower()
    
    if rule_id.startswith("lipids_"):
        return "nutrition"
    elif rule_id.startswith("glucose_"):
        return "medical_followup"
    elif rule_id.startswith("lifestyle_"):
        return "lifestyle"
    elif rule_id.startswith("cardiovascular_") or rule_id.startswith("bp_"):
        return "medical_followup"
    elif rule_id.startswith("vitamin_"):
        return "nutrition"
    elif "missing" in rule_id or "test" in rule_id:
        return "checkup"
    else:
        return "lifestyle"
