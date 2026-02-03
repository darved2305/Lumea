"""
RecommendationService tests (backend/src/services/recommendation_service.py).

Uses a fake AsyncSession; no real DB required.
"""

import uuid
from types import SimpleNamespace
from datetime import datetime, timedelta, date

import pytest

from tests.helpers import FakeAsyncSession, FakeResult
from src.services.recommendation_service import RecommendationService


@pytest.mark.anyio
async def test_build_user_context_merges_health_metrics_and_observations():
    user_id = uuid.uuid4()
    user = SimpleNamespace(id=user_id, date_of_birth=date(1990, 1, 1), gender="female")

    now = datetime.utcnow()

    hm_health_index = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user_id,
        metric_type="health_index",
        value=78.5,
        computed_at=now,
        trend=None,
        reference_low=None,
        reference_high=None,
    )

    obs_ldl = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user_id,
        metric_name="ldl",
        display_name="LDL Cholesterol",
        value=160.0,
        unit="mg/dL",
        observed_at=now - timedelta(days=3),
        reference_min=0.0,
        reference_max=130.0,
    )

    db = FakeAsyncSession(
        execute_results=[
            FakeResult(scalars_rows=[hm_health_index]),
            FakeResult(scalars_rows=[obs_ldl]),
        ]
    )

    service = RecommendationService(db=db, user=user)
    ctx = await service._build_user_context()

    assert ctx.user_id == str(user_id)
    assert "health_index" in ctx.metrics
    assert "ldl" in ctx.metrics
    assert ctx.metrics["ldl"].reference_max == 130.0
    assert ctx.age is not None


@pytest.mark.anyio
async def test_get_recommendations_never_throws_on_db_errors():
    user_id = uuid.uuid4()
    user = SimpleNamespace(id=user_id, date_of_birth=None, gender=None)
    db = FakeAsyncSession(execute_results=[])  # will raise on execute()

    service = RecommendationService(db=db, user=user)
    resp = await service.get_recommendations()

    assert isinstance(resp, dict)
    assert resp["items"] == []
    assert resp["total_count"] == 0


def test_normalize_metric_name_maps_common_variants():
    user = SimpleNamespace(id=uuid.uuid4(), date_of_birth=None, gender=None)
    db = FakeAsyncSession()
    service = RecommendationService(db=db, user=user)

    assert service._normalize_metric_name("LDL Cholesterol") == "ldl"
    assert service._normalize_metric_name("HbA1c/Hemoglobin.total") == "hba1c"
    assert service._normalize_metric_name("Systolic Blood Pressure") == "systolic_bp"


def test_convert_rule_recommendations_extracts_dynamic_data():
    """Test that _convert_rule_recommendations correctly maps RuleResult.to_dict() format."""
    from app.services.grok_recommendation_service import _convert_rule_recommendations
    
    # Mock input matching RuleResult.to_dict() format
    rule_recommendations = {
        "items": [
            {
                "id": "lipids_ldl_high",
                "title": "LDL cholesterol is high",
                "severity": "warning",
                "why": "Your LDL is 165 mg/dL (optimal: <130 mg/dL)",
                "actions": [
                    {"type": "exercise", "text": "Aim for 150 minutes/week of moderate cardio"},
                    {"type": "diet", "text": "Increase soluble fiber intake"},
                ],
                "followup": [
                    {"type": "test", "text": "Repeat lipid panel in 8-12 weeks"},
                    {"type": "doctor", "text": "Consider discussing with a clinician"},
                ],
                "sources": [
                    {"name": "AHA Cholesterol Guidelines", "url": "https://www.heart.org/en/health-topics/cholesterol"},
                ],
                "metric_name": "LDL Cholesterol",
                "metric_value": 165.0,
                "metric_unit": "mg/dL",
                "reference_min": None,
                "reference_max": 130,
                "trend": "rising",
            }
        ],
        "total_count": 1,
        "urgent_count": 0,
        "warning_count": 1,
    }
    
    converted = _convert_rule_recommendations(rule_recommendations)
    
    assert len(converted) == 1
    rec = converted[0]
    
    # Check proper field mapping
    assert rec["title"] == "LDL cholesterol is high"
    assert rec["priority"] == "medium"  # warning -> medium
    assert rec["category"] == "nutrition"  # lipids_ prefix -> nutrition
    
    # Check summary includes dynamic metric data
    assert "165" in rec["summary"]
    assert "LDL" in rec["summary"] or "ldl" in rec["summary"].lower()
    assert "rising" in rec["summary"].lower()
    
    # Check actions are extracted from list of dicts
    assert len(rec["actions"]) >= 2
    assert any("cardio" in a.lower() for a in rec["actions"])
    assert any("fiber" in a.lower() for a in rec["actions"])
    
    # Check followup actions are included
    assert any("lipid panel" in a.lower() for a in rec["actions"])
    
    # Check evidence from sources
    assert len(rec["evidence"]) >= 1
    assert any("AHA" in e for e in rec["evidence"])
    
    # Check metric_data preserved
    assert rec["metric_data"] is not None
    assert rec["metric_data"]["value"] == 165.0
    assert rec["metric_data"]["trend"] == "rising"


def test_convert_rule_recommendations_handles_empty_input():
    """Test that empty recommendations are handled gracefully."""
    from app.services.grok_recommendation_service import _convert_rule_recommendations
    
    result = _convert_rule_recommendations({"items": []})
    assert result == []
    
    result = _convert_rule_recommendations({})
    assert result == []
