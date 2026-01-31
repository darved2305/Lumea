"""
Glucose/Diabetes Recommendation Rules

Rules for HbA1c and Fasting Glucose.
Based on ADA guidelines.
"""
from typing import Optional, List
from .base import (
    Rule, RuleResult, UserContext, MetricData,
    Severity, Action, ActionType, Source
)


class HbA1cHighRule(Rule):
    """
    Rule for elevated HbA1c.
    
    Reference: <5.7% normal, 5.7-6.4% prediabetes, ≥6.5% diabetes range
    """
    
    @property
    def rule_id(self) -> str:
        return "glucose_hba1c_high"
    
    @property
    def metric_names(self) -> List[str]:
        return ["hba1c", "a1c", "hemoglobin_a1c", "glycated_hemoglobin"]
    
    @property
    def priority(self) -> int:
        return 90  # Very high priority - diabetes indicator
    
    def evaluate(self, context: UserContext) -> Optional[RuleResult]:
        metric = None
        for name in self.metric_names:
            metric = self.get_metric(context, name)
            if metric:
                break
        
        if not metric:
            return None
        
        value = metric.value
        unit = metric.unit or "%"
        
        if value < 5.7:
            return None
        
        if value >= 6.5:
            severity = Severity.URGENT
            title = "HbA1c is in the diabetes range"
        else:  # 5.7-6.4
            severity = Severity.WARNING
            title = "HbA1c indicates prediabetes"
        
        trend_text = self.format_trend(metric.trend, metric.trend_percentage)
        why = f"Your HbA1c is {value}{unit}"
        if value >= 6.5:
            why += " (diabetes threshold: ≥6.5%)"
        else:
            why += " (prediabetes: 5.7-6.4%)"
        if trend_text:
            why += f"; {trend_text}"
        
        actions = [
            Action(ActionType.DIET, "Focus on low-glycemic foods; reduce refined carbs and sugars; eat more fiber, vegetables, and lean proteins"),
            Action(ActionType.EXERCISE, "At least 150 min/week moderate exercise; include both cardio and resistance training"),
            Action(ActionType.HABIT, "Monitor portion sizes; maintain consistent meal timing; stay hydrated"),
        ]
        
        if value >= 6.5:
            actions.append(Action(ActionType.GENERAL, "Learn about blood sugar management and consider a diabetes education program"))
        
        followup = [
            Action(ActionType.TEST, "Recheck HbA1c in 3 months; consider home glucose monitoring"),
            Action(ActionType.DOCTOR, "Please consult a healthcare provider for proper diabetes screening and management guidance"),
        ]
        
        return RuleResult(
            id=self.rule_id,
            title=title,
            severity=severity,
            why=why,
            actions=actions,
            followup=followup,
            sources=[
                Source("ADA Standards of Care", "https://diabetes.org/about-diabetes/diagnosis"),
            ],
            metric_name="HbA1c",
            metric_value=value,
            metric_unit=unit,
            reference_min=None,
            reference_max=5.7,
            trend=metric.trend,
        )


class FastingGlucoseHighRule(Rule):
    """
    Rule for elevated fasting glucose.
    
    Reference: <100 mg/dL normal, 100-125 prediabetes, ≥126 diabetes range
    """
    
    @property
    def rule_id(self) -> str:
        return "glucose_fasting_high"
    
    @property
    def metric_names(self) -> List[str]:
        return ["fasting_glucose", "glucose", "blood_sugar", "fbs", "fbg"]
    
    @property
    def priority(self) -> int:
        return 85
    
    def evaluate(self, context: UserContext) -> Optional[RuleResult]:
        metric = None
        for name in self.metric_names:
            metric = self.get_metric(context, name)
            if metric:
                break
        
        if not metric:
            return None
        
        value = metric.value
        unit = metric.unit or "mg/dL"
        
        if value < 100:
            return None
        
        if value >= 126:
            severity = Severity.URGENT
            title = "Fasting glucose is in diabetes range"
        else:  # 100-125
            severity = Severity.WARNING
            title = "Fasting glucose indicates prediabetes"
        
        trend_text = self.format_trend(metric.trend, metric.trend_percentage)
        why = f"Fasting glucose is {self.format_value(value, unit)}"
        if value >= 126:
            why += " (diabetes threshold: ≥126 mg/dL)"
        else:
            why += " (prediabetes: 100-125 mg/dL)"
        if trend_text:
            why += f"; {trend_text}"
        
        actions = [
            Action(ActionType.DIET, "Reduce simple carbs and sugary foods; increase fiber intake; consider smaller, more frequent meals"),
            Action(ActionType.EXERCISE, "Regular physical activity improves insulin sensitivity - even a 30-min daily walk helps"),
            Action(ActionType.HABIT, "Maintain healthy weight; manage stress; get adequate sleep (7-9 hours)"),
        ]
        
        followup = [
            Action(ActionType.TEST, "Confirm with a repeat fasting glucose test or HbA1c"),
            Action(ActionType.DOCTOR, "Discuss with a clinician for proper evaluation and personalized guidance"),
        ]
        
        return RuleResult(
            id=self.rule_id,
            title=title,
            severity=severity,
            why=why,
            actions=actions,
            followup=followup,
            sources=[Source("ADA Diabetes Diagnosis Criteria")],
            metric_name="Fasting Glucose",
            metric_value=value,
            metric_unit=unit,
            reference_min=None,
            reference_max=100,
            trend=metric.trend,
        )
