"""
LLM Service - OpenRouter primary with multi-tier fallback

Provider priority:
  1. OpenRouter  (openrouter/pony-alpha)
  2. OpenRouter  (upstage/solar-pro-3:free)  – free fallback
  3. Gemini      (gemini-flash-latest)        – Google fallback
  4. Ollama      (MedGemma via GGUF)          – local last resort

Uses the OpenAI Python SDK pointed at OpenRouter's OpenAI-compatible endpoint.
"""
import asyncio
from typing import AsyncGenerator, Optional, List, Dict, Any
import logging

from app.settings import settings

logger = logging.getLogger(__name__)

# Resolved Ollama base URL (may differ from settings.OLLAMA_BASE_URL if we
# automatically switch from localhost → host.docker.internal when running
# inside Docker).
_resolved_ollama_base_url: Optional[str] = None

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
MEDICAL_SYSTEM_PROMPT = """You are a knowledgeable and empathetic AI medical health assistant.
Your role is to help users understand their health data, lab results, and medical information.

Guidelines:
- Provide accurate, evidence-based information
- Always recommend consulting a healthcare professional for medical decisions
- Be clear about what the data shows and what it means
- If you don't have enough information, say so
- Never diagnose conditions - only explain what the data indicates
- Be supportive and non-alarmist while being honest about concerning values

IMPORTANT - Source Attribution Rules:
When you use information from the context provided below, you MUST cite the source inline:
- For report data, say: "Based on your report '[filename]' ..."  or  "From your uploaded report ..."
- For memory/preferences, say: "From your health profile, I recall that ..."  or  "According to your stored preferences ..."
- For knowledge graph facts, say: "From the medical knowledge graph, I can see that ..."  or  "Based on your medical history graph ..."
- If combining multiple sources, mention each one.
- If you don't have relevant data, say so clearly.

You have access to the user's personal health data provided in the context below.
Answer based on their specific data when available."""


class LLMService:
    """
    LLM Service for generating responses with streaming support.

    Priority chain:
      1. OpenRouter  – pony-alpha  (primary)
      2. OpenRouter  – solar-pro-3:free  (fallback)
      3. Gemini API  (Google fallback)
      4. Ollama      (local last-resort)
    """

    def __init__(self):
        self._ollama_available: Optional[bool] = None
        self._gemini_client = None
        self._openrouter_client = None

    # ------------------------------------------------------------------
    # OpenRouter (OpenAI-compatible SDK)
    # ------------------------------------------------------------------
    def _get_openrouter_client(self):
        """Lazy-init the OpenAI client pointed at OpenRouter."""
        if self._openrouter_client is None:
            from openai import AsyncOpenAI

            self._openrouter_client = AsyncOpenAI(
                base_url=settings.OPENROUTER_BASE_URL,
                api_key=settings.OPENROUTER_API_KEY,
                default_headers={
                    "HTTP-Referer": settings.frontend_origin,
                    "X-Title": "Lumea Health Assistant",
                },
                timeout=settings.OPENROUTER_TIMEOUT,
            )
        return self._openrouter_client

    # ------------------------------------------------------------------
    # Ollama health check (kept for last-resort fallback)
    # ------------------------------------------------------------------
    async def check_ollama_health(self) -> bool:
        """Check if Ollama is available and the model is loaded."""
        global _resolved_ollama_base_url

        base_url = _resolved_ollama_base_url or settings.OLLAMA_BASE_URL

        try:
            import ollama
            client = ollama.AsyncClient(host=base_url)
            await asyncio.wait_for(client.list(), timeout=5.0)
            _resolved_ollama_base_url = base_url
            logger.info("Ollama available at %s", base_url)
            return True
        except Exception as e:
            logger.warning("Ollama not available at %s: %s", base_url, e)

            if "localhost" in base_url or "127.0.0.1" in base_url:
                fallback_url = base_url.replace("localhost", "host.docker.internal").replace(
                    "127.0.0.1", "host.docker.internal"
                )
                try:
                    import ollama
                    client = ollama.AsyncClient(host=fallback_url)
                    await asyncio.wait_for(client.list(), timeout=5.0)
                    _resolved_ollama_base_url = fallback_url
                    logger.info("Ollama available at %s", fallback_url)
                    return True
                except Exception as e2:
                    logger.warning("Fallback Ollama check at %s also failed: %s", fallback_url, e2)

            return False

    # ------------------------------------------------------------------
    # Provider resolution
    # ------------------------------------------------------------------
    async def _ensure_provider(self) -> str:
        """
        Determine which provider to use.

        Returns one of: 'openrouter', 'gemini', 'ollama', 'disabled'.
        """
        # 1. OpenRouter (primary) – needs API key
        if settings.OPENROUTER_API_KEY:
            return "openrouter"

        # 2. Gemini – needs API key
        if settings.USE_GEMINI_FALLBACK and settings.GEMINI_API_KEY:
            logger.info("OpenRouter not configured; falling back to Gemini")
            return "gemini"

        # 3. Ollama – local, needs running daemon
        if self._ollama_available is None:
            self._ollama_available = await self.check_ollama_health()
        if self._ollama_available:
            logger.info("Using Ollama as last-resort provider")
            return "ollama"

        return "disabled"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def stream_generate(
        self,
        user_message: str,
        context: str,
        chat_history: Optional[list] = None,
    ) -> AsyncGenerator[str, None]:
        """Yield tokens as they are generated."""
        provider = await self._ensure_provider()
        messages = self._build_messages(user_message, context, chat_history)

        if provider == "openrouter":
            async for token in self._stream_openrouter(messages):
                yield token
        elif provider == "gemini":
            prompt = self._build_prompt(user_message, context, chat_history)
            async for token in self._stream_gemini(prompt):
                yield token
        elif provider == "ollama":
            prompt = self._build_prompt(user_message, context, chat_history)
            async for token in self._stream_ollama(prompt):
                yield token
        else:
            yield (
                "LLM is not configured. "
                "Set `OPENROUTER_API_KEY` for the primary provider, "
                "or configure Gemini / Ollama as fallbacks."
            )

    async def generate(
        self,
        user_message: str,
        context: str,
        chat_history: Optional[list] = None,
    ) -> str:
        """Generate a complete (non-streaming) response."""
        parts: list[str] = []
        async for token in self.stream_generate(user_message, context, chat_history):
            parts.append(token)
        return "".join(parts)

    # ------------------------------------------------------------------
    # Message / prompt builders
    # ------------------------------------------------------------------
    def _build_messages(
        self,
        user_message: str,
        context: str,
        chat_history: Optional[list] = None,
    ) -> List[Dict[str, str]]:
        """Build OpenAI-style messages array for OpenRouter."""
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": MEDICAL_SYSTEM_PROMPT},
        ]

        if context:
            messages.append({
                "role": "system",
                "content": f"--- USER'S HEALTH DATA ---\n{context}\n--- END HEALTH DATA ---",
            })

        if chat_history:
            for msg in chat_history[-10:]:
                role = msg.get("role", "user")
                messages.append({"role": role, "content": msg.get("content", "")})

        messages.append({"role": "user", "content": user_message})
        return messages

    def _build_prompt(
        self,
        user_message: str,
        context: str,
        chat_history: Optional[list] = None,
    ) -> str:
        """Build a flat prompt string (Gemini / Ollama)."""
        parts = [MEDICAL_SYSTEM_PROMPT]

        if context:
            parts.append(f"\n\n--- USER'S HEALTH DATA ---\n{context}\n--- END HEALTH DATA ---")

        if chat_history:
            parts.append("\n\n--- CONVERSATION HISTORY ---")
            for msg in chat_history[-10:]:
                role = "User" if msg.get("role") == "user" else "Assistant"
                parts.append(f"{role}: {msg.get('content', '')}")
            parts.append("--- END HISTORY ---")

        parts.append(f"\n\nUser: {user_message}\n\nAssistant:")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # OpenRouter streaming (primary + in-band fallback model)
    # ------------------------------------------------------------------
    async def _stream_openrouter(
        self,
        messages: List[Dict[str, str]],
    ) -> AsyncGenerator[str, None]:
        """Stream from OpenRouter, falling back through models then providers."""
        models_to_try = [
            settings.OPENROUTER_MODEL,           # openrouter/pony-alpha
            settings.OPENROUTER_FALLBACK_MODEL,   # upstage/solar-pro-3:free
        ]

        last_error: Optional[Exception] = None

        for model in models_to_try:
            try:
                client = self._get_openrouter_client()
                logger.info("Streaming from OpenRouter model: %s", model)

                stream = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=True,
                    temperature=0.7,
                    top_p=0.9,
                    max_tokens=2048,
                )

                had_content = False
                async for chunk in stream:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if delta and delta.content:
                        had_content = True
                        yield delta.content

                if had_content:
                    return  # success – done
                else:
                    logger.warning("OpenRouter model %s returned empty stream", model)

            except Exception as e:
                last_error = e
                logger.warning("OpenRouter model %s failed: %s", model, e)
                continue

        # All OpenRouter models failed – cascade to Gemini → Ollama
        logger.error("All OpenRouter models exhausted. Cascading to Gemini/Ollama...")

        # Try Gemini
        if settings.USE_GEMINI_FALLBACK and settings.GEMINI_API_KEY:
            logger.info("Falling back to Gemini after OpenRouter failure")
            prompt = "\n".join(
                m["content"] for m in messages
            )
            async for token in self._stream_gemini(prompt):
                yield token
            return

        # Try Ollama (last resort)
        if self._ollama_available is None:
            self._ollama_available = await self.check_ollama_health()
        if self._ollama_available:
            logger.info("Falling back to Ollama after OpenRouter failure")
            prompt = "\n".join(
                m["content"] for m in messages
            )
            async for token in self._stream_ollama(prompt):
                yield token
            return

        yield f"Error: All LLM providers failed. Last error: {last_error}"

    # ------------------------------------------------------------------
    # Ollama streaming (last resort)
    # ------------------------------------------------------------------
    async def _stream_ollama(self, prompt: str) -> AsyncGenerator[str, None]:
        """Stream response from Ollama."""
        import ollama

        host = _resolved_ollama_base_url or settings.OLLAMA_BASE_URL
        client = ollama.AsyncClient(host=host)

        try:
            response = await client.chat(
                model=settings.OLLAMA_MODEL,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
                options={"temperature": 0.7, "top_p": 0.9},
            )

            async for chunk in response:
                if chunk.get("message", {}).get("content"):
                    yield chunk["message"]["content"]

        except Exception as e:
            logger.error("Ollama streaming error: %s", e)
            self._ollama_available = False
            yield f"Error: Ollama failed – {e}"

    # ------------------------------------------------------------------
    # Gemini streaming
    # ------------------------------------------------------------------
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
                    },
                )
            )

            for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error("Gemini streaming error: %s", e)
            yield f"Error: Gemini failed – {e}"


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get the LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
