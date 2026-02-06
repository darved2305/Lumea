"""
HIPAA Audit Logging Module

Provides comprehensive audit trail for PHI access and modifications.
Required by HIPAA §164.312(b) - Audit Controls.

Logs are structured for easy parsing and compliance reporting.
"""
import json
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any, Union
from uuid import UUID
from enum import Enum
from fastapi import Request
from pydantic import BaseModel


class AuditAction(str, Enum):
    """Types of auditable actions"""
    # Authentication
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILURE = "auth.login.failure"
    LOGOUT = "auth.logout"
    TOKEN_REFRESH = "auth.token.refresh"
    PASSWORD_CHANGE = "auth.password.change"
    
    # PHI Access
    PHI_VIEW = "phi.view"
    PHI_CREATE = "phi.create"
    PHI_UPDATE = "phi.update"
    PHI_DELETE = "phi.delete"
    PHI_EXPORT = "phi.export"
    PHI_PRINT = "phi.print"
    
    # Report Operations
    REPORT_UPLOAD = "report.upload"
    REPORT_VIEW = "report.view"
    REPORT_DELETE = "report.delete"
    REPORT_DOWNLOAD = "report.download"
    
    # Medical Data
    OBSERVATION_CREATE = "observation.create"
    OBSERVATION_UPDATE = "observation.update"
    OBSERVATION_DELETE = "observation.delete"
    OBSERVATION_VIEW = "observation.view"
    
    # Profile
    PROFILE_VIEW = "profile.view"
    PROFILE_UPDATE = "profile.update"
    
    # Administrative
    USER_CREATE = "admin.user.create"
    USER_UPDATE = "admin.user.update"
    USER_DELETE = "admin.user.delete"
    PERMISSION_CHANGE = "admin.permission.change"
    
    # System
    SYSTEM_ERROR = "system.error"
    SECURITY_ALERT = "security.alert"


class AuditLog(BaseModel):
    """Structured audit log entry"""
    timestamp: str
    action: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    success: bool = True
    details: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class AuditLogger:
    """
    HIPAA-compliant audit logger.
    
    Logs are written to:
    1. Structured JSON file for compliance reporting
    2. Standard Python logger for application monitoring
    
    In production, these should be forwarded to a SIEM or secure log storage.
    """
    
    def __init__(self, log_dir: str = "/app/logs/audit"):
        self.log_dir = log_dir
        self._ensure_log_dir()
        
        # Set up file logger for audit trail
        self._audit_logger = logging.getLogger("hipaa.audit")
        self._audit_logger.setLevel(logging.INFO)
        
        # Prevent duplicate handlers
        if not self._audit_logger.handlers:
            # JSON file handler for compliance
            audit_file = os.path.join(log_dir, "hipaa_audit.jsonl")
            file_handler = logging.FileHandler(audit_file)
            file_handler.setFormatter(logging.Formatter("%(message)s"))
            self._audit_logger.addHandler(file_handler)
            
            # Also log to console in structured format
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(
                logging.Formatter("[AUDIT] %(message)s")
            )
            self._audit_logger.addHandler(console_handler)
    
    def _ensure_log_dir(self):
        """Create log directory if it doesn't exist"""
        try:
            os.makedirs(self.log_dir, exist_ok=True)
        except Exception as e:
            logging.warning(f"Could not create audit log directory: {e}")
    
    def _serialize_id(self, value: Any) -> Optional[str]:
        """Convert UUID or other ID types to string"""
        if value is None:
            return None
        if isinstance(value, UUID):
            return str(value)
        return str(value)
    
    def _get_request_info(self, request: Optional[Request]) -> Dict[str, str]:
        """Extract request metadata"""
        if not request:
            return {}
        
        # Get real IP (handling proxies)
        ip = None
        if forwarded := request.headers.get("X-Forwarded-For"):
            ip = forwarded.split(",")[0].strip()
        elif real_ip := request.headers.get("X-Real-IP"):
            ip = real_ip
        elif request.client:
            ip = request.client.host
        
        return {
            "ip_address": ip,
            "user_agent": request.headers.get("User-Agent"),
            "request_id": request.headers.get("X-Request-ID"),
        }
    
    def log(
        self,
        action: Union[AuditAction, str],
        user_id: Optional[UUID] = None,
        user_email: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        request: Optional[Request] = None,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ):
        """
        Log an auditable action.
        
        Args:
            action: The action being performed (from AuditAction enum)
            user_id: ID of the user performing the action
            user_email: Email of the user (for easier log reading)
            resource_type: Type of resource being accessed (e.g., "report", "observation")
            resource_id: ID of the specific resource
            request: FastAPI Request object for IP/user agent extraction
            success: Whether the action succeeded
            details: Additional context (avoid logging PHI values!)
            error_message: Error message if action failed
        """
        request_info = self._get_request_info(request)
        
        log_entry = AuditLog(
            timestamp=datetime.utcnow().isoformat() + "Z",
            action=action.value if isinstance(action, AuditAction) else action,
            user_id=self._serialize_id(user_id),
            user_email=user_email,
            resource_type=resource_type,
            resource_id=self._serialize_id(resource_id),
            ip_address=request_info.get("ip_address"),
            user_agent=request_info.get("user_agent"),
            request_id=request_info.get("request_id"),
            success=success,
            details=details,
            error_message=error_message,
        )
        
        # Write structured JSON log
        self._audit_logger.info(log_entry.model_dump_json())
    
    def log_phi_access(
        self,
        action: AuditAction,
        user_id: UUID,
        resource_type: str,
        resource_id: UUID,
        request: Optional[Request] = None,
        fields_accessed: Optional[list] = None,
    ):
        """
        Log PHI access specifically (stricter logging).
        
        Args:
            action: PHI action (VIEW, CREATE, UPDATE, DELETE)
            user_id: User accessing the PHI
            resource_type: Type of PHI (observation, report, profile)
            resource_id: ID of the PHI record
            request: Request object
            fields_accessed: List of field names accessed (not values!)
        """
        self.log(
            action=action,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            request=request,
            details={"fields": fields_accessed} if fields_accessed else None,
        )
    
    def log_auth_event(
        self,
        action: AuditAction,
        request: Request,
        user_id: Optional[UUID] = None,
        user_email: Optional[str] = None,
        success: bool = True,
        failure_reason: Optional[str] = None,
    ):
        """Log authentication-related events"""
        self.log(
            action=action,
            user_id=user_id,
            user_email=user_email,
            request=request,
            success=success,
            error_message=failure_reason if not success else None,
            details={"auth_method": "jwt"},
        )
    
    def log_security_alert(
        self,
        alert_type: str,
        description: str,
        request: Optional[Request] = None,
        user_id: Optional[UUID] = None,
        severity: str = "medium",
    ):
        """Log security-related alerts"""
        self.log(
            action=AuditAction.SECURITY_ALERT,
            user_id=user_id,
            request=request,
            success=False,
            details={
                "alert_type": alert_type,
                "severity": severity,
            },
            error_message=description,
        )


# Global audit logger instance
audit_logger = AuditLogger()


# Convenience functions
def audit_phi_access(
    user_id: UUID,
    resource_type: str,
    resource_id: UUID,
    action: str = "view",
    request: Optional[Request] = None,
):
    """Quick function to log PHI access"""
    action_map = {
        "view": AuditAction.PHI_VIEW,
        "create": AuditAction.PHI_CREATE,
        "update": AuditAction.PHI_UPDATE,
        "delete": AuditAction.PHI_DELETE,
    }
    audit_logger.log_phi_access(
        action=action_map.get(action, AuditAction.PHI_VIEW),
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        request=request,
    )
