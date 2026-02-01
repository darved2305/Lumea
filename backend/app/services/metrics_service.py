"""
Metrics Service - Compute health scores and trends
"""
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models import Observation, HealthMetric, User, ObservationType
from app.schemas import FactorContribution, TimeSeriesPoint, TrendsStats


class MetricsService:
    """Service for computing and retrieving health metrics"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========================================================================
    # HEALTH INDEX COMPUTATION
    # ========================================================================
    
    async def compute_health_index(self, user_id: uuid.UUID) -> Optional[HealthMetric]:
        """
        Compute overall health index (0-100) for a user
        
        Algorithm:
        1. Gather recent observations (last 30 days)
        2. Score each metric category based on distance from reference ranges
        3. Weighted aggregation to produce overall score
        4. Track factor contributions for UI breakdown
        
        Args:
            user_id: User ID
        
        Returns:
            Created HealthMetric or None if insufficient data
        """
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession
        
        # Get recent observations (last 30 days) - async version
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        result = await self.db.execute(
            select(Observation)
            .where(
                Observation.user_id == user_id,
                Observation.observed_at >= cutoff_date
            )
        )
        observations = result.scalars().all()
        
        if not observations:
            return None  # No data to compute from
        
        # Group by metric
        metric_groups = {}
        for obs in observations:
            if obs.metric_name not in metric_groups:
                metric_groups[obs.metric_name] = []
            metric_groups[obs.metric_name].append(obs)
        
        # Compute scores for each factor
        factor_scores = {}
        factor_details = {}
        
        # Sleep score
        sleep_score, sleep_detail = self._compute_sleep_score(metric_groups)
        if sleep_score is not None:
            factor_scores["sleep"] = sleep_score
            factor_details["sleep"] = sleep_detail
        
        # Blood pressure score
        bp_score, bp_detail = self._compute_blood_pressure_score(metric_groups)
        if bp_score is not None:
            factor_scores["bloodPressure"] = bp_score
            factor_details["bloodPressure"] = bp_detail
        
        # Glucose score
        glucose_score, glucose_detail = self._compute_glucose_score(metric_groups)
        if glucose_score is not None:
            factor_scores["glucose"] = glucose_score
            factor_details["glucose"] = glucose_detail
        
        # Activity score
        activity_score, activity_detail = self._compute_activity_score(metric_groups)
        if activity_score is not None:
            factor_scores["activity"] = activity_score
            factor_details["activity"] = activity_detail
        
        # Stress score
        stress_score, stress_detail = self._compute_stress_score(metric_groups)
        if stress_score is not None:
            factor_scores["stress"] = stress_score
            factor_details["stress"] = stress_detail
        
        # Hydration score
        hydration_score, hydration_detail = self._compute_hydration_score(metric_groups)
        if hydration_score is not None:
            factor_scores["hydration"] = hydration_score
            factor_details["hydration"] = hydration_detail
        
        if not factor_scores:
            return None  # No scorable factors
        
        # Weighted aggregation
        weights = {
            "sleep": 0.25,
            "bloodPressure": 0.20,
            "glucose": 0.18,
            "activity": 0.15,
            "stress": 0.12,
            "hydration": 0.10,
        }
        
        # Normalize weights to available factors
        available_weight = sum(weights[k] for k in factor_scores.keys())
        normalized_weights = {
            k: weights[k] / available_weight for k in factor_scores.keys()
        }
        
        # Compute overall score
        overall_score = sum(
            factor_scores[k] * normalized_weights[k] for k in factor_scores.keys()
        )
        
        # Confidence based on data completeness
        confidence = len(factor_scores) / 6  # Max 6 factors
        
        # Create contributions breakdown
        contributions = {}
        for key in factor_scores.keys():
            contributions[key] = {
                "score": factor_scores[key],
                "contribution": normalized_weights[key] * 100,  # As percentage
                "detail": factor_details[key]
            }
        
        # Save to database - async
        now = datetime.utcnow()
        metric = HealthMetric(
            user_id=user_id,
            metric_type="health_index",
            value=overall_score,
            confidence=confidence,
            computed_at=now,
            valid_from=cutoff_date,
            valid_to=now,
            contributions=contributions
        )
        
        self.db.add(metric)
        await self.db.commit()
        await self.db.refresh(metric)
        
        return metric
    
    def _compute_sleep_score(
        self, metric_groups: Dict[str, List[Observation]]
    ) -> Tuple[Optional[float], Dict]:
        """
        Compute sleep score based on sleep hours
        Target: 7-9 hours
        """
        if "sleep_hours" not in metric_groups:
            return None, {}
        
        observations = metric_groups["sleep_hours"]
        avg_sleep = sum(obs.value for obs in observations) / len(observations)
        
        # Score: 100 at 7-9 hours, decreases outside
        if 7 <= avg_sleep <= 9:
            score = 100.0
            status = "good"
        elif 6 <= avg_sleep < 7 or 9 < avg_sleep <= 10:
            score = 80.0
            status = "warning"
        elif 5 <= avg_sleep < 6 or 10 < avg_sleep <= 11:
            score = 60.0
            status = "warning"
        else:
            score = 40.0
            status = "critical"
        
        detail = {
            "value": float(avg_sleep),
            "unit": "hours",
            "status": status,
            "label": "Sleep Quality"
        }
        
        return score, detail
    
    def _compute_blood_pressure_score(
        self, metric_groups: Dict[str, List[Observation]]
    ) -> Tuple[Optional[float], Dict]:
        """
        Compute BP score from systolic and diastolic
        Target: 90-120 systolic, 60-80 diastolic
        """
        if "systolic_bp" not in metric_groups or "diastolic_bp" not in metric_groups:
            return None, {}
        
        systolic_obs = metric_groups["systolic_bp"]
        diastolic_obs = metric_groups["diastolic_bp"]
        
        avg_systolic = sum(obs.value for obs in systolic_obs) / len(systolic_obs)
        avg_diastolic = sum(obs.value for obs in diastolic_obs) / len(diastolic_obs)
        
        # Score based on ranges
        systolic_score = self._score_in_range(avg_systolic, 90, 120, 10, 140)
        diastolic_score = self._score_in_range(avg_diastolic, 60, 80, 10, 90)
        
        score = (systolic_score + diastolic_score) / 2
        
        if score >= 85:
            status = "good"
        elif score >= 65:
            status = "warning"
        else:
            status = "critical"
        
        detail = {
            "value": float(avg_systolic),
            "unit": "mmHg",
            "status": status,
            "label": "Blood Pressure"
        }
        
        return score, detail
    
    def _compute_glucose_score(
        self, metric_groups: Dict[str, List[Observation]]
    ) -> Tuple[Optional[float], Dict]:
        """
        Compute glucose score
        Target: 70-100 mg/dL (fasting)
        """
        if "glucose" not in metric_groups:
            return None, {}
        
        observations = metric_groups["glucose"]
        avg_glucose = sum(obs.value for obs in observations) / len(observations)
        
        score = self._score_in_range(avg_glucose, 70, 100, 60, 140)
        
        if score >= 85:
            status = "good"
        elif score >= 65:
            status = "warning"
        else:
            status = "critical"
        
        detail = {
            "value": float(avg_glucose),
            "unit": "mg/dL",
            "status": status,
            "label": "Glucose Level"
        }
        
        return score, detail
    
    def _compute_activity_score(
        self, metric_groups: Dict[str, List[Observation]]
    ) -> Tuple[Optional[float], Dict]:
        """
        Compute activity score from steps or exercise minutes
        Target: 8000+ steps or 30+ min exercise
        """
        if "steps" in metric_groups:
            observations = metric_groups["steps"]
            avg_steps = sum(obs.value for obs in observations) / len(observations)
            # Score: 100 at 10000+ steps
            score = min(100, (avg_steps / 10000) * 100)
            value = float(avg_steps)
            unit = "steps"
        elif "exercise_minutes" in metric_groups:
            observations = metric_groups["exercise_minutes"]
            avg_minutes = sum(obs.value for obs in observations) / len(observations)
            # Score: 100 at 30+ minutes
            score = min(100, (avg_minutes / 30) * 100)
            value = float(avg_minutes)
            unit = "minutes"
        else:
            return None, {}
        
        if score >= 80:
            status = "good"
        elif score >= 50:
            status = "warning"
        else:
            status = "critical"
        
        detail = {
            "value": value,
            "unit": unit,
            "status": status,
            "label": "Physical Activity"
        }
        
        return score, detail
    
    def _compute_stress_score(
        self, metric_groups: Dict[str, List[Observation]]
    ) -> Tuple[Optional[float], Dict]:
        """
        Compute stress score (inverted - lower stress = higher score)
        Stress level: 1-10 scale
        """
        if "stress_level" not in metric_groups:
            return None, {}
        
        observations = metric_groups["stress_level"]
        avg_stress = sum(obs.value for obs in observations) / len(observations)
        
        # Invert: stress 1-3 = score 100-80, stress 8-10 = score 40-20
        score = max(20, 120 - (avg_stress * 10))
        
        if score >= 80:
            status = "good"
        elif score >= 50:
            status = "warning"
        else:
            status = "critical"
        
        detail = {
            "value": float(avg_stress),
            "unit": "level",
            "status": status,
            "label": "Stress Level"
        }
        
        return score, detail
    
    def _compute_hydration_score(
        self, metric_groups: Dict[str, List[Observation]]
    ) -> Tuple[Optional[float], Dict]:
        """
        Compute hydration score
        Target: 2-3 liters per day
        """
        if "water_intake" not in metric_groups:
            return None, {}
        
        observations = metric_groups["water_intake"]
        avg_water = sum(obs.value for obs in observations) / len(observations)
        
        # Score: 100 at 2-3 liters
        score = self._score_in_range(avg_water, 2.0, 3.0, 1.0, 4.0)
        
        if score >= 80:
            status = "good"
        elif score >= 50:
            status = "warning"
        else:
            status = "critical"
        
        detail = {
            "value": float(avg_water),
            "unit": "liters",
            "status": status,
            "label": "Hydration"
        }
        
        return score, detail
    
    def _score_in_range(
        self, value: float, ideal_min: float, ideal_max: float, 
        critical_min: float, critical_max: float
    ) -> float:
        """
        Score a value based on ideal and critical ranges
        
        Returns:
            100 if in ideal range
            Linearly decreases outside ideal toward critical
            40 at critical boundaries
        """
        # Convert value to float to handle Decimal types
        value = float(value)
        
        if ideal_min <= value <= ideal_max:
            return 100.0
        elif value < ideal_min:
            # Below ideal
            if value <= critical_min:
                return 40.0
            # Linear interpolation
            ratio = (value - critical_min) / (ideal_min - critical_min)
            return 40.0 + (60.0 * ratio)
        else:
            # Above ideal
            if value >= critical_max:
                return 40.0
            ratio = (critical_max - value) / (critical_max - ideal_max)
            return 40.0 + (60.0 * ratio)
    
    # ========================================================================
    # TRENDS & TIMESERIES
    # ========================================================================
    
    async def get_trends(
        self,
        user_id: uuid.UUID,
        metric: str,
        time_range: str
    ) -> Tuple[List[TimeSeriesPoint], TrendsStats]:
        """
        Get timeseries data for a metric
        
        Args:
            user_id: User ID
            metric: Metric type (health_index, glucose, etc.)
            time_range: "1D", "1W", "1M"
        
        Returns:
            (data_points, stats)
        """
        from sqlalchemy import select
        
        # Determine time window
        now = datetime.utcnow()
        if time_range == "1D":
            start_time = now - timedelta(days=1)
        elif time_range == "1W":
            start_time = now - timedelta(weeks=1)
        elif time_range == "1M":
            start_time = now - timedelta(days=30)
        else:
            # Default to 1 month instead of raising error
            start_time = now - timedelta(days=30)
        
        # Get data based on metric type
        if metric == "health_index":
            # Get computed health metrics - async
            result = await self.db.execute(
                select(HealthMetric)
                .where(
                    HealthMetric.user_id == user_id,
                    HealthMetric.metric_type == "health_index",
                    HealthMetric.computed_at >= start_time
                )
                .order_by(HealthMetric.computed_at)
            )
            metrics = result.scalars().all()
            
            data_points = [
                TimeSeriesPoint(
                    timestamp=int(m.computed_at.timestamp() * 1000),
                    value=float(m.value)
                )
                for m in metrics
            ]
        else:
            # Get observations for specific metric
            metric_name_map = {
                "sleep": "sleep_hours",
                "bloodPressure": "systolic_bp",
                "blood_pressure": "systolic_bp",
                "glucose": "glucose",
                "activity": "steps",
                "stress": "stress_level",
                "hydration": "water_intake"
            }
            
            observation_metric = metric_name_map.get(metric)
            if not observation_metric:
                # Return empty instead of error
                return [], TrendsStats(
                    current=0, average=0, minimum=0, maximum=0, change_percent=0
                )
            
            result = await self.db.execute(
                select(Observation)
                .where(
                    Observation.user_id == user_id,
                    Observation.metric_name == observation_metric,
                    Observation.observed_at >= start_time
                )
                .order_by(Observation.observed_at)
            )
            observations = result.scalars().all()
            
            data_points = [
                TimeSeriesPoint(
                    timestamp=int(obs.observed_at.timestamp() * 1000),
                    value=float(obs.value)
                )
                for obs in observations
            ]
        
        # Compute stats
        if data_points:
            values = [p.value for p in data_points]
            current = values[-1]
            previous = values[-2] if len(values) > 1 else current
            change_percent = ((current - previous) / previous * 100) if previous != 0 else 0
            
            stats = TrendsStats(
                current=current,
                average=sum(values) / len(values),
                minimum=min(values),
                maximum=max(values),
                change_percent=change_percent
            )
        else:
            stats = TrendsStats(
                current=0, average=0, minimum=0, maximum=0, change_percent=0
            )
        
        return data_points, stats
    
    # ========================================================================
    # HELPERS
    # ========================================================================
    
    def get_latest_health_index(self, user_id: uuid.UUID) -> Optional[HealthMetric]:
        """Get most recent health index metric (sync version)"""
        return (
            self.db.query(HealthMetric)
            .filter(
                HealthMetric.user_id == user_id,
                HealthMetric.metric_type == "health_index"
            )
            .order_by(HealthMetric.computed_at.desc())
            .first()
        )

    async def get_latest_health_index_async(self, user_id: uuid.UUID) -> Optional[HealthMetric]:
        """Get most recent health index metric (async version)"""
        from sqlalchemy import select
        result = await self.db.execute(
            select(HealthMetric)
            .where(
                HealthMetric.user_id == user_id,
                HealthMetric.metric_type == "health_index"
            )
            .order_by(HealthMetric.computed_at.desc())
            .limit(1)
        )
        return result.scalars().first()
