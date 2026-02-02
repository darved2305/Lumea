"""
RAGService tests (backend/src/services/rag_service.py).

We avoid heavy dependencies (chromadb, sentence-transformers) by patching
the embedding + collection methods.
"""

import uuid
from types import SimpleNamespace

import pytest

from tests.helpers import FakeAsyncSession, FakeResult
from src.services.rag_service import RAGService


def test_split_text_preserves_content_and_limits_chunk_size():
    rag = RAGService()
    text = "A" * 600 + "\n\n" + "B" * 600 + "\n\n" + "C" * 200
    chunks = rag._split_text(text, max_length=700)

    assert chunks, "Expected chunks"
    assert all(len(c) <= 700 for c in chunks)
    # Roundtrip-ish: concatenation should contain original letters
    joined = "\n\n".join(chunks)
    assert "A" * 50 in joined
    assert "B" * 50 in joined
    assert "C" * 50 in joined


@pytest.mark.anyio
async def test_get_user_context_returns_no_data_message_when_empty(monkeypatch):
    rag = RAGService()

    async def _empty_query(user_id, query, k=None):
        return []

    monkeypatch.setattr(rag, "query", _empty_query)
    out = await rag.get_user_context(user_id=uuid.uuid4(), query="anything", db=None)
    assert "No health data available" in out


@pytest.mark.anyio
async def test_get_user_context_formats_report_sources(monkeypatch):
    rag = RAGService()
    user_id = uuid.uuid4()

    async def _query(user_id, query, k=None):
        return [
            {"content": "Report chunk text", "metadata": {"source_type": "report", "filename": "lab.pdf"}, "distance": 0.1},
            {"content": "Obs summary text", "metadata": {"source_type": "observations"}, "distance": 0.2},
        ]

    monkeypatch.setattr(rag, "query", _query)
    out = await rag.get_user_context(user_id=user_id, query="ldl", db=None)
    assert "From report 'lab.pdf':" in out
    assert "Obs summary text" in out


@pytest.mark.anyio
async def test_sync_user_reports_calls_collection_upsert(monkeypatch):
    rag = RAGService()
    user_id = uuid.uuid4()

    report = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user_id,
        raw_text="Para1\n\nPara2",
        filename="r1.pdf",
        report_date=None,
    )

    db = FakeAsyncSession(execute_results=[FakeResult(scalars_rows=[report])])

    calls = {}

    async def _fake_embed_texts(texts):
        return [[0.0] * 3 for _ in texts]

    class _FakeCollection:
        def upsert(self, **kwargs):
            calls["kwargs"] = kwargs

    monkeypatch.setattr(rag, "_embed_texts", lambda texts: [[0.0] * 3 for _ in texts])
    monkeypatch.setattr(rag, "_get_collection", lambda: _FakeCollection())

    n = await rag.sync_user_reports(user_id, db)
    assert n >= 1
    assert "kwargs" in calls
    assert calls["kwargs"]["metadatas"][0]["filename"] == "r1.pdf"

