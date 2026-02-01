"""
Vitamin and Mineral Recommendation Rules

Rules for Vitamin D, B12, and Iron.
"""
from typing import Optional, List
from .base import (
    Rule, RuleResult, UserContext, MetricData,
    Severity, Action, ActionType, Source
)


class VitaminDLowRule(Rule):
    """
    Rule for low Vitamin D.
    
    Reference: <20 ng/mL deficient, 20-29 insufficient, 30-100 sufficient
    """
    
    @property
    def rule_id(self) -> str:
        return "vitamin_d_low"
    
    @property
    def metric_names(self) -> List[str]:
        return ["vitamin_d", "vit_d", "25_oh_d", "25_hydroxyvitamin_d"]
    
    @property
    def priority(self) -> int:
        return 60
    
    def evaluate(self, context: UserContext) -> Optional[RuleResult]:
        metric = None
        for name in self.metric_names:
            metric = self.get_metric(context, name)
            if metric:
                break
        
        if not metric:
            return None
        
        value = metric.value
        unit = metric.unit or "ng/mL"
        
        if value >= 30:
            return None
        
        if value < 20:
            severity = Severity.WARNING
            title = "Vitamin D is deficient"
        else:  # 20-29
            severity = Severity.INFO
            title = "Vitamin D is insufficient"
        
        trend_text = self.format_trend(metric.trend, metric.trend_percentage)
        why = f"Vitamin D is {self.format_value(value, unit)} (optimal: 30-100 {unit})"
        if trend_text:
            why += f"; {trend_text}"
        
        actions = [
            Action(ActionType.HABIT, "Get 10-30 minutes of midday sunlight several times a week (with skin safety)"),
            Action(ActionType.DIET, "Include Vitamin D rich foods: fatty fish (salmon, mackerel), fortified milk/cereals, egg yolks"),
            Action(ActionType.GENERAL, "Consider Vitamin D supplementation - but consult a clinician for proper dosing"),
        ]
        
        followup = [
            Action(ActionType.TEST, "Recheck Vitamin D levels in 2-3 months if supplementing"),
            Action(ActionType.DOCTOR, "Discuss supplementation with a healthcare provider to determine appropriate dose"),
        ]
        
        return RuleResult(
            id=self.rule_id,
            title=title,
            severity=severity,
            why=why,
            actions=actions,
            followup=followup,
            sources=[Source("Endocrine Society Vitamin D Guidelines")],
            metric_name="Vitamin D",
            metric_value=value,
            metric_unit=unit,
            reference_min=30,
            reference_max=100,
            trend=metric.trend,
        )


class VitaminB12LowRule(Rule):
    """
    Rule for low Vitamin B12.
    
    Reference: <200 pg/mL deficient, 200-300 borderline, >300 normal
    """
    
    @property
    def rule_id(self) -> str:
        return "vitamin_b12_low"
    
    @property
    def metric_names(self) -> List[str]:
        return ["vitamin_b12", "b12", "cobalamin"]
    
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
        unit = metric.unit or "pg/mL"
        
        if value > 300:
            return None
        
        if value < 200:
            severity = Severity.WARNING
            title = "Vitamin B12 is deficient"
        else:  # 200-300
            severity = Severity.INFO
            title = "Vitamin B12 is borderline low"
        
        trend_text = self.format_trend(metric.trend, metric.trend_percentage)
        why = f"Vitamin B12 is {self.format_value(value, unit)} (optimal: >300 {unit})"
        if trend_text:
            why += f"; {trend_text}"
        
        actions = [
            Action(ActionType.DIET, "Include B12-rich foods: meat, fish, poultry, eggs, dairy; if vegetarian/vegan, use fortified foods"),
            Action(ActionType.GENERAL, "B12 deficiency is common in vegetarians, older adults, and those on certain medications"),
        ]
        
        followup = [
            Action(ActionType.DOCTOR, "Consult a clinician about B12 supplementation - may need injections if severely deficient"),
            Action(ActionType.TEST, "Recheck B12 after 2-3 months of supplementation"),
        ]
        
        return RuleResult(
            id=self.rule_id,
            title=title,
            severity=severity,
            why=why,
            actions=actions,
            followup=followup,
            sources=[Source("NIH Vitamin B12 Fact Sheet")],
            metric_name="Vitamin B12",
            metric_value=value,
            metric_unit=unit,
            reference_min=300,
            reference_max=None,
            trend=metric.trend,
        )


class IronLowRule(Rule):
    """
    Rule for low Iron/Ferritin.
    
    Reference: Ferritin <30 ng/mL may indicate deficiency
    """
    
    @property
    def rule_id(self) -> str:
        return "iron_low"
    
    @property
    def metric_names(self) -> List[str]:
        return ["ferritin", "iron", "serum_iron", "serum_ferritin"]
    
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
        unit = metric.unit or "ng/mL"
        
        # Check if this is ferritin (typical range)
        if "ferritin" in metric.name.lower() or value < 300:
            threshold_low = 30
            threshold_deficient = 15
        else:
            # Serum iron has different ranges
            threshold_low = 60
            threshold_deficient = 40
        
        if value >= threshold_low:
            return None
        
        if value < threshold_deficient:
            severity = Severity.WARNING
            title = "Iron stores are low"
        else:
            severity = Severity.INFO
            title = "Iron stores could be higher"
        
        trend_text = self.format_trend(metric.trend, metric.trend_percentage)
        why = f"Iron/Ferritin is {self.format_value(value, unit)}"
        if trend_text:
            why += f"; {trend_text}"
        
        actions = [
            Action(ActionType.DIET, "Include iron-rich foods: red meat, spinach, legumes, fortified cereals; pair with Vitamin C for better absorption"),
            Action(ActionType.HABIT, "Avoid tea/coffee with iron-rich meals (tannins reduce absorption)"),
        ]
        
        followup = [
            Action(ActionType.DOCTOR, "Consult a clinician before taking iron supplements - excess iron can be harmful"),
            Action(ActionType.TEST, "Get a complete iron panel (ferritin, serum iron, TIBC) for full picture"),
        ]
        
        return RuleResult(
            id=self.rule_id,
            title=title,
            severity=severity,
            why=why,
            actions=actions,
            followup=followup,
            sources=[Source("WHO Iron Deficiency Guidelines")],
            metric_name="Iron/Ferritin",
            metric_value=value,
            metric_unit=unit,
            reference_min=threshold_low,
            reference_max=None,
            trend=metric.trend,
        )
