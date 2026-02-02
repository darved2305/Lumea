"""
MetricsService tests (backend/src/services/metrics_service.py).

Focus on deterministic helper scoring + trends stats.
"""

import uuid
from types import SimpleNamespace
from datetime import datetime, timedelta

import pytest

from tests.helpers import FakeAsyncSession, FakeResult
from src.services.metrics_service import MetricsService


def test_score_in_range_returns_100_in_ideal_and_40_at_critical_edges():
    svc = MetricsService(db=None)
    assert svc._score_in_range(100, 90, 120, 10, 140) == 100.0
    assert svc._score_in_range(10, 90, 120, 10, 140) == 40.0
    assert svc._score_in_range(140, 90, 120, 10, 140) == 40.0


def test_compute_sleep_score_status_bands():
    svc = MetricsService(db=None)

    def obs(v):
        return SimpleNamespace(value=v)

    score, detail = svc._compute_sleep_score({"sleep_hours": [obs(8), obs(8)]})
    assert score == 100.0
    assert detail["status"] == "good"

    score, detail = svc._compute_sleep_score({"sleep_hours": [obs(6.5)]})
    assert score == 80.0
    assert detail["status"] == "warning"

    score, detail = svc._compute_sleep_score({"sleep_hours": [obs(4.5)]})
    assert score == 40.0
    assert detail["status"] == "critical"


@pytest.mark.anyio
async def test_get_trends_health_index_builds_stats():
    user_id = uuid.uuid4()
    now = datetime.utcnow()
    m1 = SimpleNamespace(computed_at=now - timedelta(days=2), value=50.0)
    m2 = SimpleNamespace(computed_at=now - timedelta(days=1), value=60.0)

    db = FakeAsyncSession(execute_results=[FakeResult(scalars_rows=[m1, m2])])
    svc = MetricsService(db=db)

    points, stats = await svc.get_trends(user_id=user_id, metric="health_index", time_range="1M")

    assert len(points) == 2
    assert stats.current == 60.0
    assert stats.minimum == 50.0
    assert stats.maximum == 60.0
    assert stats.change_percent == pytest.approx(20.0)


@pytest.mark.anyio
async def test_get_trends_unknown_metric_returns_empty_and_zero_stats():
    user_id = uuid.uuid4()
    db = FakeAsyncSession(execute_results=[])
    svc = MetricsService(db=db)

    points, stats = await svc.get_trends(user_id=user_id, metric="not-a-metric", time_range="1W")
    assert points == []
    assert stats.current == 0

