"""
Conditions detection engine – maps abnormal metric values to health conditions.

Deterministic: each condition has threshold rules on specific metrics.
Returns detected conditions with severity, affected organs, and recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional


Severity = Literal["mild", "moderate", "severe"]


@dataclass
class ConditionRule:
    """A rule that detects a health condition from metric values."""
    id: str
    name: str
    description: str
    severity_thresholds: Dict[str, dict]  # metric_name -> {mild, moderate, severe}
    affected_organs: List[str]
    recommendations: List[str]
    youtube_queries: List[str] = field(default_factory=list)


@dataclass
class DetectedCondition:
    """A condition that has been detected from current metrics."""
    id: str
    name: str
    description: str
    severity: Severity
    affected_organs: List[str]
    trigger_metrics: Dict[str, float]  # metric_name -> current value
    recommendations: List[str]
    youtube_queries: List[str]


# ---------------------------------------------------------------------------
# Condition definitions
# ---------------------------------------------------------------------------

CONDITION_RULES: List[ConditionRule] = [
    ConditionRule(
        id="hypertension",
        name="Hypertension",
        description="Elevated blood pressure detected. Sustained high BP increases risk of heart disease and stroke.",
        severity_thresholds={
            "systolic_bp": {"mild": 130, "moderate": 140, "severe": 160},
            "diastolic_bp": {"mild": 85, "moderate": 90, "severe": 100},
        },
        affected_organs=["heart", "kidney", "brain"],
        recommendations=[
            "Reduce sodium intake to under 2,300 mg/day",
            "Engage in 30 minutes of moderate exercise daily",
            "Practice stress management (meditation, deep breathing)",
            "Monitor blood pressure at home twice daily",
            "Consult your physician about antihypertensive medication",
        ],
        youtube_queries=[
            "how to lower blood pressure naturally",
            "DASH diet for hypertension explained",
            "blood pressure monitoring at home tips",
        ],
    ),
    ConditionRule(
        id="tachycardia",
        name="Tachycardia",
        description="Elevated resting heart rate. May indicate stress, dehydration, or cardiac irregularity.",
        severity_thresholds={
            "heart_rate": {"mild": 100, "moderate": 120, "severe": 150},
        },
        affected_organs=["heart"],
        recommendations=[
            "Stay hydrated – aim for 8 glasses of water daily",
            "Reduce caffeine and stimulant intake",
            "Practice vagal maneuvers (cold water on face, bearing down)",
            "Get adequate sleep (7-9 hours)",
            "Seek medical evaluation if episodes are frequent",
        ],
        youtube_queries=[
            "what causes tachycardia explained",
            "vagal maneuver techniques for fast heart rate",
            "when to worry about high heart rate",
        ],
    ),
    ConditionRule(
        id="bradycardia",
        name="Bradycardia",
        description="Low resting heart rate. Normal in athletes, but may indicate conduction issues.",
        severity_thresholds={
            "heart_rate": {"mild": -55, "moderate": -50, "severe": -40},
        },
        affected_organs=["heart", "brain"],
        recommendations=[
            "Monitor for dizziness, fatigue, or fainting",
            "Maintain regular physical activity",
            "Review current medications with physician",
            "Consider ECG monitoring if symptomatic",
        ],
        youtube_queries=[
            "bradycardia explained simply",
            "low heart rate causes and treatment",
        ],
    ),
    ConditionRule(
        id="hypoxemia",
        name="Hypoxemia",
        description="Blood oxygen saturation below normal. May indicate respiratory compromise.",
        severity_thresholds={
            "spo2": {"mild": -94, "moderate": -90, "severe": -85},
        },
        affected_organs=["lungs", "heart", "brain"],
        recommendations=[
            "Practice deep breathing exercises (pursed lip breathing)",
            "Ensure adequate ventilation in living spaces",
            "Avoid high-altitude activities until resolved",
            "Seek immediate medical attention if SpO2 drops below 90%",
            "Check pulse oximeter placement and calibration",
        ],
        youtube_queries=[
            "how to improve blood oxygen levels naturally",
            "breathing exercises for better oxygen saturation",
            "when is low oxygen an emergency",
        ],
    ),
    ConditionRule(
        id="kidney_stress",
        name="Kidney Stress",
        description="Elevated creatinine or BUN suggests reduced kidney filtration capacity.",
        severity_thresholds={
            "creatinine": {"mild": 1.3, "moderate": 1.8, "severe": 3.0},
            "urea": {"mild": 22, "moderate": 30, "severe": 50},
        },
        affected_organs=["kidney"],
        recommendations=[
            "Increase water intake to 2-3 liters per day",
            "Reduce dietary protein to ease kidney workload",
            "Avoid NSAIDs (ibuprofen, naproxen)",
            "Limit potassium-rich foods if levels are elevated",
            "Schedule kidney function panel with your doctor",
        ],
        youtube_queries=[
            "how to improve kidney function naturally",
            "foods to avoid for kidney health",
            "early signs of kidney disease",
        ],
    ),
    ConditionRule(
        id="liver_stress",
        name="Liver Stress",
        description="Elevated liver enzymes (ALT/AST) indicate hepatocellular injury or inflammation.",
        severity_thresholds={
            "alt": {"mild": 60, "moderate": 100, "severe": 200},
            "ast": {"mild": 45, "moderate": 80, "severe": 160},
            "bilirubin_total": {"mild": 1.5, "moderate": 2.5, "severe": 5.0},
        },
        affected_organs=["liver"],
        recommendations=[
            "Eliminate alcohol consumption completely",
            "Adopt a Mediterranean diet rich in antioxidants",
            "Maintain healthy weight (BMI 18.5-24.9)",
            "Avoid acetaminophen and hepatotoxic supplements",
            "Get hepatitis screening if not previously done",
        ],
        youtube_queries=[
            "how to lower liver enzymes naturally",
            "liver cleanse diet what actually works",
            "signs your liver needs help",
        ],
    ),
    ConditionRule(
        id="hyperglycemia",
        name="Hyperglycemia",
        description="Elevated blood glucose. Persistent elevation may indicate prediabetes or diabetes.",
        severity_thresholds={
            "glucose": {"mild": 110, "moderate": 140, "severe": 200},
        },
        affected_organs=["kidney", "heart", "brain"],
        recommendations=[
            "Reduce refined carbohydrate and sugar intake",
            "Walk for 15 minutes after each meal",
            "Monitor fasting blood glucose regularly",
            "Consider HbA1c testing for long-term glucose control",
            "Consult endocrinologist if fasting glucose exceeds 126 mg/dL",
        ],
        youtube_queries=[
            "how to lower blood sugar quickly",
            "prediabetes reversal diet plan",
            "best exercises to reduce blood glucose",
        ],
    ),
    ConditionRule(
        id="high_stress",
        name="High Stress",
        description="Elevated stress levels impact cardiovascular, immune, and neurological health.",
        severity_thresholds={
            "stress_level": {"mild": 4.0, "moderate": 6.0, "severe": 8.0},
        },
        affected_organs=["brain", "heart"],
        recommendations=[
            "Practice 10-minute daily meditation or mindfulness",
            "Establish consistent sleep schedule (same bedtime/wake time)",
            "Engage in regular aerobic exercise (150 min/week)",
            "Limit screen time 1 hour before bed",
            "Consider cognitive behavioral therapy (CBT) techniques",
        ],
        youtube_queries=[
            "stress management techniques that work",
            "guided meditation for stress relief 10 minutes",
            "how stress affects your body explained",
        ],
    ),
    ConditionRule(
        id="sleep_deprivation",
        name="Sleep Deprivation",
        description="Insufficient sleep impairs cognitive function, immune response, and recovery.",
        severity_thresholds={
            "sleep_hours": {"mild": -6.5, "moderate": -5.0, "severe": -4.0},
        },
        affected_organs=["brain", "heart"],
        recommendations=[
            "Aim for 7-9 hours of sleep per night",
            "Create a dark, cool, quiet sleep environment",
            "Avoid caffeine after 2 PM",
            "Establish a consistent wind-down routine",
            "Limit blue light exposure 2 hours before bed",
        ],
        youtube_queries=[
            "science of sleep hygiene tips",
            "how to fall asleep faster",
            "effects of sleep deprivation on health",
        ],
    ),
    ConditionRule(
        id="tachypnea",
        name="Tachypnea",
        description="Elevated respiratory rate may indicate respiratory distress, anxiety, or metabolic acidosis.",
        severity_thresholds={
            "respiratory_rate": {"mild": 22, "moderate": 26, "severe": 30},
        },
        affected_organs=["lungs"],
        recommendations=[
            "Practice diaphragmatic breathing exercises",
            "Sit upright to improve lung expansion",
            "Monitor accompanying symptoms (chest pain, cough)",
            "Check for fever or signs of infection",
            "Seek medical evaluation if persistent",
        ],
        youtube_queries=[
            "diaphragmatic breathing technique tutorial",
            "what causes rapid breathing in adults",
        ],
    ),
]


def _check_threshold_exceeded(value: float, thresholds: dict) -> Optional[Severity]:
    """
    Check if a value exceeds condition thresholds.
    Negative threshold values indicate "below" conditions (e.g., bradycardia).
    """
    severities: List[Severity] = ["severe", "moderate", "mild"]

    # Detect direction: negative thresholds = "below" condition
    is_below = thresholds.get("mild", 0) < 0

    if is_below:
        for sev in severities:
            thresh = abs(thresholds.get(sev, 0))
            if value <= thresh:
                return sev
    else:
        for sev in severities:
            thresh = thresholds.get(sev, float('inf'))
            if value >= thresh:
                return sev

    return None


def detect_conditions(metrics: Dict[str, float]) -> List[DetectedCondition]:
    """
    Evaluate current metrics against all condition rules.
    Returns list of detected conditions sorted by severity (worst first).
    """
    detected: List[DetectedCondition] = []

    for rule in CONDITION_RULES:
        worst_severity: Optional[Severity] = None
        trigger_metrics: Dict[str, float] = {}
        severity_rank = {"mild": 1, "moderate": 2, "severe": 3}

        for metric_name, thresholds in rule.severity_thresholds.items():
            value = metrics.get(metric_name)
            if value is None:
                continue

            sev = _check_threshold_exceeded(value, thresholds)
            if sev is not None:
                trigger_metrics[metric_name] = value
                if worst_severity is None or severity_rank[sev] > severity_rank[worst_severity]:
                    worst_severity = sev

        if worst_severity is not None and trigger_metrics:
            detected.append(DetectedCondition(
                id=rule.id,
                name=rule.name,
                description=rule.description,
                severity=worst_severity,
                affected_organs=rule.affected_organs,
                trigger_metrics=trigger_metrics,
                recommendations=rule.recommendations,
                youtube_queries=rule.youtube_queries,
            ))

    # Sort by severity (severe first)
    severity_order = {"severe": 0, "moderate": 1, "mild": 2}
    detected.sort(key=lambda c: severity_order.get(c.severity, 3))

    return detected


def get_organ_conditions(conditions: List[DetectedCondition]) -> Dict[str, List[str]]:
    """
    Map organ -> list of condition IDs affecting it.
    Used to highlight organs on the body overlay.
    """
    organ_map: Dict[str, List[str]] = {}
    for cond in conditions:
        for organ in cond.affected_organs:
            if organ not in organ_map:
                organ_map[organ] = []
            organ_map[organ].append(cond.id)
    return organ_map


def get_organ_worst_severity(conditions: List[DetectedCondition]) -> Dict[str, Severity]:
    """Map organ -> worst severity from any condition affecting it."""
    severity_rank = {"mild": 1, "moderate": 2, "severe": 3}
    organ_sev: Dict[str, Severity] = {}
    for cond in conditions:
        for organ in cond.affected_organs:
            current = organ_sev.get(organ)
            if current is None or severity_rank[cond.severity] > severity_rank.get(current, 0):
                organ_sev[organ] = cond.severity
    return organ_sev
