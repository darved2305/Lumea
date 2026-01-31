"""
Rule Registry - Manages and executes all recommendation rules.
"""
from typing import List, Optional, Dict, Type
from .base import Rule, RuleResult, UserContext


class RuleRegistry:
    """
    Central registry for all recommendation rules.
    
    Handles rule registration, execution, and result aggregation.
    """
    
    _instance: Optional['RuleRegistry'] = None
    
    def __init__(self):
        self._rules: Dict[str, Rule] = {}
    
    @classmethod
    def get_instance(cls) -> 'RuleRegistry':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._register_default_rules()
        return cls._instance
    
    def register(self, rule: Rule) -> None:
        """Register a rule"""
        self._rules[rule.rule_id] = rule
    
    def unregister(self, rule_id: str) -> None:
        """Unregister a rule"""
        self._rules.pop(rule_id, None)
    
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get a specific rule by ID"""
        return self._rules.get(rule_id)
    
    def get_all_rules(self) -> List[Rule]:
        """Get all registered rules"""
        return list(self._rules.values())
    
    def evaluate_all(self, context: UserContext) -> List[RuleResult]:
        """
        Evaluate all rules against user context.
        
        Returns list of triggered rule results, sorted by priority.
        """
        results = []
        
        for rule in self._rules.values():
            try:
                result = rule.evaluate(context)
                if result:
                    results.append(result)
            except Exception as e:
                # Log error but don't fail the whole evaluation
                print(f"Error evaluating rule {rule.rule_id}: {e}")
        
        # Sort by severity (urgent first) then priority
        severity_order = {"urgent": 0, "warning": 1, "info": 2}
        results.sort(key=lambda r: (severity_order.get(r.severity.value, 3), -getattr(self._rules.get(r.id.split('_')[0], object()), 'priority', 50)))
        
        return results
    
    def evaluate_for_metrics(self, context: UserContext, metric_names: List[str]) -> List[RuleResult]:
        """
        Evaluate only rules relevant to specific metrics.
        """
        results = []
        
        for rule in self._rules.values():
            # Check if rule applies to any of the specified metrics
            if any(m in metric_names for m in rule.metric_names):
                try:
                    result = rule.evaluate(context)
                    if result:
                        results.append(result)
                except Exception as e:
                    print(f"Error evaluating rule {rule.rule_id}: {e}")
        
        return results
    
    def _register_default_rules(self) -> None:
        """Register all default rules"""
        # Import here to avoid circular imports
        from .lipid_rules import LDLHighRule, HDLLowRule, TotalCholesterolHighRule, TriglyceridesHighRule
        from .glucose_rules import HbA1cHighRule, FastingGlucoseHighRule
        from .vitamin_rules import VitaminDLowRule, VitaminB12LowRule, IronLowRule
        from .cardiovascular_rules import BPHighRule, BPLowRule, HeartRateHighRule
        from .lifestyle_rules import SleepLowRule, ActivityLowRule, StressHighRule, HydrationLowRule
        from .missing_tests_rule import MissingTestsRule
        
        # Lipid rules
        self.register(LDLHighRule())
        self.register(HDLLowRule())
        self.register(TotalCholesterolHighRule())
        self.register(TriglyceridesHighRule())
        
        # Glucose rules
        self.register(HbA1cHighRule())
        self.register(FastingGlucoseHighRule())
        
        # Vitamin rules
        self.register(VitaminDLowRule())
        self.register(VitaminB12LowRule())
        self.register(IronLowRule())
        
        # Cardiovascular rules
        self.register(BPHighRule())
        self.register(BPLowRule())
        self.register(HeartRateHighRule())
        
        # Lifestyle rules
        self.register(SleepLowRule())
        self.register(ActivityLowRule())
        self.register(StressHighRule())
        self.register(HydrationLowRule())
        
        # Missing tests rule
        self.register(MissingTestsRule())


def get_registry() -> RuleRegistry:
    """Get the global rule registry"""
    return RuleRegistry.get_instance()
