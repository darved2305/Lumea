from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from app.settings import settings
from app.db import init_db, engine
from app.services.graph_service import get_graph_service
from app.routes import auth, health, dashboard, reports, assistant, recommendations
from app.routes.profile import router as profile_router
from app.routes.websocket import router as websocket_router
from app.routes.documents import router as documents_router
from app.routes.ai_summary import router as ai_summary_router

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Database
    try:
        await init_db()
    except Exception as e:
        logger.debug(f"DB init (non-critical): {e}")

    # Initialize Knowledge Graph
    try:
        await get_graph_service().initialize()
    except Exception as e:
        logger.debug(f"Graph service init (non-critical): {e}")

    yield

    # Best-effort shutdown cleanup
    try:
        await get_graph_service().close()
    except Exception as e:
        logger.debug(f"Graph service close (non-critical): {e}")

    try:
        await engine.dispose()
    except Exception as e:
        logger.debug(f"DB engine dispose (non-critical): {e}")

app = FastAPI(title="Co-Code GGW Health Platform API", lifespan=lifespan)

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
    expose_headers=["Content-Type", "Authorization"],
    max_age=3600,
)

# Include routers
app.include_router(auth.router)
app.include_router(health.router)
app.include_router(dashboard.router)
app.include_router(reports.router)
app.include_router(assistant.router)
app.include_router(recommendations.router)
app.include_router(profile_router)
app.include_router(websocket_router)
app.include_router(documents_router)
app.include_router(ai_summary_router)

@app.get("/")
async def root():
    return {
        "message": "Co-Code GGW Health Platform API",
        "version": "2.0",
        "endpoints": {
            "auth": "/api/auth",
            "dashboard": "/api/dashboard",
            "reports": "/api/reports",
            "documents": "/api/documents",
            "assistant": "/api/assistant",
            "recommendations": "/api/recommendations",
            "profile": "/api/profile",
            "ai_summary": "/api/ai",
            "websocket": "ws://localhost:8000/ws?token=<jwt>"
        }
    }
