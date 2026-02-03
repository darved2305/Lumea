"""
AI Summary API Endpoints

Provides endpoints for generating AI summaries and comparisons of medical reports.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID
import logging

from app.db import get_db
from app.security import get_current_user
from app.models import User, Report
from app.schemas import (
    GenerateSummaryRequest,
    GenerateCompareRequest,
    SummaryResponse,
    ComparisonResponse,
    ReportForSummary
)
from app.services.ai_summary_service import AISummaryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai-summary"])


@router.get("/reports-for-summary", response_model=List[ReportForSummary])
async def list_reports_for_summary(
    category: str = None,
    doc_type: str = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List user's reports with metadata for the AI Summary page.
    
    Returns reports with preview URLs and type information for selection UI.
    """
    query = select(Report).where(Report.user_id == current_user.id)
    
    if category:
        query = query.where(Report.category == category)
    if doc_type:
        query = query.where(Report.doc_type == doc_type)
    
    query = query.order_by(Report.uploaded_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    reports = result.scalars().all()
    
    response = []
    for report in reports:
        # Build preview URL based on file path
        preview_url = f"/api/reports/{report.id}/file"
        
        response.append(ReportForSummary(
            id=report.id,
            filename=report.filename,
            category=report.category,
            doc_type=report.doc_type,
            report_date=report.report_date,
            uploaded_at=report.uploaded_at,
            file_path=report.file_path,
            file_type=report.file_type,
            preview_url=preview_url
        ))
    
    return response


@router.get("/reports/{report_id}/file")
async def get_report_file(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the actual file for a report (for preview/viewing).
    """
    from fastapi.responses import FileResponse
    import os
    
    result = await db.execute(
        select(Report).where(
            Report.id == report_id,
            Report.user_id == current_user.id
        )
    )
    report = result.scalars().first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if not os.path.exists(report.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    # Determine media type
    media_types = {
        '.pdf': 'application/pdf',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.tiff': 'image/tiff'
    }
    media_type = media_types.get(report.file_type, 'application/octet-stream')
    
    return FileResponse(
        report.file_path,
        media_type=media_type,
        filename=report.filename
    )


@router.post("/report-summary", response_model=SummaryResponse)
async def generate_report_summary(
    request: GenerateSummaryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate AI summary for a single report.
    
    Uses cached summary if available and source hasn't changed.
    Set force_regenerate=true to bypass cache.
    """
    service = AISummaryService(db)
    
    try:
        result = await service.generate_summary(
            report_id=request.report_id,
            user_id=current_user.id,
            force_regenerate=request.force_regenerate
        )
        return SummaryResponse(
            summary_json=result["summary_json"],
            cached=result["cached"],
            generated_at=result["generated_at"],
            model_name=result["model_name"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error generating summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")


@router.post("/report-compare", response_model=ComparisonResponse)
async def compare_reports(
    request: GenerateCompareRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate AI comparison for multiple reports of the same type.
    
    Requirements:
    - 2-6 reports
    - All reports must be of the same category/type
    - All reports must have extracted text
    
    Uses cached comparison if available and sources haven't changed.
    Set force_regenerate=true to bypass cache.
    """
    service = AISummaryService(db)
    
    try:
        result = await service.generate_comparison(
            report_ids=request.report_ids,
            user_id=current_user.id,
            force_regenerate=request.force_regenerate
        )
        return ComparisonResponse(
            comparison_json=result["comparison_json"],
            cached=result["cached"],
            generated_at=result["generated_at"],
            model_name=result["model_name"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error generating comparison: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate comparison: {str(e)}")


@router.post("/validate-comparison")
async def validate_comparison_selection(
    report_ids: List[UUID],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Validate whether selected reports can be compared.
    
    Returns validation result with any issues found.
    """
    if len(report_ids) < 2:
        return {
            "valid": False,
            "error": "Select at least 2 reports to compare",
            "report_ids": report_ids
        }
    
    if len(report_ids) > 6:
        return {
            "valid": False,
            "error": "Maximum 6 reports allowed for comparison",
            "report_ids": report_ids
        }
    
    # Fetch reports
    result = await db.execute(
        select(Report).where(
            Report.id.in_(report_ids),
            Report.user_id == current_user.id
        )
    )
    reports = list(result.scalars().all())
    
    if len(reports) != len(report_ids):
        return {
            "valid": False,
            "error": "One or more reports not found",
            "report_ids": report_ids
        }
    
    # Check for extracted text
    missing_text = [r.filename for r in reports if not r.raw_text]
    if missing_text:
        return {
            "valid": False,
            "error": f"Reports missing extracted text: {', '.join(missing_text)}",
            "report_ids": report_ids
        }
    
    # Check same type
    categories = set(r.category for r in reports if r.category)
    doc_types = set(r.doc_type for r in reports if r.doc_type)
    
    if len(categories) > 1 and len(doc_types) > 1:
        return {
            "valid": False,
            "error": "Please select reports of the same type for comparison",
            "categories": list(categories),
            "doc_types": list(doc_types),
            "report_ids": report_ids
        }
    
    return {
        "valid": True,
        "category": list(categories)[0] if categories else None,
        "doc_type": list(doc_types)[0] if doc_types else None,
        "report_count": len(reports),
        "report_ids": report_ids
    }


@router.get("/categories")
async def get_report_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get distinct categories and doc_types from user's reports.
    
    Useful for populating filter dropdowns.
    """
    from sqlalchemy import distinct, func
    
    # Get categories with counts
    cat_result = await db.execute(
        select(Report.category, func.count(Report.id))
        .where(Report.user_id == current_user.id)
        .where(Report.category.isnot(None))
        .group_by(Report.category)
    )
    categories = [{"name": row[0], "count": row[1]} for row in cat_result.all()]
    
    # Get doc_types with counts
    type_result = await db.execute(
        select(Report.doc_type, func.count(Report.id))
        .where(Report.user_id == current_user.id)
        .where(Report.doc_type.isnot(None))
        .group_by(Report.doc_type)
    )
    doc_types = [{"name": row[0], "count": row[1]} for row in type_result.all()]
    
    return {
        "categories": categories,
        "doc_types": doc_types
    }
