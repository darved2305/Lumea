import os
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from app.db import get_db
from app.models import User, LoginEvent
from app.schemas import UserCreate, UserLogin, TokenResponse, UserResponse
from app.security import hash_password, verify_password, create_access_token, get_current_user
from app.core.audit import audit_logger, AuditAction
from app.core.rate_limit import rate_limit, record_auth_failure

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Security settings - read from environment with secure defaults
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() == "true"
COOKIE_SAMESITE = os.environ.get("COOKIE_SAMESITE", "strict")
TOKEN_MAX_AGE = int(os.environ.get("TOKEN_MAX_AGE_SECONDS", 3600))  # 1 hour default

@router.post("/signup", response_model=TokenResponse)
@router.post("/register", response_model=TokenResponse)
@rate_limit("signup")
async def signup(request: Request, user_data: UserCreate, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(
        full_name=user_data.full_name,
        email=user_data.email,
        password_hash=hash_password(user_data.password)
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    access_token = create_access_token({"sub": str(new_user.id)})
    
    # Set secure httpOnly cookie
    response.set_cookie(
        key="auth_token",
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=TOKEN_MAX_AGE
    )
    
    # Audit log the signup
    audit_logger.log(
        action=AuditAction.USER_CREATE,
        user_id=new_user.id,
        user_email=new_user.email,
        request=request,
        details={"method": "signup"}
    )
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(new_user)
    )

@router.post("/login", response_model=TokenResponse)
@rate_limit("login")
async def login(
    login_data: UserLogin,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(login_data.password, user.password_hash):
        # Record failed attempt for stricter rate limiting
        record_auth_failure(request)
        
        # Audit log failed login (don't include which part failed for security)
        audit_logger.log_auth_event(
            action=AuditAction.LOGIN_FAILURE,
            request=request,
            user_email=login_data.email,
            success=False,
            failure_reason="Invalid credentials"
        )
        
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    user.last_login_at = datetime.utcnow()
    
    login_event = LoginEvent(
        user_id=user.id,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(login_event)
    
    await db.commit()
    await db.refresh(user)
    
    access_token = create_access_token({"sub": str(user.id)})
    
    # Set secure httpOnly cookie
    response.set_cookie(
        key="auth_token",
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=TOKEN_MAX_AGE
    )
    
    # Audit log successful login
    audit_logger.log_auth_event(
        action=AuditAction.LOGIN_SUCCESS,
        request=request,
        user_id=user.id,
        user_email=user.email,
        success=True
    )
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )

@router.post("/logout")
async def logout(request: Request, response: Response, current_user: User = Depends(get_current_user)):
    response.delete_cookie(key="auth_token", secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE)
    
    # Audit log logout
    audit_logger.log_auth_event(
        action=AuditAction.LOGOUT,
        request=request,
        user_id=current_user.id,
        user_email=current_user.email,
        success=True
    )
    
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)
