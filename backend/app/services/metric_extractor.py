"""
Metric Extraction Service - REGEX-based Structured Data Extraction

Extracts health metrics from OCR text using pattern matching.
Handles:
- Metric name recognition (synonyms mapping)
- Numeric value extraction with units
- Reference range parsing
- Unit normalization
- Missing parameter detection

Author: Lumea Health Platform
"""
import re
import logging
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ExtractedMetric:
    """Single extracted metric from OCR text"""
    metric_key: str  # Canonical key (e.g., "hemoglobin")
    display_name: str  # Original name from report
    value: float
    unit: str
    reference_min: Optional[float] = None
    reference_max: Optional[float] = None
    flag: Optional[str] = None  # Low/High/Normal/Critical
    is_abnormal: bool = False
    confidence: float = 1.0
    raw_line: str = ""
    page_num: int = 1
    source: str = "regex"  # regex/grok/manual


@dataclass
class ExtractionResult:
    """Result of metric extraction from a document"""
    metrics: List[ExtractedMetric]
    extraction_confidence: float
    unrecognized_lines: List[str]  # Lines that looked like metrics but weren't matched
    warnings: List[str]


@dataclass  
class MissingParameter:
    """Represents a required parameter that was not extracted"""
    metric_key: str
    label: str  # Human-readable label
    expected_unit: str
    required: bool = True


# ============================================================================
# METRIC DEFINITIONS
# ============================================================================

# Comprehensive metric synonyms (canonical_key -> list of variations)
METRIC_SYNONYMS: Dict[str, List[str]] = {
    # Hematology / CBC
    "hemoglobin": ["hemoglobin", "hb", "hgb", "haemoglobin", "hb%", "hemoglobin hb"],
    "hematocrit": ["hematocrit", "hct", "haematocrit", "pcv", "packed cell volume"],
    "wbc_total": ["total wbc count", "wbc", "white blood cell count", "white cell count", 
                  "leucocyte count", "wbc count", "total wbc", "total leucocyte count", "tlc"],
    "rbc_count": ["total rbc count", "rbc", "red blood cell count", "red cell count", 
                  "erythrocyte count", "rbc count", "total rbc"],
    "platelet_count": ["platelet count", "platelets", "plt", "thrombocyte count", "platelet"],
    "mcv": ["mcv", "mean corpuscular volume", "mean cell volume"],
    "mch": ["mch", "mean corpuscular hemoglobin", "mean corpuscular haemoglobin", "mean cell hemoglobin"],
    "mchc": ["mchc", "mean corpuscular hemoglobin concentration", 
             "mean corpuscular haemoglobin concentration", "mean cell hemoglobin concentration"],
    "rdw": ["rdw", "red cell distribution width", "rdw-cv", "rdw-sd", 
            "red blood cell distribution width"],
    "mpv": ["mpv", "mean platelet volume"],
    "pdw": ["pdw", "platelet distribution width"],
    "pct": ["pct", "plateletcrit", "platelet hematocrit"],
    
    # WBC Differential
    "neutrophils": ["neutrophils", "neutrophil", "absolute neutrophil count", "anc", 
                    "neutrophil %", "neutrophil percent", "neutrophils %"],
    "lymphocytes": ["lymphocytes", "lymphocyte", "absolute lymphocyte count", "alc", 
                    "lymphocyte %", "lymphocyte percent", "lymphocytes %"],
    "monocytes": ["monocytes", "monocyte", "monocyte %", "monocyte percent", "monocytes %"],
    "eosinophils": ["eosinophils", "eosinophil", "eosinophil %", "eosinophil percent", "eosinophils %"],
    "basophils": ["basophils", "basophil", "basophil %", "basophil percent", "basophils %"],
    "nlr": ["nlr", "neutrophil lymphocyte ratio", "n/l ratio", "neutrophil-lymphocyte ratio"],
    
    # Coagulation
    "esr": ["esr", "erythrocyte sedimentation rate", "sed rate"],
    "pt": ["pt", "prothrombin time", "pro time"],
    "inr": ["inr", "international normalized ratio"],
    "aptt": ["aptt", "activated partial thromboplastin time", "ptt", "partial thromboplastin time"],
    
    # Kidney Function
    "creatinine": ["creatinine", "creat", "serum creatinine", "s. creatinine"],
    "urea": ["urea", "blood urea", "bun", "blood urea nitrogen", "serum urea"],
    "uric_acid": ["uric acid", "urate", "serum uric acid"],
    "egfr": ["egfr", "estimated gfr", "glomerular filtration rate", "gfr"],
    
    # Electrolytes
    "sodium": ["sodium", "na", "serum sodium", "na+"],
    "potassium": ["potassium", "k", "serum potassium", "k+"],
    "chloride": ["chloride", "cl", "serum chloride", "cl-"],
    "calcium": ["calcium", "ca", "serum calcium", "ca++", "total calcium"],
    "phosphorus": ["phosphorus", "phosphate", "serum phosphorus", "inorganic phosphorus"],
    "magnesium": ["magnesium", "mg", "serum magnesium"],
    "bicarbonate": ["bicarbonate", "hco3", "co2", "total co2"],
    
    # Glucose / Diabetes
    "glucose": ["glucose", "blood glucose", "fasting glucose", "fasting blood sugar", 
                "fbs", "blood sugar", "fasting plasma glucose", "fpg"],
    "glucose_pp": ["pp glucose", "post prandial glucose", "ppbs", "post prandial blood sugar",
                   "2hr pp glucose", "2 hour glucose"],
    "glucose_random": ["random glucose", "random blood sugar", "rbs", "random plasma glucose"],
    "hba1c": ["hba1c", "hemoglobin a1c", "glycated hemoglobin", "glycosylated hemoglobin", 
              "hb a1c", "a1c", "glycohemoglobin"],
    
    # Lipid Panel
    "cholesterol_total": ["total cholesterol", "cholesterol", "serum cholesterol", "t. cholesterol"],
    "hdl": ["hdl", "hdl cholesterol", "hdl-c", "high density lipoprotein"],
    "ldl": ["ldl", "ldl cholesterol", "ldl-c", "low density lipoprotein"],
    "vldl": ["vldl", "vldl cholesterol", "vldl-c", "very low density lipoprotein"],
    "triglycerides": ["triglycerides", "tg", "serum triglycerides", "trigs"],
    "non_hdl_cholesterol": ["non-hdl cholesterol", "non hdl", "non-hdl-c"],
    
    # Thyroid
    "tsh": ["tsh", "thyroid stimulating hormone", "thyrotropin"],
    "t3": ["t3", "triiodothyronine", "total t3"],
    "t4": ["t4", "thyroxine", "total t4"],
    "ft3": ["ft3", "free t3", "free triiodothyronine"],
    "ft4": ["ft4", "free t4", "free thyroxine"],
    
    # Liver Function
    "ast": ["ast", "sgot", "aspartate aminotransferase", "aspartate transaminase"],
    "alt": ["alt", "sgpt", "alanine aminotransferase", "alanine transaminase"],
    "alp": ["alp", "alkaline phosphatase", "alk phos"],
    "ggt": ["ggt", "gamma gt", "gamma glutamyl transferase", "gamma glutamyl transpeptidase", "ggtp"],
    "bilirubin_total": ["total bilirubin", "bilirubin", "serum bilirubin", "t. bilirubin"],
    "bilirubin_direct": ["direct bilirubin", "conjugated bilirubin", "d. bilirubin"],
    "bilirubin_indirect": ["indirect bilirubin", "unconjugated bilirubin"],
    "albumin": ["albumin", "serum albumin", "alb"],
    "globulin": ["globulin", "serum globulin"],
    "total_protein": ["total protein", "serum protein", "t. protein"],
    "ag_ratio": ["a/g ratio", "albumin globulin ratio", "a:g ratio"],
    
    # Vitamins & Minerals
    "vitamin_d": ["vitamin d", "25-oh vitamin d", "vitamin d3", "25-hydroxyvitamin d", 
                  "25-oh-d", "cholecalciferol"],
    "vitamin_b12": ["vitamin b12", "cobalamin", "b12", "cyanocobalamin"],
    "folate": ["folate", "folic acid", "vitamin b9", "serum folate"],
    "iron": ["iron", "serum iron", "fe"],
    "ferritin": ["ferritin", "serum ferritin"],
    "tibc": ["tibc", "total iron binding capacity"],
    "transferrin": ["transferrin", "serum transferrin"],
    "transferrin_saturation": ["transferrin saturation", "tsat", "iron saturation", "% saturation"],
    
    # Vital Signs
    "systolic_bp": ["systolic", "systolic bp", "systolic blood pressure", "sbp"],
    "diastolic_bp": ["diastolic", "diastolic bp", "diastolic blood pressure", "dbp"],
    "heart_rate": ["heart rate", "pulse", "pulse rate", "hr", "bpm"],
    "respiratory_rate": ["respiratory rate", "rr", "breathing rate", "resp rate"],
    "temperature": ["temperature", "temp", "body temperature"],
    "spo2": ["spo2", "oxygen saturation", "o2 sat", "pulse ox"],
    
    # Body Measurements
    "weight": ["weight", "body weight"],
    "height": ["height", "body height", "stature"],
    "bmi": ["bmi", "body mass index"],
    "waist": ["waist", "waist circumference", "waist circ"],
}

# Reverse mapping for quick lookup
NAME_TO_KEY: Dict[str, str] = {}
for key, synonyms in METRIC_SYNONYMS.items():
    for syn in synonyms:
        NAME_TO_KEY[syn.lower()] = key


# Expected units for each metric (for validation and normalization)
METRIC_UNITS: Dict[str, str] = {
    "hemoglobin": "g/dL",
    "hematocrit": "%",
    "wbc_total": "thou/µL",
    "rbc_count": "mil/µL",
    "platelet_count": "thou/µL",
    "mcv": "fL",
    "mch": "pg",
    "mchc": "g/dL",
    "rdw": "%",
    "mpv": "fL",
    "neutrophils": "%",
    "lymphocytes": "%",
    "monocytes": "%",
    "eosinophils": "%",
    "basophils": "%",
    "esr": "mm/hr",
    "creatinine": "mg/dL",
    "urea": "mg/dL",
    "uric_acid": "mg/dL",
    "egfr": "mL/min/1.73m²",
    "sodium": "mEq/L",
    "potassium": "mEq/L",
    "chloride": "mEq/L",
    "calcium": "mg/dL",
    "phosphorus": "mg/dL",
    "magnesium": "mg/dL",
    "glucose": "mg/dL",
    "glucose_pp": "mg/dL",
    "glucose_random": "mg/dL",
    "hba1c": "%",
    "cholesterol_total": "mg/dL",
    "hdl": "mg/dL",
    "ldl": "mg/dL",
    "vldl": "mg/dL",
    "triglycerides": "mg/dL",
    "tsh": "µIU/mL",
    "t3": "ng/dL",
    "t4": "µg/dL",
    "ft3": "pg/mL",
    "ft4": "ng/dL",
    "ast": "U/L",
    "alt": "U/L",
    "alp": "U/L",
    "ggt": "U/L",
    "bilirubin_total": "mg/dL",
    "bilirubin_direct": "mg/dL",
    "albumin": "g/dL",
    "globulin": "g/dL",
    "total_protein": "g/dL",
    "vitamin_d": "ng/mL",
    "vitamin_b12": "pg/mL",
    "folate": "ng/mL",
    "iron": "µg/dL",
    "ferritin": "ng/mL",
    "tibc": "µg/dL",
    "systolic_bp": "mmHg",
    "diastolic_bp": "mmHg",
    "heart_rate": "bpm",
    "spo2": "%",
    "weight": "kg",
    "height": "cm",
    "bmi": "kg/m²",
}

# Reference ranges (simplified, for flagging)
REFERENCE_RANGES: Dict[str, Tuple[Optional[float], Optional[float]]] = {
    "hemoglobin": (12.0, 17.5),
    "hematocrit": (36.0, 54.0),
    "wbc_total": (4.0, 11.0),
    "rbc_count": (4.0, 6.0),
    "platelet_count": (150, 400),
    "mcv": (80, 100),
    "mch": (27, 33),
    "mchc": (32, 36),
    "rdw": (11.5, 14.5),
    "glucose": (70, 100),
    "glucose_pp": (70, 140),
    "hba1c": (4.0, 5.6),
    "cholesterol_total": (None, 200),
    "hdl": (40, None),
    "ldl": (None, 100),
    "triglycerides": (None, 150),
    "creatinine": (0.6, 1.2),
    "urea": (7, 20),
    "egfr": (90, None),
    "sodium": (136, 145),
    "potassium": (3.5, 5.0),
    "tsh": (0.4, 4.0),
    "ast": (None, 40),
    "alt": (None, 40),
    "alp": (44, 147),
    "bilirubin_total": (0.1, 1.2),
    "vitamin_d": (30, 100),
    "vitamin_b12": (200, 900),
    "ferritin": (20, 500),
    "systolic_bp": (90, 120),
    "diastolic_bp": (60, 80),
    "bmi": (18.5, 24.9),
}

# Human-readable labels for metrics
METRIC_LABELS: Dict[str, str] = {
    "hemoglobin": "Hemoglobin",
    "hematocrit": "Hematocrit",
    "wbc_total": "White Blood Cell Count",
    "rbc_count": "Red Blood Cell Count",
    "platelet_count": "Platelet Count",
    "glucose": "Fasting Glucose",
    "glucose_pp": "Post-Prandial Glucose",
    "hba1c": "HbA1c",
    "cholesterol_total": "Total Cholesterol",
    "hdl": "HDL Cholesterol",
    "ldl": "LDL Cholesterol",
    "triglycerides": "Triglycerides",
    "creatinine": "Creatinine",
    "egfr": "eGFR",
    "tsh": "TSH",
    "vitamin_d": "Vitamin D",
    "vitamin_b12": "Vitamin B12",
    "ferritin": "Ferritin",
    "ast": "AST (SGOT)",
    "alt": "ALT (SGPT)",
}


# ============================================================================
# REQUIRED PARAMETERS BY DOCUMENT TYPE
# ============================================================================

REQUIRED_BY_DOC_TYPE: Dict[str, List[str]] = {
    "blood_panel": [
        "hemoglobin",
        "wbc_total",
        "platelet_count",
        "rbc_count",
    ],
    "lipid_panel": [
        "cholesterol_total",
        "ldl",
        "hdl",
        "triglycerides",
    ],
    "checkup": [
        "systolic_bp",
        "diastolic_bp",
        "heart_rate",
    ],
    "diabetes_panel": [
        "glucose",
        "hba1c",
    ],
    "kidney_panel": [
        "creatinine",
        "urea",
        "egfr",
    ],
    "liver_panel": [
        "ast",
        "alt",
        "bilirubin_total",
        "albumin",
    ],
    "thyroid_panel": [
        "tsh",
        "ft3",
        "ft4",
    ],
}

# Optional but recommended parameters
OPTIONAL_BY_DOC_TYPE: Dict[str, List[str]] = {
    "blood_panel": [
        "hematocrit",
        "mcv",
        "mch",
        "mchc",
        "rdw",
        "neutrophils",
        "lymphocytes",
    ],
    "lipid_panel": [
        "vldl",
        "non_hdl_cholesterol",
    ],
}


# ============================================================================
# UNIT NORMALIZATION
# ============================================================================

UNIT_NORMALIZATIONS: Dict[str, str] = {
    # mg/dL variants
    "mg/dl": "mg/dL",
    "mg/ dl": "mg/dL",
    "mg /dl": "mg/dL",
    "mgdl": "mg/dL",
    "mg%": "mg/dL",
    
    # g/dL variants
    "g/dl": "g/dL",
    "g/ dl": "g/dL",
    "gm/dl": "g/dL",
    "gm%": "g/dL",
    
    # µL variants
    "ul": "µL",
    "/ul": "/µL",
    "cmm": "µL",
    "/cumm": "/µL",
    "/cmm": "/µL",
    "cells/ul": "cells/µL",
    
    # thou/µL variants
    "thou/ul": "thou/µL",
    "x10^3/ul": "thou/µL",
    "10^3/ul": "thou/µL",
    "k/ul": "thou/µL",
    "thou/cmm": "thou/µL",
    "x10*3/ul": "thou/µL",
    
    # mil/µL variants
    "mil/ul": "mil/µL",
    "x10^6/ul": "mil/µL",
    "10^6/ul": "mil/µL",
    "m/ul": "mil/µL",
    "mil/cmm": "mil/µL",
    
    # fL variants
    "fl": "fL",
    "femtolitre": "fL",
    "femtoliter": "fL",
    
    # pg variants
    "picogram": "pg",
    "picogramme": "pg",
    
    # Time
    "sec": "seconds",
    "secs": "seconds",
    "s": "seconds",
    
    # Other
    "mm/hr": "mm/hr",
    "mm/hour": "mm/hr",
    "mmhg": "mmHg",
    "mm hg": "mmHg",
    "u/l": "U/L",
    "iu/l": "IU/L",
    "miu/ml": "µIU/mL",
    "uiu/ml": "µIU/mL",
    "ng/ml": "ng/mL",
    "pg/ml": "pg/mL",
    "ug/dl": "µg/dL",
    "meq/l": "mEq/L",
    "mmol/l": "mmol/L",
}


def normalize_unit(unit: str) -> str:
    """Normalize unit string to standard form."""
    if not unit:
        return ""
    
    unit_lower = unit.strip().lower()
    return UNIT_NORMALIZATIONS.get(unit_lower, unit.strip())


# ============================================================================
# METRIC EXTRACTOR CLASS
# ============================================================================

class MetricExtractor:
    """
    REGEX-based metric extractor for lab reports.
    
    Extracts structured metrics from OCR text by:
    1. Pattern matching test names
    2. Extracting numeric values and units
    3. Parsing reference ranges
    4. Flagging abnormal values
    """
    
    # Pattern for matching lab lines: TEST NAME ... VALUE UNIT ... REF RANGE
    # This handles various formats found in lab reports
    LAB_LINE_PATTERNS = [
        # Format: Test Name | Value | Unit | Reference Range
        r'^([A-Za-z][A-Za-z\s\-\.\/\(\)0-9]*?)\s*[:\|\s]\s*([<>]?\s*[\d,]+\.?\d*)\s*([a-zA-Z\/%µμ\*\^0-9\/]+)?\s*(?:[\|\s]\s*)?(?:[\(\[]?\s*([\d\.\-<>\s]+)\s*[\)\]]?)?',
        
        # Format: Test Name: Value Unit (Range: low-high)
        r'^([A-Za-z][A-Za-z\s\-\.\/\(\)]*?)\s*:\s*([<>]?\s*[\d,]+\.?\d*)\s*([a-zA-Z\/%µμ]+)?\s*(?:\(?\s*(?:range|ref|normal)\s*:\s*)?([\d\.\-<>\s]+)?',
        
        # Format: Value Unit next to Test Name  
        r'^([A-Za-z][A-Za-z\s\-\.]*?)\s+([<>]?\d+\.?\d*)\s*([a-zA-Z\/%µμ]+)',
    ]
    
    def __init__(self):
        self.name_to_key = NAME_TO_KEY
        self.metric_units = METRIC_UNITS
        self.reference_ranges = REFERENCE_RANGES
        self.metric_labels = METRIC_LABELS
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for extraction."""
        # Replace common OCR errors
        text = text.replace('|', ' ')
        text = text.replace('\t', ' ')
        
        # Normalize whitespace
        text = re.sub(r' +', ' ', text)
        
        return text
    
    def _extract_number(self, text: str) -> Optional[float]:
        """Extract first number from text, handling commas."""
        text = text.replace(',', '')
        match = re.search(r'[<>]?\s*([\d]+\.?\d*)', text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None
    
    def _parse_reference_range(self, text: str) -> Tuple[Optional[float], Optional[float]]:
        """Parse reference range like '13.0-17.0' or '<5.0' or '>100'."""
        if not text:
            return None, None
        
        text = text.strip().replace(',', '')
        
        # Pattern: low-high (e.g., "13.0-17.0", "13.0 - 17.0")
        match = re.search(r'([\d.]+)\s*[-–]\s*([\d.]+)', text)
        if match:
            try:
                return float(match.group(1)), float(match.group(2))
            except ValueError:
                pass
        
        # Pattern: <value (e.g., "<5.0")
        match = re.search(r'<\s*([\d.]+)', text)
        if match:
            try:
                return None, float(match.group(1))
            except ValueError:
                pass
        
        # Pattern: >value (e.g., ">100")
        match = re.search(r'>\s*([\d.]+)', text)
        if match:
            try:
                return float(match.group(1)), None
            except ValueError:
                pass
        
        return None, None
    
    def _normalize_metric_name(self, name: str) -> Optional[str]:
        """Map test name to canonical key."""
        name_lower = name.lower().strip()
        
        # Remove common prefixes/suffixes
        name_lower = re.sub(r'^(serum|plasma|blood|total)\s+', '', name_lower)
        name_lower = re.sub(r'\s+(level|count|test|result)$', '', name_lower)
        
        # Direct lookup
        if name_lower in self.name_to_key:
            return self.name_to_key[name_lower]
        
        # Fuzzy matching - check if any synonym is contained
        for synonym, key in self.name_to_key.items():
            if synonym in name_lower or name_lower in synonym:
                return key
        
        return None
    
    def _determine_flag(
        self, 
        value: float, 
        metric_key: str,
        ref_min: Optional[float] = None,
        ref_max: Optional[float] = None
    ) -> Tuple[Optional[str], bool]:
        """
        Determine flag (Low/High/Normal) and is_abnormal status.
        Uses extracted ref range first, then falls back to default ranges.
        """
        # Use extracted reference range if available
        if ref_min is None and ref_max is None:
            # Fall back to default ranges
            defaults = self.reference_ranges.get(metric_key, (None, None))
            ref_min, ref_max = defaults
        
        if ref_min is None and ref_max is None:
            return None, False
        
        if ref_min is not None and value < ref_min:
            # Check if critically low
            if ref_min > 0 and value < ref_min * 0.7:
                return "Critical Low", True
            return "Low", True
        
        if ref_max is not None and value > ref_max:
            # Check if critically high
            if value > ref_max * 1.5:
                return "Critical High", True
            return "High", True
        
        return "Normal", False
    
    def extract_metrics(
        self, 
        ocr_text: str, 
        page_num: int = 1
    ) -> ExtractionResult:
        """
        Extract structured metrics from OCR text.
        
        Args:
            ocr_text: Raw OCR text from document
            page_num: Page number for tracking
        
        Returns:
            ExtractionResult with extracted metrics, confidence, and warnings
        """
        metrics: List[ExtractedMetric] = []
        unrecognized: List[str] = []
        warnings: List[str] = []
        
        # Normalize text
        text = self._normalize_text(ocr_text)
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            # Skip header/footer lines
            if re.match(r'^(page|date|patient|name|id|report|lab)', line.lower()):
                continue
            
            # Try each pattern
            extracted = False
            for pattern in self.LAB_LINE_PATTERNS:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    
                    test_name = groups[0].strip() if groups[0] else None
                    value_str = groups[1].strip() if len(groups) > 1 and groups[1] else None
                    unit = groups[2].strip() if len(groups) > 2 and groups[2] else None
                    ref_range = groups[3].strip() if len(groups) > 3 and groups[3] else None
                    
                    if not test_name or not value_str:
                        continue
                    
                    # Map to canonical key
                    metric_key = self._normalize_metric_name(test_name)
                    if not metric_key:
                        # Track unrecognized but potentially valid lines
                        value = self._extract_number(value_str)
                        if value is not None:
                            unrecognized.append(line)
                        continue
                    
                    # Extract numeric value
                    value = self._extract_number(value_str)
                    if value is None:
                        warnings.append(f"Could not extract numeric value from: {line}")
                        continue
                    
                    # Normalize unit
                    unit = normalize_unit(unit) if unit else self.metric_units.get(metric_key, "")
                    
                    # Parse reference range
                    ref_min, ref_max = self._parse_reference_range(ref_range) if ref_range else (None, None)
                    
                    # Determine flag
                    flag, is_abnormal = self._determine_flag(value, metric_key, ref_min, ref_max)
                    
                    # Create metric
                    metric = ExtractedMetric(
                        metric_key=metric_key,
                        display_name=test_name,
                        value=value,
                        unit=unit,
                        reference_min=ref_min,
                        reference_max=ref_max,
                        flag=flag,
                        is_abnormal=is_abnormal,
                        confidence=0.9 if unit else 0.7,  # Lower confidence if unit missing
                        raw_line=line,
                        page_num=page_num,
                        source="regex"
                    )
                    
                    metrics.append(metric)
                    extracted = True
                    break
            
            # If no pattern matched but line looks like a metric
            if not extracted:
                # Check if line has numbers that might be metrics
                if re.search(r'\d+\.?\d*\s*(?:mg|g|%|/|u)', line, re.IGNORECASE):
                    unrecognized.append(line)
        
        # Calculate overall confidence
        if metrics:
            avg_confidence = sum(m.confidence for m in metrics) / len(metrics)
            # Boost confidence if many metrics found
            extraction_confidence = min(1.0, avg_confidence + (len(metrics) * 0.02))
        else:
            extraction_confidence = 0.0
        
        return ExtractionResult(
            metrics=metrics,
            extraction_confidence=round(extraction_confidence, 2),
            unrecognized_lines=unrecognized,
            warnings=warnings
        )
    
    def get_missing_parameters(
        self, 
        doc_type: str, 
        extracted_keys: Set[str]
    ) -> List[MissingParameter]:
        """
        Get list of required parameters that were not extracted.
        
        Args:
            doc_type: Document type (blood_panel, lipid_panel, etc.)
            extracted_keys: Set of metric keys that were successfully extracted
        
        Returns:
            List of MissingParameter objects for parameters that need manual entry
        """
        missing = []
        
        required = REQUIRED_BY_DOC_TYPE.get(doc_type, [])
        for metric_key in required:
            if metric_key not in extracted_keys:
                missing.append(MissingParameter(
                    metric_key=metric_key,
                    label=self.metric_labels.get(metric_key, metric_key.replace("_", " ").title()),
                    expected_unit=self.metric_units.get(metric_key, ""),
                    required=True
                ))
        
        return missing


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

# Global extractor instance
_extractor = MetricExtractor()


def extract_metrics_regex(ocr_text: str, page_num: int = 1) -> ExtractionResult:
    """
    Extract metrics from OCR text using regex patterns.
    
    Args:
        ocr_text: Raw OCR text from document
        page_num: Page number for tracking
    
    Returns:
        ExtractionResult with extracted metrics, confidence, and warnings
    
    Example:
        >>> result = extract_metrics_regex("Hemoglobin: 14.2 g/dL (12.0-17.0)")
        >>> print(result.metrics[0].metric_key)  # "hemoglobin"
        >>> print(result.metrics[0].value)  # 14.2
    """
    return _extractor.extract_metrics(ocr_text, page_num)


def get_missing_parameters(doc_type: str, extracted_keys: Set[str]) -> List[MissingParameter]:
    """
    Get list of required parameters that were not extracted.
    
    Args:
        doc_type: Document type (blood_panel, lipid_panel, etc.)
        extracted_keys: Set of metric keys that were successfully extracted
    
    Returns:
        List of MissingParameter objects for parameters that need manual entry
    """
    return _extractor.get_missing_parameters(doc_type, extracted_keys)


def get_metric_label(metric_key: str) -> str:
    """Get human-readable label for a metric key."""
    return METRIC_LABELS.get(metric_key, metric_key.replace("_", " ").title())


def get_expected_unit(metric_key: str) -> str:
    """Get expected unit for a metric key."""
    return METRIC_UNITS.get(metric_key, "")


# ============================================================================
# TESTING
# ============================================================================

def test_extractor():
    """Test the metric extractor with sample text."""
    sample_text = """
    COMPLETE BLOOD COUNT (CBC)
    
    Test Name                Result      Unit        Reference Range
    ================================================================
    Hemoglobin              14.2        g/dL        12.0 - 17.5
    Total WBC Count         7.5         thou/uL     4.0 - 11.0
    Total RBC Count         4.8         mil/uL      4.0 - 6.0
    Platelet Count          250         thou/uL     150 - 400
    Hematocrit              42.5        %           36 - 54
    MCV                     88          fL          80 - 100
    MCH                     29.5        pg          27 - 33
    MCHC                    33.4        g/dL        32 - 36
    RDW                     13.2        %           11.5 - 14.5
    
    DIFFERENTIAL COUNT
    Neutrophils             58          %           40 - 75
    Lymphocytes             32          %           20 - 45
    Monocytes               6           %           2 - 10
    Eosinophils             3           %           1 - 6
    Basophils               1           %           0 - 2
    
    GLUCOSE
    Fasting Blood Sugar     105         mg/dL       70 - 100
    """
    
    print("=" * 80)
    print("METRIC EXTRACTOR TEST")
    print("=" * 80)
    
    result = extract_metrics_regex(sample_text)
    
    print(f"\nExtracted {len(result.metrics)} metrics (confidence: {result.extraction_confidence})")
    print("\nMetrics:")
    for m in result.metrics:
        flag_str = f" [{m.flag}]" if m.flag and m.flag != "Normal" else ""
        print(f"  {m.metric_key}: {m.value} {m.unit}{flag_str}")
    
    if result.unrecognized_lines:
        print(f"\nUnrecognized lines: {len(result.unrecognized_lines)}")
        for line in result.unrecognized_lines[:5]:
            print(f"  - {line[:60]}...")
    
    if result.warnings:
        print(f"\nWarnings: {len(result.warnings)}")
        for w in result.warnings[:5]:
            print(f"  - {w}")
    
    # Test missing parameters
    extracted_keys = {m.metric_key for m in result.metrics}
    missing = get_missing_parameters("blood_panel", extracted_keys)
    print(f"\nMissing required parameters for blood_panel: {len(missing)}")
    for m in missing:
        print(f"  - {m.label} ({m.metric_key}) [{m.expected_unit}]")


if __name__ == "__main__":
    test_extractor()
