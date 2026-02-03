import bcrypt
import logging
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional
from uuid import UUID
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.settings import settings

if TYPE_CHECKING:
    from app.models import User

logger = logging.getLogger(__name__)

# HTTPBearer security scheme - auto_error=False to handle missing tokens gracefully
security = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> "User":
    """
    Dependency to get the current authenticated user from JWT token.
    
    Supports both:
    - Authorization: Bearer <token> header
    - auth_token cookie (for browser sessions)
    
    Gets its own database session internally to avoid circular import issues.
    """
    from app.models import User
    
    # Try to get token from multiple sources
    token = None
    
    # 1. Try Bearer token from Authorization header
    if credentials and credentials.credentials:
        token = credentials.credentials
        logger.debug(f"Auth: Got Bearer token from header")
    
    # 2. Fall back to cookie
    if not token:
        token = request.cookies.get("auth_token")
        if token:
            logger.debug(f"Auth: Got token from cookie")
    
    # 3. Try raw Authorization header (some clients may not use HTTPBearer format)
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            logger.debug(f"Auth: Got token from raw Authorization header")
    
    if not token:
        logger.warning("Auth: No token found in request")
        raise HTTPException(status_code=401, detail="Not authenticated - no token provided")
    
    # Decode token
    payload = decode_access_token(token)
    if not payload:
        logger.warning("Auth: Invalid or expired token")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = payload.get("sub")
    if not user_id:
        logger.warning("Auth: Token missing 'sub' claim")
        raise HTTPException(status_code=401, detail="Invalid token payload")

    try:
        user_uuid = UUID(str(user_id))
    except Exception:
        logger.warning("Auth: Token 'sub' is not a valid UUID")
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    # Get database session and fetch user - use context manager to ensure cleanup
    from app.db import async_session_maker
    
    async with async_session_maker() as db:
        try:
            result = await db.execute(select(User).where(User.id == user_uuid))
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"Auth: User {user_id} not found in database")
                raise HTTPException(status_code=401, detail="User not found")
            
            logger.debug(f"Auth: Authenticated user {user.email}")
            return user
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Auth: Database error - {e}")
            raise HTTPException(status_code=500, detail="Database error during authentication")
