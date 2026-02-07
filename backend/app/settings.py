from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    frontend_origin: str = "http://localhost:5173"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60  # 1 hour default (was 7 days - too long for PHI)
    
    # PHI Encryption Settings (HIPAA compliance)
    phi_encryption_key: Optional[str] = None
    phi_encryption_salt: str = "lumea-health-phi-salt"
    
    # Cookie Security Settings
    cookie_secure: bool = True  # Set to False only for local HTTP development
    cookie_samesite: str = "strict"
    token_max_age_seconds: int = 3600  # 1 hour

    # Database schema management
    # In development, prefer Alembic migrations over SQLAlchemy create_all()
    # so existing databases get schema changes (new columns/indexes).
    AUTO_MIGRATE: bool = False  # Disabled - using create_all instead

    # =====================
    # OpenRouter Configuration (PRIMARY LLM)
    # =====================
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "openrouter/pony-alpha"
    OPENROUTER_FALLBACK_MODEL: str = "upstage/solar-pro-3:free"
    OPENROUTER_TIMEOUT: int = 120  # seconds

    # Ollama LLM Configuration (LAST RESORT fallback)
    # Default to localhost for direct (non‑Docker) runs.
    # When running via Docker, docker-compose.yml overrides this to use
    # http://host.docker.internal:11434 so the container can reach the host.
    OLLAMA_BASE_URL: str = "http://localhost:11434"
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

    # Groq API for recommendations and LLM extraction
    groq_api_key: Optional[str] = None
    groq_api_base: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.3-70b-versatile"  # Updated to current model
    MEM0_GROQ_MODEL: str = "llama-3.1-8b-instant"
    # Graphiti requires JSON-schema structured outputs; use a Groq model that supports it.
    GRAPHITI_GROQ_MODEL: str = "moonshotai/kimi-k2-instruct-0905"

    # Grok/xAI API (alternative)
    grok_api_key: Optional[str] = None
    xai_api_key: Optional[str] = None
    xai_api_base: str = "https://api.x.ai/v1"
    grok_model: str = "grok-beta"

    # OpenAI API (alternative)
    openai_api_key: Optional[str] = None
    openai_api_base: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    # Google Places API for pharmacy locator
    google_places_api_key: Optional[str] = None

    # ElevenLabs TTS for Voice Agent
    ELEVENLABS_API_KEY: Optional[str] = None
    ELEVENLABS_VOICE_ID: Optional[str] = "21m00Tcm4TlvDq8ikWAM"  # Default: Rachel voice

    # Neo4j (for Mem0 graph memory and Graphiti)
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "changeme"

    # Memory service (Mem0)
    MEM0_COLLECTION: str = "user_memories"
    MEM0_EMBED_MODEL: str = "nomic-embed-text"
    MEM0_CHROMA_DIR: str = "/app/mem0_chroma"  # Separate from RAG to avoid singleton conflict
    MEM0_PREFER_GROQ: bool = True

    # Groq / Mem0 rate-limit mitigation
    # Minimum seconds between consecutive Mem0 LLM calls (prevents TPM exhaustion)
    MEM0_CALL_INTERVAL_SECONDS: float = 3.0
    # Max retries per individual add() call when Groq returns 429
    MEM0_MAX_RETRIES: int = 5
    # Base backoff (seconds) for exponential retry on 429
    MEM0_RETRY_BASE_SECONDS: float = 2.0
    # Proactive delay (seconds) between profile sync batches
    MEM0_BATCH_DELAY_SECONDS: float = 5.0
    # Number of facts per Mem0 batch (larger = fewer API calls)
    MEM0_SYNC_BATCH_SIZE: int = 15

    # Graph service (Graphiti)
    # Note: Neo4j Community Edition only supports "neo4j" database name
    GRAPHITI_DATABASE: str = "neo4j"

    # =====================
    # SMS CONFIGURATION
    # =====================
    # SMS_MODE: "twilio" for real SMS, "mock" for logging only
    SMS_MODE: str = "mock"
    
    # Test phone number (from env, NEVER hardcode!)
    # Used only for testing via /api/sms/test endpoint
    SMS_TEST_TO_NUMBER: Optional[str] = None
    
    # Twilio credentials (required if SMS_MODE=twilio)
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_FROM_NUMBER: Optional[str] = None
    
    # Reminder scheduler settings
    REMINDER_SCHEDULER_ENABLED: bool = True
    REMINDER_CHECK_INTERVAL_SECONDS: int = 60  # How often to check for due reminders

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# Debug logging to verify SMS configuration
import logging
logger = logging.getLogger(__name__)
logger.info(f"SMS Configuration loaded:")
logger.info(f"  SMS_MODE: {settings.SMS_MODE}")
logger.info(f"  SMS_TEST_TO_NUMBER: {settings.SMS_TEST_TO_NUMBER}")
logger.info(f"  TWILIO_ACCOUNT_SID configured: {bool(settings.TWILIO_ACCOUNT_SID)}")
logger.info(f"  TWILIO_AUTH_TOKEN configured: {bool(settings.TWILIO_AUTH_TOKEN)}")
logger.info(f"  TWILIO_FROM_NUMBER: {settings.TWILIO_FROM_NUMBER}")
