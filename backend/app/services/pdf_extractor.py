"""
PDF Extraction Service - TEXT-FIRST with OCR Fallback

Strategy:
1. Try text extraction first (pdfplumber/PyMuPDF)
2. Only use OCR if text is insufficient
3. Store method used + debug info
"""
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import io

logger = logging.getLogger(__name__)

@dataclass
class PageExtraction:
    page_num: int
    text: str
    method: str  # "text" or "ocr"
    char_count: int
    line_count: int
    avg_confidence: Optional[float] = None

@dataclass
class ExtractionResult:
    full_text: str
    method: str  # "text", "ocr", "hybrid"
    page_stats: List[Dict]
    total_chars: int
    success: bool
    error: Optional[str] = None


class PDFExtractor:
    """
    Hybrid PDF text extractor with TEXT-FIRST strategy
    """
    
    TEXT_MIN_THRESHOLD = 300  # Minimum chars to consider text extraction successful
    
    def __init__(self):
        self.pdfplumber = None
        self.fitz = None
        self.paddleocr = None
        
    def _lazy_import_pdfplumber(self):
        """Lazy import pdfplumber"""
        if self.pdfplumber is None:
            try:
                import pdfplumber
                self.pdfplumber = pdfplumber
            except ImportError:
                logger.warning("pdfplumber not installed. Install: pip install pdfplumber")
        return self.pdfplumber
    
    def _lazy_import_fitz(self):
        """Lazy import PyMuPDF (fitz)"""
        if self.fitz is None:
            try:
                import fitz
                self.fitz = fitz
            except ImportError:
                logger.warning("PyMuPDF not installed. Install: pip install pymupdf")
        return self.fitz
    
    def _lazy_import_paddleocr(self):
        """Lazy import PaddleOCR"""
        if self.paddleocr is None:
            try:
                from paddleocr import PaddleOCR
                self.paddleocr = PaddleOCR(
                    use_angle_cls=False,  # Disable for speed
                    lang='en',
                    show_log=False,
                    use_gpu=False,
                    det_db_thresh=0.3,  # Lower threshold for faster detection
                    det_db_box_thresh=0.5
                )
            except ImportError:
                logger.warning("PaddleOCR not installed. Install: pip install paddleocr")
        return self.paddleocr
    
    def extract_text_pdfplumber(self, pdf_bytes: bytes) -> Tuple[str, List[PageExtraction]]:
        """
        Extract text using pdfplumber (best for text-based PDFs)
        """
        pdfplumber = self._lazy_import_pdfplumber()
        if not pdfplumber:
            return "", []
        
        pages_data = []
        full_text = []
        
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text() or ""
                    lines = [l.strip() for l in page_text.split('\n') if l.strip()]
                    
                    pages_data.append(PageExtraction(
                        page_num=i + 1,
                        text=page_text,
                        method="text",
                        char_count=len(page_text),
                        line_count=len(lines)
                    ))
                    
                    if page_text:
                        full_text.append(f"=== PAGE {i+1} ===\n{page_text}")
        
        except Exception as e:
            logger.error(f"pdfplumber extraction failed: {e}")
            return "", []
        
        return "\n\n".join(full_text), pages_data
    
    def extract_text_pymupdf(self, pdf_bytes: bytes) -> Tuple[str, List[PageExtraction]]:
        """
        Extract text using PyMuPDF (alternative to pdfplumber)
        """
        fitz = self._lazy_import_fitz()
        if not fitz:
            return "", []
        
        pages_data = []
        full_text = []
        
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                lines = [l.strip() for l in page_text.split('\n') if l.strip()]
                
                pages_data.append(PageExtraction(
                    page_num=page_num + 1,
                    text=page_text,
                    method="text",
                    char_count=len(page_text),
                    line_count=len(lines)
                ))
                
                if page_text:
                    full_text.append(f"=== PAGE {page_num+1} ===\n{page_text}")
            
            doc.close()
        
        except Exception as e:
            logger.error(f"PyMuPDF extraction failed: {e}")
            return "", []
        
        return "\n\n".join(full_text), pages_data
    
    def extract_text_ocr(self, pdf_bytes: bytes, dpi: int = 200) -> Tuple[str, List[PageExtraction]]:
        """
        Extract text using OCR (fallback for scanned PDFs)
        """
        fitz = self._lazy_import_fitz()
        ocr = self._lazy_import_paddleocr()
        
        if not fitz or not ocr:
            return "", []
        
        pages_data = []
        full_text = []
        
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Render page at 1.5x resolution for speed/quality balance
                mat = fitz.Matrix(1.5, 1.5)
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")
                
                # Run OCR
                ocr_result = ocr.ocr(img_bytes, cls=True)
                
                if not ocr_result or not ocr_result[0]:
                    pages_data.append(PageExtraction(
                        page_num=page_num + 1,
                        text="",
                        method="ocr",
                        char_count=0,
                        line_count=0,
                        avg_confidence=0.0
                    ))
                    continue
                
                # Extract text and confidence
                lines = []
                confidences = []
                
                for line in ocr_result[0]:
                    if len(line) >= 2:
                        text = line[1][0]
                        conf = line[1][1]
                        lines.append(text)
                        confidences.append(conf)
                
                page_text = "\n".join(lines)
                avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
                
                pages_data.append(PageExtraction(
                    page_num=page_num + 1,
                    text=page_text,
                    method="ocr",
                    char_count=len(page_text),
                    line_count=len(lines),
                    avg_confidence=avg_conf
                ))
                
                if page_text:
                    full_text.append(f"=== PAGE {page_num+1} ===\n{page_text}")
            
            doc.close()
        
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return "", []
        
        return "\n\n".join(full_text), pages_data
    
    def extract(self, pdf_bytes: bytes) -> ExtractionResult:
        """
        Main extraction method with TEXT-FIRST strategy
        
        Returns:
            ExtractionResult with full text and metadata
        """
        # Step 1: Try text extraction first
        logger.info("Attempting text extraction...")
        text, pages = self.extract_text_pdfplumber(pdf_bytes)
        
        if not text:
            logger.info("pdfplumber failed, trying PyMuPDF...")
            text, pages = self.extract_text_pymupdf(pdf_bytes)
        
        total_chars = sum(p.char_count for p in pages)
        
        # Check if text extraction was sufficient
        has_lab_patterns = any(
            keyword in text.lower() 
            for keyword in ['hemoglobin', 'platelet', 'wbc', 'rbc', 'test', 'result', 'range']
        )
        
        if total_chars >= self.TEXT_MIN_THRESHOLD or (total_chars > 100 and has_lab_patterns):
            logger.info(f"Text extraction successful: {total_chars} chars extracted")
            return ExtractionResult(
                full_text=text,
                method="text",
                page_stats=[{
                    "page": p.page_num,
                    "method": p.method,
                    "chars": p.char_count,
                    "lines": p.line_count
                } for p in pages],
                total_chars=total_chars,
                success=True
            )
        
        # Step 2: Fallback to OCR
        logger.info(f"Text extraction insufficient ({total_chars} chars), falling back to OCR...")
        ocr_text, ocr_pages = self.extract_text_ocr(pdf_bytes, dpi=300)
        
        if not ocr_text:
            return ExtractionResult(
                full_text="",
                method="failed",
                page_stats=[],
                total_chars=0,
                success=False,
                error="Both text and OCR extraction failed"
            )
        
        ocr_chars = sum(p.char_count for p in ocr_pages)
        avg_ocr_conf = sum(p.avg_confidence or 0 for p in ocr_pages) / len(ocr_pages) if ocr_pages else 0
        
        logger.info(f"OCR extraction successful: {ocr_chars} chars, avg confidence: {avg_ocr_conf:.2f}")
        
        return ExtractionResult(
            full_text=ocr_text,
            method="ocr" if total_chars == 0 else "hybrid",
            page_stats=[{
                "page": p.page_num,
                "method": p.method,
                "chars": p.char_count,
                "lines": p.line_count,
                "confidence": p.avg_confidence
            } for p in ocr_pages],
            total_chars=ocr_chars,
            success=True
        )
