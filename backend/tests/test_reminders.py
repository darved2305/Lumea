"""
compute_reminders tests (backend/src/utils/reminders.py).
"""

from datetime import datetime, timedelta

from src.utils.reminders import compute_reminders


def test_compute_reminders_includes_diabetes_specific_items_and_sorts_overdue_first():
    now = datetime.utcnow()
    profile = {
        "conditions": ["Diabetes"],
        "last_blood_test_at": now - timedelta(days=200),
        "last_dental_at": None,
        "last_eye_exam_at": None,
        "last_dental": None,
        "last_eye_exam": None,
    }

    reminders = compute_reminders(profile)
    titles = [r.title for r in reminders]

    assert "HbA1c Test" in titles
    assert "Kidney Function Test" in titles

    # Should have overdue items first (since missing dental/eye)
    assert reminders[0].urgency == "overdue"


def test_compute_reminders_ok_when_future_due_date():
    now = datetime.utcnow()
    profile = {
        "conditions": [],
        "last_blood_test_at": now - timedelta(days=30),  # next in ~335 days
        "last_dental_at": now - timedelta(days=30),      # next in ~150 days
        "last_eye_exam_at": now - timedelta(days=30),    # next in ~335 days
    }
    reminders = compute_reminders(profile)
    # At least one should be 'ok' given far away due dates
    assert any(r.urgency == "ok" for r in reminders)

