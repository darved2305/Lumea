"""
OCR Document Classifier - REGEX-based Classification

Deterministic classifier for categorizing medical documents based on OCR text and filename.
Uses pattern matching with priority-ordered rules to classify documents into:
- Categories: Lab, Dental, MRI, X-ray, Prescription, Sleep
- Document Types: Blood Panel, Lipid Panel, Checkup, Brain Scan, Chest, etc.

Author: Co-Code GGW Health Platform
"""
import re
import logging
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ClassificationRule:
    """Single classification rule with patterns and priority"""
    name: str
    patterns: List[str]  # Regex patterns to match
    priority: int  # Lower = higher priority (1 is highest)
    min_matches: int = 1  # Minimum pattern matches required
    weight: float = 1.0  # Confidence weight
    

@dataclass
class ClassificationResult:
    """Result of document classification"""
    category: str  # lab/dental/mri/xray/prescription/sleep/unknown
    document_type: str  # blood_panel/lipid_panel/checkup/etc.
    confidence: float  # 0.0-1.0
    matched_rules: List[Dict]  # List of {rule_name, matched_patterns, match_count}
    category_scores: Dict[str, float] = field(default_factory=dict)  # All category scores
    doc_type_scores: Dict[str, float] = field(default_factory=dict)  # All doc type scores


# ============================================================================
# CLASSIFICATION RULES
# ============================================================================

# Category Rules - Priority ordered (lower = higher priority)
CATEGORY_RULES: Dict[str, List[ClassificationRule]] = {
    "lab": [
        ClassificationRule(
            name="lab_keywords",
            patterns=[
                r"\b(cbc|complete\s+blood\s+count|hemoglobin|haemoglobin|hgb|hb\b)",
                r"\b(lipid|cholesterol|triglycerides|hdl|ldl|vldl)",
                r"\b(glucose|fasting|hba1c|glycated|blood\s+sugar)",
                r"\b(creatinine|egfr|kidney\s+function|urea|bun)",
                r"\b(tsh|thyroid|t3|t4|ft3|ft4)",
                r"\b(ast|alt|sgot|sgpt|liver\s+function|bilirubin)",
                r"\b(platelet|wbc|rbc|white\s+blood|red\s+blood)",
                r"\b(reference\s+range|normal\s+range|biological\s+ref)",
                r"\b(lab\s*report|laboratory|pathology|diagnostic)",
                r"\b(panel|profile|test\s+results)",
                r"\b(vitamin\s+d|vitamin\s+b12|ferritin|iron\s+studies)",
                r"\b(sodium|potassium|chloride|electrolyte)",
                r"\b(specimen|sample\s+collected|blood\s+sample)",
            ],
            priority=1,
            min_matches=2,
            weight=1.0
        ),
    ],
    "dental": [
        ClassificationRule(
            name="dental_keywords",
            patterns=[
                r"\b(tooth|teeth|dental|dentist|dds|dmd)",
                r"\b(periodontal|gingiv|gum\s+disease)",
                r"\b(cavity|cavities|caries|decay)",
                r"\b(orthodontic|braces|alignment)",
                r"\b(crown|bridge|implant|filling)",
                r"\b(root\s+canal|extraction|wisdom\s+tooth)",
                r"\b(oral\s+hygiene|plaque|tartar)",
                r"\b(bitewing|periapical|panoramic)",
            ],
            priority=2,
            min_matches=2,
            weight=1.0
        ),
    ],
    "mri": [
        ClassificationRule(
            name="mri_keywords",
            patterns=[
                r"\b(mri|magnetic\s+resonance)",
                r"\b(t1[\s-]?weighted|t2[\s-]?weighted)",
                r"\b(flair|dwi|diffusion)",
                r"\b(contrast\s+enhanced|gadolinium|gad)",
                r"\b(sagittal|coronal|axial)\s+(view|plane|section)",
                r"\b(brain\s+mri|spine\s+mri|cardiac\s+mri)",
                r"\b(impression|findings|radiology)",
                r"\b(tesla|1\.5t|3t|3\.0t)",
            ],
            priority=2,
            min_matches=2,
            weight=1.0
        ),
    ],
    "xray": [
        ClassificationRule(
            name="xray_keywords",
            patterns=[
                r"\b(x[\s-]?ray|xray|radiograph)",
                r"\b(frontal\s+view|lateral\s+view|pa\s+view|ap\s+view)",
                r"\b(chest\s+x[\s-]?ray|cxr)",
                r"\b(thorax|lungs?|cardiac\s+silhouette)",
                r"\b(impression|findings|radiology)",
                r"\b(bone|fracture|joint)",
                r"\b(portable|erect|supine)",
            ],
            priority=2,
            min_matches=2,
            weight=1.0
        ),
    ],
    "prescription": [
        ClassificationRule(
            name="prescription_keywords",
            patterns=[
                r"\b(rx|prescription|prescribed)",
                r"\b(take\s+one\s+tablet|take\s+\d+\s+tablet)",
                r"\b(mg|mcg|ml)\b",  # dosage units
                r"\b(od|bd|tid|qid|prn|hs|ac|pc)",  # dosing frequencies
                r"\b(refill|dispense|quantity)",
                r"\b(pharmacy|pharmacist|dea)",
                r"\b(sig:|directions:|dosage:)",
                r"\b(daily|twice\s+daily|three\s+times)",
            ],
            priority=3,
            min_matches=3,
            weight=0.9
        ),
    ],
    "sleep": [
        ClassificationRule(
            name="sleep_keywords",
            patterns=[
                r"\b(sleep\s+study|polysomnography|psg)",
                r"\b(apnea|ahi|rdi)",
                r"\b(spo2|oxygen\s+saturation|desaturation)",
                r"\b(snore|snoring|rera)",
                r"\b(rem\s+sleep|nrem|sleep\s+stage)",
                r"\b(cpap|bipap|sleep\s+therapy)",
                r"\b(insomnia|hypersomnia|narcolepsy)",
                r"\b(arousal\s+index|sleep\s+efficiency)",
            ],
            priority=2,
            min_matches=2,
            weight=1.0
        ),
    ],
}

# Document Type Rules - Matched AFTER category is determined
DOC_TYPE_RULES: Dict[str, List[ClassificationRule]] = {
    "blood_panel": [
        ClassificationRule(
            name="blood_panel_keywords",
            patterns=[
                r"\b(cbc|complete\s+blood\s+count)",
                r"\b(hemoglobin|haemoglobin|hgb|hb\b)",
                r"\b(wbc|white\s+blood\s+cell|leucocyte)",
                r"\b(rbc|red\s+blood\s+cell|erythrocyte)",
                r"\b(platelet|plt|thrombocyte)",
                r"\b(hematocrit|hct|pcv)",
                r"\b(mcv|mch|mchc|rdw)",
            ],
            priority=1,
            min_matches=3,
            weight=1.0
        ),
    ],
    "lipid_panel": [
        ClassificationRule(
            name="lipid_panel_keywords",
            patterns=[
                r"\b(lipid\s+panel|lipid\s+profile)",
                r"\b(cholesterol|total\s+cholesterol)",
                r"\b(hdl|high.density\s+lipoprotein)",
                r"\b(ldl|low.density\s+lipoprotein)",
                r"\b(vldl)",
                r"\b(triglycerides|tg\b)",
                r"\b(cardiovascular\s+risk)",
            ],
            priority=1,
            min_matches=3,
            weight=1.0
        ),
    ],
    "checkup": [
        ClassificationRule(
            name="checkup_keywords",
            patterns=[
                r"\b(general\s+checkup|annual\s+checkup|physical\s+exam)",
                r"\b(vitals|vital\s+signs)",
                r"\b(bp|blood\s+pressure|systolic|diastolic)",
                r"\b(pulse|heart\s+rate|bpm)",
                r"\b(weight|height|bmi)",
                r"\b(general\s+health|wellness\s+exam)",
            ],
            priority=2,
            min_matches=2,
            weight=0.9
        ),
    ],
    "brain_scan": [
        ClassificationRule(
            name="brain_scan_keywords",
            patterns=[
                r"\b(brain)\s*(mri|ct|scan)",
                r"\b(intracranial|cranial)",
                r"\b(cerebral|cerebellum|brainstem)",
                r"\b(ventricle|white\s+matter|gray\s+matter)",
                r"\b(head\s+ct|head\s+mri)",
                r"\b(neuroimaging|neuroradiology)",
            ],
            priority=1,
            min_matches=2,
            weight=1.0
        ),
    ],
    "chest": [
        ClassificationRule(
            name="chest_keywords",
            patterns=[
                r"\b(chest)\s*(x[\s-]?ray|radiograph|pa|ap)",
                r"\b(thorax|thoracic)",
                r"\b(lungs?|lung\s+fields|pulmonary)",
                r"\b(cardiac\s+silhouette|heart\s+size)",
                r"\b(costophrenic|diaphragm)",
                r"\b(mediastinum|hilum|hila)",
            ],
            priority=1,
            min_matches=2,
            weight=1.0
        ),
    ],
    "dental_exam": [
        ClassificationRule(
            name="dental_exam_keywords",
            patterns=[
                r"\b(dental\s+exam|oral\s+exam)",
                r"\b(tooth\s+chart|dental\s+chart)",
                r"\b(periodontal\s+chart|gum\s+assessment)",
                r"\b(dental\s+checkup|routine\s+dental)",
            ],
            priority=1,
            min_matches=1,
            weight=0.9
        ),
    ],
    "prescription": [
        ClassificationRule(
            name="prescription_doc_keywords",
            patterns=[
                r"\b(rx|prescription)",
                r"\b(prescribed\s+by|prescriber)",
                r"\b(medication\s+list|drug\s+list)",
            ],
            priority=1,
            min_matches=1,
            weight=0.9
        ),
    ],
    "sleep_study": [
        ClassificationRule(
            name="sleep_study_keywords",
            patterns=[
                r"\b(sleep\s+study|psg|polysomnography)",
                r"\b(ahi|apnea.hypopnea\s+index)",
                r"\b(sleep\s+report|overnight\s+study)",
            ],
            priority=1,
            min_matches=1,
            weight=0.9
        ),
    ],
}

# Filename patterns for additional hints
FILENAME_PATTERNS: Dict[str, str] = {
    "lab": r"(lab|blood|cbc|lipid|panel|test|report)",
    "dental": r"(dental|tooth|teeth|oral|dentist)",
    "mri": r"(mri|magnetic|resonance|brain|spine)",
    "xray": r"(xray|x-ray|radiograph|chest|thorax)",
    "prescription": r"(rx|prescription|medication|med)",
    "sleep": r"(sleep|apnea|psg|polysom)",
}


# ============================================================================
# CLASSIFIER CLASS
# ============================================================================

class DocumentClassifier:
    """
    REGEX-based document classifier for medical documents.
    
    Classification is deterministic and based on pattern matching with
    priority-ordered rules.
    """
    
    def __init__(self):
        self.category_rules = CATEGORY_RULES
        self.doc_type_rules = DOC_TYPE_RULES
        self.filename_patterns = FILENAME_PATTERNS
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize OCR text for pattern matching:
        - Lowercase
        - Normalize whitespace
        - Remove excessive punctuation
        """
        if not text:
            return ""
        
        # Lowercase
        text = text.lower()
        
        # Normalize whitespace (collapse multiple spaces/newlines)
        text = re.sub(r'\s+', ' ', text)
        
        # Remove non-alphanumeric except common medical symbols
        text = re.sub(r'[^\w\s\.\-\/\(\)\%\<\>]', ' ', text)
        
        return text.strip()
    
    def _match_rules(
        self, 
        text: str, 
        rules: Dict[str, List[ClassificationRule]]
    ) -> Dict[str, Tuple[float, List[Dict]]]:
        """
        Match text against classification rules.
        
        Returns:
            Dict[category/type -> (score, matched_rules)]
        """
        results = {}
        
        for category, rule_list in rules.items():
            total_score = 0.0
            matched_rules = []
            
            for rule in rule_list:
                match_count = 0
                matched_patterns = []
                
                for pattern in rule.patterns:
                    try:
                        matches = re.findall(pattern, text, re.IGNORECASE)
                        if matches:
                            match_count += len(matches)
                            matched_patterns.append({
                                "pattern": pattern,
                                "matches": matches[:5]  # Limit stored matches
                            })
                    except re.error as e:
                        logger.warning(f"Invalid regex pattern '{pattern}': {e}")
                        continue
                
                if match_count >= rule.min_matches:
                    # Calculate score: more matches = higher score, weighted by priority
                    rule_score = (match_count / len(rule.patterns)) * rule.weight
                    # Priority bonus: priority 1 gets 1.0x, priority 2 gets 0.9x, etc.
                    priority_multiplier = 1.0 - (rule.priority - 1) * 0.1
                    rule_score *= max(0.5, priority_multiplier)
                    
                    total_score += rule_score
                    matched_rules.append({
                        "rule_name": rule.name,
                        "matched_patterns": matched_patterns,
                        "match_count": match_count,
                        "score": rule_score
                    })
            
            if total_score > 0:
                results[category] = (total_score, matched_rules)
        
        return results
    
    def _classify_filename(self, filename: str) -> Dict[str, float]:
        """
        Get classification hints from filename.
        Returns category -> boost score mapping.
        """
        if not filename:
            return {}
        
        filename_lower = filename.lower()
        boosts = {}
        
        for category, pattern in self.filename_patterns.items():
            if re.search(pattern, filename_lower):
                boosts[category] = 0.15  # 15% confidence boost
        
        return boosts
    
    def classify_document(
        self, 
        ocr_text: str, 
        filename: str = ""
    ) -> ClassificationResult:
        """
        Classify a document based on OCR text and filename.
        
        Args:
            ocr_text: Full OCR-extracted text from document
            filename: Original filename (optional, provides hints)
        
        Returns:
            ClassificationResult with category, document_type, confidence, and matched rules
        """
        # Normalize text
        normalized_text = self._normalize_text(ocr_text)
        
        if not normalized_text:
            return ClassificationResult(
                category="unknown",
                document_type="unknown",
                confidence=0.0,
                matched_rules=[],
                category_scores={},
                doc_type_scores={}
            )
        
        # =====================================================================
        # Step 1: Classify Category
        # =====================================================================
        category_results = self._match_rules(normalized_text, self.category_rules)
        
        # Apply filename boosts
        filename_boosts = self._classify_filename(filename)
        for cat, boost in filename_boosts.items():
            if cat in category_results:
                score, rules = category_results[cat]
                category_results[cat] = (score + boost, rules)
            else:
                category_results[cat] = (boost, [{"rule_name": "filename_match", "match_count": 1}])
        
        # Get best category
        if category_results:
            # Sort by score, then by priority
            sorted_categories = sorted(
                category_results.items(),
                key=lambda x: x[1][0],
                reverse=True
            )
            best_category, (cat_score, cat_rules) = sorted_categories[0]
            
            # Normalize confidence (cap at 1.0)
            max_possible_score = 3.0  # Rough max
            category_confidence = min(1.0, cat_score / max_possible_score)
        else:
            best_category = "unknown"
            category_confidence = 0.0
            cat_rules = []
        
        # =====================================================================
        # Step 2: Classify Document Type
        # =====================================================================
        doc_type_results = self._match_rules(normalized_text, self.doc_type_rules)
        
        if doc_type_results:
            sorted_doc_types = sorted(
                doc_type_results.items(),
                key=lambda x: x[1][0],
                reverse=True
            )
            best_doc_type, (dtype_score, dtype_rules) = sorted_doc_types[0]
            
            # Normalize confidence
            max_possible_score = 2.5
            doc_type_confidence = min(1.0, dtype_score / max_possible_score)
        else:
            # Infer doc type from category if not matched
            best_doc_type = self._infer_doc_type_from_category(best_category)
            doc_type_confidence = 0.3
            dtype_rules = []
        
        # =====================================================================
        # Step 3: Calculate Overall Confidence
        # =====================================================================
        # Weighted average: category is more important
        overall_confidence = (category_confidence * 0.6 + doc_type_confidence * 0.4)
        
        # Apply minimum threshold
        if overall_confidence < 0.2:
            best_category = "unknown"
            best_doc_type = "unknown"
        
        # Collect all matched rules
        all_matched_rules = []
        for rule in cat_rules:
            rule["type"] = "category"
            all_matched_rules.append(rule)
        for rule in dtype_rules:
            rule["type"] = "doc_type"
            all_matched_rules.append(rule)
        
        # Build score dictionaries
        category_scores = {cat: score for cat, (score, _) in category_results.items()}
        doc_type_scores = {dt: score for dt, (score, _) in doc_type_results.items()}
        
        return ClassificationResult(
            category=best_category,
            document_type=best_doc_type,
            confidence=round(overall_confidence, 3),
            matched_rules=all_matched_rules,
            category_scores=category_scores,
            doc_type_scores=doc_type_scores
        )
    
    def _infer_doc_type_from_category(self, category: str) -> str:
        """Infer document type from category when no specific type matched."""
        inference_map = {
            "lab": "blood_panel",  # Default lab is blood panel
            "dental": "dental_exam",
            "mri": "brain_scan",
            "xray": "chest",
            "prescription": "prescription",
            "sleep": "sleep_study",
        }
        return inference_map.get(category, "unknown")


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

# Global classifier instance
_classifier = DocumentClassifier()


def classify_document(ocr_text: str, filename: str = "") -> ClassificationResult:
    """
    Classify a document based on OCR text and filename.
    
    This is the main entry point for document classification.
    
    Args:
        ocr_text: Full OCR-extracted text from document
        filename: Original filename (optional, provides hints)
    
    Returns:
        ClassificationResult with:
        - category: lab/dental/mri/xray/prescription/sleep/unknown
        - document_type: blood_panel/lipid_panel/checkup/brain_scan/chest/etc.
        - confidence: 0.0-1.0
        - matched_rules: List of rules that matched with details
    
    Example:
        >>> result = classify_document("CBC Complete Blood Count Hemoglobin 14.2 g/dL", "lab_report.pdf")
        >>> print(result.category)  # "lab"
        >>> print(result.document_type)  # "blood_panel"
        >>> print(result.confidence)  # 0.85
    """
    return _classifier.classify_document(ocr_text, filename)


# ============================================================================
# TESTING UTILITIES
# ============================================================================

def test_classifier():
    """Test the classifier with sample texts."""
    test_cases = [
        {
            "text": "COMPLETE BLOOD COUNT (CBC) Report\nHemoglobin: 14.2 g/dL (Reference: 12.0-16.0)\nWBC Total: 7.5 thou/uL\nRBC: 4.8 mil/uL\nPlatelet Count: 250 thou/uL",
            "filename": "blood_test_2024.pdf",
            "expected_cat": "lab",
            "expected_type": "blood_panel"
        },
        {
            "text": "LIPID PROFILE\nTotal Cholesterol: 210 mg/dL\nHDL Cholesterol: 55 mg/dL\nLDL Cholesterol: 130 mg/dL\nTriglycerides: 150 mg/dL",
            "filename": "lipid_panel.pdf",
            "expected_cat": "lab",
            "expected_type": "lipid_panel"
        },
        {
            "text": "MRI BRAIN WITHOUT CONTRAST\nTechnique: T1, T2, FLAIR, DWI\nFindings: No acute intracranial abnormality\nVentricles and sulci are normal",
            "filename": "brain_mri.pdf",
            "expected_cat": "mri",
            "expected_type": "brain_scan"
        },
        {
            "text": "CHEST X-RAY PA VIEW\nLungs: Clear bilateral lung fields\nCardiac silhouette: Normal size\nImpression: Normal chest radiograph",
            "filename": "cxr_report.pdf",
            "expected_cat": "xray",
            "expected_type": "chest"
        },
        {
            "text": "PRESCRIPTION\nRx: Metformin 500mg\nSig: Take one tablet twice daily (BD) with meals\nRefill: 3\nPrescribed by: Dr. Smith, MD",
            "filename": "prescription.pdf",
            "expected_cat": "prescription",
            "expected_type": "prescription"
        },
        {
            "text": "SLEEP STUDY REPORT - POLYSOMNOGRAPHY\nAHI: 15.2 events/hour (Moderate OSA)\nLowest SpO2: 82%\nSnoring Index: High\nSleep Efficiency: 78%",
            "filename": "sleep_study.pdf",
            "expected_cat": "sleep",
            "expected_type": "sleep_study"
        },
    ]
    
    print("=" * 80)
    print("DOCUMENT CLASSIFIER TEST")
    print("=" * 80)
    
    for i, tc in enumerate(test_cases, 1):
        result = classify_document(tc["text"], tc["filename"])
        cat_match = "✓" if result.category == tc["expected_cat"] else "✗"
        type_match = "✓" if result.document_type == tc["expected_type"] else "✗"
        
        print(f"\nTest {i}: {tc['filename']}")
        print(f"  Category: {result.category} {cat_match} (expected: {tc['expected_cat']})")
        print(f"  DocType:  {result.document_type} {type_match} (expected: {tc['expected_type']})")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Matched Rules: {len(result.matched_rules)}")


if __name__ == "__main__":
    test_classifier()
