"""
Missing Tests Recommendation Rule

Suggests tests that haven't been performed recently or are missing from user's data.
"""
from typing import Optional, List
from datetime import datetime, timedelta
from .base import (
    Rule, RuleResult, UserContext, MetricData,
    Severity, Action, ActionType, Source
)


# Common health tests and their recommended frequency
RECOMMENDED_TESTS = {
    # Lipid Panel
    "lipid_panel": {
        "display_name": "Lipid Panel (Cholesterol)",
        "metrics": ["ldl", "hdl", "total_cholesterol", "triglycerides"],
        "frequency_days": 365,  # Yearly
        "priority": 80,
        "description": "measures cholesterol and cardiovascular risk markers"
    },
    # Glucose/Diabetes
    "glucose_screening": {
        "display_name": "Glucose/HbA1c",
        "metrics": ["glucose", "fasting_glucose", "hba1c"],
        "frequency_days": 365,
        "priority": 85,
        "description": "screens for diabetes and blood sugar control"
    },
    # CBC
    "cbc": {
        "display_name": "Complete Blood Count (CBC)",
        "metrics": ["hemoglobin", "hematocrit", "wbc", "rbc", "platelets"],
        "frequency_days": 365,
        "priority": 70,
        "description": "evaluates overall health and detects many disorders"
    },
    # Vitamin D
    "vitamin_d": {
        "display_name": "Vitamin D",
        "metrics": ["vitamin_d", "25_oh_d"],
        "frequency_days": 365,
        "priority": 60,
        "description": "important for bone health and immune function"
    },
    # Thyroid
    "thyroid": {
        "display_name": "Thyroid Function (TSH)",
        "metrics": ["tsh", "t3", "t4", "thyroid"],
        "frequency_days": 365,
        "priority": 65,
        "description": "checks thyroid function which affects metabolism"
    },
    # Blood Pressure
    "blood_pressure": {
        "display_name": "Blood Pressure",
        "metrics": ["systolic_bp", "diastolic_bp", "blood_pressure"],
        "frequency_days": 180,  # Every 6 months
        "priority": 90,
        "description": "key indicator of cardiovascular health"
    },
    # Kidney Function
    "kidney": {
        "display_name": "Kidney Function (eGFR, Creatinine)",
        "metrics": ["creatinine", "egfr", "bun"],
        "frequency_days": 365,
        "priority": 70,
        "description": "evaluates how well your kidneys are working"
    },
    # Liver Function
    "liver": {
        "display_name": "Liver Function (ALT, AST)",
        "metrics": ["alt", "ast", "bilirubin", "albumin"],
        "frequency_days": 365,
        "priority": 70,
        "description": "assesses liver health"
    },
}


class MissingTestsRule(Rule):
    """
    Rule that suggests tests that are missing or overdue.
    
    Looks at user's available tests and recommends what might be missing
    based on standard health screening guidelines.
    """
    
    @property
    def rule_id(self) -> str:
        return "missing_tests"
    
    @property
    def metric_names(self) -> List[str]:
        # This rule can apply to any metrics (or lack thereof)
        return ["*"]
    
    @property
    def priority(self) -> int:
        return 40  # Lower priority than actual findings
    
    def evaluate(self, context: UserContext) -> Optional[RuleResult]:
        # Find tests that are missing or overdue
        available_metrics = set(context.metrics.keys())
        available_lower = {m.lower() for m in available_metrics}
        
        missing_tests = []
        overdue_tests = []
        
        for test_id, test_info in RECOMMENDED_TESTS.items():
            # Check if any metric from this test category is present
            test_metrics_lower = [m.lower() for m in test_info["metrics"]]
            has_any = any(tm in available_lower or any(tm in am for am in available_lower) 
                         for tm in test_metrics_lower)
            
            if not has_any:
                missing_tests.append((test_id, test_info))
            else:
                # Check if overdue
                for metric_name in test_info["metrics"]:
                    metric = context.metrics.get(metric_name)
                    if metric and metric.days_since_last:
                        if metric.days_since_last > test_info["frequency_days"]:
                            overdue_tests.append((test_id, test_info, metric.days_since_last))
                            break
        
        # Only return results if there are missing or overdue tests
        if not missing_tests and not overdue_tests:
            return None
        
        # Determine severity
        if len(missing_tests) >= 3 or any(days > 730 for _, _, days in overdue_tests):
            severity = Severity.INFO
        else:
            severity = Severity.INFO
        
        # Build explanation
        why_parts = []
        if missing_tests:
            names = [t[1]["display_name"] for t in missing_tests[:3]]
            why_parts.append(f"Missing: {', '.join(names)}")
            if len(missing_tests) > 3:
                why_parts[-1] += f" (+{len(missing_tests) - 3} more)"
        
        if overdue_tests:
            overdue_names = [f"{t[1]['display_name']} ({t[2]} days)" for t in overdue_tests[:2]]
            why_parts.append(f"Overdue: {', '.join(overdue_names)}")
        
        why = "; ".join(why_parts)
        
        # Build actions
        actions = []
        
        # Prioritize by priority score
        all_tests = [(tid, tinfo, None) for tid, tinfo in missing_tests] + overdue_tests
        all_tests.sort(key=lambda x: -x[1]["priority"])
        
        for test_id, test_info, days in all_tests[:4]:
            if days:
                action_text = f"Schedule {test_info['display_name']} - overdue by {days - test_info['frequency_days']} days"
            else:
                action_text = f"Consider getting {test_info['display_name']} - {test_info['description']}"
            actions.append(Action(ActionType.TEST, action_text))
        
        if len(all_tests) > 4:
            actions.append(Action(ActionType.GENERAL, f"Review {len(all_tests) - 4} additional tests with your doctor"))
        
        followup = [
            Action(ActionType.DOCTOR, "Discuss with your healthcare provider which tests are appropriate for your age and health history"),
        ]
        
        return RuleResult(
            id=self.rule_id,
            title="Some health screenings may be due",
            severity=severity,
            why=why,
            actions=actions,
            followup=followup,
            sources=[
                Source("USPSTF Preventive Services Recommendations"),
            ],
        )
