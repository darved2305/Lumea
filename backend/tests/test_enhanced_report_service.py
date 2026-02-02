"""
EnhancedReportService tests (backend/src/services/enhanced_report_service.py).

We cover key error-handling paths without touching real files/DB.
"""

import io
import uuid
from types import SimpleNamespace
from datetime import datetime

import pytest

from tests.helpers import FakeAsyncSession, FakeResult
from src.services.enhanced_report_service import EnhancedReportService
from src.services.pdf_extractor import ExtractionResult
from src.models.orm import ReportStatus


@pytest.mark.anyio
async def test_process_report_marks_failed_and_emits_on_extraction_failure(monkeypatch):
    report_id = uuid.uuid4()
    user_id = uuid.uuid4()

    report = SimpleNamespace(
        id=report_id,
        user_id=user_id,
        file_path="fake.pdf",
        status=ReportStatus.UPLOADED,
        uploaded_at=datetime.utcnow(),
        report_date=None,
        error_message=None,
        extraction_method=None,
        page_stats=None,
        raw_text=None,
    )

    db = FakeAsyncSession(execute_results=[FakeResult(scalars_rows=[report])])
    svc = EnhancedReportService(db=db)

    # Fake file read
    class _FakeFile:
        def __enter__(self):
            return io.BytesIO(b"%PDF%")

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("builtins.open", lambda *args, **kwargs: _FakeFile())

    # Force extraction failure
    monkeypatch.setattr(
        svc.extractor,
        "extract",
        lambda pdf_bytes: ExtractionResult(
            full_text="",
            method="failed",
            page_stats=[],
            total_chars=0,
            success=False,
            error="extraction failed",
        ),
    )

    # Capture websocket emissions
    events = {"started": [], "parsed": [], "list": 0}

    async def _started(uid, data):
        events["started"].append((uid, data))

    async def _parsed(uid, data):
        events["parsed"].append((uid, data))

    async def _list(uid):
        events["list"] += 1

    import src.routes.websocket as ws_mod

    monkeypatch.setattr(ws_mod, "emit_report_processing_started", _started)
    monkeypatch.setattr(ws_mod, "emit_report_parsed", _parsed)
    monkeypatch.setattr(ws_mod, "emit_reports_list_updated", _list)

    await svc.process_report(report_id=report_id, user_id=user_id)

    assert report.status == ReportStatus.FAILED
    assert report.extraction_method == "failed"
    assert events["parsed"], "Expected emit_report_parsed to be called"
    assert events["parsed"][-1][1]["status"] == "failed"
