"""
Dashboard API Endpoints
Provides bootstrap, summary, and trends data
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from app.db import get_db
from app.security import get_current_user
from app.models import User, Report, Observation, HealthMetric
from app.schemas import (
    BootstrapResponse,
    DashboardSummary,
    TrendsResponse,
    TimeRange,
    MetricType,
    FactorContribution
)
from app.services.metrics_service import MetricsService
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
        onboarding_completed=current_user.onboarding_completed,
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
    latest_health = metrics_service.get_latest_health_index(current_user.id)
    
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


@router.get("/dashboard/trends", response_model=TrendsResponse)
async def get_dashboard_trends(
    metric: MetricType = Query(..., description="Metric to retrieve"),
    range: TimeRange = Query(TimeRange.ONE_DAY, description="Time range"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get timeseries trends for a specific metric
    
    Args:
        metric: Metric type (health_index, glucose, etc.)
        range: Time range (1D, 1W, 1M)
    
    Returns:
        Timeseries data points and stats
    """
    metrics_service = MetricsService(db)
    
    try:
        data_points, stats = await metrics_service.get_trends(
            current_user.id,
            metric.value,
            range.value
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return TrendsResponse(
        metric=metric.value,
        range=range.value,
        data=data_points,
        stats=stats
    )


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
