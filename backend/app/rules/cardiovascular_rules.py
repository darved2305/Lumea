"""
Cardiovascular Recommendation Rules

Rules for Blood Pressure and Heart Rate.
"""
from typing import Optional, List
from .base import (
    Rule, RuleResult, UserContext, MetricData,
    Severity, Action, ActionType, Source
)


class BPHighRule(Rule):
    """
    Rule for elevated blood pressure (hypertension).
    
    Reference:
    - Normal: <120/80 mmHg
    - Elevated: 120-129/<80
    - Stage 1 HTN: 130-139/80-89
    - Stage 2 HTN: ≥140/≥90
    """
    
    @property
    def rule_id(self) -> str:
        return "bp_high"
    
    @property
    def metric_names(self) -> List[str]:
        return ["systolic_bp", "diastolic_bp", "blood_pressure", "bp_systolic", "bp_diastolic"]
    
    @property
    def priority(self) -> int:
        return 85
    
    def evaluate(self, context: UserContext) -> Optional[RuleResult]:
        # Try to get systolic
        systolic = None
        diastolic = None
        
        for name in ["systolic_bp", "bp_systolic", "systolic"]:
            metric = self.get_metric(context, name)
            if metric:
                systolic = metric
                break
        
        for name in ["diastolic_bp", "bp_diastolic", "diastolic"]:
            metric = self.get_metric(context, name)
            if metric:
                diastolic = metric
                break
        
        if not systolic:
            return None
        
        sys_val = systolic.value
        dia_val = diastolic.value if diastolic else 0
        
        # Determine severity
        if sys_val >= 180 or dia_val >= 120:
            severity = Severity.URGENT
            title = "Blood pressure is critically high"
        elif sys_val >= 140 or dia_val >= 90:
            severity = Severity.WARNING
            title = "Blood pressure is high (Stage 2)"
        elif sys_val >= 130 or dia_val >= 80:
            severity = Severity.WARNING
            title = "Blood pressure is elevated (Stage 1)"
        elif sys_val >= 120:
            severity = Severity.INFO
            title = "Blood pressure is slightly elevated"
        else:
            return None
        
        # Build explanation
        bp_text = f"{int(sys_val)}"
        if diastolic:
            bp_text += f"/{int(dia_val)}"
        bp_text += " mmHg"
        
        trend_text = self.format_trend(systolic.trend, systolic.trend_percentage)
        why = f"Blood pressure is {bp_text} (normal: <120/80 mmHg)"
        if trend_text:
            why += f"; {trend_text}"
        
        actions = [
            Action(ActionType.DIET, "Reduce sodium intake (<2,300mg/day, ideally <1,500mg); follow DASH diet principles"),
            Action(ActionType.EXERCISE, "Regular aerobic exercise: 30 min/day most days (walking, swimming, cycling)"),
            Action(ActionType.HABIT, "Limit alcohol; quit smoking if applicable; manage stress with relaxation techniques"),
            Action(ActionType.GENERAL, "Maintain healthy weight - even 5-10 lbs loss can improve BP"),
        ]
        
        followup = [
            Action(ActionType.TEST, "Monitor BP at home; check at different times of day"),
        ]
        
        if severity == Severity.URGENT:
            followup.insert(0, Action(ActionType.DOCTOR, "URGENT: Very high BP requires immediate medical attention"))
        else:
            followup.append(Action(ActionType.DOCTOR, "Discuss with a clinician - may need medication if lifestyle changes insufficient"))
        
        return RuleResult(
            id=self.rule_id,
            title=title,
            severity=severity,
            why=why,
            actions=actions,
            followup=followup,
            sources=[
                Source("AHA Blood Pressure Guidelines", "https://www.heart.org/en/health-topics/high-blood-pressure"),
            ],
            metric_name="Blood Pressure",
            metric_value=sys_val,
            metric_unit="mmHg",
            reference_min=None,
            reference_max=120,
            trend=systolic.trend,
        )


class BPLowRule(Rule):
    """
    Rule for low blood pressure (hypotension).
    
    Reference: <90/60 mmHg may be concerning if symptomatic
    """
    
    @property
    def rule_id(self) -> str:
        return "bp_low"
    
    @property
    def metric_names(self) -> List[str]:
        return ["systolic_bp", "diastolic_bp", "blood_pressure"]
    
    @property
    def priority(self) -> int:
        return 70
    
    def evaluate(self, context: UserContext) -> Optional[RuleResult]:
        systolic = None
        diastolic = None
        
        for name in ["systolic_bp", "bp_systolic", "systolic"]:
            metric = self.get_metric(context, name)
            if metric:
                systolic = metric
                break
        
        for name in ["diastolic_bp", "bp_diastolic", "diastolic"]:
            metric = self.get_metric(context, name)
            if metric:
                diastolic = metric
                break
        
        if not systolic:
            return None
        
        sys_val = systolic.value
        dia_val = diastolic.value if diastolic else 60
        
        if sys_val >= 90 and dia_val >= 60:
            return None
        
        severity = Severity.INFO
        title = "Blood pressure is on the lower side"
        
        bp_text = f"{int(sys_val)}"
        if diastolic:
            bp_text += f"/{int(dia_val)}"
        bp_text += " mmHg"
        
        why = f"Blood pressure is {bp_text}. Low BP is often fine but can cause dizziness/fatigue in some people."
        
        actions = [
            Action(ActionType.HYDRATION, "Stay well hydrated; increase water and electrolyte intake"),
            Action(ActionType.DIET, "Moderate salt intake may help if BP is consistently low"),
            Action(ActionType.HABIT, "Rise slowly from sitting/lying position; avoid standing for long periods"),
        ]
        
        followup = [
            Action(ActionType.DOCTOR, "If experiencing dizziness, fainting, or fatigue, consult a clinician"),
        ]
        
        return RuleResult(
            id=self.rule_id,
            title=title,
            severity=severity,
            why=why,
            actions=actions,
            followup=followup,
            sources=[Source("AHA Hypotension Information")],
            metric_name="Blood Pressure",
            metric_value=sys_val,
            metric_unit="mmHg",
            reference_min=90,
            reference_max=None,
            trend=systolic.trend,
        )


class HeartRateHighRule(Rule):
    """
    Rule for elevated resting heart rate.
    
    Reference: Normal resting HR 60-100 bpm; >100 is tachycardia
    """
    
    @property
    def rule_id(self) -> str:
        return "hr_high"
    
    @property
    def metric_names(self) -> List[str]:
        return ["heart_rate", "hr", "resting_hr", "pulse"]
    
    @property
    def priority(self) -> int:
        return 65
    
    def evaluate(self, context: UserContext) -> Optional[RuleResult]:
        metric = None
        for name in self.metric_names:
            metric = self.get_metric(context, name)
            if metric:
                break
        
        if not metric:
            return None
        
        value = metric.value
        unit = metric.unit or "bpm"
        
        if value <= 100:
            return None
        
        if value > 120:
            severity = Severity.WARNING
            title = "Resting heart rate is elevated"
        else:
            severity = Severity.INFO
            title = "Resting heart rate is slightly high"
        
        trend_text = self.format_trend(metric.trend, metric.trend_percentage)
        why = f"Resting heart rate is {int(value)} {unit} (normal: 60-100 bpm)"
        if trend_text:
            why += f"; {trend_text}"
        
        actions = [
            Action(ActionType.EXERCISE, "Regular cardio exercise can lower resting HR over time"),
            Action(ActionType.STRESS, "Practice relaxation techniques: deep breathing, meditation"),
            Action(ActionType.HABIT, "Limit caffeine; reduce stress; ensure adequate sleep"),
        ]
        
        followup = [
            Action(ActionType.DOCTOR, "If HR is persistently elevated or you have palpitations, consult a clinician"),
            Action(ActionType.TEST, "Consider an ECG if heart rate irregularities are noted"),
        ]
        
        return RuleResult(
            id=self.rule_id,
            title=title,
            severity=severity,
            why=why,
            actions=actions,
            followup=followup,
            sources=[Source("AHA Heart Rate Information")],
            metric_name="Resting Heart Rate",
            metric_value=value,
            metric_unit=unit,
            reference_min=60,
            reference_max=100,
            trend=metric.trend,
        )
