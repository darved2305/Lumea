"""
PDFExtractor tests (backend/src/services/pdf_extractor.py).

These tests stub out the actual PDF/OCR libraries and focus on the
TEXT-FIRST decision logic.
"""

from src.services.pdf_extractor import PDFExtractor, PageExtraction


def test_extract_uses_text_when_threshold_met(monkeypatch):
    extractor = PDFExtractor()

    text = "hemoglobin\n" + ("x" * 400)
    pages = [PageExtraction(page_num=1, text=text, method="text", char_count=len(text), line_count=2)]

    monkeypatch.setattr(extractor, "extract_text_pdfplumber", lambda pdf_bytes: (text, pages))
    out = extractor.extract(b"%PDF-FAKE%")

    assert out.success is True
    assert out.method == "text"
    assert out.total_chars >= extractor.TEXT_MIN_THRESHOLD


def test_extract_falls_back_to_ocr_when_text_insufficient(monkeypatch):
    extractor = PDFExtractor()

    tiny_text = "x" * 10
    tiny_pages = [PageExtraction(page_num=1, text=tiny_text, method="text", char_count=len(tiny_text), line_count=1)]
    ocr_text = "OCR RESULT " + ("y" * 400)
    ocr_pages = [PageExtraction(page_num=1, text=ocr_text, method="ocr", char_count=len(ocr_text), line_count=2, avg_confidence=0.9)]

    monkeypatch.setattr(extractor, "extract_text_pdfplumber", lambda pdf_bytes: (tiny_text, tiny_pages))
    monkeypatch.setattr(extractor, "extract_text_pymupdf", lambda pdf_bytes: ("", []))
    monkeypatch.setattr(extractor, "extract_text_ocr", lambda pdf_bytes, dpi=300: (ocr_text, ocr_pages))

    out = extractor.extract(b"%PDF-FAKE%")

    assert out.success is True
    assert out.method in ("ocr", "hybrid")
    assert "OCR RESULT" in out.full_text
