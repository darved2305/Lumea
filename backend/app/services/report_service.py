"""
Report Service - Handle report upload, extraction, and processing
"""
import os
import uuid
import shutil
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Report, Observation, ReportStatus, ObservationType, User
from app.schemas import ExtractedValue, ReportConfirmRequest
from app.settings import settings


class ReportService:
    """Service for managing medical reports"""
    
    UPLOAD_DIR = Path("./uploads")
    ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    def __init__(self, db: Session):
        self.db = db
        self._ensure_upload_dir()
    
    def _ensure_upload_dir(self):
        """Create upload directory if it doesn't exist"""
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    def _get_user_upload_dir(self, user_id: uuid.UUID) -> Path:
        """Get user-specific upload directory"""
        user_dir = self.UPLOAD_DIR / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir
    
    def _validate_file(self, filename: str, file_size: int) -> None:
        """Validate file upload"""
        # Check extension
        ext = Path(filename).suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise ValueError(f"File type {ext} not allowed. Allowed: {self.ALLOWED_EXTENSIONS}")
        
        # Check size
        if file_size > self.MAX_FILE_SIZE:
            raise ValueError(f"File too large. Max size: {self.MAX_FILE_SIZE / 1024 / 1024}MB")
        
        # Prevent path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            raise ValueError("Invalid filename")
    
    async def upload_report(
        self,
        user_id: uuid.UUID,
        filename: str,
        file_content: bytes,
        report_date: Optional[datetime] = None
    ) -> Report:
        """
        Upload a new medical report
        
        Args:
            user_id: ID of the user uploading
            filename: Original filename
            file_content: File bytes
            report_date: Date on the report (if known)
        
        Returns:
            Created Report object
        """
        # Validate
        self._validate_file(filename, len(file_content))
        
        # Generate unique filename
        ext = Path(filename).suffix.lower()
        unique_filename = f"{uuid.uuid4()}{ext}"
        user_dir = self._get_user_upload_dir(user_id)
        file_path = user_dir / unique_filename
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Create database record
        report = Report(
            user_id=user_id,
            filename=filename,
            file_path=str(file_path),
            file_type=ext[1:],  # Remove dot
            file_size=len(file_content),
            status=ReportStatus.UPLOADED,
            report_date=report_date,
        )
        
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        
        return report
    
    async def extract_report_data(self, report_id: uuid.UUID, user_id: uuid.UUID) -> Report:
        """
        Extract data from report (OCR + parsing)
        
        MVP: Stub implementation that simulates extraction
        TODO: Integrate OCR service (Tesseract, Google Vision, AWS Textract)
        
        Args:
            report_id: Report ID
            user_id: User ID (for security)
        
        Returns:
            Updated Report
        """
        report = self.db.query(Report).filter(
            Report.id == report_id,
            Report.user_id == user_id
        ).first()
        
        if not report:
            raise ValueError("Report not found")
        
        # Update status
        report.status = ReportStatus.EXTRACTING
        self.db.commit()
        
        try:
            # TODO: Actual OCR implementation
            # For now, return stub data
            report.raw_text = "[OCR PLACEHOLDER] Sample lab report text..."
            report.extracted_data = {
                "detected_metrics": [
                    {
                        "metric_name": "glucose",
                        "value": 95.0,
                        "unit": "mg/dL",
                        "observation_type": "lab_value",
                        "confidence": 0.92
                    },
                    {
                        "metric_name": "systolic_bp",
                        "value": 120.0,
                        "unit": "mmHg",
                        "observation_type": "vital_sign",
                        "confidence": 0.88
                    },
                    {
                        "metric_name": "diastolic_bp",
                        "value": 80.0,
                        "unit": "mmHg",
                        "observation_type": "vital_sign",
                        "confidence": 0.88
                    }
                ]
            }
            report.extraction_confidence = 0.89
            report.status = ReportStatus.EXTRACTED
            
        except Exception as e:
            report.status = ReportStatus.FAILED
            report.error_message = str(e)
        
        self.db.commit()
        self.db.refresh(report)
        return report
    
    async def confirm_extracted_values(
        self,
        report_id: uuid.UUID,
        user_id: uuid.UUID,
        confirmation: ReportConfirmRequest
    ) -> Report:
        """
        User confirms or corrects extracted values
        
        Args:
            report_id: Report ID
            user_id: User ID
            confirmation: Confirmed/corrected values
        
        Returns:
            Updated Report with created Observations
        """
        report = self.db.query(Report).filter(
            Report.id == report_id,
            Report.user_id == user_id
        ).first()
        
        if not report:
            raise ValueError("Report not found")
        
        if report.status not in [ReportStatus.EXTRACTED, ReportStatus.PROCESSED]:
            raise ValueError(f"Cannot confirm report in status {report.status}")
        
        # Update status
        report.status = ReportStatus.PROCESSING
        self.db.commit()
        
        try:
            # Create observations from confirmed values
            observations_created = []
            
            for val in confirmation.values:
                # Determine reference ranges
                ref_min, ref_max, is_abnormal = self._get_reference_range(
                    val.metric_name, val.value
                )
                
                obs = Observation(
                    user_id=user_id,
                    report_id=report_id,
                    observation_type=val.observation_type,
                    metric_name=val.metric_name,
                    value=val.value,
                    unit=val.unit,
                    observed_at=val.observed_at,
                    reference_min=ref_min,
                    reference_max=ref_max,
                    is_abnormal=is_abnormal,
                    notes=confirmation.notes
                )
                self.db.add(obs)
                observations_created.append(obs)
            
            report.status = ReportStatus.CONFIRMED
            report.processed_at = datetime.utcnow()
            
            self.db.commit()
            
            for obs in observations_created:
                self.db.refresh(obs)
            
            self.db.refresh(report)
            
        except Exception as e:
            report.status = ReportStatus.FAILED
            report.error_message = str(e)
            self.db.commit()
            raise
        
        return report
    
    def _get_reference_range(
        self, metric_name: str, value: float
    ) -> tuple[Optional[float], Optional[float], bool]:
        """
        Get reference ranges for a metric and determine if abnormal
        
        Returns: (min, max, is_abnormal)
        """
        # Standard reference ranges (simplified)
        ranges = {
            "glucose": (70, 100),  # mg/dL fasting
            "systolic_bp": (90, 120),  # mmHg
            "diastolic_bp": (60, 80),  # mmHg
            "heart_rate": (60, 100),  # bpm
            "temperature": (36.1, 37.2),  # Celsius
            "weight": (None, None),  # kg - no standard range
            "bmi": (18.5, 24.9),
        }
        
        if metric_name not in ranges:
            return None, None, False
        
        ref_min, ref_max = ranges[metric_name]
        
        if ref_min is None or ref_max is None:
            return ref_min, ref_max, False
        
        is_abnormal = value < ref_min or value > ref_max
        return ref_min, ref_max, is_abnormal
    
    def get_user_reports(
        self,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[Report]:
        """Get all reports for a user"""
        reports = (
            self.db.query(Report)
            .filter(Report.user_id == user_id)
            .order_by(Report.uploaded_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )
        return reports
    
    def get_report_by_id(
        self, report_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Report]:
        """Get specific report (with user_id check for security)"""
        return self.db.query(Report).filter(
            Report.id == report_id,
            Report.user_id == user_id
        ).first()
    
    def get_report_observation_count(
        self, report_id: uuid.UUID
    ) -> int:
        """Count observations linked to a report"""
        return self.db.query(func.count(Observation.id)).filter(
            Observation.report_id == report_id
        ).scalar() or 0
    
    def delete_report(
        self, report_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """
        Delete a report and its file
        
        Returns: True if deleted, False if not found
        """
        report = self.get_report_by_id(report_id, user_id)
        if not report:
            return False
        
        # Delete file
        try:
            if os.path.exists(report.file_path):
                os.remove(report.file_path)
        except Exception as e:
            print(f"Error deleting file: {e}")
        
        # Delete database record (cascades to observations)
        self.db.delete(report)
        self.db.commit()
        
        return True
