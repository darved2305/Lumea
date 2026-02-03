"""
Grok Extractor - LLM-based Structured Data Extraction

Fallback extraction using LLM when regex fails or has low confidence.
Implements a 3-stage chain:
1. Regex extraction (fast, deterministic)
2. Grok extractor (LLM with strict JSON schema)
3. Grok fallback (retry with stricter prompt / JSON repair)

HARD RULES:
- LLM must NEVER hallucinate values not present in OCR text
- If estimating, must include {estimated: true, estimation_reason: "..."}
- Prefer null for missing values + create MissingDataTask
- Always validate JSON against schema before accepting

Author: Lumea Health Platform
"""
import json
import logging
import asyncio
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import httpx

from app.settings import settings
from app.services.document_classifier import classify_document, ClassificationResult
from app.services.metric_extractor import (
    extract_metrics_regex, 
    ExtractionResult, 
    ExtractedMetric,
    get_missing_parameters,
    MissingParameter,
    METRIC_LABELS,
    METRIC_UNITS,
)

logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class GrokExtractedMetric:
    """Metric extracted by Grok LLM"""
    metric_key: str
    display_name: str
    value: Optional[float]
    unit: str
    reference_min: Optional[float] = None
    reference_max: Optional[float] = None
    flag: Optional[str] = None
    confidence: float = 0.8
    estimated: bool = False
    estimation_reason: Optional[str] = None
    raw_text_evidence: Optional[str] = None  # Exact text from OCR that supports this


@dataclass
class GrokExtractionResult:
    """Result from Grok extraction"""
    category: str
    document_type: str
    metrics: List[GrokExtractedMetric]
    extraction_confidence: float
    stage_used: str  # "regex", "grok_primary", "grok_fallback"
    warnings: List[str]
    raw_llm_response: Optional[str] = None


# ============================================================================
# JSON SCHEMA FOR LLM OUTPUT
# ============================================================================

GROK_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["category", "document_type", "metrics", "confidence"],
    "properties": {
        "category": {
            "type": "string",
            "enum": ["lab", "dental", "mri", "xray", "prescription", "sleep", "unknown"],
            "description": "Document category"
        },
        "document_type": {
            "type": "string",
            "enum": ["blood_panel", "lipid_panel", "checkup", "brain_scan", "chest", 
                     "dental_exam", "prescription", "sleep_study", "unknown"],
            "description": "Specific document type"
        },
        "metrics": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["metric_key", "value", "unit"],
                "properties": {
                    "metric_key": {"type": "string", "description": "Canonical metric identifier"},
                    "display_name": {"type": "string", "description": "Original name from document"},
                    "value": {"type": ["number", "null"], "description": "Numeric value"},
                    "unit": {"type": "string", "description": "Unit of measurement"},
                    "reference_min": {"type": ["number", "null"]},
                    "reference_max": {"type": ["number", "null"]},
                    "flag": {"type": ["string", "null"], "enum": ["Low", "High", "Normal", "Critical Low", "Critical High", None]},
                    "estimated": {"type": "boolean", "default": False},
                    "estimation_reason": {"type": ["string", "null"]},
                    "raw_text_evidence": {"type": ["string", "null"], "description": "Exact text from OCR supporting this extraction"}
                }
            }
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Extraction confidence 0-1"
        },
        "warnings": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Any warnings or notes about extraction quality"
        }
    }
}


# ============================================================================
# PROMPT TEMPLATES
# ============================================================================

GROK_SYSTEM_PROMPT = """You are a medical document extraction assistant. Your job is to extract structured health metrics from OCR text of medical documents.

CRITICAL RULES:
1. ONLY extract values that are EXPLICITLY present in the OCR text
2. NEVER hallucinate or invent values - if a value is not clearly visible, set it to null
3. If you must estimate (e.g., calculating LDL from other lipids), mark estimated=true and provide estimation_reason
4. Include raw_text_evidence for each metric - the exact text snippet that supports the extraction
5. Use standard metric_key identifiers (hemoglobin, glucose, cholesterol_total, etc.)
6. Normalize units to standard forms (mg/dL, g/dL, µL, etc.)
7. Set flag to "Low", "High", "Normal", "Critical Low", or "Critical High" if you can determine from reference ranges
8. Set confidence based on OCR quality and extraction certainty (0.0-1.0)

METRIC KEY REFERENCE:
- Blood: hemoglobin, hematocrit, wbc_total, rbc_count, platelet_count, mcv, mch, mchc
- Lipids: cholesterol_total, hdl, ldl, vldl, triglycerides
- Glucose: glucose, glucose_pp, hba1c
- Kidney: creatinine, urea, egfr, uric_acid
- Liver: ast, alt, alp, ggt, bilirubin_total, albumin
- Thyroid: tsh, t3, t4, ft3, ft4
- Vitamins: vitamin_d, vitamin_b12, folate, ferritin, iron
- Vitals: systolic_bp, diastolic_bp, heart_rate, spo2

Output ONLY valid JSON matching the schema. No explanation text."""


GROK_USER_PROMPT_TEMPLATE = """Extract health metrics from this OCR text:

FILENAME: {filename}

OCR TEXT:
---
{ocr_text}
---

{classification_hint}

Extract all visible metrics and output valid JSON with:
- category: document category
- document_type: specific type
- metrics: array of extracted metrics with raw_text_evidence
- confidence: overall extraction confidence
- warnings: any quality issues

Remember: ONLY extract what's explicitly visible. Use null for missing values."""


GROK_FALLBACK_PROMPT = """The previous extraction attempt failed validation. Please extract metrics more carefully.

ERRORS FROM PREVIOUS ATTEMPT:
{errors}

OCR TEXT:
---
{ocr_text}
---

Rules:
1. Use ONLY these exact metric_key values: hemoglobin, wbc_total, platelet_count, rbc_count, glucose, hba1c, cholesterol_total, hdl, ldl, triglycerides, creatinine, tsh, vitamin_d, vitamin_b12, ast, alt, systolic_bp, diastolic_bp
2. Every metric MUST have raw_text_evidence showing the exact text
3. Set value to null if not clearly readable
4. confidence should be 0.3-0.7 for uncertain extractions

Output ONLY valid JSON. No other text."""


JSON_REPAIR_PROMPT = """The following JSON has syntax errors. Repair it to be valid JSON:

{invalid_json}

Output ONLY the repaired valid JSON, nothing else."""


# ============================================================================
# GROK EXTRACTOR CLASS
# ============================================================================

class GrokExtractor:
    """
    LLM-based metric extraction with fallback chain.
    
    Stage 1: Regex extraction (handled externally)
    Stage 2: Grok primary extraction
    Stage 3: Grok fallback with stricter prompt
    """
    
    def __init__(self):
        self.api_key = getattr(settings, 'xai_api_key', None) or getattr(settings, 'openai_api_key', None)
        self.api_base = getattr(settings, 'xai_api_base', 'https://api.x.ai/v1')
        self.model = getattr(settings, 'grok_model', 'grok-beta')
        self.timeout = 30.0
        self.max_retries = 2
    
    async def _call_llm(
        self, 
        system_prompt: str, 
        user_prompt: str,
        temperature: float = 0.1
    ) -> Optional[str]:
        """
        Call the Grok/OpenAI-compatible API.
        
        Args:
            system_prompt: System message
            user_prompt: User message
            temperature: Sampling temperature (low for deterministic)
        
        Returns:
            Raw response text or None on failure
        """
        if not self.api_key:
            logger.warning("No API key configured for Grok extractor")
            return None
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": 4000,
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                return data["choices"][0]["message"]["content"]
                
        except httpx.TimeoutException:
            logger.error("Grok API timeout")
            return None
        except httpx.HTTPError as e:
            logger.error(f"Grok API error: {e}")
            return None
        except (KeyError, IndexError) as e:
            logger.error(f"Grok API response parsing error: {e}")
            return None
    
    def _parse_json_response(self, response: str) -> Tuple[Optional[Dict], List[str]]:
        """
        Parse JSON from LLM response, handling common issues.
        
        Returns:
            (parsed_dict, errors) - errors list is empty on success
        """
        errors = []
        
        if not response:
            return None, ["Empty response"]
        
        # Try to extract JSON from response (handle markdown code blocks)
        json_str = response.strip()
        
        # Remove markdown code blocks if present
        if json_str.startswith("```"):
            lines = json_str.split("\n")
            # Remove first and last lines (``` markers)
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            json_str = "\n".join(lines)
        
        try:
            parsed = json.loads(json_str)
            return parsed, []
        except json.JSONDecodeError as e:
            errors.append(f"JSON parse error: {e}")
            
            # Try to find JSON object within the text
            match = json_str.find("{")
            if match != -1:
                try:
                    # Find matching closing brace
                    brace_count = 0
                    end_idx = match
                    for i, char in enumerate(json_str[match:]):
                        if char == "{":
                            brace_count += 1
                        elif char == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = match + i + 1
                                break
                    
                    json_substring = json_str[match:end_idx]
                    parsed = json.loads(json_substring)
                    return parsed, []
                except:
                    pass
            
            return None, errors
    
    def _validate_extraction(self, data: Dict) -> List[str]:
        """
        Validate extracted data against schema.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check required fields
        required = ["category", "document_type", "metrics", "confidence"]
        for field in required:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        if errors:
            return errors
        
        # Validate category
        valid_categories = ["lab", "dental", "mri", "xray", "prescription", "sleep", "unknown"]
        if data["category"] not in valid_categories:
            errors.append(f"Invalid category: {data['category']}")
        
        # Validate confidence
        if not isinstance(data["confidence"], (int, float)):
            errors.append("Confidence must be a number")
        elif not 0 <= data["confidence"] <= 1:
            errors.append("Confidence must be between 0 and 1")
        
        # Validate metrics
        if not isinstance(data.get("metrics"), list):
            errors.append("Metrics must be an array")
        else:
            for i, metric in enumerate(data["metrics"]):
                if not isinstance(metric, dict):
                    errors.append(f"Metric {i} must be an object")
                    continue
                
                if "metric_key" not in metric:
                    errors.append(f"Metric {i} missing metric_key")
                if "unit" not in metric:
                    errors.append(f"Metric {i} missing unit")
                
                # Value can be null
                if "value" in metric and metric["value"] is not None:
                    if not isinstance(metric["value"], (int, float)):
                        errors.append(f"Metric {i} value must be a number or null")
        
        return errors
    
    def _convert_to_result(
        self, 
        data: Dict, 
        stage: str,
        raw_response: str
    ) -> GrokExtractionResult:
        """Convert validated dict to GrokExtractionResult."""
        metrics = []
        
        for m in data.get("metrics", []):
            metric = GrokExtractedMetric(
                metric_key=m.get("metric_key", "unknown"),
                display_name=m.get("display_name", m.get("metric_key", "unknown")),
                value=m.get("value"),
                unit=m.get("unit", ""),
                reference_min=m.get("reference_min"),
                reference_max=m.get("reference_max"),
                flag=m.get("flag"),
                confidence=m.get("confidence", 0.7),
                estimated=m.get("estimated", False),
                estimation_reason=m.get("estimation_reason"),
                raw_text_evidence=m.get("raw_text_evidence")
            )
            metrics.append(metric)
        
        return GrokExtractionResult(
            category=data.get("category", "unknown"),
            document_type=data.get("document_type", "unknown"),
            metrics=metrics,
            extraction_confidence=data.get("confidence", 0.5),
            stage_used=stage,
            warnings=data.get("warnings", []),
            raw_llm_response=raw_response
        )
    
    async def extract(
        self, 
        ocr_text: str, 
        filename: str = "",
        classification_hint: Optional[ClassificationResult] = None
    ) -> GrokExtractionResult:
        """
        Extract metrics using Grok LLM.
        
        Args:
            ocr_text: Raw OCR text
            filename: Original filename
            classification_hint: Optional pre-computed classification
        
        Returns:
            GrokExtractionResult with extracted metrics
        """
        # Build classification hint for prompt
        hint_str = ""
        if classification_hint:
            hint_str = f"HINT: Document appears to be category='{classification_hint.category}', type='{classification_hint.document_type}' (confidence: {classification_hint.confidence})"
        
        # Stage 2: Primary Grok extraction
        user_prompt = GROK_USER_PROMPT_TEMPLATE.format(
            filename=filename,
            ocr_text=ocr_text[:8000],  # Limit text length
            classification_hint=hint_str
        )
        
        logger.info("Stage 2: Calling Grok primary extraction")
        response = await self._call_llm(GROK_SYSTEM_PROMPT, user_prompt)
        
        if response:
            parsed, parse_errors = self._parse_json_response(response)
            
            if parsed and not parse_errors:
                validation_errors = self._validate_extraction(parsed)
                
                if not validation_errors:
                    logger.info("Stage 2 successful")
                    return self._convert_to_result(parsed, "grok_primary", response)
                else:
                    logger.warning(f"Stage 2 validation errors: {validation_errors}")
        
        # Stage 3: Fallback extraction
        logger.info("Stage 3: Calling Grok fallback extraction")
        
        errors_str = "\n".join(parse_errors if 'parse_errors' in dir() else ["Primary extraction returned invalid format"])
        
        fallback_prompt = GROK_FALLBACK_PROMPT.format(
            errors=errors_str,
            ocr_text=ocr_text[:6000]
        )
        
        response = await self._call_llm(GROK_SYSTEM_PROMPT, fallback_prompt, temperature=0.05)
        
        if response:
            parsed, parse_errors = self._parse_json_response(response)
            
            if parsed:
                validation_errors = self._validate_extraction(parsed)
                
                if not validation_errors:
                    logger.info("Stage 3 successful")
                    return self._convert_to_result(parsed, "grok_fallback", response)
                else:
                    # Return partial result with warnings
                    logger.warning(f"Stage 3 validation errors: {validation_errors}")
                    result = self._convert_to_result(parsed, "grok_fallback", response)
                    result.warnings.extend(validation_errors)
                    result.extraction_confidence *= 0.5  # Reduce confidence
                    return result
        
        # All stages failed
        logger.error("All Grok extraction stages failed")
        return GrokExtractionResult(
            category="unknown",
            document_type="unknown",
            metrics=[],
            extraction_confidence=0.0,
            stage_used="failed",
            warnings=["All extraction stages failed"],
            raw_llm_response=response
        )
    
    async def repair_json(self, invalid_json: str) -> Optional[Dict]:
        """
        Attempt to repair invalid JSON using LLM.
        
        Args:
            invalid_json: Malformed JSON string
        
        Returns:
            Parsed dict or None
        """
        prompt = JSON_REPAIR_PROMPT.format(invalid_json=invalid_json[:3000])
        response = await self._call_llm(
            "You are a JSON repair assistant. Output only valid JSON.",
            prompt,
            temperature=0.0
        )
        
        if response:
            parsed, _ = self._parse_json_response(response)
            return parsed
        
        return None


# ============================================================================
# EXTRACTION PIPELINE
# ============================================================================

class ExtractionPipeline:
    """
    Full extraction pipeline with 3-stage fallback chain.
    
    Stage 1: Regex extraction (fast, deterministic)
    Stage 2: Grok extractor (LLM) if regex fails or low confidence
    Stage 3: Grok fallback if Stage 2 fails
    """
    
    # Confidence thresholds
    REGEX_MIN_CONFIDENCE = 0.6  # Below this, try Grok
    REGEX_MIN_METRICS = 3  # Need at least this many metrics from regex
    
    def __init__(self):
        self.grok = GrokExtractor()
    
    async def extract(
        self, 
        ocr_text: str, 
        filename: str = "",
        doc_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run full extraction pipeline.
        
        Args:
            ocr_text: Raw OCR text
            filename: Original filename
            doc_type: Pre-determined document type (optional)
        
        Returns:
            Dict with:
            - classification: ClassificationResult
            - metrics: List of extracted metrics
            - missing_parameters: List of missing required params
            - extraction_source: "regex" | "grok_primary" | "grok_fallback"
            - confidence: Overall extraction confidence
            - warnings: Any warnings
        """
        result = {
            "classification": None,
            "metrics": [],
            "missing_parameters": [],
            "extraction_source": "regex",
            "confidence": 0.0,
            "warnings": []
        }
        
        # Step 1: Classify document
        classification = classify_document(ocr_text, filename)
        result["classification"] = classification
        
        if doc_type:
            classification.document_type = doc_type
        
        # Step 2: Try regex extraction first (Stage 1)
        logger.info("Stage 1: Running regex extraction")
        regex_result = extract_metrics_regex(ocr_text)
        
        use_grok = False
        
        if regex_result.extraction_confidence < self.REGEX_MIN_CONFIDENCE:
            logger.info(f"Regex confidence too low ({regex_result.extraction_confidence}), will try Grok")
            use_grok = True
        
        if len(regex_result.metrics) < self.REGEX_MIN_METRICS:
            logger.info(f"Too few metrics from regex ({len(regex_result.metrics)}), will try Grok")
            use_grok = True
        
        # Step 3: Determine if Grok is needed
        if not use_grok:
            # Regex extraction was good enough
            result["metrics"] = [asdict(m) for m in regex_result.metrics]
            result["extraction_source"] = "regex"
            result["confidence"] = regex_result.extraction_confidence
            result["warnings"] = regex_result.warnings
            
        else:
            # Try Grok extraction (Stages 2-3)
            grok_result = await self.grok.extract(
                ocr_text, 
                filename, 
                classification_hint=classification
            )
            
            if grok_result.extraction_confidence > regex_result.extraction_confidence:
                # Grok did better
                result["metrics"] = [asdict(m) for m in grok_result.metrics]
                result["extraction_source"] = grok_result.stage_used
                result["confidence"] = grok_result.extraction_confidence
                result["warnings"] = grok_result.warnings
                
                # Update classification if Grok provided better one
                if grok_result.extraction_confidence > classification.confidence:
                    result["classification"].category = grok_result.category
                    result["classification"].document_type = grok_result.document_type
            else:
                # Keep regex results
                result["metrics"] = [asdict(m) for m in regex_result.metrics]
                result["extraction_source"] = "regex"
                result["confidence"] = regex_result.extraction_confidence
                result["warnings"] = regex_result.warnings + ["Grok extraction did not improve results"]
        
        # Step 4: Identify missing parameters
        extracted_keys = {m["metric_key"] for m in result["metrics"]}
        doc_type_for_missing = result["classification"].document_type
        
        missing = get_missing_parameters(doc_type_for_missing, extracted_keys)
        result["missing_parameters"] = [asdict(m) for m in missing]
        
        if missing:
            result["warnings"].append(f"Missing {len(missing)} required parameters")
        
        return result


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

# Global pipeline instance
_pipeline = ExtractionPipeline()


async def extract_document_metrics(
    ocr_text: str, 
    filename: str = "",
    doc_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract metrics from document using full pipeline.
    
    This is the main entry point for document extraction.
    
    Args:
        ocr_text: Raw OCR text from document
        filename: Original filename
        doc_type: Pre-determined document type (optional)
    
    Returns:
        Dict with classification, metrics, missing_parameters, source, confidence, warnings
    
    Example:
        >>> result = await extract_document_metrics(ocr_text, "blood_test.pdf")
        >>> print(result["extraction_source"])  # "regex" or "grok_primary"
        >>> print(len(result["metrics"]))
        >>> print(result["missing_parameters"])
    """
    return await _pipeline.extract(ocr_text, filename, doc_type)


async def grok_extract_metrics(
    ocr_text: str,
    filename: str = "",
    classification_hint: Optional[ClassificationResult] = None
) -> GrokExtractionResult:
    """
    Direct Grok extraction (bypasses regex stage).
    
    Use this when you specifically want LLM extraction.
    
    Args:
        ocr_text: Raw OCR text
        filename: Original filename
        classification_hint: Optional pre-computed classification
    
    Returns:
        GrokExtractionResult
    """
    grok = GrokExtractor()
    return await grok.extract(ocr_text, filename, classification_hint)


# ============================================================================
# TESTING
# ============================================================================

async def test_grok_extractor():
    """Test the Grok extractor with sample text."""
    sample_text = """
    LIPID PROFILE REPORT
    Date: 2024-01-15
    Patient: John Doe
    
    Test                    Result      Unit        Reference
    =========================================================
    Total Cholesterol       245         mg/dL       <200
    HDL Cholesterol         42          mg/dL       >40
    LDL Cholesterol         165         mg/dL       <100
    Triglycerides           190         mg/dL       <150
    VLDL                    38          mg/dL       <30
    
    Comments: Elevated LDL and Total Cholesterol levels.
    Recommend lifestyle modifications and follow-up.
    """
    
    print("=" * 80)
    print("GROK EXTRACTOR TEST")
    print("=" * 80)
    
    result = await extract_document_metrics(sample_text, "lipid_panel_2024.pdf")
    
    print(f"\nClassification: {result['classification'].category} / {result['classification'].document_type}")
    print(f"Extraction Source: {result['extraction_source']}")
    print(f"Confidence: {result['confidence']}")
    
    print(f"\nExtracted {len(result['metrics'])} metrics:")
    for m in result['metrics']:
        print(f"  - {m['metric_key']}: {m['value']} {m['unit']}")
    
    print(f"\nMissing Parameters: {len(result['missing_parameters'])}")
    for m in result['missing_parameters']:
        print(f"  - {m['label']} ({m['metric_key']})")
    
    if result['warnings']:
        print(f"\nWarnings:")
        for w in result['warnings']:
            print(f"  - {w}")


if __name__ == "__main__":
    asyncio.run(test_grok_extractor())
