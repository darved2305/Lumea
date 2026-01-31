from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    frontend_origin: str = "http://localhost:5173"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080
    
    # Optional Gemini integration for rewording recommendations
    USE_GEMINI: bool = False
    GEMINI_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"

settings = Settings()
