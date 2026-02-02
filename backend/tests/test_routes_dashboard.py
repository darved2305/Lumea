"""
Dashboard route unit tests for normalization/fallback behavior.
"""

from types import SimpleNamespace
import uuid

import pytest


@pytest.mark.anyio
async def test_dashboard_trends_normalizes_metric_and_range(monkeypatch):
    from src.routes.dashboard import get_dashboard_trends

    calls = {}

    class _FakeMetricsService:
        def __init__(self, db):
            pass

        async def get_trends(self, user_id, metric, range_):
            calls["metric"] = metric
            calls["range"] = range_
            return ([], SimpleNamespace(current=0, average=0, minimum=0, maximum=0, change_percent=0))

    import src.routes.dashboard as dash_routes

    monkeypatch.setattr(dash_routes, "MetricsService", _FakeMetricsService)

    user = SimpleNamespace(id=uuid.uuid4())
    out = await get_dashboard_trends(metric="BP", range="1w", current_user=user, db=object())

    assert calls["metric"] == "bp"
    assert out["range"] == "1W"


@pytest.mark.anyio
async def test_dashboard_trends_returns_empty_on_value_error(monkeypatch):
    from src.routes.dashboard import get_dashboard_trends

    class _FakeMetricsService:
        def __init__(self, db):
            pass

        async def get_trends(self, user_id, metric, range_):
            raise ValueError("no data")

    import src.routes.dashboard as dash_routes

    monkeypatch.setattr(dash_routes, "MetricsService", _FakeMetricsService)

    user = SimpleNamespace(id=uuid.uuid4())
    out = await get_dashboard_trends(metric="unknown", range="BAD", current_user=user, db=object())
    assert out["data"] == []
    assert out["range"] == "1M"
