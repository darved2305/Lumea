from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.settings import settings
from app.db import init_db
from app.routes import auth, health, dashboard, reports, assistant, recommendations
from app.routes.websocket import router as websocket_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
    except Exception as e:
        print(f"DB init warning: {e}")
    yield

app = FastAPI(title="Co-Code GGW Health Platform API", lifespan=lifespan)

# CORS configuration - allow both localhost ports
origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
    "http://127.0.0.1:5176",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(health.router)
app.include_router(dashboard.router)
app.include_router(reports.router)
app.include_router(assistant.router)
app.include_router(recommendations.router)
app.include_router(websocket_router)

@app.get("/")
async def root():
    return {
        "message": "Co-Code GGW Health Platform API",
        "version": "2.0",
        "endpoints": {
            "auth": "/api/auth",
            "dashboard": "/api/dashboard",
            "reports": "/api/reports",
            "assistant": "/api/assistant",
            "recommendations": "/api/recommendations",
            "websocket": "ws://localhost:8000/ws?token=<jwt>"
        }
    }
