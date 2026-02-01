"""
Lab Report Parser - Extracts metrics from lab report text

Handles typical lab report formats with columns:
TEST NAME | RESULT | UNIT | BIOLOGICAL REF RANGE | FLAG
"""
import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ParsedMetric:
    """Parsed lab metric"""
    test_name: str
    canonical_key: str
    value: float
    unit: str
    ref_range_low: Optional[float] = None
    ref_range_high: Optional[float] = None
    flag: Optional[str] = None
    page_num: int = 1
    raw_line: str = ""


class LabParser:
    """
    Parser for lab report tables
    """
    
    # Metric name synonyms (normalized_key -> list of variations)
    METRIC_SYNONYMS = {
        "hemoglobin": ["hemoglobin", "hb", "hgb", "haemoglobin", "hb%"],
        "hematocrit": ["hematocrit", "hct", "haematocrit", "pcv", "packed cell volume"],
        "wbc_total": ["total wbc count", "wbc", "white blood cell count", "white cell count", "leucocyte count", "wbc count", "total wbc"],
        "rbc_count": ["total rbc count", "rbc", "red blood cell count", "red cell count", "erythrocyte count", "rbc count", "total rbc"],
        "platelet_count": ["platelet count", "platelets", "plt", "thrombocyte count", "platelet"],
        "mcv": ["mcv", "mean corpuscular volume", "mean cell volume"],
        "mch": ["mch", "mean corpuscular hemoglobin", "mean corpuscular haemoglobin", "mean cell hemoglobin"],
        "mchc": ["mchc", "mean corpuscular hemoglobin concentration", "mean corpuscular haemoglobin concentration", "mean cell hemoglobin concentration"],
        "rdw": ["rdw", "red cell distribution width", "rdw-cv", "rdw-sd", "red blood cell distribution width"],
        "mpv": ["mpv", "mean platelet volume"],
        "pdw": ["pdw", "platelet distribution width"],
        "pct": ["pct", "plateletcrit", "platelet hematocrit"],
        "neutrophils": ["neutrophils", "neutrophil", "absolute neutrophil count", "anc", "neutrophil %", "neutrophil percent"],
        "lymphocytes": ["lymphocytes", "lymphocyte", "absolute lymphocyte count", "alc", "lymphocyte %", "lymphocyte percent"],
        "monocytes": ["monocytes", "monocyte", "monocyte %", "monocyte percent"],
        "eosinophils": ["eosinophils", "eosinophil", "eosinophil %", "eosinophil percent"],
        "basophils": ["basophils", "basophil", "basophil %", "basophil percent"],
        "nlr": ["nlr", "neutrophil lymphocyte ratio", "n/l ratio", "neutrophil-lymphocyte ratio"],
        "esr": ["esr", "erythrocyte sedimentation rate", "sed rate"],
        "pt": ["pt", "prothrombin time", "pro time"],
        "inr": ["inr", "international normalized ratio"],
        "aptt": ["aptt", "activated partial thromboplastin time", "ptt", "partial thromboplastin time"],
        "creatinine": ["creatinine", "creat", "serum creatinine"],
        "urea": ["urea", "blood urea", "bun", "blood urea nitrogen"],
        "uric_acid": ["uric acid", "urate"],
        "sodium": ["sodium", "na", "serum sodium"],
        "potassium": ["potassium", "k", "serum potassium"],
        "chloride": ["chloride", "cl", "serum chloride"],
        "calcium": ["calcium", "ca", "serum calcium"],
        "phosphorus": ["phosphorus", "phosphate", "serum phosphorus"],
        "magnesium": ["magnesium", "mg", "serum magnesium"],
        "glucose": ["glucose", "blood glucose", "fasting glucose", "fasting blood sugar", "fbs", "blood sugar"],
        "glucose_pp": ["pp glucose", "post prandial glucose", "ppbs", "post prandial blood sugar"],
        "glucose_random": ["random glucose", "random blood sugar", "rbs"],
        "hba1c": ["hba1c", "hemoglobin a1c", "glycated hemoglobin", "glycosylated hemoglobin", "hb a1c"],
        "cholesterol_total": ["total cholesterol", "cholesterol", "serum cholesterol"],
        "hdl": ["hdl", "hdl cholesterol", "hdl-c"],
        "ldl": ["ldl", "ldl cholesterol", "ldl-c"],
        "vldl": ["vldl", "vldl cholesterol", "vldl-c"],
        "triglycerides": ["triglycerides", "tg", "serum triglycerides"],
        "tsh": ["tsh", "thyroid stimulating hormone"],
        "t3": ["t3", "triiodothyronine", "total t3"],
        "t4": ["t4", "thyroxine", "total t4"],
        "ft3": ["ft3", "free t3", "free triiodothyronine"],
        "ft4": ["ft4", "free t4", "free thyroxine"],
        "ast": ["ast", "sgot", "aspartate aminotransferase", "aspartate transaminase"],
        "alt": ["alt", "sgpt", "alanine aminotransferase", "alanine transaminase"],
        "alp": ["alp", "alkaline phosphatase"],
        "ggt": ["ggt", "gamma gt", "gamma glutamyl transferase"],
        "bilirubin_total": ["total bilirubin", "bilirubin", "serum bilirubin"],
        "bilirubin_direct": ["direct bilirubin", "conjugated bilirubin"],
        "bilirubin_indirect": ["indirect bilirubin", "unconjugated bilirubin"],
        "albumin": ["albumin", "serum albumin"],
        "globulin": ["globulin", "serum globulin"],
        "total_protein": ["total protein", "serum protein"],
        "vitamin_d": ["vitamin d", "25-oh vitamin d", "vitamin d3", "25-hydroxyvitamin d"],
        "vitamin_b12": ["vitamin b12", "cobalamin", "b12"],
        "folate": ["folate", "folic acid", "vitamin b9"],
        "iron": ["iron", "serum iron"],
        "ferritin": ["ferritin", "serum ferritin"],
        "tibc": ["tibc", "total iron binding capacity"],
        "transferrin": ["transferrin", "serum transferrin"],
    }
    
    
    # Reverse mapping for quick lookup
    NAME_TO_KEY = {}
    for key, synonyms in METRIC_SYNONYMS.items():
        for syn in synonyms:
            NAME_TO_KEY[syn.lower()] = key
    
    # Unit normalizations
    UNIT_NORMALIZATIONS = {
        "mg/dl": "mg/dL",
        "mg/ dl": "mg/dL",
        "g/dl": "g/dL",
        "g/ dl": "g/dL",
        "ul": "µL",
        "cmm": "µL",
        "/cumm": "/µL",
        "/cmm": "/µL",
        "thou/ul": "thou/µL",
        "mil/ul": "mil/µL",
        "thou/cmm": "thou/µL",
        "mil/cmm": "mil/µL",
        "fl": "fL",
        "pg": "pg",
        "sec": "seconds",
        "secs": "seconds",
    }
    
    def normalize_unit(self, unit: str) -> str:
        """Normalize unit string"""
        if not unit:
            return ""
        
        unit = unit.strip().lower()
        return self.UNIT_NORMALIZATIONS.get(unit, unit)
    
    def normalize_metric_name(self, name: str) -> Optional[str]:
        """
        Map test name to canonical key
        
        Returns:
            Canonical key or None if not recognized
        """
        name_lower = name.lower().strip()
        
        # Direct lookup
        if name_lower in self.NAME_TO_KEY:
            return self.NAME_TO_KEY[name_lower]
        
        # Partial match (contains)
        for synonym, key in self.NAME_TO_KEY.items():
            if synonym in name_lower or name_lower in synonym:
                return key
        
        return None
    
    def extract_number(self, text: str) -> Optional[float]:
        """Extract first number from text"""
        # Remove commas from numbers
        text = text.replace(',', '')
        
        # Match decimal or integer
        match = re.search(r'[-+]?[0-9]*\.?[0-9]+', text)
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None
        return None
    
    def parse_reference_range(self, text: str) -> Tuple[Optional[float], Optional[float]]:
        """
        Parse reference range like "13.0-17.0" or "< 5.0" or "> 100"
        
        Returns:
            (low, high) tuple
        """
        text = text.strip().replace(',', '')
        
        # Pattern: low-high
        match = re.search(r'([\d.]+)\s*[-–]\s*([\d.]+)', text)
        if match:
            try:
                return float(match.group(1)), float(match.group(2))
            except ValueError:
                pass
        
        # Pattern: < value
        match = re.search(r'<\s*([\d.]+)', text)
        if match:
            try:
                return None, float(match.group(1))
            except ValueError:
                pass
        
        # Pattern: > value
        match = re.search(r'>\s*([\d.]+)', text)
        if match:
            try:
                return float(match.group(1)), None
            except ValueError:
                pass
        
        return None, None
    
    def parse_line(self, line: str, page_num: int = 1) -> Optional[ParsedMetric]:
        """
        Parse a single line from lab report
        
        Expected patterns:
        - "HEMOGLOBIN (HB) 12.8 13.0-17.0 g/dL"
        - "PLATELET COUNT 143 150-410 thou/µL Low"
        - "PT 54.5 10.0-13.0 seconds High"
        - "INR 4.60 0.8-1.2 Critical High"
        
        Returns:
            ParsedMetric or None
        """
        line = line.strip()
        if not line or len(line) < 5:
            return None
        
        # Skip header lines
        if any(header in line.upper() for header in ['TEST NAME', 'PARAMETER', 'INVESTIGATION', '---', '===']):
            return None
        
        # Split line into tokens
        tokens = re.split(r'\s+', line)
        if len(tokens) < 2:
            return None
        
        # Strategy: Find the first numeric token (that's likely the value)
        value_idx = None
        value = None
        
        for i, token in enumerate(tokens):
            num = self.extract_number(token)
            if num is not None:
                value_idx = i
                value = num
                break
        
        if value_idx is None or value is None:
            return None
        
        # Everything before value is the test name
        test_name = " ".join(tokens[:value_idx]).strip()
        
        # Clean test name (remove parentheses content)
        test_name = re.sub(r'\([^)]*\)', '', test_name).strip()
        
        if not test_name:
            return None
        
        # Get canonical key
        canonical_key = self.normalize_metric_name(test_name)
        if not canonical_key:
            canonical_key = "unmapped"
        
        # Everything after value: try to find unit, ref range, flag
        remaining = tokens[value_idx + 1:]
        
        unit = ""
        ref_low = None
        ref_high = None
        flag = None
        
        # Try to find unit (usually next 1-2 tokens)
        if remaining:
            # Check if next token looks like a unit
            potential_unit = remaining[0]
            if not potential_unit[0].isdigit() and len(potential_unit) < 20:
                unit = potential_unit
                remaining = remaining[1:]
            
            # Sometimes unit is 2 tokens (e.g., "thou/µL")
            if len(remaining) > 0 and '/' not in unit and '/' in remaining[0]:
                unit = remaining[0]
                remaining = remaining[1:]
        
        # Normalize unit
        unit = self.normalize_unit(unit)
        
        # Try to find reference range
        for token in remaining:
            if '-' in token or '–' in token:
                ref_low, ref_high = self.parse_reference_range(token)
                break
        
        # Try to find flag (Low, High, Normal, Critical)
        flag_keywords = ['low', 'high', 'critical', 'abnormal', 'normal']
        remaining_text = " ".join(remaining).lower()
        for keyword in flag_keywords:
            if keyword in remaining_text:
                flag = keyword.capitalize()
                break
        
        return ParsedMetric(
            test_name=test_name,
            canonical_key=canonical_key,
            value=value,
            unit=unit,
            ref_range_low=ref_low,
            ref_range_high=ref_high,
            flag=flag,
            page_num=page_num,
            raw_line=line
        )
    
    def parse(self, text: str) -> List[ParsedMetric]:
        """
        Parse full lab report text
        
        Returns:
            List of ParsedMetric objects
        """
        metrics = []
        current_page = 1
        
        lines = text.split('\n')
        
        for line in lines:
            # Track page numbers
            if line.startswith('=== PAGE'):
                try:
                    current_page = int(re.search(r'PAGE (\d+)', line).group(1))
                except:
                    pass
                continue
            
            metric = self.parse_line(line, page_num=current_page)
            if metric:
                metrics.append(metric)
        
        logger.info(f"Parsed {len(metrics)} metrics from text")
        return metrics
