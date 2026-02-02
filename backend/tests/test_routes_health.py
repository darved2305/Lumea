"""
Health routes unit tests (backend/src/routes/health.py).
"""

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import Response

from tests.helpers import FakeAsyncSession, FakeResult
from src.models.schemas import ChatMessageCreate


def _req_no_auth():
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/reminders",
        "headers": [],
        "client": ("127.0.0.1", 1),
    }
    return Request(scope)


@pytest.mark.anyio
async def test_get_reminders_returns_empty_when_no_profile():
    from src.routes.health import get_reminders

    user = SimpleNamespace(id=uuid.uuid4())
    db = FakeAsyncSession(execute_results=[FakeResult(scalar_one_or_none=None)])
    resp = Response()

    out = await get_reminders(response=resp, current_user=user, db=db)
    assert out.reminders == []


@pytest.mark.anyio
async def test_chat_requires_auth_or_guest_key():
    from src.routes.health import chat

    db = FakeAsyncSession(execute_results=[])
    with pytest.raises(HTTPException) as exc:
        await chat(chat_request=ChatMessageCreate(message="hi", guest_key=None), request=_req_no_auth(), db=db)

    assert exc.value.status_code == 400

