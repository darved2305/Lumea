"""
Route handler tests for /api/recommendations (backend/src/routes/recommendations.py).

We call the route functions directly with fake dependencies.
"""

import uuid
from types import SimpleNamespace

import pytest

from tests.helpers import FakeAsyncSession


@pytest.mark.anyio
async def test_get_recommendations_falls_back_on_exception(monkeypatch):
    from src.routes import recommendations as rec_routes

    async def _boom(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(rec_routes, "get_user_recommendations", _boom)

    user = SimpleNamespace(id=uuid.uuid4())
    out = await rec_routes.get_recommendations(
        include_low_severity=True,
        db=FakeAsyncSession(),
        current_user=user,
    )

    assert out["items"] == []
    assert out["total_count"] == 0
    assert out["updated_at"] is not None


@pytest.mark.anyio
async def test_get_recommendations_summary_falls_back_on_exception(monkeypatch):
    from src.routes import recommendations as rec_routes

    async def _boom(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(rec_routes, "get_user_recommendations", _boom)

    user = SimpleNamespace(id=uuid.uuid4())
    out = await rec_routes.get_recommendations_summary(
        db=FakeAsyncSession(),
        current_user=user,
    )

    assert out["total_count"] == 0
    assert out["has_urgent"] is False
    assert out["updated_at"] is not None

