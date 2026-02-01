"""
Recommendations API Routes

Provides endpoints for getting personalized health recommendations.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from datetime import datetime
import logging

from src.config import get_db
from src.models import User
from src.middleware import get_current_user
from src.services.recommendation_service import get_user_recommendations

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
