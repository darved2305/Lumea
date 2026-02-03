"""
Grok API Service for Medicine Intelligence
Uses Grok AI to parse medicine names and find cheaper alternatives
"""

import os
import json
from typing import List, Dict, Optional, Any
import httpx
from pydantic import BaseModel


class MedicineInfo(BaseModel):
    """Structured medicine information from Grok"""
    brand_name: str
    generic_name: Optional[str] = None
    salts: List[str]
    strength: Optional[str] = None
    dosage_form: Optional[str] = None
    release_type: Optional[str] = None
    confidence: float = 0.0


class Alternative(BaseModel):
    """Medicine alternative with details"""
    brand_name: str
    manufacturer: str
    salts: List[str]
    strength: str
    dosage_form: str
    release_type: Optional[str] = None
    price_mrp: float
    is_jan_aushadhi: bool
    match_score: float
    match_reason: List[str]


class GrokMedicineService:
    """Service to interact with Grok API for medicine intelligence"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.3-70b-versatile"  # Grok's best model
    
    async def parse_medicine(self, medicine_text: str) -> MedicineInfo:
        """
        Parse medicine text using Grok AI
        
        Args:
            medicine_text: Raw medicine name/description
            
        Returns:
            MedicineInfo with structured data
        """
        prompt = f"""You are a pharmaceutical expert AI. Parse this medicine text and extract structured information.

Medicine text: "{medicine_text}"

Extract the following information:
1. Brand name (if mentioned)
2. Generic name (if known)
3. Active ingredient(s)/salt(s) - MUST extract this
4. Strength (e.g., 500mg, 10mg)
5. Dosage form (tablet, capsule, syrup, etc.)
6. Release type (SR/sustained, XR/extended, MR/modified, or null)

Return ONLY a JSON object with this exact structure:
{{
    "brand_name": "recognized brand or medicine name",
    "generic_name": "generic/INN name or null",
    "salts": ["active ingredient 1", "active ingredient 2"],
    "strength": "500mg" or null,
    "dosage_form": "tablet" or null,
    "release_type": "SR" or null,
    "confidence": 0.0-1.0 (how confident are you in this parse)
}}

Examples:
- "Paracetamol 500mg" → {{"brand_name": "Paracetamol", "salts": ["Paracetamol"], "strength": "500mg", "dosage_form": "tablet", "confidence": 0.95}}
- "Crocin" → {{"brand_name": "Crocin", "generic_name": "Paracetamol", "salts": ["Paracetamol"], "strength": "500mg", "dosage_form": "tablet", "confidence": 0.9}}
- "Metformin SR 500" → {{"brand_name": "Metformin SR", "salts": ["Metformin"], "strength": "500mg", "release_type": "SR", "dosage_form": "tablet", "confidence": 0.95}}

Return ONLY the JSON, no explanation."""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "You are a pharmaceutical data extraction expert. Always return valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1,  # Low temp for factual extraction
                        "max_tokens": 500
                    }
                )
                response.raise_for_status()
                
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()
                
                # Remove markdown code blocks if present
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.strip()
                
                parsed = json.loads(content)
                return MedicineInfo(**parsed)
                
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}\nContent: {content}")
            # Fallback parse
            return MedicineInfo(
                brand_name=medicine_text,
                salts=[medicine_text.split()[0]],
                confidence=0.3
            )
        except Exception as e:
            print(f"Grok API error: {e}")
            raise
    
    async def find_alternatives(self, medicine_info: MedicineInfo) -> Dict[str, Any]:
        """
        Find cheaper alternatives using Grok AI knowledge
        
        Args:
            medicine_info: Parsed medicine information
            
        Returns:
            Dict with alternatives and metadata
        """
        salts_str = ", ".join(medicine_info.salts)
        
        prompt = f"""You are a pharmaceutical expert specializing in generic medicine alternatives in India.

Given medicine:
- Active ingredient(s): {salts_str}
- Strength: {medicine_info.strength or 'not specified'}
- Form: {medicine_info.dosage_form or 'tablet'}
- Release type: {medicine_info.release_type or 'immediate'}

Find 5-8 cheaper alternatives, prioritizing:
1. Jan Aushadhi (Government generic program - usually cheapest)
2. Other generic brands
3. Cost-effective branded alternatives

For EACH alternative, provide:
- Exact brand name
- Manufacturer
- MRP (₹) - realistic Indian market prices
- Match quality (1.0 = exact match, 0.8 = near match, 0.6 = partial, 0.4 = generic only)
- Why it's a valid alternative

Return ONLY a JSON object:
{{
    "alternatives": [
        {{
            "brand_name": "Paracetamol",
            "manufacturer": "Jan Aushadhi",
            "salts": ["Paracetamol"],
            "strength": "500mg",
            "dosage_form": "tablet",
            "release_type": null,
            "price_mrp": 5.00,
            "is_jan_aushadhi": true,
            "match_score": 1.0,
            "match_reason": ["Same active ingredient", "Same strength", "Same dosage form"]
        }}
    ],
    "match_level": "exact|near|partial|generic",
    "notes": [
        "✅ Found exact Jan Aushadhi alternatives - up to 80% cheaper",
        "⚠️ Always confirm with your doctor before switching medicines"
    ]
}}

Rules:
- Jan Aushadhi prices: Paracetamol 500mg ~₹5/10tabs, Metformin 500mg ~₹12/20tabs, Atorvastatin 10mg ~₹25/10tabs
- Generic brands: 30-50% cheaper than branded
- Branded alternatives: 2-5x more expensive
- match_score: 1.0 (exact), 0.8 (near), 0.6 (partial strength), 0.4 (same salt only)
- MUST include at least 1 Jan Aushadhi if it exists for this medicine

Return ONLY the JSON."""

        try:
            async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "You are a pharmaceutical pricing expert in India. Return valid JSON only."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 2000
                    }
                )
                response.raise_for_status()
                
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()
                
                # Remove markdown code blocks
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.strip()
                
                parsed = json.loads(content)
                
                # Sort by Jan Aushadhi first, then price
                parsed["alternatives"].sort(
                    key=lambda x: (not x.get("is_jan_aushadhi", False), x.get("price_mrp", 999))
                )
                
                return parsed
                
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}\nContent: {content}")
            return {
                "alternatives": [],
                "match_level": "none",
                "notes": ["❌ Unable to find alternatives - please try a different medicine name"]
            }
        except Exception as e:
            print(f"Grok API error: {e}")
            raise
    
    async def get_alternatives_for_text(self, medicine_text: str) -> Dict[str, Any]:
        """
        Complete end-to-end: parse medicine text and find alternatives
        
        Args:
            medicine_text: Raw medicine name/description
            
        Returns:
            Complete response with normalized info and alternatives
        """
        # Step 1: Parse the medicine
        medicine_info = await self.parse_medicine(medicine_text)
        
        # Step 2: Find alternatives
        alternatives_data = await self.find_alternatives(medicine_info)
        
        # Step 3: Build complete response
        return {
            "query": medicine_text,
            "normalized": {
                "brand_name": medicine_info.brand_name,
                "generic_name": medicine_info.generic_name,
                "salts": medicine_info.salts,
                "strength": medicine_info.strength,
                "dosage_form": medicine_info.dosage_form,
                "release_type": medicine_info.release_type,
                "confidence": medicine_info.confidence
            },
            "alternatives": alternatives_data.get("alternatives", []),
            "count": len(alternatives_data.get("alternatives", [])),
            "match_level": alternatives_data.get("match_level", "none"),
            "notes": alternatives_data.get("notes", [])
        }
