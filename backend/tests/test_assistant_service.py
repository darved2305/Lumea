"""
AssistantService unit tests (backend/src/services/assistant_service.py).

We test the response generator logic with a synthetic context (no DB).
"""

import uuid
from datetime import datetime

import pytest

from src.services.assistant_service import AssistantService


@pytest.mark.anyio
async def test_generate_response_health_index_path_returns_citation():
    svc = AssistantService(db=None)

    ctx = {
        "health_index": {
            "score": 80.0,
            "confidence": 0.9,
            "contributions": {"sleep": {"score": 90, "contribution": 20, "detail": {"label": "Sleep", "status": "good"}}},
            "computed_at": datetime.utcnow().isoformat(),
        },
        "recent_observations": [],
        "abnormal_observations": [],
        "reports": [],
    }

    text, citations = await svc._generate_response(uuid.uuid4(), "what is my health score?", ctx)
    assert "health index" in text.lower()
    assert citations, "Expected at least one citation"


@pytest.mark.anyio
async def test_generate_response_reports_path_handles_empty():
    svc = AssistantService(db=None)
    ctx = {
        "health_index": {"score": None, "confidence": None, "contributions": None, "computed_at": None},
        "recent_observations": [],
        "abnormal_observations": [],
        "reports": [],
    }
    text, citations = await svc._generate_response(uuid.uuid4(), "show my reports", ctx)
    assert "haven't uploaded" in text.lower()
    assert citations == []

