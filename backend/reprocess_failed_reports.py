"""
Reprocess failed reports after fixing PDF extraction dependencies
"""
import asyncio
from app.db import async_session_maker
from app.models import Report, ReportStatus
from app.services.enhanced_report_service import EnhancedReportService
from sqlalchemy import select

async def reprocess_failed_reports():
    """Find all failed reports and reprocess them"""
    async with async_session_maker() as db:
        # Find all failed reports
        result = await db.execute(
            select(Report).where(Report.status == ReportStatus.FAILED)
        )
        failed_reports = result.scalars().all()
        
        print(f"Found {len(failed_reports)} failed reports")
        
        for report in failed_reports:
            print(f"\nReprocessing: {report.filename} (ID: {report.id})")
            print(f"  User: {report.user_id}")
            print(f"  Error was: {report.error_message}")
            
            # Reset status to uploaded
            report.status = ReportStatus.UPLOADED
            report.error_message = None
            await db.commit()
            
            # Create new service instance with this session
            service = EnhancedReportService(db)
            
            try:
                await service.process_report(report.id, report.user_id)
                print(f"  ✓ Successfully reprocessed")
            except Exception as e:
                print(f"  ✗ Failed again: {e}")

if __name__ == "__main__":
    asyncio.run(reprocess_failed_reports())
