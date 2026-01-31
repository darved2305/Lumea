"""
Manual report processor - run this to process stuck reports
"""
import asyncio
from app.db import async_session_maker
from app.services.enhanced_report_service import EnhancedReportService
from sqlalchemy import select
from app.models import Report, ReportStatus
from uuid import UUID

async def process_stuck_reports():
    async with async_session_maker() as db:
        # Find reports that are stuck in UPLOADED status
        result = await db.execute(
            select(Report).where(Report.status == ReportStatus.UPLOADED)
        )
        stuck_reports = result.scalars().all()
        
        print(f"Found {len(stuck_reports)} stuck reports")
        
        for report in stuck_reports:
            print(f"\nProcessing report {report.id}: {report.filename}")
            print(f"  User: {report.user_id}")
            print(f"  File: {report.file_path}")
            
            service = EnhancedReportService(db)
            try:
                await service.process_report(report.id, report.user_id)
                print(f"  ✅ Processing complete")
            except Exception as e:
                print(f"  ❌ Processing failed: {e}")

if __name__ == "__main__":
    asyncio.run(process_stuck_reports())
