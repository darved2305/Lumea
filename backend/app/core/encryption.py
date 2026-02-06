"""
PHI (Protected Health Information) Encryption Module

Provides field-level encryption for sensitive medical data to comply with
HIPAA §164.312(a)(2)(iv) - Encryption and Decryption.

Usage:
    from app.core.encryption import phi_cipher
    
    encrypted = phi_cipher.encrypt("patient SSN")
    decrypted = phi_cipher.decrypt(encrypted)
"""
import os
import base64
import hashlib
import logging
from typing import Optional, Union
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class PHIEncryptionError(Exception):
    """Raised when encryption/decryption fails"""
    pass


class PHIEncryption:
    """
    Field-level encryption for Protected Health Information (PHI).
    
    Uses Fernet symmetric encryption (AES-128-CBC with HMAC-SHA256).
    Key is derived from PHI_ENCRYPTION_KEY environment variable using PBKDF2.
    
    Attributes:
        ENCRYPTED_PREFIX: Marker to identify encrypted values in database
    """
    
    ENCRYPTED_PREFIX = "ENC::"
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize the encryption cipher.
        
        Args:
            encryption_key: Base encryption key. If not provided, reads from
                          PHI_ENCRYPTION_KEY environment variable.
        
        Raises:
            PHIEncryptionError: If no encryption key is configured
        """
        key = encryption_key or os.environ.get("PHI_ENCRYPTION_KEY")
        
        if not key:
            logger.warning(
                "PHI_ENCRYPTION_KEY not set. PHI encryption is DISABLED. "
                "Set this environment variable for HIPAA compliance."
            )
            self._cipher = None
            return
        
        # Derive a proper Fernet key from the provided key using PBKDF2
        # Salt is static per deployment - stored in env or derived from key
        salt = os.environ.get("PHI_ENCRYPTION_SALT", "lumea-health-phi-salt").encode()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,  # OWASP recommended minimum for PBKDF2-SHA256
        )
        
        derived_key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
        self._cipher = Fernet(derived_key)
        logger.info("PHI encryption initialized successfully")
    
    @property
    def is_enabled(self) -> bool:
        """Check if encryption is properly configured"""
        return self._cipher is not None
    
    def encrypt(self, plaintext: Union[str, None]) -> Optional[str]:
        """
        Encrypt a plaintext value.
        
        Args:
            plaintext: The value to encrypt. None values are passed through.
        
        Returns:
            Encrypted string with ENCRYPTED_PREFIX, or None if input is None.
            If encryption is disabled, returns the original value.
        
        Raises:
            PHIEncryptionError: If encryption fails
        """
        if plaintext is None:
            return None
        
        if not self._cipher:
            logger.debug("Encryption disabled, returning plaintext")
            return plaintext
        
        # Already encrypted? Return as-is
        if isinstance(plaintext, str) and plaintext.startswith(self.ENCRYPTED_PREFIX):
            return plaintext
        
        try:
            encrypted_bytes = self._cipher.encrypt(str(plaintext).encode('utf-8'))
            return f"{self.ENCRYPTED_PREFIX}{encrypted_bytes.decode('utf-8')}"
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise PHIEncryptionError(f"Failed to encrypt value: {e}")
    
    def decrypt(self, ciphertext: Union[str, None]) -> Optional[str]:
        """
        Decrypt an encrypted value.
        
        Args:
            ciphertext: The encrypted value (with ENCRYPTED_PREFIX).
        
        Returns:
            Decrypted plaintext, or None if input is None.
            If value is not encrypted (no prefix), returns as-is.
        
        Raises:
            PHIEncryptionError: If decryption fails (wrong key, corrupted data)
        """
        if ciphertext is None:
            return None
        
        if not self._cipher:
            return ciphertext
        
        # Not encrypted? Return as-is (for migration compatibility)
        if not ciphertext.startswith(self.ENCRYPTED_PREFIX):
            return ciphertext
        
        try:
            encrypted_data = ciphertext[len(self.ENCRYPTED_PREFIX):]
            decrypted_bytes = self._cipher.decrypt(encrypted_data.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except InvalidToken:
            logger.error("Decryption failed: Invalid token (wrong key or corrupted data)")
            raise PHIEncryptionError("Failed to decrypt: invalid key or corrupted data")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise PHIEncryptionError(f"Failed to decrypt value: {e}")
    
    def hash_for_search(self, value: str) -> str:
        """
        Create a searchable hash of a value.
        
        Use this for fields that need to be searchable (e.g., email lookup)
        while still protecting the actual value.
        
        Args:
            value: The value to hash
        
        Returns:
            SHA-256 hash of the value (hex encoded)
        """
        salt = os.environ.get("PHI_ENCRYPTION_SALT", "lumea-health-phi-salt")
        salted = f"{salt}:{value}"
        return hashlib.sha256(salted.encode()).hexdigest()
    
    def rotate_key(self, old_key: str, new_key: str, ciphertext: str) -> str:
        """
        Re-encrypt data with a new key (for key rotation).
        
        Args:
            old_key: The current encryption key
            new_key: The new encryption key
            ciphertext: The encrypted value
        
        Returns:
            Value encrypted with the new key
        """
        # Decrypt with old key
        old_cipher = PHIEncryption(old_key)
        plaintext = old_cipher.decrypt(ciphertext)
        
        # Encrypt with new key
        new_cipher = PHIEncryption(new_key)
        return new_cipher.encrypt(plaintext)


# Global singleton instance
phi_cipher = PHIEncryption()


# SQLAlchemy TypeDecorator for automatic encryption
from sqlalchemy import TypeDecorator, String


class EncryptedString(TypeDecorator):
    """
    SQLAlchemy column type that automatically encrypts/decrypts values.
    
    Usage:
        class Patient(Base):
            ssn = Column(EncryptedString(255), nullable=True)
            full_name = Column(EncryptedString(500), nullable=False)
    """
    
    impl = String
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        """Encrypt value before storing in database"""
        if value is not None:
            return phi_cipher.encrypt(value)
        return value
    
    def process_result_value(self, value, dialect):
        """Decrypt value when reading from database"""
        if value is not None:
            return phi_cipher.decrypt(value)
        return value


class EncryptedText(TypeDecorator):
    """
    SQLAlchemy column type for encrypted TEXT fields (longer values).
    """
    
    from sqlalchemy import Text
    impl = Text
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        if value is not None:
            return phi_cipher.encrypt(value)
        return value
    
    def process_result_value(self, value, dialect):
        if value is not None:
            return phi_cipher.decrypt(value)
        return value
