from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    frontend_origin: str = "http://localhost:5173"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080

    # ChromaDB / RAG configuration
    CHROMA_PERSIST_DIR: str = "/app/chroma_db"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    RAG_TOP_K: int = 5

    # Local MedGemma configuration (Transformers, CPU in Docker)
    MEDGEMMA_MODEL_NAME: str = "google/medgemma-4b-it"
    MEDGEMMA_MAX_NEW_TOKENS: int = 256
    MEDGEMMA_TORCH_DTYPE: str = "auto"  # passed through to transformers
    MEDGEMMA_LOW_CPU_MEM: bool = True
    HF_TOKEN: Optional[str] = None
    HUGGINGFACE_HUB_TOKEN: Optional[str] = None

    # Ollama configuration (local)
    # Default to localhost for direct (non‑Docker) runs.
    # When running via Docker, docker-compose.yml normally overrides this to use
    # http://host.docker.internal:11434 so the container can reach the host.
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "hf.co/unsloth/medgemma-4b-it-GGUF:Q6_K_XL"
    OLLAMA_PULL_ON_START: bool = True
    OLLAMA_PULL_LOG_STEP_PCT: int = 5

    # Optional Gemini integration (other features can still use this)
    USE_GEMINI: bool = False
    GEMINI_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
