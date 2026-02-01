"""
Enhanced Report Processing Service

Integrates:
- PDF extraction (text-first, OCR fallback)
- Lab report parsing  
- Observation storage
- WebSocket event emission
"""
import logging
import os
from pathlib import Path
from typing import Optional
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models import Report, Observation, ReportStatus, ObservationType
from src.services.pdf_extractor import PDFExtractor
from src.services.lab_parser import LabParser

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class EnhancedReportService:
    """
    Enhanced report processing with text-first extraction
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.extractor = PDFExtractor()
        self.parser = LabParser()
        self.upload_dir = Path("uploads")
        self.upload_dir.mkdir(exist_ok=True)
    
    async def process_report(self, report_id: UUID, user_id: UUID):
        """
        Full pipeline: extract text -> parse metrics -> save observations -> emit events
        """
        # Import here to avoid circular import
        from src.routes.websocket import (
            emit_report_processing_started,
            emit_report_parsed,
            emit_reports_list_updated
        )
        
        logger.info(f"Processing report {report_id} for user {user_id}")
        
        # Fetch report
        result = await self.db.execute(
            select(Report).where(Report.id == report_id)
        )
        report = result.scalars().first()
        
        if not report:
            logger.error(f"Report {report_id} not found")
            return
        
        try:
            # Update status
            report.status = ReportStatus.EXTRACTING
            await self.db.commit()
            
            # Emit start event
            await emit_report_processing_started(str(user_id), {
                "report_id": str(report_id),
                "progress": 10
            })
            
            # Step 1: Extract text from PDF
            logger.info(f"Extracting text from {report.file_path}")
            
            with open(report.file_path, 'rb') as f:
                pdf_bytes = f.read()
            
            extraction_result = self.extractor.extract(pdf_bytes)
            
            if not extraction_result.success:
                logger.error(f"Extraction failed: {extraction_result.error}")
                report.status = ReportStatus.FAILED
                report.error_message = extraction_result.error
                report.extraction_method = "failed"
                await self.db.commit()
                
                await emit_report_parsed(str(user_id), {
                    "report_id": str(report_id),
                    "extracted_metrics_count": 0,
                    "status": "failed"
                })
                return
            
            # Save extraction results
            report.raw_text = extraction_result.full_text
            report.extraction_method = extraction_result.method
            report.page_stats = extraction_result.page_stats
            report.status = ReportStatus.EXTRACTED
            await self.db.commit()
            
            logger.info(f"Extraction successful: {extraction_result.method}, {extraction_result.total_chars} chars")
            
            await emit_report_processing_started(str(user_id), {
                "report_id": str(report_id),
                "progress": 40
            })
            
            # Step 2: Parse lab metrics
            logger.info("Parsing lab metrics...")
            report.status = ReportStatus.PROCESSING
            await self.db.commit()
            
            metrics = self.parser.parse(extraction_result.full_text)
            
            if not metrics:
                logger.warning("No metrics parsed from text")
                report.status = ReportStatus.PROCESSED
                report.processed_at = datetime.utcnow()
                await self.db.commit()
                
                await emit_report_parsed(str(user_id), {
                    "report_id": str(report_id),
                    "extracted_metrics_count": 0,
                    "status": "complete"
                })
                await emit_reports_list_updated(str(user_id))
                return
            
            logger.info(f"Parsed {len(metrics)} metrics")
            
            # Step 3: Save observations
            observation_count = 0
            observed_at = report.report_date or report.uploaded_at
            
            for metric in metrics:
                # Log unmapped metrics but still save them
                if metric.canonical_key == "unmapped":
                    logger.warning(f"Unmapped metric (saving anyway): {metric.test_name} = {metric.value} {metric.unit}")
                    # Use the test name as metric_name for unmapped items
                    metric_name = metric.test_name.lower().replace(' ', '_')[:50]
                else:
                    metric_name = metric.canonical_key
                
                observation = Observation(
                    user_id=user_id,
                    report_id=report_id,
                    observation_type=ObservationType.LAB_VALUE,
                    metric_name=metric_name,
                    display_name=metric.test_name,
                    value=metric.value,
                    unit=metric.unit,
                    reference_min=metric.ref_range_low,
                    reference_max=metric.ref_range_high,
                    flag=metric.flag,
                    observed_at=observed_at,
                    raw_line=metric.raw_line,
                    page_num=metric.page_num
                )
                
                # Determine if abnormal
                if metric.ref_range_low is not None and metric.value < metric.ref_range_low:
                    observation.is_abnormal = True
                elif metric.ref_range_high is not None and metric.value > metric.ref_range_high:
                    observation.is_abnormal = True
                
                self.db.add(observation)
                observation_count += 1
            
            await self.db.commit()
            
            logger.info(f"Saved {observation_count} observations")
            
            # Update report status
            report.status = ReportStatus.PROCESSED
            report.processed_at = datetime.utcnow()
            report.extraction_confidence = 0.9 if extraction_result.method == "text" else 0.7
            await self.db.commit()
            
            # Emit completion events
            await emit_report_parsed(str(user_id), {
                "report_id": str(report_id),
                "extracted_metrics_count": observation_count,
                "status": "complete"
            })
            
            await emit_reports_list_updated(str(user_id))
            
            # Trigger health index recomputation
            await self._recompute_health_index_and_emit(user_id)
            
            logger.info(f"Report {report_id} processing complete with {observation_count} observations")
            
        except Exception as e:
            logger.exception(f"Error processing report {report_id}: {e}")
            report.status = ReportStatus.FAILED
            report.error_message = str(e)
            await self.db.commit()
            
            await emit_report_parsed(str(user_id), {
                "report_id": str(report_id),
                "extracted_metrics_count": 0,
                "status": "failed"
            })

    async def _recompute_health_index_and_emit(self, user_id: UUID):
        """Recompute health index after processing and emit WebSocket events"""
        from src.routes.websocket import (
            emit_health_index_updated,
            emit_trends_updated,
            emit_recommendations_updated
        )
        from src.services.metrics_service import MetricsService
        
        try:
            metrics_service = MetricsService(self.db)
            health_metric = await metrics_service.compute_health_index(user_id)
            
            if health_metric:
                logger.info(f"Health index recomputed for user {user_id}: {health_metric.value}")
                
                # Emit health index update
                await emit_health_index_updated(str(user_id), {
                    "score": float(health_metric.value),
                    "confidence": float(health_metric.confidence),
                    "contributions": health_metric.contributions
                })
                
                # Emit trends update
                await emit_trends_updated(str(user_id), {
                    "metrics": ["health_index"]
                })
                
                # Emit recommendations update (count will be fetched by frontend)
                await emit_recommendations_updated(str(user_id), count=0, urgent_count=0)
            else:
                logger.info(f"No health index computed for user {user_id} (insufficient data)")
                
        except Exception as e:
            logger.exception(f"Error computing health index for user {user_id}: {e}")
