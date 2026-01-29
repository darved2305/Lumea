from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.settings import settings
from app.db import init_db
from app.routes import auth

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="Co-Code GGW Auth API", lifespan=lifespan)

# CORS configuration to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)

@app.get("/")
async def root():
    return {"message": "Co-Code GGW Auth API"}
