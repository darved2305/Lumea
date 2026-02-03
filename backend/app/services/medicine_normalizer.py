"""
Medicine Normalizer Service

DATA-DRIVEN medicine text parsing with DB lookup support.
NO hardcoded brand mappings - all lookups come from database.
Graceful degradation when data is missing.
"""
import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

logger = logging.getLogger(__name__)


# Common dosage forms (expanded)
DOSAGE_FORMS = {
    'tablet': ['tablet', 'tab', 'tabs', 'tablets', 'tbl'],
    'capsule': ['capsule', 'cap', 'caps', 'capsules'],
    'syrup': ['syrup', 'syr', 'suspension', 'susp', 'liquid', 'oral solution', 'solution'],
    'injection': ['injection', 'inj', 'vial', 'amp', 'ampoule', 'iv', 'im', 'injectable'],
    'cream': ['cream', 'ointment', 'gel', 'lotion', 'topical'],
    'drops': ['drops', 'drop', 'eye drops', 'ear drops', 'nasal drops'],
    'inhaler': ['inhaler', 'rotacap', 'respule', 'nebulizer', 'puff'],
    'powder': ['powder', 'sachet', 'granules'],
    'patch': ['patch', 'transdermal'],
    'spray': ['spray', 'nasal spray'],
}

# Release type patterns (expanded)
RELEASE_PATTERNS = {
    'SR': ['sr', 's.r.', 's.r', 'sustained release', 'sustained-release'],
    'ER': ['er', 'e.r.', 'e.r', 'extended release', 'extended-release'],
    'CR': ['cr', 'c.r.', 'c.r', 'controlled release', 'controlled-release'],
    'MR': ['mr', 'm.r.', 'modified release', 'modified-release'],
    'DR': ['dr', 'd.r.', 'delayed release', 'delayed-release'],
    'IR': ['ir', 'i.r.', 'immediate release', 'immediate-release'],
    'XL': ['xl', 'x.l.', 'extra long'],
    'XR': ['xr', 'x.r.', 'extended release'],
}

# Strength patterns (handles multiple strengths for combo drugs)
STRENGTH_PATTERN = re.compile(
    r'(\d+(?:\.\d+)?)\s*(mg|mcg|µg|g|ml|iu|%|gm|gram|milligram|microgram|unit|u)',
    re.IGNORECASE
)


@dataclass
class NormalizedMedicine:
    """Normalized medicine data structure with full parsing details"""
    raw_line: str
    cleaned_name: str
    brand_name: Optional[str]
    salts: List[str]  # Can be multiple for combo drugs
    strength_value: Optional[float]
    strength_unit: Optional[str]
    strength: Optional[str]  # Combined string for display
    form: Optional[str]
    release_type: Optional[str]
    confidence: float
    needs_user_confirmation: bool
    missing_fields: List[str]
    parse_method: str  # 'db_lookup', 'regex_parse', 'llm_fallback'
    suggestions: List[str]  # User-facing suggestions
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'raw_line': self.raw_line,
            'cleaned_name': self.cleaned_name,
            'brand_name': self.brand_name,
            'salt': ' + '.join(self.salts) if self.salts else None,  # Legacy field
            'salts': self.salts,
            'strength_value': self.strength_value,
            'strength_unit': self.strength_unit,
            'strength': self.strength,
            'form': self.form,
            'release_type': self.release_type,
            'confidence': self.confidence,
            'needs_user_confirmation': self.needs_user_confirmation,
            'missing_fields': self.missing_fields,
            'parse_method': self.parse_method,
            'suggestions': self.suggestions,
        }


class MedicineNormalizer:
    """
    DATA-DRIVEN medicine normalizer with DB lookup.
    NO hardcoded brand mappings - uses generic_catalog table.
    """
    
    def __init__(self, db: Optional[AsyncSession] = None):
        """
        Initialize normalizer with optional database session.
        If DB provided, will attempt DB lookup for brand→salt.
        """
        self.db = db
    
    async def normalize(self, text: str) -> NormalizedMedicine:
        """
        Normalize medicine text using regex + optional DB lookup.
        
        Args:
            text: Raw medicine text (e.g., "Glycomet 500 SR", "Paracetamol 650mg")
            
        Returns:
            NormalizedMedicine with extracted + inferred fields
        """
        if not text or not text.strip():
            return self._empty_result(text or '')
        
        text = text.strip()
        text_lower = text.lower()
        
        # Clean up common prefixes
        cleaned = re.sub(r'^(tab\.?|cap\.?|inj\.?|syr\.?|dr\.?)\s*', '', text, flags=re.IGNORECASE).strip()
        
        # Extract components using regex
        brand_name = self._extract_brand_name(cleaned)
        strength_info = self._extract_strength(cleaned)
        form = self._extract_form(text_lower)
        release_type = self._extract_release_type(text_lower)
        
        # Try DB lookup if database available
        salts = []
        parse_method = 'regex_parse'
        
        if self.db and brand_name:
            db_result = await self._lookup_in_db(brand_name, strength_info.get('strength'))
            if db_result:
                salts = db_result['salts']
                # If DB has better info, use it
                if db_result.get('form') and not form:
                    form = db_result['form']
                if db_result.get('release_type') and not release_type:
                    release_type = db_result['release_type']
                parse_method = 'db_lookup'
        
        # Fallback: try to extract salt from text if DB lookup failed
        if not salts:
            salts = self._extract_salts_from_text(cleaned, brand_name)
        
        # Calculate confidence
        confidence, missing_fields, suggestions = self._calculate_confidence(
            salts, strength_info, form, release_type
        )
        
        return NormalizedMedicine(
            raw_line=text,
            cleaned_name=cleaned,
            brand_name=brand_name,
            salts=salts,
            strength_value=strength_info.get('value'),
            strength_unit=strength_info.get('unit'),
            strength=strength_info.get('strength'),
            form=form,
            release_type=release_type,
            confidence=confidence,
            needs_user_confirmation=confidence < 0.7 or len(missing_fields) > 0,
            missing_fields=missing_fields,
            parse_method=parse_method,
            suggestions=suggestions,
        )
    
    async def normalize_batch(self, texts: List[str]) -> List[NormalizedMedicine]:
        """Normalize multiple medicine texts."""
        results = []
        for text in texts:
            result = await self.normalize(text)
            results.append(result)
        return results
    
    async def _lookup_in_db(self, brand_query: str, strength: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Look up medicine in generic_catalog by brand/product name.
        Returns salts, form, release_type if found.
        """
        if not self.db:
            return None
        
        try:
            from app.models import GenericCatalog
            
            # Try exact match first
            query = select(GenericCatalog).where(
                func.lower(GenericCatalog.product_name).contains(brand_query.lower())
            )
            
            # Add strength filter if provided
            if strength:
                query = query.where(
                    func.lower(GenericCatalog.strength).contains(strength.lower())
                )
            
            query = query.limit(1)
            result = await self.db.execute(query)
            medicine = result.scalar_one_or_none()
            
            if medicine:
                # Extract salts (handle combo drugs with +)
                salt_str = medicine.salt or ''
                salts = [s.strip().title() for s in salt_str.split('+') if s.strip()]
                
                return {
                    'salts': salts,
                    'form': medicine.form,
                    'release_type': medicine.release_type,
                    'strength': medicine.strength,
                }
        except Exception as e:
            logger.warning(f"DB lookup failed for '{brand_query}': {e}")
        
        return None
    
    def _extract_brand_name(self, text: str) -> Optional[str]:
        """Extract potential brand/product name (usually first word or words before strength)."""
        # Get text before first number (likely the brand)
        match = re.match(r'^([a-zA-Z\s\-]+?)(?:\s*\d)', text)
        if match:
            brand = match.group(1).strip()
            if brand and len(brand) > 1:
                return brand.title()
        
        # Fallback: first word
        words = text.split()
        if words:
            brand = words[0]
            brand = re.sub(r'[^\w\s-]', '', brand)
            if brand and len(brand) > 1:
                return brand.title()
        
        return None
    
    def _extract_salts_from_text(self, text: str, brand_name: Optional[str]) -> List[str]:
        """
        Try to extract salt names from text.
        Looks for chemical-sounding words after removing brand name.
        """
        if brand_name:
            # Remove brand name to see what's left
            text_without_brand = text.replace(brand_name, '').strip()
        else:
            text_without_brand = text
        
        # Common patterns: word ending in -in, -ol, -ide, -ate, -pril, etc.
        salt_pattern = re.compile(
            r'\b([A-Z][a-z]+(?:in|ol|ide|ate|pril|sartan|floxacin|mycin|cillin|zole|tidine|vastatin|gliptin|gliflozin|ipine|pressin|phylline|tropine|amine|barbital))\b'
        )
        
        matches = salt_pattern.findall(text_without_brand)
        if matches:
            return [m.title() for m in matches]
        
        # If text is chemical name without brand (e.g., "Paracetamol 500mg")
        # First word might be the salt
        words = text_without_brand.split()
        if words and len(words[0]) > 4 and words[0][0].isupper():
            return [words[0].title()]
        
        return []
    
    def _extract_strength(self, text: str) -> Dict[str, Any]:
        """
        Extract strength value + unit.
        Returns dict with 'value', 'unit', 'strength' (formatted string).
        """
        matches = STRENGTH_PATTERN.findall(text)
        if matches:
            # Handle combo drugs (multiple strengths)
            strengths = []
            first_value = None
            first_unit = None
            
            for value_str, unit in matches:
                value = float(value_str)
                unit_normalized = unit.lower().replace('gram', 'g').replace('milligram', 'mg').replace('microgram', 'mcg')
                strengths.append(f"{value_str}{unit_normalized}")
                
                if first_value is None:
                    first_value = value
                    first_unit = unit_normalized
            
            strength_str = ' + '.join(strengths)
            
            return {
                'value': first_value,
                'unit': first_unit,
                'strength': strength_str,
            }
        
        return {'value': None, 'unit': None, 'strength': None}
    
    def _extract_form(self, text_lower: str) -> Optional[str]:
        """Extract dosage form from text."""
        for form, keywords in DOSAGE_FORMS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return form
        
        # Default to tablet (most common) only if other indicators present
        # Don't assume if text is very short
        if len(text_lower) > 10:
            return 'tablet'
        
        return None
    
    def _extract_release_type(self, text_lower: str) -> Optional[str]:
        """Extract release type (SR/ER/CR/etc.)."""
        for release, keywords in RELEASE_PATTERNS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return release
        return None
    
    def _calculate_confidence(
        self,
        salts: List[str],
        strength_info: Dict[str, Any],
        form: Optional[str],
        release_type: Optional[str]
    ) -> Tuple[float, List[str], List[str]]:
        """
        Calculate confidence score and identify missing fields.
        Returns (confidence, missing_fields, suggestions).
        """
        confidence_factors = []
        missing_fields = []
        suggestions = []
        
        # Salt is most critical
        if salts:
            confidence_factors.append(0.5)
        else:
            missing_fields.append('salt')
            suggestions.append("Unable to identify active ingredient - please verify medicine name")
        
        # Strength is important
        if strength_info.get('strength'):
            confidence_factors.append(0.3)
        else:
            missing_fields.append('strength')
            suggestions.append("Strength not found - alternatives may include multiple strengths")
        
        # Form is helpful
        if form:
            confidence_factors.append(0.15)
        else:
            missing_fields.append('form')
            suggestions.append("Dosage form unclear - will search across forms")
        
        # Release type optional
        if release_type:
            confidence_factors.append(0.05)
        
        confidence = sum(confidence_factors)
        return round(confidence, 2), missing_fields, suggestions
    
    def _empty_result(self, text: str) -> NormalizedMedicine:
        """Return empty normalized result for invalid input."""
        return NormalizedMedicine(
            raw_line=text,
            cleaned_name='',
            brand_name=None,
            salts=[],
            strength_value=None,
            strength_unit=None,
            strength=None,
            form=None,
            release_type=None,
            confidence=0.0,
            needs_user_confirmation=True,
            missing_fields=['salt', 'strength', 'form'],
            parse_method='none',
            suggestions=["Please enter a valid medicine name"],
        )


# Singleton pattern removed - must pass db session
# Use: normalizer = MedicineNormalizer(db=session)
