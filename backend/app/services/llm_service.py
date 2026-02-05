"""
LLM Service - Ollama streaming with Gemini fallback

Provides async streaming generation using MedGemma via Ollama,
with automatic fallback to Gemini API if Ollama is unavailable.
"""
import asyncio
from typing import AsyncGenerator, Optional
import logging

from app.settings import settings

logger = logging.getLogger(__name__)

# Resolved Ollama base URL (may differ from settings.OLLAMA_BASE_URL if we
# automatically switch from localhost → host.docker.internal when running
# inside Docker).
_resolved_ollama_base_url: Optional[str] = None

# Medical system prompt for the LLM
MEDICAL_SYSTEM_PROMPT = """You are a knowledgeable and empathetic AI medical health assistant. 
Your role is to help users understand their health data, lab results, and medical information.

Guidelines:
- Provide accurate, evidence-based information
- Always recommend consulting a healthcare professional for medical decisions
- Be clear about what the data shows and what it means
- If you don't have enough information, say so
- Never diagnose conditions - only explain what the data indicates
- Be supportive and non-alarmist while being honest about concerning values

You have access to the user's personal health data provided in the context below.
Answer based on their specific data when available."""


class LLMService:
    """
    LLM Service for generating responses with streaming support.
    
    Primary: Ollama (MedGemma)
    Fallback: Gemini API
    """
    
    def __init__(self):
        self._ollama_available: Optional[bool] = None
        self._gemini_client = None
    
    async def check_ollama_health(self) -> bool:
        """Check if Ollama is available and the model is loaded."""
        global _resolved_ollama_base_url

        # Prefer a previously successful URL if we discovered one.
        base_url = _resolved_ollama_base_url or settings.OLLAMA_BASE_URL

        try:
            import ollama
            client = ollama.AsyncClient(host=base_url)
            # Try to list models to check connectivity
            models = await asyncio.wait_for(
                client.list(),
                timeout=5.0
            )
            # We only care that the server is reachable. The model might not be
            # pulled yet; Ollama will automatically pull it on first use.
            model_names = [m.get('name', '') for m in models.get('models', [])]
            if settings.OLLAMA_MODEL in model_names or any(
                settings.OLLAMA_MODEL.split(':')[0] in m for m in model_names
            ):
                logger.info(f"Ollama available with model {settings.OLLAMA_MODEL} at {base_url}")
            else:
                logger.warning(
                    "Ollama reachable at %s but model %s not found. "
                    "Available models: %s. The server will attempt to pull the "
                    "model on first use.",
                    base_url,
                    settings.OLLAMA_MODEL,
                    model_names,
                )

            _resolved_ollama_base_url = base_url
            return True
        except Exception as e:
            logger.warning(f"Ollama not available at {base_url}: {e}")

            # Common misconfig: using http://localhost:11434 from inside Docker.
            # If we see that, try host.docker.internal automatically so the
            # container can reach the host's Ollama daemon.
            if "localhost" in base_url or "127.0.0.1" in base_url:
                fallback_url = base_url.replace("localhost", "host.docker.internal").replace(
                    "127.0.0.1", "host.docker.internal"
                )
                try:
                    import ollama

                    logger.info(
                        "Retrying Ollama health check using %s "
                        "(likely running from inside Docker).",
                        fallback_url,
                    )
                    client = ollama.AsyncClient(host=fallback_url)
                    await asyncio.wait_for(client.list(), timeout=5.0)
                    _resolved_ollama_base_url = fallback_url
                    logger.info("Ollama available at %s", fallback_url)
                    return True
                except Exception as e2:
                    logger.warning(
                        "Fallback Ollama check at %s also failed: %s",
                        fallback_url,
                        e2,
                    )

            return False
    
    async def _ensure_provider(self) -> str:
        """Determine which provider to use. Returns 'ollama', 'gemini', or 'disabled'."""
        # If Gemini is configured, use it directly - no need to check Ollama
        if settings.USE_GEMINI_FALLBACK and settings.GEMINI_API_KEY:
            logger.info("Using Gemini API (configured)")
            return "gemini"
        
        # Only check Ollama if Gemini is not configured
        if self._ollama_available is None:
            self._ollama_available = await self.check_ollama_health()
        
        if self._ollama_available:
            return "ollama"
        
        # Make LLM optional: return a friendly message rather than hard-failing
        # core app features when neither provider is configured.
        return "disabled"
    
    async def stream_generate(
        self,
        user_message: str,
        context: str,
        chat_history: Optional[list] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from the LLM.
        
        Args:
            user_message: The user's question/message
            context: Retrieved context from RAG (user's health data)
            chat_history: Optional list of previous messages
            
        Yields:
            String tokens as they are generated
        """
        provider = await self._ensure_provider()
        
        # Build the full prompt
        full_prompt = self._build_prompt(user_message, context, chat_history)
        
        if provider == "ollama":
            async for token in self._stream_ollama(full_prompt):
                yield token
        elif provider == "gemini":
            async for token in self._stream_gemini(full_prompt):
                yield token
        else:
            yield (
                "LLM is not configured. "
                "Start Ollama (and set `OLLAMA_BASE_URL`/`OLLAMA_MODEL`) "
                "or set `GEMINI_API_KEY` with `USE_GEMINI_FALLBACK=true`."
            )
    
    def _build_prompt(
        self,
        user_message: str,
        context: str,
        chat_history: Optional[list] = None
    ) -> str:
        """Build the full prompt with system instructions, context, and history."""
        prompt_parts = [MEDICAL_SYSTEM_PROMPT]
        
        if context:
            prompt_parts.append(f"\n\n--- USER'S HEALTH DATA ---\n{context}\n--- END HEALTH DATA ---")
        
        if chat_history:
            prompt_parts.append("\n\n--- CONVERSATION HISTORY ---")
            for msg in chat_history[-10:]:  # Last 10 messages
                role = "User" if msg.get("role") == "user" else "Assistant"
                prompt_parts.append(f"{role}: {msg.get('content', '')}")
            prompt_parts.append("--- END HISTORY ---")
        
        prompt_parts.append(f"\n\nUser: {user_message}\n\nAssistant:")
        
        return "\n".join(prompt_parts)
    
    async def _stream_ollama(self, prompt: str) -> AsyncGenerator[str, None]:
        """Stream response from Ollama."""
        import ollama
        
        # Use any resolved URL from health checks, falling back to settings.
        host = _resolved_ollama_base_url or settings.OLLAMA_BASE_URL
        client = ollama.AsyncClient(host=host)
        
        try:
            response = await client.chat(
                model=settings.OLLAMA_MODEL,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
                options={
                    "temperature": 0.7,
                    "top_p": 0.9,
                }
            )
            
            async for chunk in response:
                if chunk.get("message", {}).get("content"):
                    yield chunk["message"]["content"]
                    
        except Exception as e:
            logger.error(f"Ollama streaming error: {e}")
            # Mark as unavailable and try fallback
            self._ollama_available = False
            if settings.USE_GEMINI_FALLBACK and settings.GEMINI_API_KEY:
                logger.info("Falling back to Gemini after Ollama error")
                async for token in self._stream_gemini(prompt):
                    yield token
            else:
                yield f"Error: Unable to generate response. {str(e)}"
    
    async def _stream_gemini(self, prompt: str) -> AsyncGenerator[str, None]:
        """Stream response from Gemini API."""
        try:
            import google.generativeai as genai
            
            if not self._gemini_client:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self._gemini_client = genai.GenerativeModel("gemini-flash-latest")
            
            response = await asyncio.to_thread(
                lambda: self._gemini_client.generate_content(
                    prompt,
                    stream=True,
                    generation_config={
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "max_output_tokens": 2048,
                    }
                )
            )
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            logger.error(f"Gemini streaming error: {e}")
            yield f"Error: Unable to generate response. {str(e)}"
    
    async def generate(
        self,
        user_message: str,
        context: str,
        chat_history: Optional[list] = None
    ) -> str:
        """
        Generate a complete (non-streaming) response.
        Useful for testing or when streaming is not needed.
        """
        response_parts = []
        async for token in self.stream_generate(user_message, context, chat_history):
            response_parts.append(token)
        return "".join(response_parts)


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get the LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
