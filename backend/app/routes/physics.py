"""
Physics Twin – API router.

Endpoints:
  GET  /api/physics/latest    – auto-compute snapshot from real Observation data
  GET  /api/physics/history   – historical snapshots grouped by report
  GET  /api/physics/config    – expose organ metric config to frontend
  POST /api/physics/metrics   – manual metrics submission (fallback / override)

All data is pulled from the Observation table (extracted from uploaded reports)
and the UserProfile table (self-reported lifestyle data).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Observation, UserProfile
from app.security import get_current_user
from app.services.physics_config import (
    ORGAN_LABELS,
    ORGAN_METRICS,
    compute_all_organs,
)
from app.services.conditions import (
    detect_conditions,
    get_organ_conditions,
    get_organ_worst_severity,
)
from app.services.youtube_recommendation_service import YouTubeRecommendationService
from app.settings import Settings
from functools import lru_cache

@lru_cache()
def get_settings():
    return Settings()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/physics", tags=["physics-twin"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class MetricsInput(BaseModel):
    """Body for POST /metrics."""
    timestamp: Optional[datetime] = Field(default=None, description="ISO timestamp; defaults to now")
    metrics: Dict[str, float] = Field(..., description="metric_name -> value")


class OrganResult(BaseModel):
    score: float
    status: str
    coverage: float
    contributions: list


class SnapshotResponse(BaseModel):
    id: str
    user_id: str
    timestamp: str
    overall_score: float
    overall_status: str
    organs: Dict[str, OrganResult]
    raw_metrics: Dict[str, float]
    conditions: Optional[list] = None
    organ_conditions: Optional[Dict[str, list]] = None
    organ_severities: Optional[Dict[str, str]] = None
    data_source: Optional[str] = None  # "reports", "manual", "profile"


class MetricConfigItem(BaseModel):
    name: str
    unit: str
    ref_min: float
    ref_max: float
    weight: float
    direction: str


class OrganConfigResponse(BaseModel):
    organs: Dict[str, dict]  # organ -> { label, metrics: [...] }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _gather_user_metrics(
    db: AsyncSession,
    user_id,
    days: int = 90,
) -> Dict[str, float]:
    """
    Pull the latest value of each metric from the Observation table
    for the given user within the last `days` days.

    Also enriches with lifestyle data from UserProfile (sleep, stress, etc.)
    that may not appear in lab reports.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Query all observations for the user within the window
    result = await db.execute(
        select(Observation)
        .where(
            and_(
                Observation.user_id == user_id,
                Observation.observed_at >= cutoff,
            )
        )
        .order_by(desc(Observation.observed_at))
    )
    observations = result.scalars().all()

    # Deduplicate: keep the most recent value per metric_name
    metrics: Dict[str, float] = {}
    seen: set = set()
    for obs in observations:
        key = obs.metric_name
        if key not in seen:
            seen.add(key)
            metrics[key] = float(obs.value)

    # Enrich from UserProfile (lifestyle data)
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = profile_result.scalar_one_or_none()
    if profile:
        if profile.sleep_hours_avg and "sleep_hours" not in metrics:
            metrics["sleep_hours"] = float(profile.sleep_hours_avg)

        # Map activity_level to a numeric stress approximation if not reported
        if "stress_level" not in metrics:
            # Default moderate stress; will be overridden if an Observation exists
            metrics["stress_level"] = 3.0

    return metrics


def _make_snapshot(
    user_id: str,
    metrics: Dict[str, float],
    ts: Optional[datetime] = None,
    data_source: str = "reports",
) -> dict:
    ts = ts or datetime.utcnow()
    result = compute_all_organs(metrics)

    # Detect conditions from current metrics
    conditions = detect_conditions(metrics)
    organ_cond_map = get_organ_conditions(conditions)
    organ_sev_map = get_organ_worst_severity(conditions)

    conditions_data = [
        {
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "severity": c.severity,
            "affected_organs": c.affected_organs,
            "trigger_metrics": c.trigger_metrics,
            "recommendations": c.recommendations,
            "youtube_queries": c.youtube_queries,
        }
        for c in conditions
    ]

    snapshot = {
        "id": f"{user_id}_{ts.isoformat()}",
        "user_id": user_id,
        "timestamp": ts.isoformat(),
        "overall_score": result["overall_score"],
        "overall_status": result["overall_status"],
        "organs": result["organs"],
        "raw_metrics": metrics,
        "conditions": conditions_data,
        "organ_conditions": organ_cond_map,
        "organ_severities": organ_sev_map,
        "data_source": data_source,
    }
    return snapshot


async def _get_historical_snapshots(
    db: AsyncSession,
    user_id,
    days: int = 90,
) -> List[dict]:
    """
    Build historical snapshots by grouping Observations by report_id (or by day
    for observations without a report).  Each group becomes one scored snapshot.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(Observation)
        .where(
            and_(
                Observation.user_id == user_id,
                Observation.observed_at >= cutoff,
            )
        )
        .order_by(Observation.observed_at)
    )
    observations = result.scalars().all()

    if not observations:
        return []

    # Group by report_id (or by date for manual entries)
    groups: Dict[str, List] = defaultdict(list)
    for obs in observations:
        key = str(obs.report_id) if obs.report_id else obs.observed_at.strftime("%Y-%m-%d")
        groups[key].append(obs)

    snapshots = []
    for group_key, obs_list in groups.items():
        metrics: Dict[str, float] = {}
        latest_ts = obs_list[0].observed_at
        for obs in obs_list:
            metrics[obs.metric_name] = float(obs.value)
            if obs.observed_at > latest_ts:
                latest_ts = obs.observed_at

        snap = _make_snapshot(str(user_id), metrics, latest_ts, data_source="reports")
        snap["id"] = f"{user_id}_{group_key}"
        snapshots.append(snap)

    # Sort by timestamp ascending
    snapshots.sort(key=lambda s: s["timestamp"])
    return snapshots


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/latest", response_model=Optional[SnapshotResponse])
async def get_latest(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Auto-compute the physics twin snapshot from the user's real Observation data.
    Pulls latest values (last 90 days) from reports + UserProfile lifestyle data.
    Returns null only if the user has zero observations.
    """
    uid = str(user.id)
    try:
        metrics = await _gather_user_metrics(db, user.id, days=90)
        if not metrics:
            logger.info("Physics Twin: No observations found for user %s", uid)
            return None

        snapshot = _make_snapshot(uid, metrics, data_source="reports")
        logger.info(
            "Physics Twin: Computed snapshot for %s — %d metrics, overall=%s",
            uid, len(metrics), snapshot["overall_score"],
        )
        return snapshot
    except Exception as e:
        logger.error("Physics Twin latest error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to compute physics snapshot")


@router.post("/metrics", response_model=SnapshotResponse)
async def submit_metrics(body: MetricsInput, user=Depends(get_current_user)):
    """
    Manual metrics submission — compute organ scores without persisting.
    Useful for "what-if" scenarios or when the user doesn't have reports yet.
    """
    uid = str(user.id)
    snapshot = _make_snapshot(uid, body.metrics, body.timestamp, data_source="manual")
    return snapshot


@router.get("/history", response_model=List[SnapshotResponse])
async def get_history(
    days: int = Query(90, ge=1, le=365),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return historical snapshots grouped by report/date within the last N days."""
    try:
        snapshots = await _get_historical_snapshots(db, user.id, days=days)
        return snapshots
    except Exception as e:
        logger.error("Physics Twin history error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch physics history")


@router.get("/config", response_model=OrganConfigResponse)
async def get_config(user=Depends(get_current_user)):
    """Expose organ metric configuration for the frontend explainability panel."""
    organs: Dict[str, dict] = {}
    for organ, specs in ORGAN_METRICS.items():
        organs[organ] = {
            "label": ORGAN_LABELS.get(organ, organ),
            "metrics": [
                {
                    "name": s.name,
                    "unit": s.unit,
                    "ref_min": s.ref_min,
                    "ref_max": s.ref_max,
                    "weight": s.weight,
                    "direction": s.direction,
                }
                for s in specs
            ],
        }
    return {"organs": organs}


class YouTubeRecommendationRequest(BaseModel):
    """Request body for YouTube recommendations"""
    organ: str = Field(..., description="Organ name (kidney, heart, liver, etc.)")
    score: float = Field(..., description="Organ health score 0-100")
    status: str = Field(..., description="Health status (Healthy, Watch, Risk)")
    metrics: Dict[str, float] = Field(default_factory=dict, description="Current metric values")
    conditions: List[dict] = Field(default_factory=list, description="Detected conditions")


class YouTubeRecommendationResponse(BaseModel):
    """Response with YouTube video recommendations"""
    organ: str
    recommendations: List[Dict[str, str]]


@router.post("/youtube-recommendations", response_model=YouTubeRecommendationResponse)
async def get_youtube_recommendations(
    body: YouTubeRecommendationRequest,
    user=Depends(get_current_user),
):
    """
    Generate YouTube video recommendations based on organ telemetry.
    Uses OpenRouter AI to generate targeted search queries and returns
    actual YouTube videos (if API key is available) or search links.
    """
    try:
        settings = get_settings()
        service = YouTubeRecommendationService(settings)
        
        recommendations = await service.generate_recommendations(
            organ=body.organ,
            score=body.score,
            status=body.status,
            metrics=body.metrics,
            conditions=body.conditions,
        )
        
        return {
            "organ": body.organ,
            "recommendations": recommendations,
        }
    except Exception as e:
        logger.exception(f"Error generating YouTube recommendations: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate recommendations: {str(e)}"
        )
