"""
Reports routes unit tests (backend/src/routes/reports.py).
"""

import uuid
from types import SimpleNamespace
from datetime import datetime

import pytest

from tests.helpers import FakeAsyncSession, FakeResult
from src.models.orm import ReportStatus


@pytest.mark.anyio
async def test_list_reports_returns_items_with_observation_count():
    from src.routes.reports import list_reports

    user_id = uuid.uuid4()
    user = SimpleNamespace(id=user_id)
    now = datetime.utcnow()

    report1 = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user_id,
        filename="a.pdf",
        file_type="pdf",
        file_size=123,
        status=ReportStatus.UPLOADED,
        report_date=None,
        uploaded_at=now,
        processed_at=None,
        extraction_confidence=None,
    )
    report2 = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user_id,
        filename="b.pdf",
        file_type="pdf",
        file_size=456,
        status=ReportStatus.PROCESSED,
        report_date=None,
        uploaded_at=now,
        processed_at=now,
        extraction_confidence=0.9,
    )

    db = FakeAsyncSession(
        execute_results=[
            FakeResult(scalars_rows=[report1, report2]),
            FakeResult(scalar=2),
            FakeResult(scalar=0),
        ]
    )

    items = await list_reports(limit=50, offset=0, current_user=user, db=db)
    assert len(items) == 2
    assert items[0].observation_count == 2
    assert items[1].observation_count == 0

