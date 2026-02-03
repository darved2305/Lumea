"""
ReportService tests (backend/src/services/report_service.py).
"""

import uuid
from types import SimpleNamespace
from datetime import datetime

import pytest

from src.services.report_service import ReportService


class _FakeSyncSession:
    def __init__(self):
        self.added = []
        self.commits = 0
        self.refreshed = []

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        self.refreshed.append(obj)


def test_validate_file_rejects_bad_extension():
    svc = ReportService(db=_FakeSyncSession())
    with pytest.raises(ValueError):
        svc._validate_file("malware.exe", 10)


def test_validate_file_rejects_path_traversal():
    svc = ReportService(db=_FakeSyncSession())
    with pytest.raises(ValueError):
        svc._validate_file("../secret.pdf", 10)


def test_get_reference_range_flags_abnormal_values():
    svc = ReportService(db=_FakeSyncSession())
    ref_min, ref_max, is_abnormal = svc._get_reference_range("glucose", 150)
    assert (ref_min, ref_max) == (70, 100)
    assert is_abnormal is True


@pytest.mark.anyio
async def test_upload_report_writes_file_and_creates_report(tmp_path, monkeypatch):
    # Write into a temp directory instead of repo ./uploads
    monkeypatch.setattr(ReportService, "UPLOAD_DIR", tmp_path)
    db = _FakeSyncSession()
    svc = ReportService(db=db)

    user_id = uuid.uuid4()
    report = await svc.upload_report(
        user_id=user_id,
        filename="lab.pdf",
        file_content=b"PDFDATA",
        report_date=datetime.utcnow(),
    )

    assert db.commits == 1
    assert report.filename == "lab.pdf"
    # Ensure file exists on disk
    assert report.file_path
    # Normalize paths for Windows/Linux compatibility
    from pathlib import Path
    assert Path(tmp_path).resolve() in Path(report.file_path).resolve().parents
