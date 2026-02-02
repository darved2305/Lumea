"""
LLMService (Ollama) tests (backend/src/services/llm_service.py).

No real network calls: httpx + ollama are faked.
"""

import json
import types

import pytest


class _FakePullResponse:
    def __init__(self, lines):
        self._lines = list(lines)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        return None

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class _FakeHTTPXClient:
    def __init__(self, *, lines, capture):
        self._lines = lines
        self._capture = capture

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def stream(self, method, url, json=None):
        self._capture["method"] = method
        self._capture["url"] = url
        self._capture["json"] = json
        return _FakePullResponse(self._lines)


class _FakeOllamaChatStream:
    def __init__(self, chunks):
        self._chunks = list(chunks)

    def __aiter__(self):
        return self._aiter()

    async def _aiter(self):
        for c in self._chunks:
            yield c


class _FakeOllamaAsyncClient:
    def __init__(self, host=None):
        self.host = host

    async def chat(self, **kwargs):
        # Simulate Ollama streaming chunks.
        return _FakeOllamaChatStream(
            [
                {"message": {"content": "Hello "}},
                {"message": {"content": "world"}},
            ]
        )


@pytest.mark.anyio
async def test_pull_model_with_progress_sets_complete_and_calls_api(monkeypatch, caplog):
    import src.services.llm_service as llm_mod

    # Reset global state between tests
    monkeypatch.setattr(llm_mod, "_pull_complete", None)

    capture = {}
    lines = [
        json.dumps({"status": "pulling", "total": 100, "completed": 0}),
        json.dumps({"status": "pulling", "total": 100, "completed": 50}),
        json.dumps({"status": "pulling", "total": 100, "completed": 100}),
        json.dumps({"status": "success"}),
    ]

    fake_httpx = types.SimpleNamespace(
        AsyncClient=lambda timeout=None: _FakeHTTPXClient(lines=lines, capture=capture)
    )
    monkeypatch.setattr(llm_mod, "httpx", fake_httpx)

    # Avoid depending on real settings values
    monkeypatch.setattr(llm_mod.settings, "OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    monkeypatch.setattr(llm_mod.settings, "OLLAMA_MODEL", "hf.co/unsloth/medgemma-4b-it-GGUF:Q6_K_XL")
    monkeypatch.setattr(llm_mod.settings, "OLLAMA_PULL_LOG_STEP_PCT", 50)

    with caplog.at_level("INFO"):
        await llm_mod._pull_model_with_progress()

    assert capture["url"].endswith("/api/pull")
    assert capture["json"]["name"] == "hf.co/unsloth/medgemma-4b-it-GGUF:Q6_K_XL"
    assert llm_mod._pull_complete is True


@pytest.mark.anyio
async def test_stream_generate_yields_streamed_content(monkeypatch):
    import src.services.llm_service as llm_mod

    # Skip pulling to focus on streaming behavior
    async def _noop_pull():
        return None

    monkeypatch.setattr(llm_mod, "_pull_model_with_progress", _noop_pull)
    monkeypatch.setattr(llm_mod.settings, "OLLAMA_PULL_ON_START", True)

    fake_ollama = types.SimpleNamespace(AsyncClient=_FakeOllamaAsyncClient)
    monkeypatch.setattr(llm_mod, "ollama", fake_ollama)

    svc = llm_mod.LLMService()
    out = []
    async for token in svc.stream_generate("hi", "CTX"):
        out.append(token)

    assert "".join(out) == "Hello world"

