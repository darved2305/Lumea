"""
Physics Twin – deterministic organ scoring configuration.

Single source of truth for organ metrics, reference ranges, weights, and normalisation direction.
"""

from typing import Dict, List, Literal

# Direction: "lower_better" means lower raw value → higher normalised score
# Direction: "higher_better" means higher raw value → higher normalised score
MetricDirection = Literal["lower_better", "higher_better"]


class MetricSpec:
    """Specification for a single health metric used in organ scoring."""

    def __init__(
        self,
        name: str,
        unit: str,
        ref_min: float,
        ref_max: float,
        abs_min: float,
        abs_max: float,
        weight: float,
        direction: MetricDirection = "lower_better",
    ):
        self.name = name
        self.unit = unit
        self.ref_min = ref_min      # healthy-range lower bound
        self.ref_max = ref_max      # healthy-range upper bound
        self.abs_min = abs_min      # absolute physiological minimum
        self.abs_max = abs_max      # absolute physiological maximum
        self.weight = weight
        self.direction = direction

    def normalise(self, value: float) -> float:
        """Return 0-1 score (1 = ideal) for a raw metric value."""
        # Clamp into absolute range
        clamped = max(self.abs_min, min(self.abs_max, value))

        # Inside reference range → perfect score
        if self.ref_min <= clamped <= self.ref_max:
            return 1.0

        # Outside reference range → linear decay to 0 at absolute boundary
        if clamped < self.ref_min:
            span = self.ref_min - self.abs_min
            if span == 0:
                return 0.0
            return max(0.0, (clamped - self.abs_min) / span)
        else:
            span = self.abs_max - self.ref_max
            if span == 0:
                return 0.0
            return max(0.0, 1.0 - (clamped - self.ref_max) / span)


# ---------------------------------------------------------------------------
# Organ configurations
# ---------------------------------------------------------------------------

ORGAN_METRICS: Dict[str, List[MetricSpec]] = {
    "kidney": [
        MetricSpec("creatinine",  "mg/dL",  0.6, 1.2,   0.2,  8.0,  weight=0.25, direction="lower_better"),
        MetricSpec("urea",        "mg/dL",  7.0, 20.0,  2.0,  80.0, weight=0.20, direction="lower_better"),
        MetricSpec("egfr",        "mL/min", 90.0, 120.0, 15.0, 150.0, weight=0.25, direction="higher_better"),
        MetricSpec("sodium",      "mEq/L",  136.0, 145.0, 120.0, 160.0, weight=0.10),
        MetricSpec("potassium",   "mEq/L",  3.5, 5.0, 2.5, 7.0, weight=0.05),
        MetricSpec("systolic_bp", "mmHg",   90.0, 120.0, 60.0, 200.0, weight=0.15, direction="lower_better"),
    ],
    "heart": [
        MetricSpec("heart_rate",    "bpm",   60.0, 100.0, 30.0, 200.0, weight=0.25),
        MetricSpec("systolic_bp",  "mmHg",  90.0, 120.0, 60.0, 200.0, weight=0.25, direction="lower_better"),
        MetricSpec("diastolic_bp", "mmHg",  60.0, 80.0,  30.0, 130.0, weight=0.20, direction="lower_better"),
        MetricSpec("spo2",         "%",     95.0, 100.0, 70.0, 100.0, weight=0.15, direction="higher_better"),
        MetricSpec("cholesterol_total", "mg/dL", 0.0, 200.0, 0.0, 400.0, weight=0.10, direction="lower_better"),
        MetricSpec("triglycerides", "mg/dL", 0.0, 150.0, 0.0, 500.0, weight=0.05, direction="lower_better"),
    ],
    "liver": [
        MetricSpec("alt",             "U/L",   7.0,  56.0,  0.0, 300.0, weight=0.25, direction="lower_better"),
        MetricSpec("ast",             "U/L",   10.0, 40.0,  0.0, 300.0, weight=0.25, direction="lower_better"),
        MetricSpec("bilirubin_total", "mg/dL",  0.1,  1.2,  0.0,  15.0, weight=0.15, direction="lower_better"),
        MetricSpec("albumin",         "g/dL",  3.5,  5.5,  1.0,  7.0,  weight=0.15, direction="higher_better"),
        MetricSpec("alp",             "U/L",   44.0, 147.0, 0.0, 500.0, weight=0.10, direction="lower_better"),
        MetricSpec("total_protein",   "g/dL",  6.0,  8.3,  3.0,  12.0, weight=0.10, direction="higher_better"),
    ],
    "lungs": [
        MetricSpec("spo2",             "%",     95.0, 100.0, 70.0, 100.0, weight=0.50, direction="higher_better"),
        MetricSpec("respiratory_rate", "bpm",   12.0, 20.0,  6.0,  40.0, weight=0.30),
        MetricSpec("hemoglobin",       "g/dL",  12.0, 17.5,  5.0,  22.0, weight=0.20, direction="higher_better"),
    ],
    "brain": [
        MetricSpec("sleep_hours",   "hrs",   7.0, 9.0, 0.0, 16.0, weight=0.30, direction="higher_better"),
        MetricSpec("stress_level",  "score", 0.0, 3.0, 0.0, 10.0, weight=0.25, direction="lower_better"),
        MetricSpec("glucose",       "mg/dL", 70.0, 100.0, 30.0, 400.0, weight=0.20),
        MetricSpec("systolic_bp",   "mmHg",  90.0, 120.0, 60.0, 200.0, weight=0.15, direction="lower_better"),
        MetricSpec("tsh",           "µIU/mL", 0.4, 4.0, 0.01, 50.0, weight=0.10),
    ],
    "blood": [
        MetricSpec("hemoglobin",    "g/dL",    12.0, 17.5,  5.0,  22.0,  weight=0.25, direction="higher_better"),
        MetricSpec("wbc_total",     "thou/µL", 4.0,  11.0,  1.0,  30.0,  weight=0.15),
        MetricSpec("platelet_count","thou/µL", 150.0, 400.0, 50.0, 800.0, weight=0.15),
        MetricSpec("rbc_count",     "mil/µL",  4.0,  6.0,  2.0,  8.0,   weight=0.10, direction="higher_better"),
        MetricSpec("glucose",       "mg/dL",   70.0, 100.0, 30.0, 400.0, weight=0.10),
        MetricSpec("hba1c",         "%",       4.0,  5.7,  3.0,  14.0,  weight=0.15, direction="lower_better"),
        MetricSpec("ferritin",      "ng/mL",   20.0, 500.0, 5.0, 1500.0, weight=0.10, direction="higher_better"),
    ],
}

# Human-readable labels
ORGAN_LABELS: Dict[str, str] = {
    "kidney": "Kidney",
    "heart": "Heart",
    "liver": "Liver",
    "lungs": "Lungs",
    "brain": "Brain",
    "blood": "Blood",
}


def compute_organ_score(organ: str, metrics: Dict[str, float]) -> Dict:
    """
    Compute deterministic organ health score.

    Returns dict with:
      score          – 0-100 weighted score
      status         – "Healthy" | "Watch" | "Risk"
      coverage       – fraction of metrics present (0-1)
      contributions  – per-metric breakdown [{name, value, normalised, weight, weighted}]
    """
    specs = ORGAN_METRICS.get(organ, [])
    if not specs:
        return {"score": 0, "status": "Risk", "coverage": 0, "contributions": []}

    contributions = []
    total_weight = 0.0
    weighted_sum = 0.0
    present_count = 0

    for spec in specs:
        raw = metrics.get(spec.name)
        if raw is None:
            contributions.append({
                "name": spec.name,
                "unit": spec.unit,
                "value": None,
                "normalised": None,
                "weight": spec.weight,
                "weighted": None,
            })
            continue

        present_count += 1
        norm = spec.normalise(raw)
        w = spec.weight * norm
        total_weight += spec.weight
        weighted_sum += w

        contributions.append({
            "name": spec.name,
            "unit": spec.unit,
            "value": round(raw, 2),
            "normalised": round(norm, 4),
            "weight": spec.weight,
            "weighted": round(w, 4),
        })

    coverage = present_count / len(specs) if specs else 0
    score = (weighted_sum / total_weight * 100) if total_weight > 0 else 0
    score = round(score, 1)

    if score >= 75:
        status = "Healthy"
    elif score >= 50:
        status = "Watch"
    else:
        status = "Risk"

    return {
        "score": score,
        "status": status,
        "coverage": round(coverage, 2),
        "contributions": contributions,
    }


def compute_all_organs(metrics: Dict[str, float]) -> Dict:
    """Compute scores for all organs + an overall composite."""
    organ_scores = {}
    total = 0.0
    count = 0

    for organ in ORGAN_METRICS:
        result = compute_organ_score(organ, metrics)
        organ_scores[organ] = result
        if result["coverage"] > 0:
            total += result["score"]
            count += 1

    overall = round(total / count, 1) if count else 0.0
    if overall >= 75:
        overall_status = "Healthy"
    elif overall >= 50:
        overall_status = "Watch"
    else:
        overall_status = "Risk"

    return {
        "overall_score": overall,
        "overall_status": overall_status,
        "organs": organ_scores,
    }
