# Enhanced Extraction Pipeline

## Overview

This extraction pipeline implements a **TEXT-FIRST, OCR-FALLBACK** strategy for maximum accuracy and efficiency when processing medical reports.

## Architecture

### 1. PDF Extraction (`pdf_extractor.py`)

**Strategy:**
1. **Text Extraction First** - Try `pdfplumber` → `PyMuPDF` for text-based PDFs
2. **OCR Fallback** - Only use `PaddleOCR` if text extraction yields insufficient results
3. **Threshold** - Text must be >= 300 chars OR contain lab patterns (hemoglobin, platelet, etc.)

**Methods:**
- `extract_text_pdfplumber()` - Best for clean text PDFs
- `extract_text_pymupdf()` - Alternative text extraction
- `extract_text_ocr()` - High-resolution OCR at 300 DPI with PaddleOCR
- `extract()` - Main method that orchestrates the strategy

**Returns:**
```python
ExtractionResult(
    full_text=str,          # Complete extracted text
    method=str,              # "text", "ocr", "hybrid", or "failed"
    page_stats=List[Dict],   # Per-page metadata
    total_chars=int,
    success=bool,
    error=Optional[str]
)
```

### 2. Lab Report Parser (`lab_parser.py`)

**Capabilities:**
- Parses typical lab report tables with columns: TEST NAME | RESULT | UNIT | REF RANGE | FLAG
- Handles various formatting patterns
- Maps test names to canonical keys using synonym dictionary
- Extracts reference ranges and flags (Low/High/Normal/Critical)
- Normalizes units (mg/dl → mg/dL, uL → µL, etc.)

**Metric Synonyms:**
```python
{
    "hemoglobin": ["hemoglobin", "hb", "hgb"],
    "platelet_count": ["platelet count", "platelets", "plt"],
    "wbc_total": ["total wbc count", "wbc", "white blood cell count"],
    "pt": ["pt", "prothrombin time"],
    "inr": ["inr"],
    # ... 30+ metrics
}
```

**Line Parsing Examples:**
```
"HEMOGLOBIN (HB) 12.8 13.0-17.0 g/dL" ✓
"PLATELET COUNT 143 150-410 thou/µL Low" ✓  
"PT 54.5 10.0-13.0 seconds High" ✓
"INR 4.60 0.8-1.2 Critical High" ✓
```

**Returns:**
```python
List[ParsedMetric(
    test_name=str,
    canonical_key=str,      # Normalized key
    value=float,
    unit=str,
    ref_range_low=Optional[float],
    ref_range_high=Optional[float],
    flag=Optional[str],
    page_num=int,
    raw_line=str
)]
```

### 3. Enhanced Report Service (`enhanced_report_service.py`)

**Full Pipeline:**
1. Update status → `EXTRACTING`
2. Extract text from PDF (text-first strategy)
3. Save extraction metadata (method, page_stats, text)
4. Parse lab metrics from text
5. Save observations to database
6. Update status → `PROCESSED`
7. Emit WebSocket events

**WebSocket Events Emitted:**
- `report_processing_started` - With progress %
- `report_parsed` - With metrics count and status
- `reports_list_updated` - Triggers dashboard refresh

### 4. Database Schema

**New Fields in `reports` table:**
- `extraction_method` VARCHAR - "text", "ocr", "hybrid", or "failed"
- `page_stats` JSONB - Per-page extraction statistics

**New Fields in `observations` table:**
- `display_name` VARCHAR - Original test name from report
- `flag` VARCHAR - "Low", "High", "Normal", "Critical"
- `raw_line` TEXT - Original line from report
- `page_num` INTEGER - Page number in report

## API Endpoints

### GET /api/reports/{id}/debug

Returns detailed extraction debug information:

```json
{
  "report_id": "uuid",
  "status": "processed",
  "extraction_method": "text",
  "page_stats": [
    {
      "page": 1,
      "method": "text",
      "chars": 2456,
      "lines": 98
    }
  ],
  "text_preview": "First 2500 chars...",
  "text_length": 12000,
  "extracted_metrics_count": 24,
  "extraction_confidence": 0.9,
  "failure_reason": null,
  "processed_at": "2026-01-31T10:30:00Z"
}
```

### POST /api/reports/upload

Enhanced upload with background processing:
- Saves PDF to disk
- Creates report record
- Triggers `EnhancedReportService.process_report()` in background
- Emits WebSocket events

## Testing

### Smoke Test Script

```bash
python scripts/ocr_smoke_test.py path/to/sample_report.pdf
```

**Output:**
- Extraction method and statistics
- Text preview
- Parsed metrics table
- Coverage of expected metrics (hemoglobin, WBC, RBC, etc.)
- Pass/Fail verdict

**Expected Coverage:**
- ✓ PASS: >= 80% of expected metrics found
- ⚠ PARTIAL: >= 50% found
- ✗ FAIL: < 50% found

### Manual Testing

1. Upload a lab report via `/api/reports/upload`
2. Check debug info: `GET /api/reports/{id}/debug`
3. Verify observations: `GET /api/observations?report_id={id}`
4. Check WebSocket events in browser DevTools

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run database migration
python migrate_extraction_fields.py

# Test extraction locally
python scripts/ocr_smoke_test.py uploads/sample.pdf
```

## Performance

**Text Extraction:**
- Speed: ~0.5-2 seconds per page
- Accuracy: 99%+ for text-based PDFs
- Works with: Most lab reports from electronic systems

**OCR Fallback:**
- Speed: ~5-10 seconds per page at 300 DPI
- Accuracy: 85-95% depending on image quality
- Works with: Scanned documents, photos of reports

**Memory:**
- Text extraction: ~10-50 MB
- OCR: ~200-500 MB (PaddleOCR models)

## Troubleshooting

### No metrics extracted
1. Check `/api/reports/{id}/debug` for extraction method
2. If method is "failed", check `failure_reason`
3. If method is "text" but no metrics, text may not contain lab data
4. If method is "ocr" but poor results, try higher DPI or manual entry

### Low extraction confidence
- Text-based PDFs: 0.9+ confidence
- OCR-based: 0.6-0.8 confidence
- If OCR confidence < 0.5, recommend manual review

### Unmapped metrics
- Check `raw_line` in database
- Add synonyms to `LabParser.METRIC_SYNONYMS`
- Or mark as "unmapped" and handle separately

## Future Enhancements

- [ ] Support for other report types (imaging, pathology)
- [ ] Multi-language OCR support
- [ ] Machine learning for metric extraction
- [ ] Confidence-based UI warnings
- [ ] Batch processing for multiple reports
- [ ] Export to HL7 FHIR format
