"""
Rule-Based Recommendations Engine

This module contains deterministic, testable rules for generating
personalized health recommendations based on:
- Metric values vs reference ranges
- Trend direction (worsening/improving)
- Missing tests/data

IMPORTANT: These are wellness suggestions only, NOT medical advice.
"""

from .base import Rule, RuleResult, Severity, ActionType, MetricData, UserContext
from .registry import RuleRegistry, get_registry
from .lipid_rules import LDLHighRule, HDLLowRule, TotalCholesterolHighRule, TriglyceridesHighRule
from .glucose_rules import HbA1cHighRule, FastingGlucoseHighRule
from .vitamin_rules import VitaminDLowRule, VitaminB12LowRule, IronLowRule
from .cardiovascular_rules import BPHighRule, BPLowRule, HeartRateHighRule
from .lifestyle_rules import SleepLowRule, ActivityLowRule, StressHighRule, HydrationLowRule
from .missing_tests_rule import MissingTestsRule

__all__ = [
    'Rule', 'RuleResult', 'Severity', 'ActionType', 'MetricData', 'UserContext',
    'RuleRegistry', 'get_registry',
    'LDLHighRule', 'HDLLowRule', 'TotalCholesterolHighRule', 'TriglyceridesHighRule',
    'HbA1cHighRule', 'FastingGlucoseHighRule',
    'VitaminDLowRule', 'VitaminB12LowRule', 'IronLowRule',
    'BPHighRule', 'BPLowRule', 'HeartRateHighRule',
    'SleepLowRule', 'ActivityLowRule', 'StressHighRule', 'HydrationLowRule',
    'MissingTestsRule',
]
