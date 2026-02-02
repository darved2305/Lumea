"""
Rule engine tests (backend/src/rules).

These are pure unit tests: no DB, no network.
"""

from src.rules import (
    get_registry,
    MetricData,
    UserContext,
    Severity,
    LDLHighRule,
    HDLLowRule,
    HbA1cHighRule,
    VitaminDLowRule,
    BPHighRule,
    SleepLowRule,
    MissingTestsRule,
)


def test_user_context_accepts_age_and_gender():
    ctx = UserContext(user_id="u", metrics={}, age=40, gender="male")
    assert ctx.age == 40
    assert ctx.gender == "male"


def test_registry_is_singleton():
    assert get_registry() is get_registry()


def test_registry_evaluate_all_returns_rule_results():
    registry = get_registry()
    ctx = UserContext(
        user_id="u",
        metrics={
            "ldl": MetricData(name="ldl", value=200, unit="mg/dL"),
            "hba1c": MetricData(name="hba1c", value=7.0, unit="%"),
        },
    )

    results = registry.evaluate_all(ctx)
    assert results, "Expected at least one rule to trigger"
    assert all(r.id and r.title for r in results)


def test_ldl_rule_severity_thresholds():
    rule = LDLHighRule()

    # Below trigger threshold
    ctx = UserContext(user_id="u", metrics={"ldl": MetricData(name="ldl", value=120, unit="mg/dL")})
    assert rule.evaluate(ctx) is None

    # Borderline high => INFO (130-159)
    ctx = UserContext(user_id="u", metrics={"ldl": MetricData(name="ldl", value=140, unit="mg/dL")})
    assert rule.evaluate(ctx).severity == Severity.INFO

    # High => WARNING (>=160)
    ctx = UserContext(user_id="u", metrics={"ldl": MetricData(name="ldl", value=170, unit="mg/dL")})
    assert rule.evaluate(ctx).severity == Severity.WARNING

    # Very high => URGENT (>=190)
    ctx = UserContext(user_id="u", metrics={"ldl": MetricData(name="ldl", value=200, unit="mg/dL")})
    assert rule.evaluate(ctx).severity == Severity.URGENT


def test_hdl_low_rule_triggers_and_sets_reference_min():
    rule = HDLLowRule()
    ctx = UserContext(user_id="u", metrics={"hdl": MetricData(name="hdl", value=30, unit="mg/dL")})
    res = rule.evaluate(ctx)
    assert res is not None
    assert res.reference_min == 40


def test_hba1c_rule_warning_and_urgent():
    rule = HbA1cHighRule()

    ctx = UserContext(user_id="u", metrics={"hba1c": MetricData(name="hba1c", value=6.0, unit="%")})
    assert rule.evaluate(ctx).severity == Severity.WARNING

    ctx = UserContext(user_id="u", metrics={"hba1c": MetricData(name="hba1c", value=7.0, unit="%")})
    assert rule.evaluate(ctx).severity == Severity.URGENT


def test_vitamin_d_rule_triggers_below_30():
    rule = VitaminDLowRule()
    ctx = UserContext(user_id="u", metrics={"vitamin_d": MetricData(name="vitamin_d", value=18, unit="ng/mL")})
    assert rule.evaluate(ctx) is not None


def test_bp_high_rule_stage1_and_crisis():
    rule = BPHighRule()
    ctx = UserContext(
        user_id="u",
        metrics={
            "systolic_bp": MetricData(name="systolic_bp", value=135, unit="mmHg"),
            "diastolic_bp": MetricData(name="diastolic_bp", value=85, unit="mmHg"),
        },
    )
    assert rule.evaluate(ctx) is not None

    ctx = UserContext(
        user_id="u",
        metrics={
            "systolic_bp": MetricData(name="systolic_bp", value=185, unit="mmHg"),
            "diastolic_bp": MetricData(name="diastolic_bp", value=125, unit="mmHg"),
        },
    )
    assert rule.evaluate(ctx).severity == Severity.URGENT


def test_sleep_low_rule_triggers_below_7_hours():
    rule = SleepLowRule()
    ctx = UserContext(user_id="u", metrics={"sleep_hours": MetricData(name="sleep_hours", value=5.5, unit="hours")})
    assert rule.evaluate(ctx) is not None


def test_missing_tests_rule_triggers_when_no_metrics():
    rule = MissingTestsRule()
    ctx = UserContext(user_id="u", metrics={})
    assert rule.evaluate(ctx) is not None

