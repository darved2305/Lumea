"""
Recommendations API Routes

Provides endpoints for getting personalized health recommendations.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from datetime import datetime
import logging

from ..db import get_db
from ..models import User, ProfileRecommendation
from ..security import get_current_user
from ..services.recommendation_service import get_user_recommendations
from ..services.grok_recommendation_service import generate_and_save_recommendations
from sqlalchemy import select, desc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

# Safe fallback response when recommendations fail
FALLBACK_RESPONSE = {
    "updated_at": None,  # Will be set to current time
    "disclaimer": "⚕️ This is wellness guidance, not medical advice. Consult a licensed healthcare provider for diagnosis, treatment, or medical decisions.",
    "items": [],
    "total_count": 0,
    "urgent_count": 0,
    "warning_count": 0,
}


@router.get("", response_model=None)
async def get_recommendations(
    include_low_severity: bool = Query(True, description="Include INFO severity recommendations"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get personalized health recommendations for the current user.
    
    NEVER returns 500 - falls back to empty list on errors.
    
    Returns recommendations based on:
    - Metric values vs reference ranges
    - Trend direction (worsening/improving)
    - Missing or overdue tests
    
    Response includes:
    - updated_at: Timestamp of generation
    - disclaimer: Safety disclaimer
    - items: Array of recommendation objects
    - total_count: Total recommendations
    - urgent_count: Count of URGENT items
    - warning_count: Count of WARNING items
    """
    try:
        recommendations = await get_user_recommendations(
            db=db,
            user=current_user,
            include_low_severity=include_low_severity,
        )
        return recommendations
    
    except Exception as e:
        # Log error but return safe fallback
        logger.exception(f"Error generating recommendations for user {current_user.id}: {e}")
        fallback = FALLBACK_RESPONSE.copy()
        fallback["updated_at"] = datetime.utcnow().isoformat()
        return fallback


@router.get("/summary")
async def get_recommendations_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get a brief summary of recommendations without full details.
    
    NEVER returns 500 - falls back to empty summary on errors.
    """
    try:
        recommendations = await get_user_recommendations(
            db=db,
            user=current_user,
            include_low_severity=True,
        )
        
        return {
            "updated_at": recommendations["updated_at"],
            "total_count": recommendations["total_count"],
            "urgent_count": recommendations["urgent_count"],
            "warning_count": recommendations["warning_count"],
            "has_urgent": recommendations["urgent_count"] > 0,
            "disclaimer": recommendations["disclaimer"],
        }
    
    except Exception as e:
        # Log error but return safe fallback
        logger.exception(f"Error generating recommendations summary for user {current_user.id}: {e}")
        return {
            "updated_at": datetime.utcnow().isoformat(),
            "total_count": 0,
            "urgent_count": 0,
            "warning_count": 0,
            "has_urgent": False,
            "disclaimer": FALLBACK_RESPONSE["disclaimer"],
        }


@router.post("/generate")
async def generate_recommendations(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Generate new recommendations using Grok API + rule-based fallback.
    
    This endpoint triggers recommendation generation and saves to database.
    The generation happens in the background if it takes time.
    """
    try:
        # Run generation synchronously for now (can be moved to background if slow)
        result = await generate_and_save_recommendations(
            user_id=str(current_user.id),
            db=db,
            user=current_user
        )
        
        return {
            "success": True,
            "message": f"Generated {result['count']} recommendations",
            "source": result["source"],
            "timestamp": result["timestamp"]
        }
    
    except Exception as e:
        logger.exception(f"Error generating recommendations for user {current_user.id}: {e}")
        return {
            "success": False,
            "message": "Failed to generate recommendations",
            "error": str(e)
        }


@router.get("/stored")
async def get_stored_recommendations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get recommendations stored in database (from ProfileRecommendation table).
    
    Returns recommendations that were previously generated and saved.
    """
    try:
        result = await db.execute(
            select(ProfileRecommendation)
            .where(ProfileRecommendation.user_id == current_user.id)
            .where(ProfileRecommendation.is_active == True)
            .order_by(ProfileRecommendation.priority.asc(), desc(ProfileRecommendation.created_at))
        )
        recommendations = result.scalars().all()
        
        items = []
        for rec in recommendations:
            items.append({
                "id": str(rec.id),
                "title": rec.title,
                "description": rec.description,
                "category": rec.category,
                "priority": _priority_to_label(rec.priority),
                "actions": rec.evidence_jsonb.get("actions", []) if rec.evidence_jsonb else [],
                "evidence": rec.evidence_jsonb.get("evidence", []) if rec.evidence_jsonb else [],
                "created_at": rec.created_at.isoformat() if rec.created_at else None,
                "is_completed": rec.completed_at is not None
            })
        
        # Calculate counts
        high_priority = sum(1 for item in items if item["priority"] == "high")
        medium_priority = sum(1 for item in items if item["priority"] == "medium")
        
        return {
            "items": items,
            "total_count": len(items),
            "urgent_count": high_priority,
            "warning_count": medium_priority,
            "updated_at": datetime.utcnow().isoformat(),
            "disclaimer": "⚕️ This is wellness guidance, not medical advice. Consult a licensed healthcare provider for diagnosis, treatment, or medical decisions."
        }
    
    except Exception as e:
        logger.exception(f"Error fetching stored recommendations for user {current_user.id}: {e}")
        return {
            "items": [],
            "total_count": 0,
            "urgent_count": 0,
            "warning_count": 0,
            "updated_at": datetime.utcnow().isoformat(),
            "disclaimer": "⚕️ This is wellness guidance, not medical advice."
        }


def _priority_to_label(priority: int) -> str:
    """Convert numeric priority to label."""
    if priority <= 3:
        return "high"
    elif priority <= 6:
        return "medium"
    else:
        return "low"
