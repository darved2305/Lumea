"""
Document Processing Pipeline Service

Orchestrates the full document processing flow:
1. File upload and validation
2. OCR text extraction
3. REGEX classification
4. Metric extraction (REGEX → Grok fallback)
5. Missing parameter detection
6. Database persistence
7. Recompute trigger

Author: Co-Code GGW Health Platform
"""
import logging
import uuid
import os
from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models import (
    Report, ReportStatus, Observation, ObservationType,
    DocumentOCR, MissingDataTask, User
)
from app.services.pdf_extractor import PDFExtractor
from app.services.document_classifier import classify_document, ClassificationResult
from app.services.metric_extractor import (
    extract_metrics_regex, 
    ExtractedMetric, 
    get_missing_parameters,
    MissingParameter,
    METRIC_LABELS,
    METRIC_UNITS,
)
from app.services.grok_extractor import extract_document_metrics

logger = logging.getLogger(__name__)


class DocumentProcessingService:
    """
    Full document processing pipeline service.
    
    Handles the entire flow from file upload to extracted observations.
    """
    
    UPLOAD_DIR = Path("./uploads")
    ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
    
    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user
        self.pdf_extractor = PDFExtractor()
    
    def _get_user_upload_dir(self) -> Path:
        """Get user-specific upload directory"""
        user_dir = self.UPLOAD_DIR / str(self.user.id)
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir
    
    def _validate_file(self, filename: str, file_size: int) -> None:
        """Validate file upload"""
        ext = Path(filename).suffix.lower()
        
        if ext not in self.ALLOWED_EXTENSIONS:
            raise ValueError(f"File type {ext} not allowed. Allowed: {self.ALLOWED_EXTENSIONS}")
        
        if file_size > self.MAX_FILE_SIZE:
            raise ValueError(f"File too large. Max size: {self.MAX_FILE_SIZE / 1024 / 1024}MB")
        
        # Prevent path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            raise ValueError("Invalid filename")
    
    async def upload_document(
        self,
        filename: str,
        file_content: bytes,
        report_date: Optional[datetime] = None
    ) -> Report:
        """
        Upload and initially save a document.
        
        Args:
            filename: Original filename
            file_content: File bytes
            report_date: Date on the report (if known)
        
        Returns:
            Created Report object (status: UPLOADED)
        """
        # Validate
        self._validate_file(filename, len(file_content))
        
        # Generate unique filename
        ext = Path(filename).suffix.lower()
        unique_filename = f"{uuid.uuid4()}{ext}"
        user_dir = self._get_user_upload_dir()
        file_path = user_dir / unique_filename
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Create database record
        report = Report(
            id=uuid.uuid4(),
            user_id=self.user.id,
            filename=filename,
            file_path=str(file_path),
            file_type=ext[1:],
            file_size=len(file_content),
            status=ReportStatus.UPLOADED,
            report_date=report_date,
        )
        
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        
        logger.info(f"Document uploaded: {report.id} ({filename})")
        return report
    
    async def extract_ocr_text(self, report: Report) -> DocumentOCR:
        """
        Extract text from document using TEXT-FIRST + OCR fallback.
        
        Args:
            report: Report to extract text from
        
        Returns:
            DocumentOCR record with extracted text
        """
        # Update status
        report.status = ReportStatus.EXTRACTING
        await self.db.commit()
        
        try:
            # Read file
            with open(report.file_path, "rb") as f:
                file_content = f.read()
            
            # Extract based on file type
            if report.file_type == "pdf":
                extraction_result = self.pdf_extractor.extract(file_content)
            else:
                # For images, go straight to OCR
                extraction_result = self.pdf_extractor.extract_text_ocr(file_content)
            
            # Create/update DocumentOCR record
            doc_ocr = DocumentOCR(
                id=uuid.uuid4(),
                document_id=report.id,
                ocr_text=extraction_result.full_text,
                ocr_json={
                    "page_stats": extraction_result.page_stats,
                    "method": extraction_result.method,
                },
                extraction_method=extraction_result.method,
                total_chars=extraction_result.total_chars,
                total_pages=len(extraction_result.page_stats) if extraction_result.page_stats else 0,
            )
            
            self.db.add(doc_ocr)
            
            # Update report with raw text
            report.raw_text = extraction_result.full_text
            report.extraction_method = extraction_result.method
            report.page_stats = extraction_result.page_stats
            
            if extraction_result.success:
                report.status = ReportStatus.EXTRACTED
            else:
                report.status = ReportStatus.FAILED
                report.error_message = extraction_result.error
            
            await self.db.commit()
            await self.db.refresh(doc_ocr)
            
            logger.info(f"OCR extraction complete for {report.id}: {extraction_result.method}, {extraction_result.total_chars} chars")
            return doc_ocr
            
        except Exception as e:
            logger.error(f"OCR extraction failed for {report.id}: {e}")
            report.status = ReportStatus.FAILED
            report.error_message = str(e)
            await self.db.commit()
            raise
    
    async def classify_document(self, report: Report, ocr_text: str) -> ClassificationResult:
        """
        Classify document using REGEX rules.
        
        Args:
            report: Report to classify
            ocr_text: Extracted OCR text
        
        Returns:
            ClassificationResult with category, type, confidence
        """
        classification = classify_document(ocr_text, report.filename)
        
        # Update report with classification
        report.category = classification.category
        report.doc_type = classification.document_type
        report.classification_confidence = classification.confidence
        report.classification_rules_matched = [
            {"rule": r["rule_name"], "count": r["match_count"]}
            for r in classification.matched_rules
        ]
        
        await self.db.commit()
        
        logger.info(f"Document {report.id} classified: {classification.category}/{classification.document_type} ({classification.confidence})")
        return classification
    
    async def extract_and_save_metrics(
        self, 
        report: Report, 
        ocr_text: str,
        classification: ClassificationResult
    ) -> Dict[str, Any]:
        """
        Extract metrics and save as observations.
        
        Uses the full extraction pipeline:
        1. REGEX extraction
        2. Grok fallback if needed
        3. Create observations
        4. Create missing data tasks
        
        Args:
            report: Report being processed
            ocr_text: Extracted OCR text
            classification: Document classification
        
        Returns:
            Dict with metrics, missing_parameters, extraction_source, confidence
        """
        report.status = ReportStatus.PROCESSING
        await self.db.commit()
        
        try:
            # Run full extraction pipeline
            extraction_result = await extract_document_metrics(
                ocr_text, 
                report.filename,
                classification.document_type
            )
            
            # Update report extraction info
            report.extraction_source = extraction_result["extraction_source"]
            report.extraction_confidence = extraction_result["confidence"]
            report.extracted_data = {
                "metrics": extraction_result["metrics"],
                "warnings": extraction_result["warnings"]
            }
            
            # Create observations from extracted metrics
            observations_created = []
            report_date = report.report_date or datetime.utcnow()
            
            for metric in extraction_result["metrics"]:
                # Skip if no value
                if metric.get("value") is None:
                    continue
                
                # Determine observation type
                obs_type = self._determine_observation_type(metric["metric_key"])
                
                obs = Observation(
                    id=uuid.uuid4(),
                    user_id=self.user.id,
                    report_id=report.id,
                    observation_type=obs_type,
                    metric_name=metric["metric_key"],
                    display_name=metric.get("display_name", metric["metric_key"]),
                    value=metric["value"],
                    unit=metric.get("unit", ""),
                    observed_at=report_date,
                    reference_min=metric.get("reference_min"),
                    reference_max=metric.get("reference_max"),
                    is_abnormal=metric.get("is_abnormal", False),
                    flag=metric.get("flag"),
                    source=extraction_result["extraction_source"],
                    confidence=metric.get("confidence", 0.8),
                    user_corrected=False,
                    raw_line=metric.get("raw_line", ""),
                    page_num=metric.get("page_num", 1),
                )
                
                self.db.add(obs)
                observations_created.append(obs)
            
            # Create missing data tasks
            missing_tasks_created = []
            for missing in extraction_result["missing_parameters"]:
                task = MissingDataTask(
                    id=uuid.uuid4(),
                    user_id=self.user.id,
                    document_id=report.id,
                    metric_key=missing["metric_key"],
                    label=missing["label"],
                    expected_unit=missing.get("expected_unit", ""),
                    required=missing.get("required", True),
                    status="pending",
                )
                
                self.db.add(task)
                missing_tasks_created.append(task)
            
            # Update report status
            if missing_tasks_created:
                report.status = ReportStatus.EXTRACTED  # Needs user input
            else:
                report.status = ReportStatus.PROCESSED
            
            report.processed_at = datetime.utcnow()
            
            await self.db.commit()
            
            # Refresh all created objects
            for obs in observations_created:
                await self.db.refresh(obs)
            for task in missing_tasks_created:
                await self.db.refresh(task)
            
            logger.info(f"Document {report.id}: {len(observations_created)} observations, {len(missing_tasks_created)} missing tasks")
            
            return {
                "observations_created": len(observations_created),
                "missing_tasks_created": len(missing_tasks_created),
                "extraction_source": extraction_result["extraction_source"],
                "confidence": extraction_result["confidence"],
                "warnings": extraction_result["warnings"]
            }
            
        except Exception as e:
            logger.error(f"Metric extraction failed for {report.id}: {e}")
            report.status = ReportStatus.FAILED
            report.error_message = str(e)
            await self.db.commit()
            raise
    
    def _determine_observation_type(self, metric_key: str) -> ObservationType:
        """Determine observation type from metric key."""
        vital_signs = {"systolic_bp", "diastolic_bp", "heart_rate", "respiratory_rate", "temperature", "spo2"}
        physical = {"weight", "height", "bmi", "waist"}
        lifestyle = {"sleep_hours", "exercise_minutes", "steps"}
        
        if metric_key in vital_signs:
            return ObservationType.VITAL_SIGN
        elif metric_key in physical:
            return ObservationType.PHYSICAL_MEASUREMENT
        elif metric_key in lifestyle:
            return ObservationType.LIFESTYLE
        else:
            return ObservationType.LAB_VALUE
    
    async def process_document_full(
        self,
        filename: str,
        file_content: bytes,
        report_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Run full document processing pipeline.
        
        This is the main entry point for processing uploaded documents.
        
        Args:
            filename: Original filename
            file_content: File bytes
            report_date: Date on the report (if known)
        
        Returns:
            Dict with report_id, status, classification, metrics info
        """
        # Step 1: Upload
        report = await self.upload_document(filename, file_content, report_date)
        
        # Step 2: Extract OCR text
        doc_ocr = await self.extract_ocr_text(report)
        
        if not doc_ocr.ocr_text or len(doc_ocr.ocr_text) < 50:
            return {
                "report_id": str(report.id),
                "status": "failed",
                "error": "Could not extract text from document",
                "classification": None,
                "metrics_info": None
            }
        
        # Step 3: Classify
        classification = await self.classify_document(report, doc_ocr.ocr_text)
        
        # Step 4: Extract metrics
        metrics_info = await self.extract_and_save_metrics(
            report, doc_ocr.ocr_text, classification
        )
        
        return {
            "report_id": str(report.id),
            "status": report.status.value,
            "classification": {
                "category": classification.category,
                "document_type": classification.document_type,
                "confidence": classification.confidence
            },
            "metrics_info": metrics_info
        }
    
    # =========================================================================
    # MISSING DATA TASKS
    # =========================================================================
    
    async def get_missing_tasks(
        self, 
        document_id: Optional[uuid.UUID] = None
    ) -> List[MissingDataTask]:
        """
        Get pending missing data tasks for user.
        
        Args:
            document_id: Optional - filter by specific document
        
        Returns:
            List of pending MissingDataTask records
        """
        query = select(MissingDataTask).where(
            MissingDataTask.user_id == self.user.id,
            MissingDataTask.status == "pending"
        )
        
        if document_id:
            query = query.where(MissingDataTask.document_id == document_id)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def resolve_missing_tasks(
        self,
        document_id: uuid.UUID,
        values: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Resolve missing data tasks with user-provided values.
        
        Args:
            document_id: Document these values belong to
            values: List of dicts with {metric_key, value, unit, observed_at?}
        
        Returns:
            Dict with observations_created, tasks_resolved counts
        """
        # Get the report
        result = await self.db.execute(
            select(Report).where(
                Report.id == document_id,
                Report.user_id == self.user.id
            )
        )
        report = result.scalar_one_or_none()
        
        if not report:
            raise ValueError("Document not found")
        
        observations_created = 0
        tasks_resolved = 0
        
        for val in values:
            metric_key = val.get("metric_key")
            value = val.get("value")
            
            if metric_key is None or value is None:
                continue
            
            # Create observation
            obs_type = self._determine_observation_type(metric_key)
            observed_at = val.get("observed_at") or report.report_date or datetime.utcnow()
            
            obs = Observation(
                id=uuid.uuid4(),
                user_id=self.user.id,
                report_id=document_id,
                observation_type=obs_type,
                metric_name=metric_key,
                display_name=METRIC_LABELS.get(metric_key, metric_key),
                value=value,
                unit=val.get("unit") or METRIC_UNITS.get(metric_key, ""),
                observed_at=observed_at,
                source="manual",
                confidence=1.0,
                user_corrected=True,
            )
            
            self.db.add(obs)
            observations_created += 1
            
            # Resolve matching task
            task_result = await self.db.execute(
                select(MissingDataTask).where(
                    MissingDataTask.document_id == document_id,
                    MissingDataTask.user_id == self.user.id,
                    MissingDataTask.metric_key == metric_key,
                    MissingDataTask.status == "pending"
                )
            )
            task = task_result.scalar_one_or_none()
            
            if task:
                task.status = "resolved"
                task.resolved_at = datetime.utcnow()
                tasks_resolved += 1
        
        # Check if all tasks for this document are resolved
        remaining_tasks = await self.get_missing_tasks(document_id)
        
        if not remaining_tasks:
            # All tasks resolved, update report status
            report.status = ReportStatus.CONFIRMED
        
        await self.db.commit()
        
        logger.info(f"Resolved {tasks_resolved} missing tasks, created {observations_created} observations")
        
        return {
            "observations_created": observations_created,
            "tasks_resolved": tasks_resolved,
            "remaining_tasks": len(remaining_tasks)
        }
    
    async def skip_missing_tasks(
        self,
        document_id: uuid.UUID,
        metric_keys: List[str]
    ) -> int:
        """
        Skip specified missing data tasks.
        
        Args:
            document_id: Document these tasks belong to
            metric_keys: List of metric keys to skip
        
        Returns:
            Number of tasks skipped
        """
        skipped = 0
        
        for metric_key in metric_keys:
            result = await self.db.execute(
                select(MissingDataTask).where(
                    MissingDataTask.document_id == document_id,
                    MissingDataTask.user_id == self.user.id,
                    MissingDataTask.metric_key == metric_key,
                    MissingDataTask.status == "pending"
                )
            )
            task = result.scalar_one_or_none()
            
            if task:
                task.status = "skipped"
                task.resolved_at = datetime.utcnow()
                skipped += 1
        
        await self.db.commit()
        return skipped
    
    # =========================================================================
    # REPROCESSING
    # =========================================================================
    
    async def reprocess_document(self, document_id: uuid.UUID) -> Dict[str, Any]:
        """
        Reprocess an existing document (re-run extraction).
        
        Args:
            document_id: Document to reprocess
        
        Returns:
            Dict with new processing results
        """
        # Get report
        result = await self.db.execute(
            select(Report).where(
                Report.id == document_id,
                Report.user_id == self.user.id
            )
        )
        report = result.scalar_one_or_none()
        
        if not report:
            raise ValueError("Document not found")
        
        # Get existing OCR text or re-extract
        if report.raw_text:
            ocr_text = report.raw_text
        else:
            doc_ocr = await self.extract_ocr_text(report)
            ocr_text = doc_ocr.ocr_text
        
        # Re-classify
        classification = await self.classify_document(report, ocr_text)
        
        # Clear existing observations and tasks for this document
        await self.db.execute(
            Observation.__table__.delete().where(Observation.report_id == document_id)
        )
        await self.db.execute(
            MissingDataTask.__table__.delete().where(MissingDataTask.document_id == document_id)
        )
        
        # Re-extract metrics
        metrics_info = await self.extract_and_save_metrics(report, ocr_text, classification)
        
        return {
            "report_id": str(report.id),
            "status": report.status.value,
            "classification": {
                "category": classification.category,
                "document_type": classification.document_type,
                "confidence": classification.confidence
            },
            "metrics_info": metrics_info
        }
