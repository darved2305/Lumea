"""
Assistant Service - AI Health Assistant with grounded responses
"""
import uuid
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.models import User, Report, Observation, HealthMetric, ChatSession, ChatMessage
from src.models import Citation


class AssistantService:
    """
    AI Health Assistant Service
    
    Provides grounded, context-aware responses based ONLY on user's own data.
    Uses retrieval-augmented generation (RAG) approach.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    async def chat(
        self,
        user_id: uuid.UUID,
        message: str,
        session_id: Optional[uuid.UUID] = None
    ) -> tuple[str, List[Citation], uuid.UUID, uuid.UUID]:
        """
        Process chat message and generate response
        
        Args:
            user_id: User ID
            message: User's message
            session_id: Existing session ID or None for new session
        
        Returns:
            (response_content, citations, session_id, message_id)
        """
        # Get or create session
        if session_id:
            session = self.db.query(ChatSession).filter(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id
            ).first()
            if not session:
                raise ValueError("Session not found")
            session.last_active_at = datetime.utcnow()
        else:
            session = ChatSession(
                user_id=user_id,
                created_at=datetime.utcnow(),
                last_active_at=datetime.utcnow()
            )
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
        
        # Save user message
        user_msg = ChatMessage(
            session_id=session.id,
            role="user",
            content=message,
            created_at=datetime.utcnow()
        )
        self.db.add(user_msg)
        self.db.commit()
        
        # Retrieve user context
        context = await self._retrieve_user_context(user_id, message)
        
        # Generate response
        response_content, citations = await self._generate_response(
            user_id, message, context
        )
        
        # Save assistant message
        assistant_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=response_content,
            message_metadata={"citations": [c.dict() for c in citations]},
            created_at=datetime.utcnow()
        )
        self.db.add(assistant_msg)
        self.db.commit()
        self.db.refresh(assistant_msg)
        
        return response_content, citations, session.id, assistant_msg.id
    
    async def _retrieve_user_context(
        self, user_id: uuid.UUID, query: str
    ) -> Dict[str, Any]:
        """
        Retrieve relevant user data for context
        
        Returns:
            Dictionary with user profile, recent observations, abnormalities, reports
        """
        # Get user profile
        user = self.db.query(User).filter(User.id == user_id).first()
        
        # Get latest health index
        latest_health = (
            self.db.query(HealthMetric)
            .filter(
                HealthMetric.user_id == user_id,
                HealthMetric.metric_type == "health_index"
            )
            .order_by(HealthMetric.computed_at.desc())
            .first()
        )
        
        # Get recent observations (last 30 days)
        cutoff = datetime.utcnow() - timedelta(days=30)
        recent_observations = (
            self.db.query(Observation)
            .filter(
                Observation.user_id == user_id,
                Observation.observed_at >= cutoff
            )
            .order_by(Observation.observed_at.desc())
            .limit(50)
            .all()
        )
        
        # Get abnormal observations
        abnormal_observations = (
            self.db.query(Observation)
            .filter(
                Observation.user_id == user_id,
                Observation.is_abnormal == True,
                Observation.observed_at >= cutoff
            )
            .order_by(Observation.observed_at.desc())
            .limit(20)
            .all()
        )
        
        # Get recent reports
        recent_reports = (
            self.db.query(Report)
            .filter(Report.user_id == user_id)
            .order_by(Report.uploaded_at.desc())
            .limit(3)
            .all()
        )
        
        context = {
            "user": {
                "name": user.full_name,
                "email": user.email
            },
            "health_index": {
                "score": float(latest_health.value) if latest_health else None,
                "confidence": float(latest_health.confidence) if latest_health else None,
                "contributions": latest_health.contributions if latest_health else None,
                "computed_at": latest_health.computed_at.isoformat() if latest_health else None
            },
            "recent_observations": [
                {
                    "id": str(obs.id),
                    "metric": obs.metric_name,
                    "value": float(obs.value),
                    "unit": obs.unit,
                    "date": obs.observed_at.isoformat(),
                    "is_abnormal": obs.is_abnormal
                }
                for obs in recent_observations
            ],
            "abnormal_observations": [
                {
                    "id": str(obs.id),
                    "metric": obs.metric_name,
                    "value": float(obs.value),
                    "unit": obs.unit,
                    "date": obs.observed_at.isoformat(),
                    "reference_min": float(obs.reference_min) if obs.reference_min else None,
                    "reference_max": float(obs.reference_max) if obs.reference_max else None
                }
                for obs in abnormal_observations
            ],
            "reports": [
                {
                    "id": str(rep.id),
                    "filename": rep.filename,
                    "date": rep.report_date.isoformat() if rep.report_date else rep.uploaded_at.isoformat(),
                    "status": rep.status.value,
                    "text_snippet": rep.raw_text[:500] if rep.raw_text else None
                }
                for rep in recent_reports
            ]
        }
        
        return context
    
    async def _generate_response(
        self,
        user_id: uuid.UUID,
        query: str,
        context: Dict[str, Any]
    ) -> tuple[str, List[Citation]]:
        """
        Generate AI response using context
        
        MVP: Rule-based responses with templates
        TODO: Integrate actual LLM API (OpenAI, Anthropic, local model)
        
        Returns:
            (response_text, citations)
        """
        query_lower = query.lower()
        
        # Extract relevant info
        health_index = context["health_index"]
        recent_obs = context["recent_observations"]
        abnormal_obs = context["abnormal_observations"]
        reports = context["reports"]
        
        citations = []
        
        # Rule-based response generation
        
        # Query about health index/score
        if any(word in query_lower for word in ["index", "score", "overall", "health"]):
            if health_index["score"]:
                score = health_index["score"]
                confidence = health_index["confidence"] * 100
                contribs = health_index["contributions"]
                
                # Build response
                response = f"Your current health index is **{score:.1f}%** (computed {health_index['computed_at'][:10]}) with {confidence:.0f}% confidence based on available data.\n\n"
                
                if contribs:
                    response += "**Breakdown by factor:**\n"
                    for key, data in contribs.items():
                        factor_score = data["score"]
                        contribution = data["contribution"]
                        detail = data["detail"]
                        status_emoji = "✓" if detail["status"] == "good" else "⚠" if detail["status"] == "warning" else "⚠"
                        response += f"• {status_emoji} {detail['label']}: {factor_score:.0f}/100 (contributing {contribution:.1f}%)\n"
                
                response += "\n**Recommendations:**\n"
                if contribs:
                    # Find lowest scoring factor
                    lowest = min(contribs.items(), key=lambda x: x[1]["score"])
                    response += f"Focus on improving your **{lowest[1]['detail']['label']}** which is currently your lowest scoring factor.\n"
                
                # Add citation
                citations.append(Citation(
                    report_id=None,
                    metric_name="health_index",
                    value=f"{score:.1f}%",
                    excerpt=f"Health index computed from your recent health data"
                ))
                
                return response, citations
            else:
                return "I don't have enough data yet to compute your health index. Please upload some medical reports or add health observations to get started.", []
        
        # Query about specific metric
        metric_keywords = {
            "glucose": ["glucose", "sugar", "blood sugar"],
            "blood pressure": ["blood pressure", "bp", "hypertension"],
            "sleep": ["sleep", "rest", "sleeping"],
            "activity": ["activity", "exercise", "steps", "workout"],
            "stress": ["stress", "anxiety", "tension"],
            "hydration": ["water", "hydration", "fluid"]
        }
        
        for metric, keywords in metric_keywords.items():
            if any(kw in query_lower for kw in keywords):
                # Find relevant observations
                relevant = [obs for obs in recent_obs if any(kw in obs["metric"] for kw in keywords)]
                
                if relevant:
                    latest = relevant[0]
                    response = f"Based on your recent data, your **{metric}** is:\n\n"
                    response += f"**Latest reading:** {latest['value']} {latest['unit']} (recorded {latest['date'][:10]})\n\n"
                    
                    if latest["is_abnormal"]:
                        response += "⚠ This value is outside the normal reference range. Consider consulting with your healthcare provider.\n\n"
                    else:
                        response += "✓ This value is within the normal range.\n\n"
                    
                    # Add trend if multiple readings
                    if len(relevant) > 1:
                        values = [r["value"] for r in relevant[:5]]
                        avg = sum(values) / len(values)
                        response += f"**Average (last {len(values)} readings):** {avg:.1f} {latest['unit']}\n\n"
                    
                    response += "**Recommendation:** Continue monitoring regularly and maintain healthy lifestyle habits."
                    
                    # Add citation
                    citations.append(Citation(
                        observation_id=uuid.UUID(latest["id"]),
                        metric_name=latest["metric"],
                        value=f"{latest['value']} {latest['unit']}",
                        excerpt=f"From observation recorded on {latest['date'][:10]}"
                    ))
                    
                    return response, citations
                else:
                    return f"I don't have any recent data about your {metric}. Upload a medical report or manually add observations to track this metric.", []
        
        # Query about abnormalities/concerns
        if any(word in query_lower for word in ["abnormal", "concern", "worry", "problem", "issue", "wrong"]):
            if abnormal_obs:
                response = "Based on your recent data, here are the values outside normal ranges:\n\n"
                for obs in abnormal_obs[:5]:
                    response += f"• **{obs['metric']}:** {obs['value']} {obs['unit']} (recorded {obs['date'][:10]})\n"
                    if obs['reference_min'] and obs['reference_max']:
                        response += f"  Normal range: {obs['reference_min']}-{obs['reference_max']} {obs['unit']}\n"
                    
                    citations.append(Citation(
                        observation_id=uuid.UUID(obs["id"]),
                        metric_name=obs["metric"],
                        value=f"{obs['value']} {obs['unit']}",
                        excerpt=f"Abnormal value from {obs['date'][:10]}"
                    ))
                
                response += "\n**Important:** These findings should be reviewed with your healthcare provider for proper medical advice."
                return response, citations
            else:
                return "Good news! Based on your recent data, all your health metrics are within normal ranges. Keep up the healthy habits!", []
        
        # Query about reports
        if any(word in query_lower for word in ["report", "upload", "document", "test", "lab"]):
            if reports:
                response = f"You have **{len(reports)} recent report(s):**\n\n"
                for rep in reports:
                    response += f"• **{rep['filename']}** (uploaded {rep['date'][:10]})\n"
                    response += f"  Status: {rep['status']}\n"
                    
                    citations.append(Citation(
                        report_id=uuid.UUID(rep["id"]),
                        report_name=rep["filename"],
                        report_date=datetime.fromisoformat(rep["date"]),
                        excerpt=rep["text_snippet"][:200] if rep["text_snippet"] else None
                    ))
                
                response += "\nYou can view detailed extracted data from each report in the Reports section."
                return response, citations
            else:
                return "You haven't uploaded any medical reports yet. Upload your lab reports, prescriptions, or test results to get personalized health insights.", []
        
        # Default fallback
        response = f"I can help you understand your health data! I have access to:\n\n"
        response += f"• Your health index: {'Available' if health_index['score'] else 'Not yet computed'}\n"
        response += f"• Recent observations: {len(recent_obs)} data points\n"
        response += f"• Medical reports: {len(reports)} uploaded\n\n"
        response += "Try asking me about:\n"
        response += "• Your overall health score\n"
        response += "• Specific metrics (glucose, blood pressure, sleep, etc.)\n"
        response += "• Any abnormal values or concerns\n"
        response += "• Your uploaded reports\n\n"
        response += "What would you like to know?"
        
        return response, citations
    
    def get_session_history(
        self, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> List[ChatMessage]:
        """Get chat history for a session"""
        session = self.db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id
        ).first()
        
        if not session:
            raise ValueError("Session not found")
        
        messages = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .all()
        )
        
        return messages
