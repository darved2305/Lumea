from datetime import datetime, timedelta
from typing import List, Optional
from app.schemas import ReminderItem

def compute_reminders(profile_data: dict) -> List[ReminderItem]:
    """
    Compute health reminders based on patient profile and last checkup dates.
    Rules are simple and non-clinical - focused on preventive care scheduling.
    """
    reminders = []
    today = datetime.utcnow()
    
    # Get profile data
    conditions = profile_data.get('conditions', [])
    last_blood_test = profile_data.get('last_blood_test_at')
    last_dental = profile_data.get('last_dental_at')
    last_eye_exam = profile_data.get('last_eye_exam_at')
    
    # Helper to determine urgency
    def get_urgency(due_date: datetime) -> str:
        days_until = (due_date - today).days
        if days_until < 0:
            return 'overdue'
        elif days_until <= 30:
            return 'soon'
        else:
            return 'ok'
    
    # Dental checkup - every 6 months
    if last_dental:
        next_dental = last_dental + timedelta(days=180)
        reminders.append(ReminderItem(
            title="Dental Checkup",
            reason="Regular dental hygiene and oral health maintenance",
            due_date=next_dental,
            urgency=get_urgency(next_dental),
            frequency_months=6
        ))
    else:
        reminders.append(ReminderItem(
            title="Dental Checkup",
            reason="Schedule your routine dental checkup",
            due_date=today,
            urgency='overdue',
            frequency_months=6
        ))
    
    # Basic blood work - every 12 months
    if last_blood_test:
        next_blood = last_blood_test + timedelta(days=365)
        reminders.append(ReminderItem(
            title="Basic Blood Work",
            reason="Annual health screening and wellness check",
            due_date=next_blood,
            urgency=get_urgency(next_blood),
            frequency_months=12
        ))
    else:
        reminders.append(ReminderItem(
            title="Basic Blood Work",
            reason="Recommended to schedule your health screening",
            due_date=today,
            urgency='overdue',
            frequency_months=12
        ))
    
    # Diabetes-specific reminders
    if 'Diabetes' in conditions or 'diabetes' in [c.lower() for c in conditions]:
        # HbA1c every 3 months
        if last_blood_test:
            next_hba1c = last_blood_test + timedelta(days=90)
            reminders.append(ReminderItem(
                title="HbA1c Test",
                reason="Regular diabetes monitoring for optimal blood sugar control",
                due_date=next_hba1c,
                urgency=get_urgency(next_hba1c),
                frequency_months=3
            ))
        else:
            reminders.append(ReminderItem(
                title="HbA1c Test",
                reason="Important for diabetes management",
                due_date=today,
                urgency='overdue',
                frequency_months=3
            ))
    
    # Hypertension or Diabetes - kidney function
    if any(cond.lower() in ['hypertension', 'diabetes'] for cond in conditions):
        if last_blood_test:
            next_kidney = last_blood_test + timedelta(days=180)
            reminders.append(ReminderItem(
                title="Kidney Function Test",
                reason="Routine monitoring for cardiovascular and metabolic health",
                due_date=next_kidney,
                urgency=get_urgency(next_kidney),
                frequency_months=6
            ))
        else:
            reminders.append(ReminderItem(
                title="Kidney Function Test",
                reason="Recommended for your health profile",
                due_date=today,
                urgency='overdue',
                frequency_months=6
            ))
    
    # Eye exam - yearly, higher priority for diabetes
    has_diabetes = any('diabetes' in c.lower() for c in conditions)
    if last_eye_exam:
        next_eye = last_eye_exam + timedelta(days=365)
        reason = "Annual eye health check" + (" - important for diabetes management" if has_diabetes else "")
        reminders.append(ReminderItem(
            title="Eye Examination",
            reason=reason,
            due_date=next_eye,
            urgency=get_urgency(next_eye),
            frequency_months=12
        ))
    else:
        reminders.append(ReminderItem(
            title="Eye Examination",
            reason="Recommended to schedule your eye health check" + (" - important for diabetes care" if has_diabetes else ""),
            due_date=today,
            urgency='overdue',
            frequency_months=12
        ))
    
    # Sort by urgency (overdue first, then soon, then ok) and date
    urgency_order = {'overdue': 0, 'soon': 1, 'ok': 2}
    reminders.sort(key=lambda r: (urgency_order[r.urgency], r.due_date))
    
    return reminders
