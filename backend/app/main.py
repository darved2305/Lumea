from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os
from app.settings import settings
from app.db import init_db, engine
from app.services.graph_service import get_graph_service
from app.services.reminder_scheduler import start_reminder_scheduler, stop_reminder_scheduler
from app.routes import auth, health, dashboard, reports, assistant, recommendations
from app.routes.profile import router as profile_router
from app.routes.profile_me import router as profile_me_router
from app.routes.websocket import router as websocket_router
from app.routes.documents import router as documents_router
from app.routes.ai_summary import router as ai_summary_router
from app.routes.medicines import router as medicines_router
from app.routes.voice import router as voice_router
from app.core.rate_limit import RateLimitMiddleware

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Database
    try:
        logger.info("Initializing database...")
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"DB init failed (continuing anyway): {e}")

    # Initialize Knowledge Graph (non-blocking)
    try:
        logger.info("Initializing graph service...")
        await get_graph_service().initialize()
        logger.info("Graph service initialized")
    except Exception as e:
        logger.warning(f"Graph service init skipped: {e}")

    # Start Reminder Scheduler
    try:
        logger.info("Starting reminder scheduler...")
        start_reminder_scheduler()
        logger.info("Reminder scheduler started")
    except Exception as e:
        logger.warning(f"Reminder scheduler start failed: {e}")

    logger.info("Application startup complete")
    yield

    # Best-effort shutdown cleanup
    try:
        stop_reminder_scheduler()
    except Exception as e:
        logger.debug(f"Reminder scheduler stop: {e}")

    try:
        await get_graph_service().close()
    except Exception as e:
        logger.debug(f"Graph service close: {e}")

    try:
        await engine.dispose()
    except Exception as e:
        logger.debug(f"DB engine dispose: {e}")

app = FastAPI(title="Lumea Health Platform API", lifespan=lifespan)

# CORS configuration - allow both localhost ports and Docker
origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
    "http://127.0.0.1:5176",
    "http://frontend:5173",  # Docker service name
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin"],
    expose_headers=["Content-Type", "Authorization", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
    max_age=3600,
)

# Rate limiting middleware - protects against brute force and abuse
# Must be added after CORS middleware
app.add_middleware(RateLimitMiddleware)

# Include routers
app.include_router(auth.router)
app.include_router(health.router)
app.include_router(dashboard.router)
app.include_router(reports.router)
app.include_router(assistant.router)
app.include_router(recommendations.router)
app.include_router(profile_router)
app.include_router(profile_me_router)  # Profile /me and reminders endpoints
app.include_router(websocket_router)
app.include_router(documents_router)
app.include_router(ai_summary_router)
app.include_router(medicines_router)
app.include_router(voice_router)

@app.get("/")
async def root():
    return {
        "message": "Lumea Health Platform API",
        "version": "2.0",
        "endpoints": {
            "auth": "/api/auth",
            "dashboard": "/api/dashboard",
            "reports": "/api/reports",
            "documents": "/api/documents",
            "assistant": "/api/assistant",
            "recommendations": "/api/recommendations",
            "medicines": "/api/medicines",
            "profile": "/api/profile",
            "profile_me": "/api/profile/me",
            "reminders": "/api/reminders",
            "sms": "/api/sms",
            "ai_summary": "/api/ai",
            "websocket": "ws://localhost:8000/ws?token=<jwt>"
        }
    }
