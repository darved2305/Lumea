from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.settings import settings
from app.db import init_db
from app.routes import auth
from app.routes import health

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
    except Exception as e:
        print(f"DB init warning: {e}")
    yield

app = FastAPI(title="Co-Code GGW Auth API", lifespan=lifespan)

# CORS configuration - allow both localhost ports
origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(auth.router)
app.include_router(health.router)

@app.get("/")
async def root():
    return {"message": "Co-Code GGW Auth API"}
