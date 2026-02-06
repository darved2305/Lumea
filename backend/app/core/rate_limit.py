"""
Rate Limiting Module

Provides protection against brute-force attacks and API abuse.
Critical for HIPAA security (preventing unauthorized access attempts).

Uses in-memory storage by default. For production, configure Redis backend.
"""
import time
import logging
from typing import Callable, Optional, Dict, Tuple
from collections import defaultdict
from functools import wraps
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimitExceeded(HTTPException):
    """Raised when rate limit is exceeded"""
    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)}
        )


class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter using sliding window algorithm.
    
    For production with multiple workers, use Redis-based implementation.
    """
    
    def __init__(self):
        # Structure: {key: [(timestamp, count), ...]}
        self._requests: Dict[str, list] = defaultdict(list)
        self._cleanup_interval = 60  # Cleanup old entries every 60 seconds
        self._last_cleanup = time.time()
    
    def _cleanup(self):
        """Remove expired entries to prevent memory growth"""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        cutoff = now - 3600  # Keep last hour of data
        for key in list(self._requests.keys()):
            self._requests[key] = [
                (ts, count) for ts, count in self._requests[key]
                if ts > cutoff
            ]
            if not self._requests[key]:
                del self._requests[key]
        
        self._last_cleanup = now
    
    def is_allowed(self, key: str, limit: int, window_seconds: int) -> Tuple[bool, int]:
        """
        Check if request is allowed under rate limit.
        
        Args:
            key: Unique identifier (IP, user ID, etc.)
            limit: Maximum requests allowed
            window_seconds: Time window in seconds
        
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        self._cleanup()
        
        now = time.time()
        window_start = now - window_seconds
        
        # Count requests in current window
        entries = self._requests[key]
        current_count = sum(
            count for ts, count in entries
            if ts > window_start
        )
        
        if current_count >= limit:
            # Calculate when the oldest request in window expires
            oldest_in_window = min(
                (ts for ts, _ in entries if ts > window_start),
                default=now
            )
            retry_after = int(oldest_in_window + window_seconds - now) + 1
            return False, max(1, retry_after)
        
        # Record this request
        entries.append((now, 1))
        return True, 0
    
    def record_failure(self, key: str):
        """Record a failed attempt (e.g., wrong password) for stricter limiting"""
        now = time.time()
        # Failed attempts count double
        self._requests[key].append((now, 2))


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter()


# Rate limit configurations for different endpoints
RATE_LIMITS = {
    # Auth endpoints - strict limits to prevent brute force
    "login": (5, 60),       # 5 attempts per minute
    "signup": (3, 60),      # 3 signups per minute per IP
    "password_reset": (3, 300),  # 3 reset requests per 5 minutes
    
    # API endpoints - moderate limits
    "api_default": (100, 60),    # 100 requests per minute
    "upload": (10, 60),          # 10 uploads per minute
    "ai_summary": (20, 60),      # 20 AI requests per minute
    
    # Sensitive data endpoints - stricter
    "phi_access": (50, 60),      # 50 PHI accesses per minute
}


def get_client_ip(request: Request) -> str:
    """Extract real client IP, handling proxies"""
    # Check X-Forwarded-For header (set by reverse proxies)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP (original client)
        return forwarded.split(",")[0].strip()
    
    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct connection IP
    if request.client:
        return request.client.host
    
    return "unknown"


def rate_limit(limit_type: str = "api_default"):
    """
    Decorator to apply rate limiting to a route.
    
    Usage:
        @router.post("/login")
        @rate_limit("login")
        async def login(request: Request, ...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find request in args/kwargs
            request = kwargs.get("request")
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if request:
                client_ip = get_client_ip(request)
                limit, window = RATE_LIMITS.get(limit_type, RATE_LIMITS["api_default"])
                key = f"{limit_type}:{client_ip}"
                
                allowed, retry_after = rate_limiter.is_allowed(key, limit, window)
                if not allowed:
                    logger.warning(
                        f"Rate limit exceeded for {limit_type} from {client_ip}"
                    )
                    raise RateLimitExceeded(retry_after)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def record_auth_failure(request: Request):
    """
    Record a failed authentication attempt.
    Call this after failed login to increase rate limit strictness.
    """
    client_ip = get_client_ip(request)
    key = f"login:{client_ip}"
    rate_limiter.record_failure(key)
    logger.info(f"Recorded auth failure from {client_ip}")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Global rate limiting middleware.
    
    Applies default rate limits to all requests and stricter limits
    to sensitive endpoints.
    """
    
    # Paths that get stricter rate limits
    SENSITIVE_PATHS = {
        "/api/auth/login": "login",
        "/api/auth/signup": "signup",
        "/api/auth/register": "signup",
        "/api/reports/upload": "upload",
        "/api/documents/upload": "upload",
        "/api/ai/": "ai_summary",
    }
    
    async def dispatch(self, request: Request, call_next):
        client_ip = get_client_ip(request)
        path = request.url.path
        
        # Determine rate limit type based on path
        limit_type = "api_default"
        for pattern, lt in self.SENSITIVE_PATHS.items():
            if path.startswith(pattern) or path == pattern:
                limit_type = lt
                break
        
        limit, window = RATE_LIMITS.get(limit_type, RATE_LIMITS["api_default"])
        key = f"{limit_type}:{client_ip}"
        
        allowed, retry_after = rate_limiter.is_allowed(key, limit, window)
        
        if not allowed:
            logger.warning(
                f"Rate limit exceeded: {limit_type} from {client_ip} on {path}"
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Rate limit exceeded. Try again in {retry_after} seconds."
                },
                headers={"Retry-After": str(retry_after)}
            )
        
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - 1))
        
        return response
