"""
Medicines API Endpoints

Handles medicine normalization, substitute lookup, pharmacy search,
and user saved medicines functionality.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
import logging

from app.db import get_db
from app.security import get_current_user
from app.models import User
from app.services.medicine_normalizer import MedicineNormalizer
from app.services.substitute_finder import SubstituteFinder
from app.services.pharmacy_locator import PharmacyLocator
from app.services.grok_medicine_service import GrokMedicineService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/medicines", tags=["medicines"])


# ========================
# Request/Response Schemas
# ========================

class NormalizeMedicineRequest(BaseModel):
    """Request to normalize medicine text."""
    text: str = Field(..., description="Medicine text from prescription", min_length=1)

class NormalizeBatchRequest(BaseModel):
    """Request to normalize multiple medicine lines."""
    lines: List[str] = Field(..., description="List of medicine text lines")

class SubstituteRequest(BaseModel):
    """Request to find substitutes for a medicine."""
    salt: str = Field(..., description="Active ingredient/salt")
    strength: str = Field(..., description="Dosage strength (e.g., 500mg)")
    form: str = Field(..., description="Dosage form (tablet, capsule, etc.)")
    release_type: Optional[str] = Field(None, description="Release type (SR/ER/CR)")

class NormalizedMedicineResponse(BaseModel):
    """Response for normalized medicine."""
    brand_name: Optional[str]
    salt: Optional[str]
    strength: Optional[str]
    form: str
    release_type: Optional[str]
    raw_line: str
    confidence: float

class SubstituteItem(BaseModel):
    """A substitute medicine item."""
    id: str
    product_name: str
    salt: str
    strength: str
    form: str
    release_type: Optional[str]
    mrp: Optional[float]
    manufacturer: Optional[str]
    is_jan_aushadhi: bool
    source: Optional[str]

class SubstituteResponse(BaseModel):
    """Response with substitutes for a medicine."""
    original: NormalizedMedicineResponse
    substitutes: List[SubstituteItem]
    count: int
    disclaimer: str

class PharmacyItem(BaseModel):
    """A pharmacy item."""
    place_id: str
    name: str
    address: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    rating: Optional[float]
    total_ratings: Optional[int]
    is_open: Optional[bool]
    is_jan_aushadhi: bool

class PharmacySearchResponse(BaseModel):
    """Response for pharmacy search."""
    pharmacies: List[PharmacyItem]
    next_page_token: Optional[str]
    total: int

class SaveMedicineRequest(BaseModel):
    """Request to save a medicine to user's list."""
    brand_name: Optional[str] = None
    salt: str
    strength: str
    form: str = "tablet"
    release_type: Optional[str] = None
    notes: Optional[str] = None


# ====================
# Normalize Endpoints
# ====================

@router.post("/normalize", response_model=NormalizedMedicineResponse)
async def normalize_medicine(
    request: NormalizeMedicineRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Normalize a medicine text line.
    
    Extracts brand name, salt, strength, form, and release type
    from free-form prescription text using DB lookup.
    """
    normalizer = MedicineNormalizer(db=db)
    result = await normalizer.normalize(request.text)
    
    return {
        'brand_name': result.brand_name,
        'salt': ' + '.join(result.salts) if result.salts else None,
        'strength': result.strength,
        'form': result.form,
        'release_type': result.release_type,
        'raw_line': result.raw_line,
        'confidence': result.confidence
    }


@router.post("/normalize/batch", response_model=List[NormalizedMedicineResponse])
async def normalize_medicines_batch(
    request: NormalizeBatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Normalize multiple medicine text lines.
    
    Useful for processing an entire prescription page at once.
    """
    normalizer = MedicineNormalizer(db=db)
    results = await normalizer.normalize_batch(request.lines)
    
    return [{
        'brand_name': r.brand_name,
        'salt': ' + '.join(r.salts) if r.salts else None,
        'strength': r.strength,
        'form': r.form,
        'release_type': r.release_type,
        'raw_line': r.raw_line,
        'confidence': r.confidence
    } for r in results]


# =====================
# Substitute Endpoints
# =====================

@router.post("/substitutes", response_model=SubstituteResponse)
async def find_substitutes(
    request: SubstituteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Find generic substitutes for a medicine.
    
    Searches the generic catalog for medicines matching:
    - Same salt (active ingredient)
    - Same strength
    - Same form (tablet/capsule/etc)
    - Same release type if specified (SR/ER/CR)
    
    Results are sorted with Jan Aushadhi medicines first (cheapest),
    then by MRP.
    """
    finder = SubstituteFinder(db)
    
    normalized = {
        'salt': request.salt,
        'strength': request.strength,
        'form': request.form,
        'release_type': request.release_type,
        'raw_line': f"{request.salt} {request.strength}"
    }
    
    result = await finder.find_substitutes_for_normalized(
        normalized,
        user_id=current_user.id
    )
    
    return {
        'original': {
            'brand_name': None,
            'salt': request.salt,
            'strength': request.strength,
            'form': request.form,
            'release_type': request.release_type,
            'raw_line': f"{request.salt} {request.strength}",
            'confidence': 1.0
        },
        'substitutes': result['substitutes'],
        'count': result['count'],
        'disclaimer': result['disclaimer']
    }


@router.post("/substitutes/from-text")
async def find_substitutes_from_text(
    text: str = Form(..., description="Medicine text from prescription"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Find substitutes directly from prescription text using Grok AI.
    
    Uses Grok API to:
    1. Parse and normalize medicine text
    2. Find cheaper alternatives intelligently
    3. Provide match scores and explanations
    """
    try:
        # Use Grok AI for end-to-end intelligence
        grok_service = GrokMedicineService()
        result = await grok_service.get_alternatives_for_text(text)
        
        return result
        
    except Exception as e:
        logger.error(f"Error finding substitutes with Grok: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to find alternatives: {str(e)}"
        )


# ====================
# Pharmacy Endpoints
# ====================

@router.get("/pharmacies/nearby", response_model=PharmacySearchResponse)
async def search_nearby_pharmacies(
    latitude: float = Query(..., description="User latitude"),
    longitude: float = Query(..., description="User longitude"),
    radius: int = Query(5000, description="Search radius in meters", ge=100, le=50000),
    pharmacy_type: str = Query("all", description="Filter: all, jan_aushadhi, generic"),
    page_token: Optional[str] = Query(None, description="Pagination token"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Search for nearby pharmacies.
    
    Uses Google Places API to find pharmacies near the user's location.
    Highlights Jan Aushadhi Kendras which sell medicines at government-fixed prices.
    """
    locator = PharmacyLocator(db)
    result = await locator.search_nearby(
        latitude=latitude,
        longitude=longitude,
        radius_meters=radius,
        pharmacy_type=pharmacy_type,
        page_token=page_token
    )
    
    return {
        'pharmacies': result['pharmacies'],
        'next_page_token': result.get('next_page_token'),
        'total': result['total']
    }


@router.get("/pharmacies/{place_id}")
async def get_pharmacy_details(
    place_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a pharmacy.
    
    Returns address, phone, hours, ratings, and directions URL.
    """
    locator = PharmacyLocator(db)
    details = await locator.get_place_details(place_id)
    return details


@router.post("/pharmacies/{place_id}/click")
async def log_pharmacy_click(
    place_id: str,
    action: str = Query("directions", description="Action type: directions, call, website"),
    latitude: Optional[float] = Query(None, description="User latitude for analytics"),
    longitude: Optional[float] = Query(None, description="User longitude for analytics"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Log when a user clicks on a pharmacy.
    
    Used for analytics to understand user behavior.
    """
    locator = PharmacyLocator(db)
    await locator.log_pharmacy_click(
        user_id=current_user.id,
        place_id=place_id,
        action=action,
        latitude=latitude,
        longitude=longitude
    )
    return {"status": "logged"}


# =============================
# Saved Medicines Endpoints
# =============================

@router.post("/saved")
async def save_medicine(
    request: SaveMedicineRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Save a medicine to user's personal list.
    
    Users can save medicines they frequently need to buy
    for quick access to substitutes.
    """
    finder = SubstituteFinder(db)
    
    normalized = {
        'brand_name': request.brand_name,
        'salt': request.salt,
        'strength': request.strength,
        'form': request.form,
        'release_type': request.release_type,
        'raw_line': f"{request.brand_name or ''} {request.salt} {request.strength}".strip()
    }
    
    result = await finder.save_medicine_for_user(
        user_id=current_user.id,
        normalized=normalized,
        notes=request.notes
    )
    
    return result


@router.get("/saved")
async def get_saved_medicines(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's saved medicines list.
    """
    finder = SubstituteFinder(db)
    medicines = await finder.get_user_saved_medicines(current_user.id)
    return {"medicines": medicines, "count": len(medicines)}


@router.delete("/saved/{medicine_id}")
async def delete_saved_medicine(
    medicine_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a medicine from user's saved list.
    """
    from sqlalchemy import delete
    from app.models import UserSavedMedicine
    
    result = await db.execute(
        delete(UserSavedMedicine).where(
            UserSavedMedicine.id == medicine_id,
            UserSavedMedicine.user_id == current_user.id
        )
    )
    await db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Medicine not found")
    
    return {"status": "deleted"}


# =====================
# OCR Extract Endpoint
# =====================

@router.post("/extract-from-image")
async def extract_medicines_from_image(
    file: UploadFile = File(..., description="Image of prescription"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Extract and normalize medicines from a prescription image.
    
    Uses OCR to extract text, then normalizes each medicine line.
    Returns normalized medicines with substitute counts.
    """
    import io
    from pathlib import Path
    
    # Validate file type
    allowed_types = {'.png', '.jpg', '.jpeg', '.pdf', '.tiff', '.bmp'}
    file_ext = Path(file.filename).suffix.lower() if file.filename else ''
    
    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_types)}"
        )
    
    # Read file
    content = await file.read()
    
    try:
        # Try to use existing OCR services
        from app.services.pdf_extractor import PDFTextExtractor
        
        extractor = PDFTextExtractor()
        
        # For images, we'd need image OCR
        if file_ext == '.pdf':
            text = await extractor.extract_text(io.BytesIO(content))
        else:
            # For images, try direct OCR
            try:
                from paddleocr import PaddleOCR
                import numpy as np
                from PIL import Image
                
                ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
                image = Image.open(io.BytesIO(content))
                image_np = np.array(image)
                
                result = ocr.ocr(image_np, cls=True)
                
                # Extract text lines
                lines = []
                if result and result[0]:
                    for line in result[0]:
                        if len(line) >= 2:
                            text_content = line[1][0] if isinstance(line[1], tuple) else line[1]
                            lines.append(text_content)
                
                text = '\n'.join(lines)
                
            except ImportError:
                # Fallback: return error if OCR not available
                raise HTTPException(
                    status_code=503,
                    detail="OCR service not available. Please install paddleocr."
                )
    except Exception as e:
        logger.error(f"OCR extraction error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract text from image: {str(e)}"
        )
    
    # Normalize extracted text using Grok AI
    try:
        from app.services.grok_medicine_service import GrokMedicineService
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Filter lines that look like medicines (basic heuristics)
        medicine_lines = []
        for line in lines:
            # Skip very short lines or headers
            if len(line) < 3:
                continue
            # Skip common non-medicine patterns
            if any(keyword in line.lower() for keyword in ['patient', 'date:', 'doctor', 'clinic', 'advice', 'investigation']):
                continue
            # Look for medicine-like patterns (has numbers, dosage terms, or medicine indicators)
            if any(char.isdigit() for char in line) or any(keyword in line.lower() for keyword in ['tab', 'cap', 'mg', 'ml', 'syrup', 'inj']):
                medicine_lines.append(line)
        
        # Use Grok to parse each medicine line
        grok_service = GrokMedicineService()
        medicines = []
        
        for line in medicine_lines[:10]:  # Limit to first 10 medicine lines
            try:
                parsed = await grok_service.parse_medicine(line)
                if parsed.salts and parsed.confidence >= 0.3:
                    medicines.append({
                        'brand_name': parsed.brand_name,
                        'generic_name': parsed.generic_name,
                        'salts': parsed.salts,
                        'strength': parsed.strength,
                        'dosage_form': parsed.dosage_form,
                        'release_type': parsed.release_type,
                        'raw_line': line,
                        'confidence': parsed.confidence
                    })
            except Exception as e:
                logger.warning(f"Failed to parse medicine line '{line}': {e}")
                continue
        
        return {
            'extracted_text': text[:2000],  # Truncate for response
            'medicines': medicines,
            'count': len(medicines)
        }
    
    except Exception as e:
        logger.error(f"Medicine normalization error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to normalize medicines: {str(e)}"
        )
