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
    
    # Grok/xAI API for LLM extraction fallback
    xai_api_key: Optional[str] = None
    xai_api_base: str = "https://api.x.ai/v1"
    grok_model: str = "grok-beta"
    
    # OpenAI API (alternative to Grok)
    openai_api_key: Optional[str] = None
    openai_api_base: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    class Config:
        env_file = ".env"

settings = Settings()
