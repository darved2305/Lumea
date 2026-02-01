"""
Recompute Service

Orchestrates recomputation of health index, recommendations, trends,
and derived features when profile or reports change.
Emits WebSocket events to update UI in real-time.
"""
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.services.profile_service import ProfileService
from app.services.metrics_service import MetricsService
from app.services.recommendation_service import RecommendationService
from app.routes.websocket import (
    emit_health_index_updated,
    emit_trends_updated,
    emit_recommendations_updated,
)

logger = logging.getLogger(__name__)


class RecomputeService:
    """
    Coordinates recomputation of all user health data.
    Ensures idempotent and safe updates.
    """
    
    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user
        self.profile_service = ProfileService(db, user)
        self.metrics_service = MetricsService(db)
    
    async def recompute_all(self, emit_events: bool = True) -> Dict[str, Any]:
        """
        Full recomputation pipeline:
        1. Compute derived features (BMI, age, risk flags)
        2. Compute health index from observations + profile
        3. Generate recommendations
        4. Refresh trends cache
        5. Emit WebSocket events
        
        Returns summary of what was computed.
        """
        user_id = str(self.user.id)
        results = {
            "user_id": user_id,
            "computed_at": datetime.utcnow().isoformat(),
            "derived_features": None,
            "health_index": None,
            "recommendations": None,
            "events_emitted": []
        }
        
        try:
            # 1. Compute derived features
            logger.info(f"[Recompute] Computing derived features for user {user_id}")
            derived_features = await self.profile_service.compute_derived_features()
            results["derived_features"] = {
                "count": len(derived_features),
                "features": [f.feature_name for f in derived_features]
            }
            
            # 2. Compute health index
            logger.info(f"[Recompute] Computing health index for user {user_id}")
            try:
                health_metric = await self.metrics_service.compute_health_index(self.user.id)
                if health_metric:
                    results["health_index"] = {
                        "score": float(health_metric.value),
                        "confidence": float(health_metric.confidence) if health_metric.confidence else None,
                        "contributions": health_metric.contributions
                    }
                    
                    if emit_events:
                        await emit_health_index_updated(user_id, {
                            "score": float(health_metric.value),
                            "breakdown": health_metric.contributions or {},
                            "confidence": float(health_metric.confidence) if health_metric.confidence else 0.5
                        })
                        results["events_emitted"].append("health_index_updated")
            except Exception as e:
                logger.warning(f"[Recompute] Health index computation failed: {e}")
                results["health_index"] = {"error": str(e)}
            
            # 3. Generate recommendations
            logger.info(f"[Recompute] Generating recommendations for user {user_id}")
            try:
                reco_service = RecommendationService(self.db, self.user)
                recommendations = await reco_service.get_recommendations()
                results["recommendations"] = {
                    "total_count": recommendations.get("total_count", 0),
                    "urgent_count": recommendations.get("urgent_count", 0)
                }
                
                if emit_events:
                    await emit_recommendations_updated(
                        user_id,
                        recommendations.get("total_count", 0),
                        recommendations.get("urgent_count", 0)
                    )
                    results["events_emitted"].append("recommendations_updated")
            except Exception as e:
                logger.warning(f"[Recompute] Recommendations generation failed: {e}")
                results["recommendations"] = {"error": str(e)}
            
            # 4. Emit trends updated (UI can refetch if needed)
            if emit_events:
                await emit_trends_updated(user_id, {"refresh": True})
                results["events_emitted"].append("trends_updated")
            
            # 5. Emit profile updated event
            if emit_events:
                await emit_profile_updated(user_id)
                results["events_emitted"].append("profile_updated")
            
            logger.info(f"[Recompute] Completed for user {user_id}")
            
        except Exception as e:
            logger.exception(f"[Recompute] Failed for user {user_id}: {e}")
            results["error"] = str(e)
        
        return results
    
    async def recompute_derived_only(self) -> Dict[str, Any]:
        """Quick recompute of just derived features"""
        derived_features = await self.profile_service.compute_derived_features()
        return {
            "count": len(derived_features),
            "features": [f.feature_name for f in derived_features]
        }
    
    async def recompute_health_index_only(self, emit_events: bool = True) -> Optional[Dict[str, Any]]:
        """Recompute just health index"""
        user_id = str(self.user.id)
        
        try:
            health_metric = await self.metrics_service.compute_health_index(self.user.id)
            if health_metric:
                if emit_events:
                    await emit_health_index_updated(user_id, {
                        "score": float(health_metric.value),
                        "breakdown": health_metric.contributions or {},
                        "confidence": float(health_metric.confidence) if health_metric.confidence else 0.5
                    })
                
                return {
                    "score": float(health_metric.value),
                    "confidence": float(health_metric.confidence) if health_metric.confidence else None
                }
        except Exception as e:
            logger.warning(f"[Recompute] Health index failed: {e}")
        
        return None


# Add profile_updated event emitter to websocket module
async def emit_profile_updated(user_id: str):
    """Emit when profile is updated"""
    from app.routes.websocket import manager
    await manager.broadcast_to_user(user_id, "profile_updated", {
        "updated_at": datetime.utcnow().isoformat()
    })
