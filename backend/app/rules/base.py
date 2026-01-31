"""
Base classes for the rule-based recommendations engine.

All rules inherit from Rule and return RuleResult objects.
Rules are deterministic and testable.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime


class Severity(str, Enum):
    """Severity levels for recommendations"""
    INFO = "info"           # General wellness tip
    WARNING = "warning"     # Needs attention
    URGENT = "urgent"       # Seek medical care (still non-diagnostic)


class ActionType(str, Enum):
    """Types of recommended actions"""
    EXERCISE = "exercise"
    DIET = "diet"
    HABIT = "habit"
    SLEEP = "sleep"
    STRESS = "stress"
    HYDRATION = "hydration"
    TEST = "test"           # Recommend a follow-up test
    DOCTOR = "doctor"       # Consult a clinician
    GENERAL = "general"


@dataclass
class Action:
    """A single recommended action"""
    type: ActionType
    text: str
    
    def to_dict(self) -> Dict[str, str]:
        return {"type": self.type.value, "text": self.text}


@dataclass
class Source:
    """Reference source for recommendation"""
    name: str
    url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, str]:
        result = {"name": self.name}
        if self.url:
            result["url"] = self.url
        return result


@dataclass
class RuleResult:
    """
    Result of evaluating a rule.
    
    Contains all information needed to display a recommendation.
    """
    id: str                          # Unique identifier (e.g., "lipids_ldl_high")
    title: str                       # Short title
    severity: Severity               # info, warning, urgent
    why: str                         # Explanation with data
    actions: List[Action]            # Lifestyle/wellness actions
    followup: List[Action]           # Follow-up tests/doctor visits
    sources: List[Source] = field(default_factory=list)
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    metric_unit: Optional[str] = None
    reference_min: Optional[float] = None
    reference_max: Optional[float] = None
    trend: Optional[str] = None      # "rising", "falling", "stable"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "severity": self.severity.value,
            "why": self.why,
            "actions": [a.to_dict() for a in self.actions],
            "followup": [f.to_dict() for f in self.followup],
            "sources": [s.to_dict() for s in self.sources],
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "metric_unit": self.metric_unit,
            "reference_min": self.reference_min,
            "reference_max": self.reference_max,
            "trend": self.trend,
        }


@dataclass
class MetricData:
    """
    Input data for rule evaluation.
    
    Contains current value, reference range, and trend information.
    """
    name: str
    value: float
    unit: str
    reference_min: Optional[float] = None
    reference_max: Optional[float] = None
    is_abnormal: bool = False
    trend: Optional[str] = None      # "rising", "falling", "stable"
    trend_percentage: Optional[float] = None  # e.g., +15% over last 60 days
    days_since_last: Optional[int] = None  # Days since last measurement
    

@dataclass
class UserContext:
    """
    Context about the user for personalized recommendations.
    
    Note: We don't store sensitive medical history.
    This is for basic personalization only.
    """
    user_id: str
    metrics: Dict[str, MetricData] = field(default_factory=dict)
    available_test_names: List[str] = field(default_factory=list)
    days_since_last_report: Optional[int] = None


class Rule(ABC):
    """
    Base class for all recommendation rules.
    
    Each rule evaluates specific health metrics and returns
    actionable recommendations if the rule triggers.
    """
    
    @property
    @abstractmethod
    def rule_id(self) -> str:
        """Unique identifier for this rule"""
        pass
    
    @property
    @abstractmethod
    def metric_names(self) -> List[str]:
        """List of metric names this rule evaluates"""
        pass
    
    @property
    def priority(self) -> int:
        """Priority for ordering (higher = more important). Default: 50"""
        return 50
    
    @abstractmethod
    def evaluate(self, context: UserContext) -> Optional[RuleResult]:
        """
        Evaluate the rule against user context.
        
        Returns RuleResult if rule triggers, None otherwise.
        """
        pass
    
    def get_metric(self, context: UserContext, name: str) -> Optional[MetricData]:
        """Helper to safely get a metric from context"""
        return context.metrics.get(name)
    
    def format_value(self, value: float, unit: str) -> str:
        """Format a metric value with unit"""
        if value == int(value):
            return f"{int(value)} {unit}"
        return f"{value:.1f} {unit}"
    
    def format_trend(self, trend: Optional[str], percentage: Optional[float] = None) -> str:
        """Format trend information"""
        if not trend:
            return ""
        
        trend_text = {
            "rising": "trending up",
            "falling": "trending down", 
            "stable": "stable"
        }.get(trend, "")
        
        if percentage and trend in ("rising", "falling"):
            direction = "+" if percentage > 0 else ""
            trend_text += f" ({direction}{percentage:.0f}%)"
        
        return trend_text
