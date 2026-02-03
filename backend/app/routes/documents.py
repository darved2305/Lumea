"""
Document Processing API Routes

Provides endpoints for:
- Document upload and processing
- Classification results
- Missing data task management
- Reprocessing

Author: Co-Code GGW Health Platform
"""
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field, ConfigDict

from app.db import get_db
from app.db import async_session_maker
from app.security import get_current_user
from app.models import User, Report, MissingDataTask, Observation
from app.services.document_processing import DocumentProcessingService
from app.services.recompute_service import RecomputeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])


# ============================================================================
# SCHEMAS
# ============================================================================

class ClassificationResponse(BaseModel):
    category: str
    document_type: str
    confidence: float
    rules_matched: Optional[List[dict]] = None


class MetricsInfoResponse(BaseModel):
    observations_created: int
    missing_tasks_created: int
    extraction_source: str
    confidence: float
    warnings: List[str]


class DocumentUploadResponse(BaseModel):
    report_id: str
    status: str
    classification: Optional[ClassificationResponse] = None
    metrics_info: Optional[MetricsInfoResponse] = None
    error: Optional[str] = None


class MissingTaskResponse(BaseModel):
    id: UUID
    metric_key: str
    label: str
    expected_unit: Optional[str]
    required: bool
    
    model_config = ConfigDict(from_attributes=True)


class MissingTasksListResponse(BaseModel):
    document_id: UUID
    tasks: List[MissingTaskResponse]


class ManualValueInput(BaseModel):
    metric_key: str
    value: float
    unit: Optional[str] = None
    observed_at: Optional[datetime] = None


class ResolveMissingTasksRequest(BaseModel):
    values: List[ManualValueInput]


class ResolveMissingTasksResponse(BaseModel):
    observations_created: int
    tasks_resolved: int
    remaining_tasks: int


class SkipTasksRequest(BaseModel):
    metric_keys: List[str]


class DocumentDetailResponse(BaseModel):
    id: UUID
    filename: str
    file_type: str
    file_size: int
    status: str
    category: Optional[str]
    doc_type: Optional[str]
    classification_confidence: Optional[float]
    extraction_source: Optional[str]
    extraction_confidence: Optional[float]
    report_date: Optional[datetime]
    uploaded_at: datetime
    processed_at: Optional[datetime]
    error_message: Optional[str]
    observation_count: int
    missing_task_count: int
    
    model_config = ConfigDict(from_attributes=True)


class ObservationBriefResponse(BaseModel):
    id: UUID
    metric_name: str
    display_name: Optional[str]
    value: float
    unit: str
    flag: Optional[str]
    is_abnormal: bool
    source: Optional[str]
    user_corrected: bool
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    report_date: Optional[datetime] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload and process a medical document.
    
    The document goes through:
    1. File validation
    2. OCR text extraction
    3. REGEX classification
    4. Metric extraction (REGEX + Grok fallback)
    5. Missing parameter detection
    
    Returns classification, extraction results, and any missing tasks.
    """
    try:
        # Read file content
        file_content = await file.read()
        
        # Initialize service
        service = DocumentProcessingService(db, current_user)
        
        # Process document
        result = await service.process_document_full(
            filename=file.filename,
            file_content=file_content,
            report_date=report_date
        )
        
        # Trigger recompute in background
        async def bg_recompute():
            try:
                # Use a fresh DB session; request-scoped `db` is closed after response.
                async with async_session_maker() as session:
                    recompute_service = RecomputeService(session, current_user)
                    await recompute_service.recompute_all(emit_events=True)
            except Exception as e:
                logger.error(f"Background recompute failed: {e}")
        
        background_tasks.add_task(bg_recompute)
        
        # Build response
        response = DocumentUploadResponse(
            report_id=result["report_id"],
            status=result["status"],
            error=result.get("error")
        )
        
        if result.get("classification"):
            response.classification = ClassificationResponse(
                category=result["classification"]["category"],
                document_type=result["classification"]["document_type"],
                confidence=result["classification"]["confidence"]
            )
        
        if result.get("metrics_info"):
            response.metrics_info = MetricsInfoResponse(
                observations_created=result["metrics_info"]["observations_created"],
                missing_tasks_created=result["metrics_info"]["missing_tasks_created"],
                extraction_source=result["metrics_info"]["extraction_source"],
                confidence=result["metrics_info"]["confidence"],
                warnings=result["metrics_info"]["warnings"]
            )
        
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(status_code=500, detail="Document processing failed")


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document_detail(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a document.
    
    Includes classification, extraction info, observation count, and missing task count.
    """
    # Get report
    result = await db.execute(
        select(Report).where(
            Report.id == document_id,
            Report.user_id == current_user.id
        )
    )
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Count observations
    obs_result = await db.execute(
        select(Observation).where(Observation.report_id == document_id)
    )
    observations = obs_result.scalars().all()
    
    # Count missing tasks
    task_result = await db.execute(
        select(MissingDataTask).where(
            MissingDataTask.document_id == document_id,
            MissingDataTask.status == "pending"
        )
    )
    missing_tasks = task_result.scalars().all()
    
    return DocumentDetailResponse(
        id=report.id,
        filename=report.filename,
        file_type=report.file_type,
        file_size=report.file_size,
        status=report.status.value,
        category=report.category,
        doc_type=report.doc_type,
        classification_confidence=report.classification_confidence,
        extraction_source=report.extraction_source,
        extraction_confidence=report.extraction_confidence,
        report_date=report.report_date,
        uploaded_at=report.uploaded_at,
        processed_at=report.processed_at,
        error_message=report.error_message,
        observation_count=len(observations),
        missing_task_count=len(missing_tasks)
    )


@router.get("/{document_id}/observations", response_model=List[ObservationBriefResponse])
async def get_document_observations(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all observations extracted from a document.
    """
    # Verify document belongs to user
    result = await db.execute(
        select(Report).where(
            Report.id == document_id,
            Report.user_id == current_user.id
        )
    )
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get observations
    obs_result = await db.execute(
        select(Observation).where(Observation.report_id == document_id)
    )
    observations = obs_result.scalars().all()
    
    return [
        ObservationBriefResponse(
            id=obs.id,
            metric_name=obs.metric_name,
            display_name=obs.display_name,
            value=float(obs.value),
            unit=obs.unit,
            flag=obs.flag,
            is_abnormal=obs.is_abnormal,
            source=obs.source,
            user_corrected=obs.user_corrected
        )
        for obs in observations
    ]


@router.get("/{document_id}/missing-tasks", response_model=MissingTasksListResponse)
async def get_document_missing_tasks(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get pending missing data tasks for a document.
    
    These are required parameters that could not be extracted and need
    manual input from the user.
    """
    service = DocumentProcessingService(db, current_user)
    
    # Verify document belongs to user
    result = await db.execute(
        select(Report).where(
            Report.id == document_id,
            Report.user_id == current_user.id
        )
    )
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="Document not found")
    
    tasks = await service.get_missing_tasks(document_id)
    
    return MissingTasksListResponse(
        document_id=document_id,
        tasks=[
            MissingTaskResponse(
                id=task.id,
                metric_key=task.metric_key,
                label=task.label,
                expected_unit=task.expected_unit,
                required=task.required
            )
            for task in tasks
        ]
    )


@router.post("/{document_id}/missing-tasks", response_model=ResolveMissingTasksResponse)
async def resolve_missing_tasks(
    document_id: UUID,
    request: ResolveMissingTasksRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit manual values for missing parameters.
    
    This creates new observations with user_corrected=true and resolves
    the corresponding missing data tasks.
    """
    service = DocumentProcessingService(db, current_user)
    
    try:
        result = await service.resolve_missing_tasks(
            document_id=document_id,
            values=[v.model_dump() for v in request.values]
        )
        
        # Trigger recompute in background (fresh session)
        async def bg_recompute():
            try:
                async with async_session_maker() as session:
                    recompute_service = RecomputeService(session, current_user)
                    await recompute_service.recompute_all(emit_events=True)
            except Exception as e:
                logger.error(f"Background recompute failed: {e}")
        
        background_tasks.add_task(bg_recompute)
        
        return ResolveMissingTasksResponse(
            observations_created=result["observations_created"],
            tasks_resolved=result["tasks_resolved"],
            remaining_tasks=result["remaining_tasks"]
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{document_id}/missing-tasks/skip")
async def skip_missing_tasks(
    document_id: UUID,
    request: SkipTasksRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Skip specified missing data tasks.
    
    Use this when the user doesn't have the values and wants to proceed anyway.
    """
    service = DocumentProcessingService(db, current_user)
    
    try:
        skipped = await service.skip_missing_tasks(document_id, request.metric_keys)
        return {"skipped": skipped}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{document_id}/reprocess", response_model=DocumentUploadResponse)
async def reprocess_document(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reprocess an existing document.
    
    This re-runs the entire extraction pipeline (classification, metric extraction)
    and replaces previous results.
    """
    service = DocumentProcessingService(db, current_user)
    
    try:
        result = await service.reprocess_document(document_id)
        
        # Trigger recompute in background (fresh session)
        async def bg_recompute():
            try:
                async with async_session_maker() as session:
                    recompute_service = RecomputeService(session, current_user)
                    await recompute_service.recompute_all(emit_events=True)
            except Exception as e:
                logger.error(f"Background recompute failed: {e}")
        
        background_tasks.add_task(bg_recompute)
        
        # Build response
        response = DocumentUploadResponse(
            report_id=result["report_id"],
            status=result["status"],
            error=result.get("error")
        )
        
        if result.get("classification"):
            response.classification = ClassificationResponse(
                category=result["classification"]["category"],
                document_type=result["classification"]["document_type"],
                confidence=result["classification"]["confidence"]
            )
        
        if result.get("metrics_info"):
            response.metrics_info = MetricsInfoResponse(
                observations_created=result["metrics_info"]["observations_created"],
                missing_tasks_created=result["metrics_info"]["missing_tasks_created"],
                extraction_source=result["metrics_info"]["extraction_source"],
                confidence=result["metrics_info"]["confidence"],
                warnings=result["metrics_info"]["warnings"]
            )
        
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Document reprocess failed: {e}")
        raise HTTPException(status_code=500, detail="Reprocessing failed")


# ============================================================================
# USER MISSING TASKS (ALL DOCUMENTS)
# ============================================================================

@router.get("/user/missing-tasks")
async def get_user_missing_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all pending missing data tasks across all user documents.
    
    Useful for showing a global "action required" list.
    """
    service = DocumentProcessingService(db, current_user)
    tasks = await service.get_missing_tasks()
    
    # Group by document
    by_document = {}
    for task in tasks:
        doc_id = str(task.document_id)
        if doc_id not in by_document:
            by_document[doc_id] = []
        by_document[doc_id].append({
            "id": str(task.id),
            "metric_key": task.metric_key,
            "label": task.label,
            "expected_unit": task.expected_unit,
            "required": task.required
        })
    
    return {
        "total_count": len(tasks),
        "by_document": by_document
    }
