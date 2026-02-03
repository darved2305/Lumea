"""
AI Report Summary Service

Uses Grok API to generate AI summaries and comparisons of medical reports.
Implements caching via source_hash to avoid regenerating unchanged content.
"""
import hashlib
import json
import logging
import httpx
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings import settings
from app.models import Report, ReportAISummary, ReportAIComparison, Observation

logger = logging.getLogger(__name__)

# LLM API configuration - support Groq, Grok (xAI), and OpenAI
def get_llm_config():
    """Determine which LLM API to use based on available keys."""
    if settings.groq_api_key:
        return {
            "api_key": settings.groq_api_key,
            "api_url": f"{settings.groq_api_base}/chat/completions",
            "model": settings.groq_model,
            "service": "Groq"
        }
    elif settings.grok_api_key or settings.xai_api_key:
        return {
            "api_key": settings.grok_api_key or settings.xai_api_key,
            "api_url": f"{settings.xai_api_base}/chat/completions",
            "model": settings.grok_model,
            "service": "Grok"
        }
    elif settings.openai_api_key:
        return {
            "api_key": settings.openai_api_key,
            "api_url": f"{settings.openai_api_base}/chat/completions",
            "model": settings.openai_model,
            "service": "OpenAI"
        }
    return None

# System prompts for AI
SUMMARY_SYSTEM_PROMPT = """You are a medical report analyst AI assistant. Your task is to analyze medical reports and provide clear, accurate summaries.

IMPORTANT RULES:
1. NEVER hallucinate or make up values - if information is not in the report, say "Not found in report"
2. Be factual and precise
3. Use plain language that patients can understand
4. Always include this disclaimer in your analysis: This is an AI-generated summary for informational purposes only. It is not a substitute for professional medical advice.
5. Return ONLY valid JSON matching the exact schema requested

You will receive OCR text from a medical report. Analyze it and return a structured JSON summary."""

COMPARE_SYSTEM_PROMPT = """You are a medical report analyst AI assistant. Your task is to compare multiple medical reports over time and identify trends, improvements, and areas of concern.

IMPORTANT RULES:
1. NEVER hallucinate or make up values - if information is not in a report, say "Not found in report"
2. Focus on changes between reports - improvements, worsening, and stable metrics
3. Use plain language that patients can understand
4. Always include this disclaimer: This is an AI-generated comparison for informational purposes only. It is not a substitute for professional medical advice.
5. Return ONLY valid JSON matching the exact schema requested

You will receive OCR text from multiple medical reports. Compare them chronologically and return a structured JSON comparison."""

SUMMARY_JSON_SCHEMA = """{
  "title": "Brief title summarizing the report",
  "highlights": {
    "positive": ["List of positive findings"],
    "needs_attention": ["List of items needing attention"],
    "next_steps": ["Suggested follow-up actions"]
  },
  "plain_language_summary": "A 2-3 paragraph summary in plain language",
  "key_findings": [
    {"item": "Finding name", "evidence": "Evidence from report"}
  ],
  "confidence": 0.85
}"""

COMPARE_JSON_SCHEMA = """{
  "title": "Brief title for the comparison",
  "overall_change": "One sentence summary of overall health trend",
  "improvements": ["List of metrics that improved"],
  "worsened": ["List of metrics that worsened"],
  "stable": ["List of metrics that remained stable"],
  "key_differences": [
    {"metric": "Metric name", "from": "Old value", "to": "New value", "evidence": "Supporting evidence"}
  ],
  "next_steps": ["Recommended follow-up actions"],
  "confidence": 0.85
}"""


def compute_source_hash(text: str) -> str:
    """Compute SHA256 hash of source text for cache invalidation."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def compute_multi_source_hash(report_ids: List[UUID], texts: List[str]) -> str:
    """Compute hash for multiple reports based on sorted IDs and their texts."""
    sorted_pairs = sorted(zip([str(rid) for rid in report_ids], texts))
    combined = "|".join([f"{rid}:{text[:1000]}" for rid, text in sorted_pairs])
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()


class AISummaryService:
    """Service for generating and caching AI report summaries."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_config = get_llm_config()
        if not self.llm_config:
            logger.warning("No LLM API key configured (GROQ_API_KEY, GROK_API_KEY, or OPENAI_API_KEY) - AI summaries will fail")
        else:
            logger.info(f"Using {self.llm_config['service']} API for AI summaries")

    async def get_report_text(self, report_id: UUID, user_id: UUID) -> Optional[Report]:
        """Fetch report with validation that it belongs to user."""
        result = await self.db.execute(
            select(Report).where(
                Report.id == report_id,
                Report.user_id == user_id
            )
        )
        return result.scalars().first()

    async def get_reports_for_comparison(
        self, report_ids: List[UUID], user_id: UUID
    ) -> List[Report]:
        """Fetch multiple reports and validate ownership + same type."""
        result = await self.db.execute(
            select(Report).where(
                Report.id.in_(report_ids),
                Report.user_id == user_id
            )
        )
        reports = list(result.scalars().all())
        return reports

    async def call_grok_api(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: str
    ) -> Dict[str, Any]:
        """Call LLM API (Groq/Grok/OpenAI) with the given prompts."""
        if not self.llm_config:
            raise ValueError("No LLM API key configured. Please set GROQ_API_KEY, GROK_API_KEY, or OPENAI_API_KEY in your environment.")

        headers = {
            "Authorization": f"Bearer {self.llm_config['api_key']}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.llm_config['model'],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{user_prompt}\n\nReturn your response as JSON matching this exact schema:\n{json_schema}"}
            ],
            "temperature": 0.3,
            "max_tokens": 2000
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.llm_config['api_url'],
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # Parse JSON from response
                # Handle potential markdown code blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                
                return json.loads(content.strip())
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Grok API HTTP error: {e.response.status_code} - {e.response.text}")
            raise ValueError(f"Grok API error: {e.response.status_code}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Grok response as JSON: {e}")
            raise ValueError("Failed to parse AI response")
        except Exception as e:
            logger.error(f"Grok API call failed: {e}")
            raise ValueError(f"AI service error: {str(e)}")

    async def generate_summary(
        self,
        report_id: UUID,
        user_id: UUID,
        force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """Generate or retrieve cached AI summary for a single report."""
        
        # Fetch report
        report = await self.get_report_text(report_id, user_id)
        if not report:
            raise ValueError("Report not found or access denied")

        if not report.raw_text:
            raise ValueError("Report has no extracted text. Please wait for processing to complete.")

        # Compute source hash
        source_hash = compute_source_hash(report.raw_text)

        # Check cache if not forcing regeneration
        if not force_regenerate:
            cached = await self.db.execute(
                select(ReportAISummary).where(
                    ReportAISummary.report_id == report_id,
                    ReportAISummary.user_id == user_id,
                    ReportAISummary.source_hash == source_hash
                )
            )
            existing = cached.scalars().first()
            if existing:
                return {
                    "summary_json": existing.summary_json,
                    "cached": True,
                    "generated_at": existing.created_at,
                    "model_name": existing.model_name
                }

        # Build context from extracted metrics if available
        metrics_context = ""
        metrics_result = await self.db.execute(
            select(Observation).where(Observation.report_id == report_id)
        )
        observations = metrics_result.scalars().all()
        if observations:
            metrics_lines = []
            for obs in observations:
                flag_str = f" [{obs.flag}]" if obs.flag else ""
                metrics_lines.append(f"- {obs.metric_name}: {obs.value} {obs.unit}{flag_str}")
            metrics_context = "\n\nExtracted Metrics:\n" + "\n".join(metrics_lines)

        # Build user prompt
        user_prompt = f"""Analyze this medical report:

Report Type: {report.category or 'Unknown'} / {report.doc_type or 'Unknown'}
Report Date: {report.report_date.strftime('%Y-%m-%d') if report.report_date else 'Unknown'}

OCR Text:
{report.raw_text[:8000]}
{metrics_context}

Generate a comprehensive summary focusing on key health insights."""

        # Call LLM API
        llm_config = get_llm_config()
        if not llm_config:
            raise ValueError("No LLM API configured. Please set GROQ_API_KEY, GROK_API_KEY, or OPENAI_API_KEY")
        
        summary_json = await self.call_grok_api(
            SUMMARY_SYSTEM_PROMPT,
            user_prompt,
            SUMMARY_JSON_SCHEMA
        )

        # Save to database
        new_summary = ReportAISummary(
            user_id=user_id,
            report_id=report_id,
            summary_json=summary_json,
            model_name=llm_config["model"],
            source_hash=source_hash
        )
        self.db.add(new_summary)
        await self.db.commit()
        await self.db.refresh(new_summary)

        return {
            "summary_json": summary_json,
            "cached": False,
            "generated_at": new_summary.created_at,
            "model_name": llm_config["model"]
        }

    async def generate_comparison(
        self,
        report_ids: List[UUID],
        user_id: UUID,
        force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """Generate or retrieve cached AI comparison for multiple reports."""
        
        if len(report_ids) < 2:
            raise ValueError("At least 2 reports required for comparison")
        if len(report_ids) > 6:
            raise ValueError("Maximum 6 reports allowed for comparison")

        # Fetch reports
        reports = await self.get_reports_for_comparison(report_ids, user_id)
        
        if len(reports) != len(report_ids):
            raise ValueError("One or more reports not found or access denied")

        # Validate same type
        categories = set(r.category for r in reports if r.category)
        doc_types = set(r.doc_type for r in reports if r.doc_type)
        
        # Allow comparison if same category OR same doc_type
        if len(categories) > 1 and len(doc_types) > 1:
            raise ValueError("Reports must be of the same type for comparison")

        # Check all have text
        for report in reports:
            if not report.raw_text:
                raise ValueError(f"Report {report.filename} has no extracted text")

        # Sort reports by date
        reports_sorted = sorted(
            reports,
            key=lambda r: r.report_date or r.uploaded_at
        )

        # Compute source hash
        source_hash = compute_multi_source_hash(
            [r.id for r in reports_sorted],
            [r.raw_text for r in reports_sorted]
        )

        # Check cache if not forcing regeneration
        if not force_regenerate:
            cached = await self.db.execute(
                select(ReportAIComparison).where(
                    ReportAIComparison.user_id == user_id,
                    ReportAIComparison.source_hash == source_hash
                )
            )
            existing = cached.scalars().first()
            if existing:
                return {
                    "comparison_json": existing.comparison_json,
                    "cached": True,
                    "generated_at": existing.created_at,
                    "model_name": existing.model_name
                }

        # Build comparison prompt
        reports_text = []
        for i, report in enumerate(reports_sorted, 1):
            date_str = report.report_date.strftime('%Y-%m-%d') if report.report_date else 'Unknown date'
            
            # Get metrics for this report
            metrics_result = await self.db.execute(
                select(Observation).where(Observation.report_id == report.id)
            )
            observations = metrics_result.scalars().all()
            metrics_context = ""
            if observations:
                metrics_lines = []
                for obs in observations:
                    flag_str = f" [{obs.flag}]" if obs.flag else ""
                    metrics_lines.append(f"  - {obs.metric_name}: {obs.value} {obs.unit}{flag_str}")
                metrics_context = "\n  Extracted Metrics:\n" + "\n".join(metrics_lines)
            
            reports_text.append(
                f"""--- REPORT {i} ---
Filename: {report.filename}
Type: {report.category or 'Unknown'} / {report.doc_type or 'Unknown'}
Date: {date_str}

Text:
{report.raw_text[:4000]}
{metrics_context}
"""
            )

        user_prompt = f"""Compare these {len(reports_sorted)} medical reports chronologically:

{chr(10).join(reports_text)}

Identify trends, improvements, areas of concern, and recommended next steps. Focus on meaningful changes between reports."""

        # Call LLM API
        llm_config = get_llm_config()
        if not llm_config:
            raise ValueError("No LLM API configured. Please set GROQ_API_KEY, GROK_API_KEY, or OPENAI_API_KEY")
        
        comparison_json = await self.call_grok_api(
            COMPARE_SYSTEM_PROMPT,
            user_prompt,
            COMPARE_JSON_SCHEMA
        )

        # Save to database
        new_comparison = ReportAIComparison(
            user_id=user_id,
            report_ids_json=[str(r.id) for r in reports_sorted],
            comparison_json=comparison_json,
            model_name=llm_config["model"],
            source_hash=source_hash
        )
        self.db.add(new_comparison)
        await self.db.commit()
        await self.db.refresh(new_comparison)

        return {
            "comparison_json": comparison_json,
            "cached": False,
            "generated_at": new_comparison.created_at,
            "model_name": llm_config["model"]
        }

    @staticmethod
    def validate_same_type(reports: List[Report]) -> bool:
        """Check if reports are of the same type for comparison."""
        if not reports:
            return False
        
        # Group by category first
        categories = [r.category for r in reports if r.category]
        if categories and len(set(categories)) == 1:
            return True
        
        # Then by doc_type
        doc_types = [r.doc_type for r in reports if r.doc_type]
        if doc_types and len(set(doc_types)) == 1:
            return True
        
        return False
