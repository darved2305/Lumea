"""
Substitute Finder Service - UPGRADED

DATA-DRIVEN substitute matching with ranked results and match explanations.
Matches on: salts + strength + form + release_type with fallback logic.
Returns actual products from generic_catalog with match scores.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from sqlalchemy.sql import text

from app.models import GenericCatalog, SubstituteQuery, UserSavedMedicine

logger = logging.getLogger(__name__)


class SubstituteFinder:
    """
    Find substitute medicines using ranked matching algorithm.
    
    Matching Priority (from strictest to most lenient):
    1. Exact: same salts + strength + form + release_type (score 1.0)
    2. Near: same salts + strength + form, different/missing release (score 0.8)
    3. Partial: same salts + form, different strength (score 0.6) + warning
    4. Generic: same salts only (score 0.4) + strong warning
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def find_substitutes(
        self,
        salts: List[str],
        strength: Optional[str] = None,
        form: Optional[str] = None,
        release_type: Optional[str] = None,
        limit: int = 15
    ) -> Dict[str, Any]:
        """
        Find substitutes with ranked matching.
        
        Args:
            salts: List of active ingredients (e.g., ["Paracetamol"] or ["Ibuprofen", "Paracetamol"])
            strength: Dosage strength (e.g., "500mg", "500mg + 650mg")
            form: Dosage form (tablet, capsule, etc.)
            release_type: SR/ER/CR/None
            limit: Max results
            
        Returns:
            Dict with alternatives list and metadata
        """
        if not salts:
            return {
                "alternatives": [],
                "query_understood": False,
                "notes": ["Unable to identify active ingredient - please check medicine name"],
            }
        
        # Normalize inputs
        salt_query = self._normalize_salt_list(salts)
        strength_normalized = self._normalize_strength(strength) if strength else None
        form_normalized = form.lower().strip() if form else None
        release_normalized = release_type.upper().strip() if release_type else None
        
        # Try different match levels
        alternatives = []
        match_level = None
        
        # Level 1: Exact match (salts + strength + form + release)
        if strength_normalized and form_normalized:
            level1 = await self._find_exact_match(
                salt_query, strength_normalized, form_normalized, release_normalized, limit
            )
            if level1:
                alternatives = level1
                match_level = "exact"
        
        # Level 2: Near match (salts + strength + form, any release)
        if not alternatives and strength_normalized and form_normalized:
            level2 = await self._find_near_match(
                salt_query, strength_normalized, form_normalized, release_normalized, limit
            )
            if level2:
                alternatives = level2
                match_level = "near"
        
        # Level 3: Partial match (salts + form, any strength)
        if not alternatives and form_normalized:
            level3 = await self._find_partial_match(
                salt_query, form_normalized, limit
            )
            if level3:
                alternatives = level3
                match_level = "partial"
        
        # Level 4: Generic match (salts only)
        if not alternatives:
            level4 = await self._find_generic_match(salt_query, limit)
            if level4:
                alternatives = level4
                match_level = "generic"
        
        # Build response with notes
        notes = self._generate_notes(match_level, strength_normalized, form_normalized, release_normalized)
        
        return {
            "alternatives": alternatives,
            "query_understood": True,
            "match_level": match_level,
            "notes": notes,
        }
    
    async def _find_exact_match(
        self,
        salt_query: str,
        strength: str,
        form: str,
        release_type: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Find exact matches: same salt + strength + form + release."""
        query = select(GenericCatalog).where(
            and_(
                func.lower(GenericCatalog.salt).contains(salt_query.lower()),
                func.lower(GenericCatalog.strength) == strength.lower(),
                func.lower(GenericCatalog.form) == form.lower()
            )
        )
        
        if release_type:
            query = query.where(
                func.upper(GenericCatalog.release_type) == release_type
            )
        else:
            # No release type specified = match only IR/normal medicines
            query = query.where(
                or_(
                    GenericCatalog.release_type.is_(None),
                    GenericCatalog.release_type == "",
                    func.upper(GenericCatalog.release_type) == "IR",
                    func.upper(GenericCatalog.release_type) == "NORMAL"
                )
            )
        
        query = query.order_by(
            GenericCatalog.is_jan_aushadhi.desc(),
            GenericCatalog.mrp.asc().nullslast()
        ).limit(limit)
        
        result = await self.db.execute(query)
        medicines = result.scalars().all()
        
        return [self._medicine_to_dict(m, match_score=1.0, match_reasons=[
            "Same active ingredient(s)",
            "Same strength",
            "Same dosage form",
            "Same release type" if release_type else "Immediate release"
        ]) for m in medicines]
    
    async def _find_near_match(
        self,
        salt_query: str,
        strength: str,
        form: str,
        preferred_release: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Find near matches: same salt + strength + form, any release."""
        query = select(GenericCatalog).where(
            and_(
                func.lower(GenericCatalog.salt).contains(salt_query.lower()),
                func.lower(GenericCatalog.strength) == strength.lower(),
                func.lower(GenericCatalog.form) == form.lower()
            )
        )
        
        # Order preferred release first
        if preferred_release:
            query = query.order_by(
                (func.upper(GenericCatalog.release_type) == preferred_release).desc(),
                GenericCatalog.is_jan_aushadhi.desc(),
                GenericCatalog.mrp.asc().nullslast()
            )
        else:
            query = query.order_by(
                GenericCatalog.is_jan_aushadhi.desc(),
                GenericCatalog.mrp.asc().nullslast()
            )
        
        query = query.limit(limit)
        
        result = await self.db.execute(query)
        medicines = result.scalars().all()
        
        return [self._medicine_to_dict(m, match_score=0.8, match_reasons=[
            "Same active ingredient(s)",
            "Same strength",
            "Same dosage form",
            f"Release type: {m.release_type or 'IR'}" + (" (may differ)" if preferred_release else "")
        ]) for m in medicines]
    
    async def _find_partial_match(
        self,
        salt_query: str,
        form: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Find partial matches: same salt + form, any strength."""
        query = select(GenericCatalog).where(
            and_(
                func.lower(GenericCatalog.salt).contains(salt_query.lower()),
                func.lower(GenericCatalog.form) == form.lower()
            )
        ).order_by(
            GenericCatalog.is_jan_aushadhi.desc(),
            GenericCatalog.mrp.asc().nullslast()
        ).limit(limit)
        
        result = await self.db.execute(query)
        medicines = result.scalars().all()
        
        return [self._medicine_to_dict(m, match_score=0.6, match_reasons=[
            "Same active ingredient(s)",
            "Same dosage form",
            f" Different strength: {m.strength} (verify with doctor)"
        ]) for m in medicines]
    
    async def _find_generic_match(
        self,
        salt_query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Find generic matches: same salt only."""
        query = select(GenericCatalog).where(
            func.lower(GenericCatalog.salt).contains(salt_query.lower())
        ).order_by(
            GenericCatalog.is_jan_aushadhi.desc(),
            GenericCatalog.mrp.asc().nullslast()
        ).limit(limit)
        
        result = await self.db.execute(query)
        medicines = result.scalars().all()
        
        return [self._medicine_to_dict(m, match_score=0.4, match_reasons=[
            "Same active ingredient(s)",
            f" Form: {m.form}",
            f" Strength: {m.strength}",
            " Confirm details with pharmacist/doctor before using"
        ]) for m in medicines]
    
    def _generate_notes(
        self,
        match_level: Optional[str],
        strength: Optional[str],
        form: Optional[str],
        release_type: Optional[str]
    ) -> List[str]:
        """Generate user-facing notes based on match quality."""
        notes = []
        
        if not match_level:
            notes.append(" No alternatives found in our database for this medicine")
            if not strength:
                notes.append(" Try specifying the strength (e.g., 500mg)")
            if not form:
                notes.append(" Try specifying the form (tablet/capsule/syrup)")
            return notes
        
        # General disclaimer
        notes.append(" Always confirm with your doctor or pharmacist before switching medicines")
        
        if match_level == "exact":
            notes.append(" Found exact matches with same ingredients, strength, and form")
        elif match_level == "near":
            notes.append(" Found similar matches - verify release type")
        elif match_level == "partial":
            notes.append(" Showing alternatives with different strengths - doctor confirmation required")
        elif match_level == "generic":
            notes.append(" Limited information - showing all products with same ingredient")
            notes.append(" Please verify strength and form with healthcare professional")
        
        return notes
    
    async def find_substitutes_for_normalized(
        self,
        normalized: Dict[str, Any],
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Find substitutes for normalized medicine dict.
        Returns properly formatted response with alternatives.
        """
        salts = normalized.get("salts", [])
        if not salts and normalized.get("salt"):
            # Legacy support: split salt string
            salts = [s.strip() for s in normalized["salt"].split("+")]
        
        strength = normalized.get("strength")
        form = normalized.get("form")
        release_type = normalized.get("release_type")
        
        # Get alternatives
        result = await self.find_substitutes(
            salts=salts,
            strength=strength,
            form=form,
            release_type=release_type
        )
        
        # Build response
        response = {
            "query": normalized.get("raw_line", ""),
            "normalized": normalized,
            "alternatives": result["alternatives"],
            "count": len(result["alternatives"]),
            "match_level": result.get("match_level"),
            "notes": result.get("notes", []),
        }
        
        # Log query if user provided
        if user_id:
            try:
                query_log = SubstituteQuery(
                    user_id=user_id,
                    query_raw=normalized.get("raw_line", ""),
                    normalized_json=normalized,
                    results_json={"count": len(result["alternatives"]), "match_level": result.get("match_level")},
                    results_count=len(result["alternatives"])
                )
                self.db.add(query_log)
                await self.db.commit()
            except Exception as e:
                logger.error(f"Failed to log substitute query: {e}")
        
        return response
    
    async def find_substitutes_batch(
        self,
        normalized_list: List[Dict[str, Any]],
        user_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Find substitutes for multiple normalized medicines."""
        results = []
        for normalized in normalized_list:
            result = await self.find_substitutes_for_normalized(normalized, user_id)
            results.append(result)
        return results
    
    async def save_medicine_for_user(
        self,
        user_id: UUID,
        normalized: Dict[str, Any],
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Save medicine to user's list."""
        salts = normalized.get("salts", [])
        salt_str = " + ".join(salts) if salts else normalized.get("salt", "")
        
        saved = UserSavedMedicine(
            user_id=user_id,
            original_name=normalized.get("brand_name") or normalized.get("raw_line"),
            salt=salt_str,
            strength=normalized.get("strength", ""),
            form=normalized.get("form", "tablet"),
            release_type=normalized.get("release_type"),
            notes=notes
        )
        self.db.add(saved)
        await self.db.commit()
        await self.db.refresh(saved)
        
        return {
            "id": str(saved.id),
            "message": "Medicine saved successfully"
        }
    
    async def get_user_saved_medicines(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Get user's saved medicines."""
        result = await self.db.execute(
            select(UserSavedMedicine)
            .where(UserSavedMedicine.user_id == user_id)
            .order_by(UserSavedMedicine.created_at.desc())
        )
        medicines = result.scalars().all()
        
        return [{
            "id": str(m.id),
            "original_name": m.original_name,
            "salt": m.salt,
            "strength": m.strength,
            "form": m.form,
            "release_type": m.release_type,
            "notes": m.notes,
            "created_at": m.created_at.isoformat() if m.created_at else None
        } for m in medicines]
    
    def _normalize_salt_list(self, salts: List[str]) -> str:
        """Convert salt list to normalized search string."""
        if not salts:
            return ""
        # Join with + for combo drugs, remove extra spaces
        return "+".join(s.strip().title() for s in salts if s.strip())
    
    def _normalize_strength(self, strength: str) -> str:
        """Normalize strength for matching."""
        if not strength:
            return ""
        # Remove spaces, lowercase
        return strength.lower().strip().replace(" ", "")
    
    def _medicine_to_dict(
        self,
        medicine: GenericCatalog,
        match_score: float = 1.0,
        match_reasons: List[str] = None
    ) -> Dict[str, Any]:
        """Convert medicine model to dict with match info."""
        return {
            "id": str(medicine.id),
            "brand_name": medicine.product_name,
            "product_name": medicine.product_name,
            "salts": [s.strip() for s in medicine.salt.split("+") if s.strip()] if medicine.salt else [],
            "salt": medicine.salt,  # Legacy
            "strength": medicine.strength,
            "dosage_form": medicine.form,
            "form": medicine.form,  # Legacy
            "release_type": medicine.release_type,
            "price_mrp": float(medicine.mrp) if medicine.mrp else None,
            "mrp": float(medicine.mrp) if medicine.mrp else None,  # Legacy
            "manufacturer": medicine.manufacturer,
            "is_jan_aushadhi": medicine.is_jan_aushadhi,
            "source": medicine.source,
            "match_score": match_score,
            "match_reason": match_reasons or [],
        }
