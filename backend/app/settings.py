from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    frontend_origin: str = "http://localhost:5173"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080
    
    # Ollama LLM Configuration
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"  # Host machine via Docker
    OLLAMA_MODEL: str = "hf.co/unsloth/medgemma-4b-it-GGUF:Q6_K_XL"
    OLLAMA_TIMEOUT: int = 120  # seconds
    
    # ChromaDB Configuration
    CHROMA_PERSIST_DIR: str = "/app/chroma_db"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    RAG_TOP_K: int = 5
    
    # Gemini Fallback (optional)
    USE_GEMINI_FALLBACK: bool = True
    USE_GEMINI: bool = True # Alias for compatibility
    GEMINI_API_KEY: Optional[str] = None
    
    # Grok/xAI API for LLM extraction fallback
    xai_api_key: Optional[str] = None
    xai_api_base: str = "https://api.x.ai/v1"
    grok_model: str = "grok-beta"
    
    # OpenAI API (alternative to Grok)
    openai_api_key: Optional[str] = None
    openai_api_base: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    # Neo4j (for Mem0 graph memory and Graphiti)
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "changeme"

    # Memory service (Mem0)
    MEM0_COLLECTION: str = "user_memories"

    # Graph service (Graphiti)
    # Note: Neo4j Community Edition only supports "neo4j" database name
    GRAPHITI_DATABASE: str = "neo4j"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
