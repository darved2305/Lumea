"""
Recommendation Service

Orchestrates rule evaluation and generates personalized recommendations
based on user's health data.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.models import User, HealthMetric, Observation
from src.rules import (
    get_registry,
    RuleResult,
    MetricData,
    UserContext,
    Severity,
)
from src.config import settings

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    Service for generating personalized health recommendations.
    
    Uses deterministic rules to evaluate user metrics and produce
    actionable wellness suggestions.
    """
    
    DISCLAIMER = (
        "⚕️ This is wellness guidance, not medical advice. "
        "Consult a licensed healthcare provider for diagnosis, treatment, or medical decisions."
    )
    
    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user
        self.registry = get_registry()
    
    async def get_recommendations(self, include_low_severity: bool = True) -> Dict[str, Any]:
        """
        Get all applicable recommendations for the user.
        
        NEVER throws - returns empty list on any error.
        
        Returns:
            Dict containing:
                - updated_at: ISO timestamp
                - disclaimer: Safety disclaimer text
                - items: List of recommendation items
        """
        try:
            # Build user context from stored metrics
            context = await self._build_user_context()
            
            # Evaluate all rules
            results = self.registry.evaluate_all(context)
            
            # Filter by severity if requested
            if not include_low_severity:
                results = [r for r in results if r.severity != Severity.INFO]
            
            # Sort by severity (URGENT > WARNING > INFO) then by rule priority
            severity_order = {Severity.URGENT: 0, Severity.WARNING: 1, Severity.INFO: 2}
            results.sort(key=lambda r: (severity_order.get(r.severity, 3),))
            
            # Optionally apply LLM rewording - but catch errors
            if settings.USE_GEMINI and settings.GEMINI_API_KEY:
                try:
                    results = await self._reword_with_gemini(results)
                except Exception as e:
                    logger.warning(f"Gemini rewording failed, using original text: {e}")
            
            return {
                "updated_at": datetime.utcnow().isoformat(),
                "disclaimer": self.DISCLAIMER,
                "items": [r.to_dict() for r in results],
                "total_count": len(results),
                "urgent_count": sum(1 for r in results if r.severity == Severity.URGENT),
                "warning_count": sum(1 for r in results if r.severity == Severity.WARNING),
            }
        except Exception as e:
            logger.exception(f"Error generating recommendations: {e}")
            # Return empty but valid response
            return {
                "updated_at": datetime.utcnow().isoformat(),
                "disclaimer": self.DISCLAIMER,
                "items": [],
                "total_count": 0,
                "urgent_count": 0,
                "warning_count": 0,
            }
    
    async def _build_user_context(self) -> UserContext:
        """
        Build UserContext from the user's stored health data.
        """
        metrics: Dict[str, MetricData] = {}
        
        # Get latest computed health metrics (scores like health_index, sleep_score, etc.)
        stmt = select(HealthMetric).where(
            HealthMetric.user_id == self.user.id
        ).order_by(HealthMetric.computed_at.desc()).limit(50)
        
        result = await self.db.execute(stmt)
        health_metrics = result.scalars().all()
        
        # Process computed health metrics into MetricData
        # Note: HealthMetric model uses 'metric_type', not 'metric_name'
        for hm in health_metrics:
            # Try metric_type first (actual column name), fallback to metric_name for compatibility
            metric_key = getattr(hm, "metric_type", None) or getattr(hm, "metric_name", None)
            if not metric_key:
                logger.warning(f"HealthMetric {hm.id} missing metric_type, skipping")
                continue
            
            if metric_key not in metrics:
                metrics[metric_key] = MetricData(
                    name=metric_key,
                    value=float(hm.value) if hm.value is not None else 0.0,
                    unit=getattr(hm, "unit", None) or "score",
                    reference_min=getattr(hm, "reference_min", None) or getattr(hm, "reference_low", None),
                    reference_max=getattr(hm, "reference_max", None) or getattr(hm, "reference_high", None),
                    days_since_last=self._days_since(getattr(hm, "computed_at", None)),
                    trend=getattr(hm, "trend", None),
                )
        
        # Also get observations for more detailed data
        obs_stmt = select(Observation).where(
            Observation.user_id == self.user.id
        ).order_by(Observation.observed_at.desc()).limit(100)
        
        obs_result = await self.db.execute(obs_stmt)
        observations = obs_result.scalars().all()
        
        # Process observations
        for obs in observations:
            # Observation ORM uses `metric_name` and optional `display_name`
            metric_name = self._normalize_metric_name(obs.display_name or obs.metric_name)
            if metric_name and metric_name not in metrics:
                metrics[metric_name] = MetricData(
                    name=metric_name,
                    value=float(obs.value),
                    unit=obs.unit,
                    reference_min=float(obs.reference_min) if obs.reference_min is not None else None,
                    reference_max=float(obs.reference_max) if obs.reference_max is not None else None,
                    days_since_last=self._days_since(obs.observed_at),
                )
        
        # Calculate user age
        age = None
        date_of_birth = getattr(self.user, "date_of_birth", None)
        if date_of_birth:
            today = datetime.utcnow().date()
            age = today.year - date_of_birth.year
            if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
                age -= 1
        
        return UserContext(
            user_id=str(self.user.id),
            metrics=metrics,
            age=age,
            gender=getattr(self.user, "gender", None),
        )
    
    def _days_since(self, date_value) -> Optional[int]:
        """Calculate days since a date."""
        if not date_value:
            return None
        
        if isinstance(date_value, datetime):
            date_value = date_value.date()
        
        today = datetime.utcnow().date()
        delta = today - date_value
        return delta.days
    
    def _normalize_metric_name(self, name: str) -> Optional[str]:
        """
        Normalize metric name to a standard format.
        """
        if not name:
            return None
        
        # Convert to lowercase and replace common separators
        normalized = name.lower().strip()
        normalized = normalized.replace("-", "_").replace(" ", "_")
        
        # Common mappings
        mappings = {
            "cholesterol_in_ldl": "ldl",
            "ldl_cholesterol": "ldl",
            "cholesterol_in_hdl": "hdl",
            "hdl_cholesterol": "hdl",
            "total_cholesterol": "total_cholesterol",
            "triglyceride": "triglycerides",
            "hemoglobin_a1c": "hba1c",
            "hba1c/hemoglobin.total": "hba1c",
            "glucose": "glucose",
            "fasting_glucose": "fasting_glucose",
            "vitamin_d": "vitamin_d",
            "25_hydroxyvitamin_d": "vitamin_d",
            "vitamin_b12": "vitamin_b12",
            "cobalamin": "vitamin_b12",
            "ferritin": "ferritin",
            "serum_iron": "iron",
            "systolic_blood_pressure": "systolic_bp",
            "diastolic_blood_pressure": "diastolic_bp",
            "heart_rate": "heart_rate",
            "resting_heart_rate": "heart_rate",
        }
        
        # Check for exact match
        if normalized in mappings:
            return mappings[normalized]
        
        # Check for partial matches
        for key, value in mappings.items():
            if key in normalized or normalized in key:
                return value
        
        return normalized
    
    def _extract_value(self, obs: Observation) -> Optional[float]:
        """
        Extract numeric value from an observation.
        """
        if obs.value_quantity is not None:
            return float(obs.value_quantity)
        
        if obs.value_string:
            try:
                # Try to parse numeric value from string
                import re
                match = re.search(r'[\d.]+', obs.value_string)
                if match:
                    return float(match.group())
            except (ValueError, AttributeError):
                pass
        
        return None
    
    async def _reword_with_gemini(self, results: List[RuleResult]) -> List[RuleResult]:
        """
        Optionally use Gemini to reword recommendations for better readability.
        
        NOTE: This does NOT change the medical content or recommendations,
        only improves clarity and personalization of the wording.
        """
        if not results:
            return results
        
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            for result in results:
                prompt = f"""
                Reword the following health recommendation to be more personal and encouraging,
                while keeping the exact same meaning and all action items.
                Do NOT add medical advice or change any recommendations.
                Keep it concise (2-3 sentences max for the explanation).
                
                Original title: {result.title}
                Original explanation: {result.why}
                
                Return ONLY the reworded title and explanation, separated by a newline.
                Format:
                TITLE: [reworded title]
                EXPLANATION: [reworded explanation]
                """
                
                response = await model.generate_content_async(prompt)
                
                if response.text:
                    lines = response.text.strip().split('\n')
                    for line in lines:
                        if line.startswith('TITLE:'):
                            result.title = line.replace('TITLE:', '').strip()
                        elif line.startswith('EXPLANATION:'):
                            result.why = line.replace('EXPLANATION:', '').strip()
        
        except ImportError:
            logger.warning("google-generativeai package not installed, skipping Gemini rewording")
        except Exception as e:
            logger.error(f"Error using Gemini for rewording: {e}")
            # Continue with original wording
        
        return results


async def get_user_recommendations(
    db: AsyncSession,
    user: User,
    include_low_severity: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to get recommendations for a user.
    """
    service = RecommendationService(db, user)
    return await service.get_recommendations(include_low_severity)
