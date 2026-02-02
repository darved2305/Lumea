"""
WebSocket chat handler tests (backend/src/routes/websocket.py).

We test message sequencing and token batching without a running server.
"""

import uuid
from contextlib import asynccontextmanager

import pytest


class FakeWebSocket:
    def __init__(self):
        self.sent = []

    async def send_json(self, payload):
        self.sent.append(payload)


class FakeRAG:
    async def get_user_context(self, user_id, query, db=None):
        return "CTX: hello"


class FakeLLM:
    async def stream_generate(self, user_message, context, chat_history=None):
        # Small chunks to exercise server-side batching.
        yield "Hello "
        yield "world"


@pytest.mark.anyio
async def test_handle_chat_request_sends_start_tokens_and_complete(monkeypatch):
    from src.routes.websocket import handle_chat_request

    import src.services.rag_service as rag_mod
    import src.services.llm_service as llm_mod
    import src.config.database as db_mod

    monkeypatch.setattr(rag_mod, "get_rag_service", lambda: FakeRAG())
    monkeypatch.setattr(llm_mod, "get_llm_service", lambda: FakeLLM())

    @asynccontextmanager
    async def _fake_session():
        yield object()

    monkeypatch.setattr(db_mod, "async_session", lambda: _fake_session())

    ws = FakeWebSocket()
    user_id = str(uuid.uuid4())

    await handle_chat_request(websocket=ws, user_id=user_id, message_content="hi", session_id=None)

    assert ws.sent, "Expected websocket messages"
    assert ws.sent[0]["type"] == "chat_start"

    token_msgs = [m for m in ws.sent if m["type"] == "chat_token"]
    assert token_msgs, "Expected at least one chat_token message"
    streamed = "".join(m["data"]["token"] for m in token_msgs)
    assert streamed == "Hello world"

    assert ws.sent[-1]["type"] == "chat_complete"
    assert ws.sent[-1]["data"]["full_response"] == "Hello world"

