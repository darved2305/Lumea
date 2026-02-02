"""
LLM Service - Ollama streaming (local only)

Uses an Ollama model for streaming responses and logs pull progress
so you can watch download status in backend logs.
"""
import asyncio
import json
from typing import AsyncGenerator, Optional
import logging

import httpx
import ollama

from src.config.settings import settings

logger = logging.getLogger(__name__)


# Medical system prompt for the LLM
MEDICAL_SYSTEM_PROMPT = """You are an AI assistant for a personal health dashboard.
Your primary job is to answer questions using ONLY the user's provided context:
uploaded reports, extracted observations, and any document snippets included.

Guardrails:
- Do NOT use external knowledge or guess missing details.
- If the answer is not in the provided context, say so and ask the user to upload the relevant report.
- Never diagnose conditions or provide treatment plans.
- Provide clear, concise explanations of what the data shows and what it might imply.
- Always recommend consulting a licensed clinician for medical decisions.
- If the user asks about a document, reference the report filename/date from context when possible.

You have access to the user's personal health data provided in the context below.
Answer strictly based on that data."""


_pull_lock = asyncio.Lock()
_pull_complete: Optional[bool] = None


async def _pull_model_with_progress() -> None:
    """Pull the Ollama model (if needed) and log progress."""
    global _pull_complete

    if _pull_complete is True:
        return

    async with _pull_lock:
        if _pull_complete is True:
            return

        url = settings.OLLAMA_BASE_URL.rstrip("/")
        pull_url = f"{url}/api/pull"

        logger.info("Ollama pull starting for model %s", settings.OLLAMA_MODEL)
        last_logged_pct = -1

        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                pull_url,
                json={"name": settings.OLLAMA_MODEL, "stream": True},
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        logger.debug("Ollama pull raw: %s", line)
                        continue

                    status = payload.get("status")
                    total = payload.get("total")
                    completed = payload.get("completed")

                    if total and completed is not None:
                        pct = int((completed / total) * 100)
                        step = max(1, settings.OLLAMA_PULL_LOG_STEP_PCT)
                        if pct >= last_logged_pct + step or pct == 100:
                            last_logged_pct = pct
                            logger.info("Ollama pull progress: %s%%", pct)
                    elif status:
                        logger.info("Ollama pull status: %s", status)

        _pull_complete = True
        logger.info("Ollama pull complete for model %s", settings.OLLAMA_MODEL)


class LLMService:
    """
    LLM Service for generating responses with streaming support using Ollama.
    """

    async def stream_generate(
        self,
        user_message: str,
        context: str,
        chat_history: Optional[list] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from the LLM.

        Args:
            user_message: The user's question/message.
            context: Retrieved context from RAG (user's health data).
            chat_history: Optional list of previous messages.

        Yields:
            String tokens as they are generated.
        """
        if settings.OLLAMA_PULL_ON_START:
            await _pull_model_with_progress()

        # Build the full prompt including system instructions, context and history
        full_prompt = self._build_prompt(user_message, context, chat_history)

        client = ollama.AsyncClient(host=settings.OLLAMA_BASE_URL)
        try:
            response = await client.chat(
                model=settings.OLLAMA_MODEL,
                messages=[{"role": "user", "content": full_prompt}],
                stream=True,
                options={
                    "temperature": 0.7,
                    "top_p": 0.9,
                },
            )

            async for chunk in response:
                if chunk.get("message", {}).get("content"):
                    yield chunk["message"]["content"]
        except Exception as e:
            logger.error("Ollama streaming error: %s", e)
            yield f"Error: Unable to generate response. {str(e)}"

    def _build_prompt(
        self,
        user_message: str,
        context: str,
        chat_history: Optional[list] = None,
    ) -> str:
        """Build the full prompt with system instructions, context, and history."""
        prompt_parts = [MEDICAL_SYSTEM_PROMPT]

        if context:
            prompt_parts.append(
                f"\n\n--- USER'S HEALTH DATA ---\n{context}\n--- END HEALTH DATA ---"
            )

        if chat_history:
            prompt_parts.append("\n\n--- CONVERSATION HISTORY ---")
            for msg in chat_history[-10:]:  # Last 10 messages
                role = "User" if msg.get("role") == "user" else "Assistant"
                prompt_parts.append(f"{role}: {msg.get('content', '')}")
            prompt_parts.append("--- END HISTORY ---")

        prompt_parts.append(f"\n\nUser: {user_message}\n\nAssistant:")

        return "\n".join(prompt_parts)

    async def generate(
        self,
        user_message: str,
        context: str,
        chat_history: Optional[list] = None,
    ) -> str:
        """
        Convenience helper: generate a complete (non-streaming) response.
        """
        parts: list[str] = []
        async for token in self.stream_generate(user_message, context, chat_history):
            parts.append(token)
        return "".join(parts)


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get the LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
