"""
Lifestyle Recommendation Rules

Rules for Sleep, Activity, Stress, and Hydration.
These are based on wellness metrics tracked by the app.
"""
from typing import Optional, List
from .base import (
    Rule, RuleResult, UserContext, MetricData,
    Severity, Action, ActionType, Source
)


class SleepLowRule(Rule):
    """
    Rule for insufficient sleep.
    
    Reference: Adults need 7-9 hours per night
    """
    
    @property
    def rule_id(self) -> str:
        return "lifestyle_sleep_low"
    
    @property
    def metric_names(self) -> List[str]:
        return ["sleep_hours", "sleep", "sleep_duration", "avg_sleep"]
    
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
        unit = metric.unit or "hours"
        
        if value >= 7:
            return None
        
        if value < 5:
            severity = Severity.WARNING
            title = "Sleep duration is very low"
        else:  # 5-7 hours
            severity = Severity.INFO
            title = "Sleep duration could be improved"
        
        trend_text = self.format_trend(metric.trend, metric.trend_percentage)
        why = f"Average sleep is {self.format_value(value, unit)} (recommended: 7-9 hours)"
        if trend_text:
            why += f"; {trend_text}"
        
        actions = [
            Action(ActionType.SLEEP, "Set a consistent sleep schedule - same bedtime and wake time daily, even weekends"),
            Action(ActionType.SLEEP, "Create a sleep-friendly environment: dark, cool (65-68°F), quiet"),
            Action(ActionType.HABIT, "Limit screens 1 hour before bed; avoid caffeine after 2pm"),
            Action(ActionType.SLEEP, "Develop a relaxing bedtime routine: reading, stretching, or meditation"),
        ]
        
        followup = []
        if value < 5:
            followup.append(Action(ActionType.DOCTOR, "Chronic sleep deprivation can affect health significantly - consider consulting a sleep specialist"))
        
        return RuleResult(
            id=self.rule_id,
            title=title,
            severity=severity,
            why=why,
            actions=actions,
            followup=followup,
            sources=[
                Source("CDC Sleep Guidelines", "https://www.cdc.gov/sleep/about_sleep/how_much_sleep.html"),
            ],
            metric_name="Sleep Duration",
            metric_value=value,
            metric_unit=unit,
            reference_min=7,
            reference_max=9,
            trend=metric.trend,
        )


class ActivityLowRule(Rule):
    """
    Rule for insufficient physical activity.
    
    Reference: 150 min/week moderate activity or 75 min/week vigorous
    """
    
    @property
    def rule_id(self) -> str:
        return "lifestyle_activity_low"
    
    @property
    def metric_names(self) -> List[str]:
        return ["activity_minutes", "exercise_minutes", "weekly_activity", "steps"]
    
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
        name = metric.name.lower()
        
        # Handle steps vs minutes differently
        if "step" in name:
            # 10,000 steps/day ≈ 150 min activity/week
            if value >= 7000:
                return None
            threshold_warning = 5000
            unit = "steps/day"
            target = "7,000-10,000 steps/day"
        else:
            # Weekly activity minutes
            if value >= 150:
                return None
            threshold_warning = 75
            unit = metric.unit or "min/week"
            target = "150 min/week"
        
        if value < threshold_warning:
            severity = Severity.WARNING
            title = "Physical activity is low"
        else:
            severity = Severity.INFO
            title = "Physical activity could be increased"
        
        trend_text = self.format_trend(metric.trend, metric.trend_percentage)
        why = f"Activity level is {self.format_value(value, unit)} (target: {target})"
        if trend_text:
            why += f"; {trend_text}"
        
        actions = [
            Action(ActionType.EXERCISE, "Start with achievable goals: 10-15 min walks, gradually increase"),
            Action(ActionType.EXERCISE, "Include both cardio (walking, cycling) and strength training (bodyweight, resistance)"),
            Action(ActionType.HABIT, "Take stairs, park farther away, walk during calls - small changes add up"),
            Action(ActionType.GENERAL, "Find activities you enjoy - dancing, hiking, sports - adherence matters most"),
        ]
        
        followup = [
            Action(ActionType.GENERAL, "Use a fitness tracker or app to monitor progress"),
        ]
        
        return RuleResult(
            id=self.rule_id,
            title=title,
            severity=severity,
            why=why,
            actions=actions,
            followup=followup,
            sources=[
                Source("WHO Physical Activity Guidelines"),
            ],
            metric_name="Physical Activity",
            metric_value=value,
            metric_unit=unit,
            reference_min=150 if "min" in unit else 7000,
            reference_max=None,
            trend=metric.trend,
        )


class StressHighRule(Rule):
    """
    Rule for elevated stress levels.
    
    Based on app-tracked stress score (0-100 scale, higher = more stress)
    """
    
    @property
    def rule_id(self) -> str:
        return "lifestyle_stress_high"
    
    @property
    def metric_names(self) -> List[str]:
        return ["stress_score", "stress", "stress_level"]
    
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
        
        # Assuming 0-100 scale where higher = more stress
        if value < 50:
            return None
        
        if value >= 75:
            severity = Severity.WARNING
            title = "Stress levels are high"
        else:  # 50-74
            severity = Severity.INFO
            title = "Stress levels are elevated"
        
        trend_text = self.format_trend(metric.trend, metric.trend_percentage)
        why = f"Stress score is {int(value)}/100"
        if trend_text:
            why += f"; {trend_text}"
        
        actions = [
            Action(ActionType.STRESS, "Practice daily relaxation: 10-15 min deep breathing, meditation, or progressive muscle relaxation"),
            Action(ActionType.EXERCISE, "Regular exercise is a powerful stress reducer - even a 20-min walk helps"),
            Action(ActionType.HABIT, "Set boundaries; take breaks; limit news/social media consumption"),
            Action(ActionType.SLEEP, "Prioritize sleep - stress and sleep deprivation create a vicious cycle"),
        ]
        
        followup = []
        if value >= 75:
            followup.append(Action(ActionType.DOCTOR, "If stress is significantly affecting daily life, consider speaking with a mental health professional"))
        
        return RuleResult(
            id=self.rule_id,
            title=title,
            severity=severity,
            why=why,
            actions=actions,
            followup=followup,
            sources=[Source("APA Stress Management")],
            metric_name="Stress Score",
            metric_value=value,
            metric_unit="/100",
            reference_min=None,
            reference_max=50,
            trend=metric.trend,
        )


class HydrationLowRule(Rule):
    """
    Rule for insufficient hydration.
    
    Based on app-tracked hydration score (0-100 scale)
    """
    
    @property
    def rule_id(self) -> str:
        return "lifestyle_hydration_low"
    
    @property
    def metric_names(self) -> List[str]:
        return ["hydration_score", "hydration", "water_intake"]
    
    @property
    def priority(self) -> int:
        return 50
    
    def evaluate(self, context: UserContext) -> Optional[RuleResult]:
        metric = None
        for name in self.metric_names:
            metric = self.get_metric(context, name)
            if metric:
                break
        
        if not metric:
            return None
        
        value = metric.value
        name = metric.name.lower()
        
        # Handle score vs liters/oz
        if "score" in name or value <= 100:
            # Score out of 100
            if value >= 70:
                return None
            threshold = 50
            unit = "/100"
            display = f"{int(value)}/100"
        else:
            # Assume liters
            if value >= 2.0:
                return None
            threshold = 1.5
            unit = metric.unit or "L"
            display = f"{value:.1f} {unit}"
        
        if value < threshold:
            severity = Severity.INFO
            title = "Hydration could be improved"
        else:
            severity = Severity.INFO
            title = "Hydration is slightly low"
        
        trend_text = self.format_trend(metric.trend, metric.trend_percentage)
        why = f"Hydration is {display}"
        if trend_text:
            why += f"; {trend_text}"
        
        actions = [
            Action(ActionType.HYDRATION, "Aim for 8 glasses (64 oz / 2L) of water daily; more if active or in hot weather"),
            Action(ActionType.HYDRATION, "Keep a water bottle visible as a reminder; set hourly hydration reminders"),
            Action(ActionType.DIET, "Water-rich foods count too: cucumbers, watermelon, oranges, soups"),
            Action(ActionType.HABIT, "Drink a glass of water with each meal and between meals"),
        ]
        
        return RuleResult(
            id=self.rule_id,
            title=title,
            severity=severity,
            why=why,
            actions=actions,
            followup=[],
            sources=[Source("CDC Water and Healthier Drinks")],
            metric_name="Hydration",
            metric_value=value,
            metric_unit=unit,
            reference_min=70,
            reference_max=None,
            trend=metric.trend,
        )
