"""
Reports API Endpoints
Handle report upload, listing, and confirmation
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
import uuid
from datetime import datetime
from pathlib import Path
import os
import asyncio
import logging

from src.config import get_db, async_session_maker
from src.middleware import get_current_user
from src.models import User, Report, ReportStatus
from src.models import (
    ReportListItem,
    ReportDetail,
    ReportConfirmRequest,
    ReportStatusEnum
)
from src.services.report_service import ReportService
from src.services.enhanced_report_service import EnhancedReportService

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/api/reports", tags=["reports"])

# Upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Allowed file types
ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def run_async_in_thread(coro):
    """Run an async coroutine in a new event loop (for background tasks)"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _process_report_async(report_id: UUID, user_id: UUID):
    """Async processing with its own DB session"""
    async with async_session_maker() as db:
        try:
            logger.info(f"Background: Starting processing for report {report_id}")
            enhanced_service = EnhancedReportService(db)
            await enhanced_service.process_report(report_id, user_id)
            logger.info(f"Background: Completed processing for report {report_id}")
        except Exception as e:
            logger.exception(f"Background: Error processing report {report_id}: {e}")


def process_report_background(report_id: UUID, user_id: UUID):
    """Sync wrapper for background task - creates its own async context"""
    run_async_in_thread(_process_report_async(report_id, user_id))


@router.get("", response_model=List[ReportListItem])
async def list_reports(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all reports for current user
    
    Returns paginated list of reports with metadata
    """
    from sqlalchemy import select, func
    
    # Fetch reports with async query
    result = await db.execute(
        select(Report)
        .where(Report.user_id == current_user.id)
        .order_by(Report.uploaded_at.desc())
        .limit(limit)
        .offset(offset)
    )
    reports = result.scalars().all()
    
    # Build response with observation counts
    from src.models import Observation
    result_list = []
    for report in reports:
        # Count observations for this report
        count_result = await db.execute(
            select(func.count(Observation.id)).where(Observation.report_id == report.id)
        )
        obs_count = count_result.scalar() or 0
        
        result_list.append(ReportListItem(
            id=report.id,
            filename=report.filename,
            file_type=report.file_type,
            file_size=report.file_size,
            status=ReportStatusEnum(report.status.value),
            report_date=report.report_date,
            uploaded_at=report.uploaded_at,
            processed_at=report.processed_at,
            extraction_confidence=report.extraction_confidence,
            observation_count=obs_count
        ))
    
    return result_list


@router.post("/upload")
async def upload_report(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    report_date: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a new medical report
    
    Accepts PDF, PNG, JPG, JPEG, TIFF files
    Automatically triggers extraction in background using enhanced pipeline
    
    Args:
        file: Report file (multipart/form-data)
        report_date: Optional date on the report (ISO format)
        category: Optional category (Lab, Dental, MRI, etc.)
    
    Returns:
        Created report with ID and status
    """
    logger.info(f"Upload request received: {file.filename} from user {current_user.id}")
    
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower() if file.filename else ''
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"File type not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    try:
        content = await file.read()
        
        # Validate file size
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        # Parse report_date if provided
        parsed_date = None
        if report_date:
            try:
                parsed_date = datetime.fromisoformat(report_date.replace("Z", "+00:00"))
            except:
                raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format (YYYY-MM-DD)")
        
        # Create user-specific upload directory
        user_upload_dir = UPLOAD_DIR / str(current_user.id)
        user_upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file to disk with unique name
        file_id = str(uuid.uuid4())
        safe_filename = f"{file_id}{file_ext}"
        file_path = user_upload_dir / safe_filename
        
        with open(file_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"File saved to: {file_path}")
        
        # Create report record
        report = Report(
            user_id=current_user.id,
            filename=file.filename,
            file_path=str(file_path),
            file_type=file_ext,
            file_size=len(content),
            status=ReportStatus.UPLOADED,
            report_date=parsed_date
        )
        
        db.add(report)
        await db.commit()
        await db.refresh(report)
        
        report_id = report.id
        user_id = current_user.id
        
        logger.info(f"Report record created: {report_id}")
        
        # Trigger processing in background - use asyncio.create_task
        asyncio.create_task(_process_report_async(report_id, user_id))
        
        return {
            "id": str(report.id),
            "filename": report.filename,
            "status": report.status.value,
            "uploaded_at": report.uploaded_at.isoformat(),
            "message": "Report uploaded successfully. Extraction started in background."
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/{report_id}", response_model=ReportDetail)
async def get_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed report information
    
    Includes extracted data and raw text
    """
    report_service = ReportService(db)
    report = report_service.get_report_by_id(report_id, current_user.id)
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return ReportDetail(
        id=report.id,
        filename=report.filename,
        file_type=report.file_type,
        file_size=report.file_size,
        status=ReportStatusEnum(report.status.value),
        report_date=report.report_date,
        uploaded_at=report.uploaded_at,
        processed_at=report.processed_at,
        raw_text=report.raw_text,
        extracted_data=report.extracted_data,
        extraction_confidence=report.extraction_confidence,
        error_message=report.error_message
    )


@router.post("/{report_id}/confirm")
async def confirm_report(
    report_id: UUID,
    confirmation: ReportConfirmRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Confirm or correct extracted values from a report
    
    Creates observations from confirmed values and triggers metric recomputation
    
    Args:
        report_id: Report ID
        confirmation: Confirmed/corrected values
    
    Returns:
        Updated report status
    """
    report_service = ReportService(db)
    
    try:
        report = await report_service.confirm_extracted_values(
            report_id,
            current_user.id,
            confirmation
        )
        
        # Trigger metrics recomputation in background
        from src.services.metrics_service import MetricsService
        metrics_service = MetricsService(db)
        background_tasks.add_task(
            metrics_service.compute_health_index,
            current_user.id
        )
        
        return {
            "id": report.id,
            "status": report.status.value,
            "processed_at": report.processed_at.isoformat() if report.processed_at else None,
            "message": "Values confirmed. Health metrics recomputing in background."
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Confirmation failed: {str(e)}")


@router.delete("/{report_id}")
async def delete_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a report and its associated data
    
    This will also delete all observations extracted from this report
    """
    from sqlalchemy import select, delete
    from src.models import Observation
    import os
    
    # Fetch report
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.user_id == current_user.id)
    )
    report = result.scalars().first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    try:
        # Delete file from disk
        if report.file_path and os.path.exists(report.file_path):
            os.remove(report.file_path)
            logger.info(f"Deleted file: {report.file_path}")
        
        # Delete observations
        await db.execute(delete(Observation).where(Observation.report_id == report_id))
        
        # Delete report
        await db.delete(report)
        await db.commit()
        
        logger.info(f"Deleted report {report_id}")
    except Exception as e:
        logger.error(f"Error deleting report {report_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete report: {str(e)}")
    
    return {
        "success": True,
        "message": "Report deleted successfully"
    }


@router.post("/{report_id}/extract")
async def trigger_extraction(
    report_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger extraction for a report
    
    Useful if automatic extraction failed or needs to be retried
    """
    report_service = ReportService(db)
    
    # Verify report exists and belongs to user
    report = report_service.get_report_by_id(report_id, current_user.id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Trigger extraction in background
    background_tasks.add_task(
        report_service.extract_report_data,
        report.id,
        current_user.id
    )
    
    return {
        "id": report.id,
        "message": "Extraction started in background"
    }


@router.get("/{report_id}/debug")
async def get_report_debug(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get debug information for report extraction
    
    Returns:
        - status: current report status
        - method: extraction method used (text/ocr/hybrid/failed)
        - page_stats: per-page extraction statistics
        - text_preview: first 2500 chars of extracted text
        - extracted_metrics_count: number of metrics found
        - failure_reason: error message if failed
    """
    from sqlalchemy import select, func
    from src.models import Observation
    
    # Fetch report
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.user_id == current_user.id)
    )
    report = result.scalars().first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Count observations
    count_result = await db.execute(
        select(func.count(Observation.id)).where(Observation.report_id == report.id)
    )
    obs_count = count_result.scalar() or 0
    
    # Get text preview
    text_preview = ""
    if report.raw_text:
        text_preview = report.raw_text[:2500]
        if len(report.raw_text) > 2500:
            text_preview += "..."
    
    return {
        "report_id": str(report.id),
        "status": report.status.value,
        "extraction_method": report.extraction_method or "not_started",
        "page_stats": report.page_stats or [],
        "text_preview": text_preview,
        "text_length": len(report.raw_text) if report.raw_text else 0,
        "extracted_metrics_count": obs_count,
        "extraction_confidence": report.extraction_confidence,
        "failure_reason": report.error_message,
        "processed_at": report.processed_at.isoformat() if report.processed_at else None,
        "uploaded_at": report.uploaded_at.isoformat(),
    }
