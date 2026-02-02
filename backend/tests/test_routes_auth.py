"""
Auth route unit tests (backend/src/routes/auth.py).

We call route functions directly with fake DB sessions.
"""

from types import SimpleNamespace
from datetime import datetime
import uuid

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import Response

from tests.helpers import FakeAsyncSession, FakeResult
from src.middleware.security import hash_password
from src.models.schemas import UserLogin


def _make_request():
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/auth/login",
        "headers": [(b"user-agent", b"pytest")],
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


@pytest.mark.anyio
async def test_login_rejects_invalid_password():
    from src.routes.auth import login

    user = SimpleNamespace(
        id=uuid.uuid4(),
        email="a@example.com",
        full_name="A",
        created_at=datetime.utcnow(),
        password_hash=hash_password("correct"),
        last_login_at=None,
    )

    db = FakeAsyncSession(execute_results=[FakeResult(scalar_one_or_none=user)])

    with pytest.raises(HTTPException) as exc:
        await login(
            login_data=UserLogin(email="a@example.com", password="wrong"),
            request=_make_request(),
            response=Response(),
            db=db,
        )

    assert exc.value.status_code == 401


@pytest.mark.anyio
async def test_login_sets_cookie_and_returns_token():
    from src.routes.auth import login

    user = SimpleNamespace(
        id=uuid.uuid4(),
        email="a@example.com",
        full_name="A",
        created_at=datetime.utcnow(),
        password_hash=hash_password("pw"),
        last_login_at=None,
    )

    db = FakeAsyncSession(execute_results=[FakeResult(scalar_one_or_none=user)])
    resp = Response()

    out = await login(
        login_data=UserLogin(email="a@example.com", password="pw"),
        request=_make_request(),
        response=resp,
        db=db,
    )

    assert out.access_token
    # httpOnly cookie set
    assert "auth_token=" in resp.headers.get("set-cookie", "")
    assert db.commits == 1

