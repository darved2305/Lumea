"""
OCR Smoke Test

Tests the extraction and parsing pipeline locally without database
"""
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.pdf_extractor import PDFExtractor
from src.services.lab_parser import LabParser


def test_sample_report(pdf_path: str):
    """
    Test extraction and parsing on a sample PDF
    """
    print(f"Testing extraction on: {pdf_path}\n")
    
    if not os.path.exists(pdf_path):
        print(f"ERROR: File not found: {pdf_path}")
        return False
    
    # Read PDF
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()
    
    print(f"PDF size: {len(pdf_bytes)} bytes\n")
    
    # Step 1: Extract text
    print("=" * 60)
    print("STEP 1: TEXT EXTRACTION")
    print("=" * 60)
    
    extractor = PDFExtractor()
    result = extractor.extract(pdf_bytes)
    
    if not result.success:
        print(f"❌ EXTRACTION FAILED: {result.error}")
        return False
    
    print(f"✓ Extraction method: {result.method}")
    print(f"✓ Total characters: {result.total_chars}")
    print(f"✓ Pages: {len(result.page_stats)}")
    print()
    
    for page in result.page_stats:
        print(f"  Page {page['page']}: {page['chars']} chars via {page['method']}")
        if 'confidence' in page:
            print(f"    OCR confidence: {page['confidence']:.2f}")
    
    print()
    print("Text preview (first 500 chars):")
    print("-" * 60)
    print(result.full_text[:500])
    print("-" * 60)
    print()
    
    # Step 2: Parse metrics
    print("=" * 60)
    print("STEP 2: LAB METRIC PARSING")
    print("=" * 60)
    
    parser = LabParser()
    metrics = parser.parse(result.full_text)
    
    print(f"✓ Parsed {len(metrics)} metrics\n")
    
    if not metrics:
        print("❌ WARNING: No metrics extracted!")
        print("\nFull extracted text:")
        print("=" * 60)
        print(result.full_text)
        print("=" * 60)
        return False
    
    # Group by mapped vs unmapped
    mapped = [m for m in metrics if m.canonical_key != "unmapped"]
    unmapped = [m for m in metrics if m.canonical_key == "unmapped"]
    
    print(f"Mapped metrics: {len(mapped)}")
    print(f"Unmapped metrics: {len(unmapped)}")
    print()
    
    # Display mapped metrics
    if mapped:
        print("MAPPED METRICS:")
        print("-" * 100)
        print(f"{'Test Name':<30} {'Key':<20} {'Value':<10} {'Unit':<10} {'Ref Range':<15} {'Flag':<10}")
        print("-" * 100)
        
        for m in mapped:
            ref_range = ""
            if m.ref_range_low is not None and m.ref_range_high is not None:
                ref_range = f"{m.ref_range_low}-{m.ref_range_high}"
            elif m.ref_range_low is not None:
                ref_range = f">{m.ref_range_low}"
            elif m.ref_range_high is not None:
                ref_range = f"<{m.ref_range_high}"
            
            flag = m.flag or "-"
            
            print(f"{m.test_name[:28]:<30} {m.canonical_key[:18]:<20} {m.value:<10.2f} {m.unit[:8]:<10} {ref_range:<15} {flag:<10}")
        
        print("-" * 100)
        print()
    
    # Display unmapped metrics
    if unmapped:
        print(f"UNMAPPED METRICS ({len(unmapped)}):")
        print("-" * 80)
        for m in unmapped[:10]:  # Show first 10
            print(f"  {m.test_name}: {m.value} {m.unit}")
        if len(unmapped) > 10:
            print(f"  ... and {len(unmapped) - 10} more")
        print("-" * 80)
        print()
    
    # Validation
    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)
    
    expected_metrics = [
        "hemoglobin", "wbc_total", "rbc_count", "platelet_count",
        "hematocrit", "mcv", "mch", "mchc", "rdw", "mpv",
        "neutrophils", "lymphocytes",
        "pt", "inr",
        "creatinine", "sodium", "potassium", "chloride"
    ]
    
    found_keys = {m.canonical_key for m in mapped}
    
    print("Expected metrics status:")
    for expected in expected_metrics:
        status = "✓" if expected in found_keys else "✗"
        print(f"  {status} {expected}")
    
    found_count = sum(1 for exp in expected_metrics if exp in found_keys)
    coverage = (found_count / len(expected_metrics)) * 100
    
    print()
    print(f"Coverage: {found_count}/{len(expected_metrics)} ({coverage:.1f}%)")
    
    if coverage >= 80:
        print("✓ PASS: Good coverage")
        return True
    elif coverage >= 50:
        print("⚠ PARTIAL: Moderate coverage")
        return True
    else:
        print("❌ FAIL: Poor coverage")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/ocr_smoke_test.py <path_to_pdf>")
        print("\nExample:")
        print("  python scripts/ocr_smoke_test.py uploads/sample_lab_report.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    success = test_sample_report(pdf_path)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
