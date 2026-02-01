"""
Lipid Panel Recommendation Rules

Rules for LDL, HDL, Total Cholesterol, and Triglycerides.
Based on standard reference ranges and AHA guidelines.
"""
from typing import Optional, List
from .base import (
    Rule, RuleResult, UserContext, MetricData,
    Severity, Action, ActionType, Source
)


class LDLHighRule(Rule):
    """
    Rule for elevated LDL cholesterol.
    
    Reference: <100 mg/dL optimal, <130 near optimal, 130-159 borderline high, ≥160 high
    """
    
    @property
    def rule_id(self) -> str:
        return "lipids_ldl_high"
    
    @property
    def metric_names(self) -> List[str]:
        return ["ldl", "ldl_cholesterol", "ldl-c"]
    
    @property
    def priority(self) -> int:
        return 80  # High priority - cardiovascular risk factor
    
    def evaluate(self, context: UserContext) -> Optional[RuleResult]:
        # Find LDL metric
        metric = None
        for name in self.metric_names:
            metric = self.get_metric(context, name)
            if metric:
                break
        
        if not metric:
            return None
        
        value = metric.value
        unit = metric.unit or "mg/dL"
        
        # Determine severity based on value
        if value < 130:
            return None  # Within acceptable range
        
        if value >= 190:
            severity = Severity.URGENT
            title = "LDL cholesterol is very high"
        elif value >= 160:
            severity = Severity.WARNING
            title = "LDL cholesterol is high"
        else:  # 130-159
            severity = Severity.INFO
            title = "LDL cholesterol is borderline high"
        
        # Build explanation
        trend_text = self.format_trend(metric.trend, metric.trend_percentage)
        why = f"Your LDL is {self.format_value(value, unit)}"
        if metric.reference_max:
            why += f" (optimal: <{int(metric.reference_max)} {unit})"
        if trend_text:
            why += f"; {trend_text} recently"
        
        # Build actions
        actions = [
            Action(ActionType.EXERCISE, "Aim for 150 minutes/week of moderate cardio (brisk walking, cycling) plus 2 days of strength training"),
            Action(ActionType.DIET, "Increase soluble fiber (oats, beans, fruits); reduce saturated and trans fats; consider plant sterols"),
            Action(ActionType.HABIT, "If you smoke, consider cessation resources; limit alcohol to moderate levels"),
        ]
        
        # Build follow-up
        followup = [
            Action(ActionType.TEST, "Repeat lipid panel in 8-12 weeks to track progress"),
        ]
        
        if severity == Severity.URGENT:
            followup.append(Action(ActionType.DOCTOR, "With LDL this high, please consult a healthcare provider to discuss your cardiovascular risk"))
        elif severity == Severity.WARNING:
            followup.append(Action(ActionType.DOCTOR, "Consider discussing with a clinician, especially if you have other risk factors (diabetes, high BP, family history)"))
        
        return RuleResult(
            id=self.rule_id,
            title=title,
            severity=severity,
            why=why,
            actions=actions,
            followup=followup,
            sources=[
                Source("AHA Cholesterol Guidelines", "https://www.heart.org/en/health-topics/cholesterol"),
            ],
            metric_name="LDL Cholesterol",
            metric_value=value,
            metric_unit=unit,
            reference_min=None,
            reference_max=130,
            trend=metric.trend,
        )


class HDLLowRule(Rule):
    """
    Rule for low HDL cholesterol.
    
    Reference: >60 mg/dL optimal, <40 mg/dL (men) / <50 mg/dL (women) is low
    """
    
    @property
    def rule_id(self) -> str:
        return "lipids_hdl_low"
    
    @property
    def metric_names(self) -> List[str]:
        return ["hdl", "hdl_cholesterol", "hdl-c"]
    
    @property
    def priority(self) -> int:
        return 75
    
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
        
        # Using 40 as threshold (conservative)
        if value >= 40:
            return None
        
        severity = Severity.WARNING if value < 35 else Severity.INFO
        title = "HDL cholesterol is low" if value < 35 else "HDL cholesterol could be higher"
        
        trend_text = self.format_trend(metric.trend, metric.trend_percentage)
        why = f"Your HDL ('good cholesterol') is {self.format_value(value, unit)}"
        why += f" (optimal: >60 {unit})"
        if trend_text:
            why += f"; {trend_text}"
        
        actions = [
            Action(ActionType.EXERCISE, "Regular aerobic exercise can significantly raise HDL - aim for 30+ minutes most days"),
            Action(ActionType.DIET, "Include healthy fats: olive oil, avocados, fatty fish, nuts; avoid trans fats completely"),
            Action(ActionType.HABIT, "Maintain a healthy weight; if you smoke, quitting can raise HDL by up to 10%"),
        ]
        
        followup = [
            Action(ActionType.TEST, "Recheck lipid panel in 3 months after lifestyle changes"),
            Action(ActionType.DOCTOR, "Low HDL combined with other risk factors warrants clinical discussion"),
        ]
        
        return RuleResult(
            id=self.rule_id,
            title=title,
            severity=severity,
            why=why,
            actions=actions,
            followup=followup,
            sources=[Source("AHA HDL Guidelines")],
            metric_name="HDL Cholesterol",
            metric_value=value,
            metric_unit=unit,
            reference_min=40,
            reference_max=None,
            trend=metric.trend,
        )


class TotalCholesterolHighRule(Rule):
    """
    Rule for elevated total cholesterol.
    
    Reference: <200 mg/dL desirable, 200-239 borderline, ≥240 high
    """
    
    @property
    def rule_id(self) -> str:
        return "lipids_total_high"
    
    @property
    def metric_names(self) -> List[str]:
        return ["total_cholesterol", "cholesterol", "tc"]
    
    @property
    def priority(self) -> int:
        return 70
    
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
        
        if value < 200:
            return None
        
        if value >= 240:
            severity = Severity.WARNING
            title = "Total cholesterol is high"
        else:
            severity = Severity.INFO
            title = "Total cholesterol is borderline high"
        
        trend_text = self.format_trend(metric.trend, metric.trend_percentage)
        why = f"Total cholesterol is {self.format_value(value, unit)} (desirable: <200 {unit})"
        if trend_text:
            why += f"; {trend_text}"
        
        actions = [
            Action(ActionType.DIET, "Focus on heart-healthy eating: more vegetables, whole grains, lean proteins; less processed food"),
            Action(ActionType.EXERCISE, "Regular physical activity helps improve overall cholesterol profile"),
            Action(ActionType.HABIT, "Consider the DASH or Mediterranean diet patterns"),
        ]
        
        followup = [
            Action(ActionType.TEST, "Get a complete lipid panel to see LDL/HDL breakdown"),
            Action(ActionType.DOCTOR, "Discuss your cardiovascular risk profile with a clinician"),
        ]
        
        return RuleResult(
            id=self.rule_id,
            title=title,
            severity=severity,
            why=why,
            actions=actions,
            followup=followup,
            sources=[Source("AHA Cholesterol Guidelines")],
            metric_name="Total Cholesterol",
            metric_value=value,
            metric_unit=unit,
            reference_min=None,
            reference_max=200,
            trend=metric.trend,
        )


class TriglyceridesHighRule(Rule):
    """
    Rule for elevated triglycerides.
    
    Reference: <150 mg/dL normal, 150-199 borderline, 200-499 high, ≥500 very high
    """
    
    @property
    def rule_id(self) -> str:
        return "lipids_triglycerides_high"
    
    @property
    def metric_names(self) -> List[str]:
        return ["triglycerides", "tg", "trigs"]
    
    @property
    def priority(self) -> int:
        return 75
    
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
        
        if value < 150:
            return None
        
        if value >= 500:
            severity = Severity.URGENT
            title = "Triglycerides are very high"
        elif value >= 200:
            severity = Severity.WARNING
            title = "Triglycerides are high"
        else:
            severity = Severity.INFO
            title = "Triglycerides are borderline high"
        
        trend_text = self.format_trend(metric.trend, metric.trend_percentage)
        why = f"Triglycerides are {self.format_value(value, unit)} (normal: <150 {unit})"
        if trend_text:
            why += f"; {trend_text}"
        
        actions = [
            Action(ActionType.DIET, "Limit sugars and refined carbs; reduce alcohol intake; eat more omega-3 rich foods (fatty fish, walnuts)"),
            Action(ActionType.EXERCISE, "Regular exercise can lower triglycerides by 20-30%"),
            Action(ActionType.HABIT, "Maintain healthy weight; avoid sugary beverages"),
        ]
        
        followup = [
            Action(ActionType.TEST, "Recheck triglycerides fasting in 6-8 weeks"),
        ]
        
        if severity == Severity.URGENT:
            followup.insert(0, Action(ActionType.DOCTOR, "Very high triglycerides need medical evaluation - risk of pancreatitis"))
        elif severity == Severity.WARNING:
            followup.append(Action(ActionType.DOCTOR, "Discuss with clinician if lifestyle changes don't improve levels"))
        
        return RuleResult(
            id=self.rule_id,
            title=title,
            severity=severity,
            why=why,
            actions=actions,
            followup=followup,
            sources=[Source("AHA Triglyceride Guidelines")],
            metric_name="Triglycerides",
            metric_value=value,
            metric_unit=unit,
            reference_min=None,
            reference_max=150,
            trend=metric.trend,
        )
