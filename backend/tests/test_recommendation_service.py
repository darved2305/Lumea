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
