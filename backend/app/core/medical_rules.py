"""
Medical Inference Rules
-----------------------
This module contains standard medical reference ranges and inference rules
used to generate insights from extracted health data.

Note: These are general guidelines and should not replace professional medical advice.
Sources: WHO, ADA (Diabetes), AHA (Heart), CDC
"""

from typing import Dict, Any, List, Optional

# Standard reference ranges and interpretation rules
MEDICAL_INFERENCE_RULES: Dict[str, Dict[str, Any]] = {
    # Diabetes Markers
    "hba1c": {
        "name": "HbA1c",
        "unit": "%",
        "thresholds": [
            {"max": 5.7, "status": "Normal", "flag": "normal"},
            {"max": 6.4, "status": "Prediabetes", "flag": "warning"},
            {"max": 100.0, "status": "Diabetes", "flag": "critical"}
        ],
        "indicates": "Long-term blood sugar control",
        "icd10": "R73.9", # Hyperglycemia, unspecified
        "recommended_tests": ["fasting_glucose", "kidney_function_panel", "eye_exam"]
    },
    "fasting_glucose": {
        "name": "Fasting Glucose",
        "unit": "mg/dL",
        "thresholds": [
            {"max": 99, "status": "Normal", "flag": "normal"},
            {"max": 125, "status": "Prediabetes", "flag": "warning"},
            {"max": 1000, "status": "Diabetes", "flag": "critical"}
        ],
        "indicates": "Current blood sugar levels",
        "icd10": "R73.0", # Abnormal glucose
        "recommended_tests": ["hba1c"]
    },

    # Cholesterol / Lipid Panel
    "ldl_cholesterol": {
        "name": "LDL Cholesterol",
        "unit": "mg/dL",
        "thresholds": [
            {"max": 100, "status": "Optimal", "flag": "normal"},
            {"max": 129, "status": "Near Optimal", "flag": "normal"},
            {"max": 159, "status": "Borderline High", "flag": "warning"},
            {"max": 189, "status": "High", "flag": "warning"},
            {"max": 1000, "status": "Very High", "flag": "critical"}
        ],
        "indicates": "Bad cholesterol (heart disease risk)",
        "icd10": "E78.0", # Pure hypercholesterolemia
        "recommended_tests": ["lipid_panel", "hscrp"]
    },
    "total_cholesterol": {
        "name": "Total Cholesterol",
        "unit": "mg/dL",
        "thresholds": [
            {"max": 200, "status": "Desirable", "flag": "normal"},
            {"max": 239, "status": "Borderline High", "flag": "warning"},
            {"max": 1000, "status": "High", "flag": "critical"}
        ],
        "indicates": "Overall cholesterol health",
        "icd10": "E78.5", # Hyperlipidemia, unspecified
        "recommended_tests": ["lipid_panel"]
    },
    "triglycerides": {
        "name": "Triglycerides",
        "unit": "mg/dL",
        "thresholds": [
            {"max": 150, "status": "Normal", "flag": "normal"},
            {"max": 199, "status": "Borderline High", "flag": "warning"},
            {"max": 499, "status": "High", "flag": "warning"},
            {"max": 5000, "status": "Very High", "flag": "critical"}
        ],
        "indicates": "Fat in blood",
        "icd10": "E78.1", # Pure hyperglyceridemia
        "recommended_tests": ["fasting_glucose", "hba1c"]
    },

    # Thyroid Function
    "tsh": {
        "name": "TSH",
        "unit": "mIU/L",
        "thresholds": [
            {"max": 0.4, "status": "Low (Hyperthyroid risk)", "flag": "warning"},
            {"max": 4.0, "status": "Normal", "flag": "normal"},
            {"max": 100.0, "status": "High (Hypothyroid risk)", "flag": "warning"}
        ],
        "indicates": "Thyroid function",
        "icd10": "E07.9", # Disorder of thyroid, unspecified
        "recommended_tests": ["free_t4", "free_t3", "tpo_antibodies"]
    },

    # Blood Pressure
    "systolic_bp": {
        "name": "Systolic BP",
        "unit": "mmHg",
        "thresholds": [
            {"max": 120, "status": "Normal", "flag": "normal"},
            {"max": 129, "status": "Elevated", "flag": "warning"},
            {"max": 139, "status": "Hypertension Stage 1", "flag": "warning"},
            {"max": 180, "status": "Hypertension Stage 2", "flag": "critical"},
            {"max": 300, "status": "Hypertensive Crisis", "flag": "critical"}
        ],
        "indicates": "Pressure during heart beat",
        "icd10": "I10", # Essential (primary) hypertension
        "recommended_tests": ["kidney_function_panel", "ecg"]
    },
    "diastolic_bp": {
        "name": "Diastolic BP",
        "unit": "mmHg",
        "thresholds": [
            {"max": 80, "status": "Normal", "flag": "normal"},
            {"max": 89, "status": "Hypertension Stage 1", "flag": "warning"},
            {"max": 120, "status": "Hypertension Stage 2", "flag": "critical"},
            {"max": 200, "status": "Hypertensive Crisis", "flag": "critical"}
        ],
        "indicates": "Pressure between heart beats",
        "icd10": "I10",
        "recommended_tests": ["kidney_function_panel"]
    },

    # Kidney Function
    "creatinine": {
        "name": "Creatinine",
        "unit": "mg/dL",
        "thresholds": [
            {"max": 0.6, "status": "Low", "flag": "normal"},
            {"max": 1.2, "status": "Normal", "flag": "normal"},
            {"max": 20.0, "status": "High (Kidney concern)", "flag": "warning"}
        ],
        "indicates": "Kidney filtration efficiency",
        "icd10": "R79.89", # Other specified abnormal findings of blood chemistry
        "recommended_tests": ["bun", "egfr", "urinalysis"]
    },

    # Blood Count
    "hemoglobin": {
        "name": "Hemoglobin",
        "unit": "g/dL",
        "thresholds": [
            {"max": 12.0, "status": "Low (Anemia risk)", "flag": "warning"}, # Female floor
            {"max": 17.5, "status": "Normal", "flag": "normal"},
            {"max": 25.0, "status": "High", "flag": "warning"}
        ],
        "indicates": "Oxygen carrying capacity",
        "icd10": "D64.9", # Anemia, unspecified
        "recommended_tests": ["ferritin", "iron_panel", "vitamin_b12"]
    },

    # Vitamins
    "vitamin_d": {
        "name": "Vitamin D (25-OH)",
        "unit": "ng/mL",
        "thresholds": [
            {"max": 20, "status": "Deficient", "flag": "warning"},
            {"max": 30, "status": "Insufficient", "flag": "warning"},
            {"max": 100, "status": "Optimal", "flag": "normal"},
            {"max": 200, "status": "Potential Toxicity", "flag": "warning"}
        ],
        "indicates": "Bone health, immune function",
        "icd10": "E55.9", # Vitamin D deficiency, unspecified
        "recommended_tests": ["calcium", "parathyroid_hormone"]
    },
    "vitamin_b12": {
        "name": "Vitamin B12",
        "unit": "pg/mL",
        "thresholds": [
            {"max": 200, "status": "Deficient", "flag": "warning"},
            {"max": 900, "status": "Normal", "flag": "normal"},
            {"max": 2000, "status": "High", "flag": "normal"}
        ],
        "indicates": "Nerve health, red blood cell formation",
        "icd10": "E53.8", # Deficiency of other specified B group vitamins
        "recommended_tests": ["homocysteine", "methylmalonic_acid"]
    },

    # Liver Function
    "alt": {
        "name": "ALT (Alanine Aminotransferase)",
        "unit": "U/L",
        "thresholds": [
            {"max": 29, "status": "Normal", "flag": "normal"},
            {"max": 2000, "status": "High (Liver concern)", "flag": "warning"}
        ],
        "indicates": "Liver cell damage",
        "icd10": "R74.0", # Nonspecific elevation of levels of transaminase and lactic acid dehydrogenase
        "recommended_tests": ["ast", "alkaline_phosphatase", "bilirubin"]
    },
    "ast": {
        "name": "AST (Aspartate Aminotransferase)",
        "unit": "U/L",
        "thresholds": [
            {"max": 35, "status": "Normal", "flag": "normal"},
            {"max": 2000, "status": "High (Liver concern)", "flag": "warning"}
        ],
        "indicates": "Liver or tissue damage",
        "icd10": "R74.0",
        "recommended_tests": ["alt", "gamma_gt"]
    }
}

def analyze_metric(metric_name: str, value: float) -> Optional[Dict[str, Any]]:
    """
    Analyze a specific medical metric against known rules.
    Returns analysis dict or None if metric unknown.
    """
    key = metric_name.lower().replace(" ", "_").replace("-", "_")

    # Try direct match or partial match
    rule = None
    if key in MEDICAL_INFERENCE_RULES:
        rule = MEDICAL_INFERENCE_RULES[key]
    else:
        # Simple fuzzy match attempt
        for k, v in MEDICAL_INFERENCE_RULES.items():
            if k in key or key in k:
                rule = v
                break

    if not rule:
        return None

    # Evaluate thresholds
    status = "Unknown"
    flag = "unknown"

    # Find the first threshold that the value is less than or equal to
    # (Rules are ordered by max value)
    for threshold in rule["thresholds"]:
        if value <= threshold["max"]:
            status = threshold["status"]
            flag = threshold["flag"]
            break

    # Handle values above the highest threshold
    if status == "Unknown" and rule["thresholds"]:
         last = rule["thresholds"][-1]
         if value > last["max"]:
             status = last["status"]
             flag = last["flag"]

    return {
        "metric": rule["name"],
        "value": value,
        "unit": rule["unit"],
        "status": status,
        "flag": flag,
        "interpretation": f"{rule['name']} is {status} ({value} {rule['unit']}). indicates {rule['indicates']}.",
        "recommendation": f"Consider checking: {', '.join(rule['recommended_tests'])}" if flag != "normal" else None,
        "icd10_candidate": rule["icd10"] if flag != "normal" else None
    }
