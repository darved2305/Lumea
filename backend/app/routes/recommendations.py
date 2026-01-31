"""
Recommendations API Routes

Provides endpoints for getting personalized health recommendations.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from ..db import get_db
from ..models import User
from ..security import get_current_user
from ..services.recommendation_service import get_user_recommendations

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("", response_model=None)
async def get_recommendations(
    include_low_severity: bool = Query(True, description="Include INFO severity recommendations"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get personalized health recommendations for the current user.
    
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
    
    Each recommendation item contains:
    - id: Unique rule ID
    - title: Brief summary
    - severity: URGENT | WARNING | INFO
    - why: Explanation of why this recommendation applies
    - actions: List of suggested actions
    - followup: Follow-up recommendations
    - sources: Medical/wellness sources
    """
    try:
        recommendations = await get_user_recommendations(
            db=db,
            user=current_user,
            include_low_severity=include_low_severity,
        )
        return recommendations
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating recommendations: {str(e)}"
        )


@router.get("/summary")
async def get_recommendations_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get a brief summary of recommendations without full details.
    
    Useful for dashboard badges and quick overview.
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
        raise HTTPException(
            status_code=500,
            detail=f"Error generating recommendations summary: {str(e)}"
        )
