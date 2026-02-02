from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    frontend_origin: str = "http://localhost:5173"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080
    
    # Ollama LLM Configuration
    OLLAMA_BASE_URL: str = "http://ollama:11434"  # Docker service name
    OLLAMA_MODEL: str = "medgemma:4b"
    OLLAMA_TIMEOUT: int = 120  # seconds
    
    # ChromaDB Configuration
    CHROMA_PERSIST_DIR: str = "/app/chroma_db"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    RAG_TOP_K: int = 5
    
    # Gemini Fallback (optional)
    USE_GEMINI_FALLBACK: bool = True
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
