"""
Core Security Module

Provides HIPAA-compliant security features:
- PHI field-level encryption
- Rate limiting and brute-force protection
- Audit logging for compliance

Usage:
    from app.core.encryption import phi_cipher, EncryptedString
    from app.core.rate_limit import rate_limit, RateLimitMiddleware
    from app.core.audit import audit_logger, AuditAction
"""
from app.core.encryption import phi_cipher, EncryptedString, EncryptedText
from app.core.rate_limit import rate_limit, RateLimitMiddleware, record_auth_failure
from app.core.audit import audit_logger, AuditAction, audit_phi_access

__all__ = [
    # Encryption
    "phi_cipher",
    "EncryptedString",
    "EncryptedText",
    # Rate Limiting
    "rate_limit",
    "RateLimitMiddleware",
    "record_auth_failure",
    # Audit
    "audit_logger",
    "AuditAction",
    "audit_phi_access",
]
