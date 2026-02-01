"""
Dashboard API Endpoints
Provides bootstrap, summary, and trends data
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from src.config import get_db
from src.middleware import get_current_user
from src.models import User, Report, Observation, HealthMetric
from src.models import (
    BootstrapResponse,
    DashboardSummary,
    TrendsResponse,
    TimeRange,
    MetricType,
    FactorContribution
)
from src.services.metrics_service import MetricsService
from sqlalchemy import func, and_, select
from datetime import datetime, timedelta

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/me/bootstrap", response_model=BootstrapResponse)
async def get_bootstrap(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Bootstrap endpoint - called after login to get initial state
    
    Returns user profile, onboarding status, and basic health metrics
    """
    # Count reports - async
    result = await db.execute(
        select(func.count(Report.id)).where(Report.user_id == current_user.id)
    )
    report_count = result.scalar() or 0
    
    has_reports = report_count > 0
    
    # Get latest health index
    metrics_service = MetricsService(db)
    latest_health = await metrics_service.get_latest_health_index_async(current_user.id)
    
    # Get last report date - async
    result = await db.execute(
        select(Report).where(Report.user_id == current_user.id)
        .order_by(Report.uploaded_at.desc()).limit(1)
    )
    last_report = result.scalars().first()
    
    return BootstrapResponse(
        user_id=current_user.id,
        full_name=current_user.full_name,
        email=current_user.email,
        onboarding_completed=current_user.onboarding_completed or False,
        has_reports=has_reports,
        report_count=report_count,
        latest_health_index=float(latest_health.value) if latest_health else None,
        health_index_confidence=float(latest_health.confidence) if latest_health else None,
        last_report_date=last_report.uploaded_at if last_report else None
    )


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get health index summary with factor breakdown
    
    Returns current score, confidence, trend, and contributing factors
    """
    metrics_service = MetricsService(db)
    
    # Get latest health metric
    latest_health = await metrics_service.get_latest_health_index_async(current_user.id)
    
    if not latest_health:
        raise HTTPException(
            status_code=404,
            detail="No health metrics available. Upload medical reports or add observations first."
        )
    
    # Determine trend
    # Get previous health metric to compare
    previous_health = await db.execute(
        select(HealthMetric).where(
            HealthMetric.user_id == current_user.id,
            HealthMetric.metric_type == "health_index",
            HealthMetric.computed_at < latest_health.computed_at
        ).order_by(HealthMetric.computed_at.desc())
    )
    previous_health = previous_health.scalars().first()
    
    if previous_health:
        if latest_health.value > previous_health.value + 2:
            trend = "up"
        elif latest_health.value < previous_health.value - 2:
            trend = "down"
        else:
            trend = "stable"
    else:
        trend = "stable"
    
    # Build factor contributions
    factors = []
    if latest_health.contributions:
        for key, data in latest_health.contributions.items():
            detail = data["detail"]
            factors.append(FactorContribution(
                key=key,
                label=detail["label"],
                value=detail["value"],
                contribution=data["contribution"],
                status=detail["status"],
                unit=detail.get("unit")
            ))
    
    return DashboardSummary(
        health_index_score=float(latest_health.value),
        confidence=float(latest_health.confidence),
        trend=trend,
        last_updated=latest_health.computed_at,
        factors=factors
    )


@router.get("/dashboard/trends", response_model=None)
async def get_dashboard_trends(
    metric: Optional[str] = Query("health_index", description="Metric to retrieve"),
    range: Optional[str] = Query("1m", description="Time range"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get timeseries trends for a specific metric
    
    Args:
        metric: Metric type (health_index, glucose, etc.) - defaults to health_index
        range: Time range (1D, 1W, 1M) - defaults to 1M, case-insensitive
    
    Returns:
        Timeseries data points and stats (NEVER 422 - returns empty on no data)
    """
    from src.models import TrendsStats, TimeSeriesPoint
    
    # Normalize metric - handle aliases
    metric_normalized = (metric or "health_index").lower()
    if metric_normalized in ("index", "health_index"):
        metric_normalized = "health_index"
    elif metric_normalized in ("bloodpressure", "blood_pressure"):
        metric_normalized = "bloodPressure"  # Match service expectation
    
    # Normalize range - handle case variations
    range_normalized = (range or "1m").upper()  # "1d" -> "1D"
    if range_normalized not in ("1D", "1W", "1M"):
        range_normalized = "1M"  # Safe default
    
    metrics_service = MetricsService(db)
    
    try:
        data_points, stats = await metrics_service.get_trends(
            current_user.id,
            metric_normalized,
            range_normalized
        )
        
        return {
            "metric": metric_normalized,
            "range": range_normalized,
            "data": [{"timestamp": p.timestamp, "value": p.value} for p in data_points],
            "stats": {
                "current": stats.current,
                "average": stats.average,
                "minimum": stats.minimum,
                "maximum": stats.maximum,
                "change_percent": stats.change_percent
            }
        }
    except ValueError as e:
        # Return empty data instead of 400
        return {
            "metric": metric_normalized,
            "range": range_normalized,
            "data": [],
            "stats": {
                "current": 0,
                "average": 0,
                "minimum": 0,
                "maximum": 0,
                "change_percent": 0
            }
        }

@router.get("/health-index")
async def get_health_index(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current health index score
    
    Returns the real calculated health index from the database.
    NEVER hardcoded - returns null if no data available.
    """
    metrics_service = MetricsService(db)
    latest = await metrics_service.get_latest_health_index_async(current_user.id)
    
    if not latest:
        return {
            "score": None,
            "confidence": None,
            "computed_at": None,
            "message": "Upload lab reports to compute your Health Index"
        }
    
    return {
        "score": float(latest.value),
        "confidence": float(latest.confidence),
        "computed_at": latest.computed_at.isoformat(),
        "contributions": latest.contributions
    }


@router.get("/health-index/debug")
async def get_health_index_debug(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Debug endpoint to prove Health Index is NOT hardcoded.
    
    Returns:
        - score: Current health index
        - components: Breakdown of each factor's contribution
        - last_observation_at: Most recent observation timestamp
        - last_report_id: ID of last processed report
        - observation_count: Number of observations used
    """
    metrics_service = MetricsService(db)
    latest = await metrics_service.get_latest_health_index_async(current_user.id)
    
    # Get last observation
    result = await db.execute(
        select(Observation)
        .where(Observation.user_id == current_user.id)
        .order_by(Observation.observed_at.desc())
        .limit(1)
    )
    last_obs = result.scalars().first()
    
    # Get observation count
    count_result = await db.execute(
        select(func.count(Observation.id))
        .where(Observation.user_id == current_user.id)
    )
    obs_count = count_result.scalar() or 0
    
    # Get last report
    result = await db.execute(
        select(Report)
        .where(Report.user_id == current_user.id)
        .order_by(Report.uploaded_at.desc())
        .limit(1)
    )
    last_report = result.scalars().first()
    
    if not latest:
        return {
            "score": None,
            "confidence": None,
            "components": {},
            "last_observation_at": last_obs.observed_at.isoformat() if last_obs else None,
            "last_report_id": str(last_report.id) if last_report else None,
            "observation_count": obs_count,
            "message": "No health index computed yet - upload reports to generate"
        }
    
    # Build components breakdown
    components = {}
    if latest.contributions:
        for key, data in latest.contributions.items():
            components[key] = {
                "score": data.get("score", 0),
                "contribution_percent": data.get("contribution", 0),
                "details": data.get("detail", {})
            }
    
    return {
        "score": float(latest.value),
        "confidence": float(latest.confidence),
        "computed_at": latest.computed_at.isoformat(),
        "components": components,
        "last_observation_at": last_obs.observed_at.isoformat() if last_obs else None,
        "last_report_id": str(last_report.id) if last_report else None,
        "observation_count": obs_count,
        "raw_contributions": latest.contributions
    }


@router.post("/recompute")
async def recompute_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger recomputation of health metrics
    
    Call this after confirming extracted report values
    """
    metrics_service = MetricsService(db)
    
    try:
        metric = await metrics_service.compute_health_index(current_user.id)
        
        if not metric:
            return {
                "success": False,
                "message": "Insufficient data to compute health index"
            }
        
        return {
            "success": True,
            "health_index": float(metric.value),
            "confidence": float(metric.confidence),
            "computed_at": metric.computed_at.isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute metrics: {str(e)}")