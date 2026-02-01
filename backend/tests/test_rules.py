"""
Tests for the Recommendations Rules Engine

Run with: pytest backend/tests/test_rules.py -v
"""
import pytest
from datetime import datetime

# Import rules components
import sys
sys.path.insert(0, 'backend')

from src.rules import (
    get_registry,
    RuleResult,
    MetricData,
    UserContext,
    Severity,
    ActionType,
    LDLHighRule,
    HDLLowRule,
    HbA1cHighRule,
    VitaminDLowRule,
    BPHighRule,
    SleepLowRule,
    MissingTestsRule,
)


class TestRuleBase:
    """Test base rule functionality"""
    
    def test_metric_data_creation(self):
        """Test MetricData dataclass"""
        metric = MetricData(
            name="ldl",
            value=150.0,
            unit="mg/dL",
            reference_low=0,
            reference_high=100,
            days_since_last=30,
            trend="increasing"
        )
        
        assert metric.name == "ldl"
        assert metric.value == 150.0
        assert metric.is_above_range
        assert not metric.is_below_range
    
    def test_metric_below_range(self):
        """Test below range detection"""
        metric = MetricData(
            name="hdl",
            value=30.0,
            unit="mg/dL",
            reference_low=40,
            reference_high=60
        )
        
        assert metric.is_below_range
        assert not metric.is_above_range
    
    def test_user_context(self):
        """Test UserContext creation"""
        metrics = {
            "ldl": MetricData(name="ldl", value=150.0),
            "hdl": MetricData(name="hdl", value=55.0),
        }
        
        context = UserContext(
            user_id="test-user",
            metrics=metrics,
            age=45,
            gender="male"
        )
        
        assert context.user_id == "test-user"
        assert context.age == 45
        assert "ldl" in context.metrics
    
    def test_rule_result_to_dict(self):
        """Test RuleResult serialization"""
        from src.rules.base import Action, Source
        
        result = RuleResult(
            id="test_rule",
            title="Test Rule",
            severity=Severity.WARNING,
            why="Test explanation",
            actions=[Action(ActionType.EXERCISE, "Go for a walk")],
            followup=[Action(ActionType.DOCTOR, "Consult doctor")],
            sources=[Source("Test Source")]
        )
        
        data = result.to_dict()
        
        assert data["id"] == "test_rule"
        assert data["severity"] == "WARNING"
        assert len(data["actions"]) == 1
        assert data["actions"][0]["type"] == "EXERCISE"


class TestLipidRules:
    """Test lipid-related rules"""
    
    def test_ldl_high_rule_triggers_warning(self):
        """Test LDL rule triggers at 130+ mg/dL"""
        rule = LDLHighRule()
        
        context = UserContext(
            user_id="test",
            metrics={
                "ldl": MetricData(name="ldl", value=145.0, unit="mg/dL")
            }
        )
        
        result = rule.evaluate(context)
        
        assert result is not None
        assert result.severity == Severity.WARNING
        assert "LDL" in result.title
    
    def test_ldl_high_rule_urgent_at_190(self):
        """Test LDL rule is URGENT at 190+ mg/dL"""
        rule = LDLHighRule()
        
        context = UserContext(
            user_id="test",
            metrics={
                "ldl": MetricData(name="ldl", value=195.0, unit="mg/dL")
            }
        )
        
        result = rule.evaluate(context)
        
        assert result is not None
        assert result.severity == Severity.URGENT
    
    def test_ldl_normal_no_trigger(self):
        """Test LDL rule does not trigger at normal levels"""
        rule = LDLHighRule()
        
        context = UserContext(
            user_id="test",
            metrics={
                "ldl": MetricData(name="ldl", value=95.0, unit="mg/dL")
            }
        )
        
        result = rule.evaluate(context)
        
        assert result is None
    
    def test_hdl_low_rule_triggers(self):
        """Test HDL rule triggers at <40 mg/dL"""
        rule = HDLLowRule()
        
        context = UserContext(
            user_id="test",
            metrics={
                "hdl": MetricData(name="hdl", value=35.0, unit="mg/dL")
            }
        )
        
        result = rule.evaluate(context)
        
        assert result is not None
        assert "HDL" in result.title


class TestGlucoseRules:
    """Test glucose-related rules"""
    
    def test_hba1c_prediabetes_warning(self):
        """Test HbA1c rule triggers WARNING at 5.7-6.4%"""
        rule = HbA1cHighRule()
        
        context = UserContext(
            user_id="test",
            metrics={
                "hba1c": MetricData(name="hba1c", value=6.0, unit="%")
            }
        )
        
        result = rule.evaluate(context)
        
        assert result is not None
        assert result.severity == Severity.WARNING
        assert "prediabetes" in result.why.lower() or "HbA1c" in result.title
    
    def test_hba1c_diabetes_urgent(self):
        """Test HbA1c rule triggers URGENT at 6.5%+"""
        rule = HbA1cHighRule()
        
        context = UserContext(
            user_id="test",
            metrics={
                "hba1c": MetricData(name="hba1c", value=7.2, unit="%")
            }
        )
        
        result = rule.evaluate(context)
        
        assert result is not None
        assert result.severity == Severity.URGENT


class TestVitaminRules:
    """Test vitamin deficiency rules"""
    
    def test_vitamin_d_low_triggers(self):
        """Test Vitamin D rule triggers at <30 ng/mL"""
        rule = VitaminDLowRule()
        
        context = UserContext(
            user_id="test",
            metrics={
                "vitamin_d": MetricData(name="vitamin_d", value=18.0, unit="ng/mL")
            }
        )
        
        result = rule.evaluate(context)
        
        assert result is not None
        assert "Vitamin D" in result.title


class TestCardiovascularRules:
    """Test cardiovascular rules"""
    
    def test_bp_high_stage1(self):
        """Test BP rule triggers at Stage 1 hypertension"""
        rule = BPHighRule()
        
        context = UserContext(
            user_id="test",
            metrics={
                "systolic_bp": MetricData(name="systolic_bp", value=135.0, unit="mmHg"),
                "diastolic_bp": MetricData(name="diastolic_bp", value=85.0, unit="mmHg"),
            }
        )
        
        result = rule.evaluate(context)
        
        assert result is not None
        assert result.severity == Severity.WARNING
    
    def test_bp_hypertensive_crisis(self):
        """Test BP rule triggers URGENT at hypertensive crisis"""
        rule = BPHighRule()
        
        context = UserContext(
            user_id="test",
            metrics={
                "systolic_bp": MetricData(name="systolic_bp", value=185.0, unit="mmHg"),
                "diastolic_bp": MetricData(name="diastolic_bp", value=125.0, unit="mmHg"),
            }
        )
        
        result = rule.evaluate(context)
        
        assert result is not None
        assert result.severity == Severity.URGENT


class TestLifestyleRules:
    """Test lifestyle rules"""
    
    def test_sleep_low_triggers(self):
        """Test sleep rule triggers at <7 hours"""
        rule = SleepLowRule()
        
        context = UserContext(
            user_id="test",
            metrics={
                "sleep_hours": MetricData(name="sleep_hours", value=5.5, unit="hours")
            }
        )
        
        result = rule.evaluate(context)
        
        assert result is not None
        assert "sleep" in result.title.lower()


class TestMissingTestsRule:
    """Test missing tests rule"""
    
    def test_missing_tests_triggers(self):
        """Test missing tests rule triggers when no data"""
        rule = MissingTestsRule()
        
        # User with no test data
        context = UserContext(
            user_id="test",
            metrics={}
        )
        
        result = rule.evaluate(context)
        
        assert result is not None
        assert result.severity == Severity.INFO


class TestRuleRegistry:
    """Test rule registry functionality"""
    
    def test_registry_singleton(self):
        """Test registry is a singleton"""
        reg1 = get_registry()
        reg2 = get_registry()
        
        assert reg1 is reg2
    
    def test_registry_has_rules(self):
        """Test registry has registered rules"""
        registry = get_registry()
        
        rules = registry.get_all_rules()
        
        assert len(rules) > 0
    
    def test_evaluate_all(self):
        """Test evaluating all rules"""
        registry = get_registry()
        
        # Context with some concerning values
        context = UserContext(
            user_id="test",
            metrics={
                "ldl": MetricData(name="ldl", value=155.0, unit="mg/dL"),
                "hba1c": MetricData(name="hba1c", value=6.2, unit="%"),
            }
        )
        
        results = registry.evaluate_all(context)
        
        # Should get at least the LDL and HbA1c rules triggered
        assert len(results) >= 2
        
        # All results should be RuleResult instances
        for result in results:
            assert isinstance(result, RuleResult)
    
    def test_evaluate_for_metrics(self):
        """Test evaluating rules for specific metrics"""
        registry = get_registry()
        
        context = UserContext(
            user_id="test",
            metrics={
                "ldl": MetricData(name="ldl", value=155.0, unit="mg/dL"),
            }
        )
        
        # Only evaluate lipid rules
        results = registry.evaluate_for_metrics(context, ["ldl", "hdl"])
        
        # Should trigger LDL rule
        assert any("ldl" in r.id.lower() for r in results)


class TestActionTypes:
    """Test action types are properly categorized"""
    
    def test_all_actions_have_valid_types(self):
        """Test all rule actions have valid ActionType"""
        registry = get_registry()
        
        # Create context that triggers multiple rules
        context = UserContext(
            user_id="test",
            metrics={
                "ldl": MetricData(name="ldl", value=200.0),
                "hdl": MetricData(name="hdl", value=30.0),
                "hba1c": MetricData(name="hba1c", value=7.0),
                "sleep_hours": MetricData(name="sleep_hours", value=5.0),
            }
        )
        
        results = registry.evaluate_all(context)
        
        valid_types = {at.value for at in ActionType}
        
        for result in results:
            for action in result.actions:
                assert action.type.value in valid_types, f"Invalid action type: {action.type}"
            for followup in result.followup:
                assert followup.type.value in valid_types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
