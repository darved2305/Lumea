import logging
import asyncio
import random
import re
import threading
import copy
import time
from typing import List, Dict, Any, Optional, Tuple
from app.settings import settings

# Configure logger
logger = logging.getLogger(__name__)

def _import_mem0_memory():
    """
    Mem0 is distributed as `mem0ai` on PyPI, but the importable module may be
    `mem0` depending on the version. Support both and allow graceful disable.
    """
    try:
        from mem0 import Memory  # type: ignore
        return Memory
    except Exception:
        try:
            from mem0ai import Memory  # type: ignore
            return Memory
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Groq / LLM call throttle
# ---------------------------------------------------------------------------

def _extract_retry_seconds(error_text: str) -> float:
    """Parse 'try again in <N>s' from Groq 429 responses."""
    match = re.search(r"try again in ([0-9.]+)s", error_text, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except (TypeError, ValueError):
            pass
    return 0.0


def _is_rate_limit_error(error_text: str) -> bool:
    """Check if an error string indicates a Groq/OpenAI 429 rate limit."""
    lower = error_text.lower()
    return "rate_limit" in lower or "429" in lower or "rate limit" in lower


class _LLMThrottle:
    """
    Async token-bucket style throttle for outbound Mem0→LLM calls.

    Enforces a minimum interval between consecutive calls so the
    aggregate tokens-per-minute stays within provider quotas.
    All callers in the process share a single lock.
    """

    def __init__(self, min_interval: float):
        self._min_interval = max(min_interval, 0.0)
        self._lock: Optional[asyncio.Lock] = None
        self._last_call: float = 0.0

    def _ensure_lock(self) -> asyncio.Lock:
        """Lazily create the lock inside the running event loop."""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def acquire(self) -> None:
        """Wait until enough time has elapsed since the last call."""
        lock = self._ensure_lock()
        async with lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            if elapsed < self._min_interval:
                wait = self._min_interval - elapsed
                logger.debug("LLMThrottle: waiting %.2fs before next Mem0 call", wait)
                await asyncio.sleep(wait)
            self._last_call = time.monotonic()

    async def backoff(self, seconds: float) -> None:
        """Push the next-allowed timestamp forward (e.g. after a 429)."""
        lock = self._ensure_lock()
        async with lock:
            self._last_call = time.monotonic() + seconds - self._min_interval


# Module-level throttle shared by every MemoryService instance.
_llm_throttle = _LLMThrottle(settings.MEM0_CALL_INTERVAL_SECONDS)


class MemoryService:
    """
    Service for interacting with Mem0 memory layer.
    Stores unstructured user preferences, facts, and conversation history.

    All outbound calls are throttled through ``_llm_throttle`` so that
    aggregate LLM TPM usage stays within quota.  Individual ``add()``
    calls self-retry with exponential back-off on 429 errors.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MemoryService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Lazy initialization of the Memory client
        self._memory_cls = _import_mem0_memory()
        self.memory_client = None
        self._client_lock = threading.Lock()
        self._last_init_error: Optional[str] = None
        self._last_init_attempt_at: float = 0.0
        self._init_retry_cooldown_seconds = 10
        self._active_config_name: Optional[str] = None

        self.last_error: Optional[str] = None
        self.config_candidates = self._build_config_candidates()
        # For compatibility/debugging: populated with the selected config after init.
        self.config: Optional[Dict[str, Any]] = None
        self._initialized = True
        logger.info("MemoryService initialized (lazy loading client)")

    @property
    def is_available(self) -> bool:
        return self._memory_cls is not None

    def _base_store_config(self) -> Dict[str, Any]:
        return {
            "vector_store": {
                "provider": "chroma",
                "config": {
                    "collection_name": settings.MEM0_COLLECTION,
                    "path": settings.MEM0_CHROMA_DIR,  # Separate from RAG's ChromaDB
                },
            },
            "graph_store": {
                "provider": "neo4j",
                "config": {
                    "url": settings.NEO4J_URI,
                    "username": settings.NEO4J_USER,
                    "password": settings.NEO4J_PASSWORD,
                },
            },
        }

    def _build_llm_candidates(self) -> List[Tuple[str, Dict[str, Any]]]:
        openrouter_candidates: List[Tuple[str, Dict[str, Any]]] = []
        groq_candidates: List[Tuple[str, Dict[str, Any]]] = []
        ollama_candidates: List[Tuple[str, Dict[str, Any]]] = []

        # OpenRouter support via OpenAI-compatible config (preferred).
        if settings.OPENROUTER_API_KEY and settings.MEM0_PREFER_OPENROUTER:
            openrouter_candidates.append(
                (
                    "openrouter_openai_compat",
                    {
                        "provider": "openai",
                        "config": {
                            "api_key": settings.OPENROUTER_API_KEY,
                            "model": settings.MEM0_OPENROUTER_MODEL,
                            "openai_base_url": settings.OPENROUTER_BASE_URL,
                            "temperature": 0.1,
                        },
                    },
                )
            )

        # Groq support via OpenAI-compatible config (fallback if OpenRouter not available).
        if settings.groq_api_key:
            groq_candidates.append(
                (
                    "groq_openai_compat",
                    {
                        "provider": "openai",
                        "config": {
                            "api_key": settings.groq_api_key,
                            "model": settings.MEM0_GROQ_MODEL,
                            "openai_base_url": settings.groq_api_base,
                            "temperature": 0.1,
                        },
                    },
                )
            )

        # Determine if a cloud LLM is preferred and available
        _cloud_llm_preferred = (
            (settings.MEM0_PREFER_OPENROUTER and settings.OPENROUTER_API_KEY)
            or (settings.MEM0_PREFER_GROQ and settings.groq_api_key)
        )

        # Only add Ollama candidates if no cloud LLM is preferred.
        # This prevents noisy "Failed to connect to Ollama" warnings.
        if not _cloud_llm_preferred:
            ollama_model = settings.OLLAMA_MODEL
            ollama_url = settings.OLLAMA_BASE_URL
            ollama_candidates.extend(
                [
                    (
                        "ollama_ollama_base_url",
                        {
                            "provider": "ollama",
                            "config": {
                                "model": ollama_model,
                                "ollama_base_url": ollama_url,
                            },
                        },
                    ),
                    (
                        "ollama_model_only",
                        {
                            "provider": "ollama",
                            "config": {
                                "model": ollama_model,
                            },
                        },
                    ),
                ]
            )

        return openrouter_candidates + groq_candidates + ollama_candidates

    def _build_embedder_candidates(self) -> List[Tuple[str, Dict[str, Any]]]:
        # Prefer local sentence-transformers embedder (works without Ollama or external APIs).
        # Only include Ollama embedder candidates if we're not preferring Groq (i.e., Ollama is expected to run).
        candidates = [
            (
                "huggingface_local",
                {
                    "provider": "huggingface",
                    "config": {
                        "model": settings.EMBEDDING_MODEL,
                    },
                },
            ),
        ]

        # Skip Ollama embedder candidates when using a cloud LLM (Ollama likely not running).
        _cloud_llm_active = (
            (settings.MEM0_PREFER_OPENROUTER and settings.OPENROUTER_API_KEY)
            or (settings.MEM0_PREFER_GROQ and settings.groq_api_key)
        )
        if not _cloud_llm_active:
            embed_model = settings.MEM0_EMBED_MODEL
            ollama_url = settings.OLLAMA_BASE_URL
            candidates.extend([
                (
                    "ollama_embed_ollama_base_url",
                    {
                        "provider": "ollama",
                        "config": {
                            "model": embed_model,
                            "ollama_base_url": ollama_url,
                        },
                    },
                ),
                (
                    "ollama_embed_model_only",
                    {
                        "provider": "ollama",
                        "config": {
                            "model": embed_model,
                        },
                    },
                ),
            ])

        return candidates

    def _build_config_candidates(self) -> List[Tuple[str, Dict[str, Any]]]:
        base = self._base_store_config()
        llm_candidates = self._build_llm_candidates()
        embedder_candidates = self._build_embedder_candidates()

        configs: List[Tuple[str, Dict[str, Any]]] = []
        seen_signatures = set()

        for llm_name, llm_config in llm_candidates:
            # With explicit embedder config
            for embed_name, embedder_config in embedder_candidates:
                cfg = copy.deepcopy(base)
                cfg["llm"] = copy.deepcopy(llm_config)
                cfg["embedder"] = copy.deepcopy(embedder_config)

                signature = repr(cfg)
                if signature in seen_signatures:
                    continue
                seen_signatures.add(signature)
                configs.append((f"{llm_name}+{embed_name}", cfg))

            # Fallback: let Mem0 decide embedder defaults
            cfg = copy.deepcopy(base)
            cfg["llm"] = copy.deepcopy(llm_config)
            signature = repr(cfg)
            if signature not in seen_signatures:
                seen_signatures.add(signature)
                configs.append((f"{llm_name}+default_embedder", cfg))

        return configs

    def _set_error(self, message: str) -> None:
        self.last_error = message

    def _clear_error(self) -> None:
        self.last_error = None

    def _get_client(self):
        """Get or initialize the Mem0 client"""
        if not self.is_available:
            raise RuntimeError(
                "Mem0 is not installed/available. "
                "Install `mem0ai` (and ensure it provides importable `mem0`/`mem0ai`)."
            )
        if self.memory_client is None:
            with self._client_lock:
                if self.memory_client is None:
                    now = time.time()
                    if (
                        self._last_init_error
                        and (now - self._last_init_attempt_at) < self._init_retry_cooldown_seconds
                    ):
                        raise RuntimeError(self._last_init_error)
                    try:
                        logger.info("Initializing Mem0 client connection...")
                        self._last_init_attempt_at = now

                        init_errors = []
                        for config_name, candidate in self.config_candidates:
                            try:
                                self.memory_client = self._memory_cls.from_config(candidate)
                                self._active_config_name = config_name
                                self.config = candidate
                                self._last_init_error = None
                                self._clear_error()
                                logger.info(
                                    "Mem0 client initialized successfully (config=%s)",
                                    config_name,
                                )
                                break
                            except Exception as candidate_error:
                                err = f"{config_name}: {candidate_error}"
                                init_errors.append(err)
                                logger.warning("Mem0 config attempt failed (%s)", err)

                        if self.memory_client is None:
                            joined = "; ".join(init_errors) if init_errors else "Unknown Mem0 init error"
                            self._last_init_error = f"Mem0 initialization failed: {joined}"
                            raise RuntimeError(self._last_init_error)
                        logger.info("Mem0 client initialized successfully")
                    except Exception as e:
                        logger.error(f"Failed to initialize Mem0 client: {e}")
                        self._set_error(str(e))
                        raise
        return self.memory_client

    async def add(
        self,
        content: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        *,
        _max_retries: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Add a memory for a user asynchronously.

        Automatically throttles outbound Groq calls and retries on 429
        rate-limit errors with exponential back-off + jitter.

        Args:
            content: The text content to remember
            user_id: The user ID (will be used as user_id in Mem0)
            metadata: Optional metadata to attach
            _max_retries: Override default retry count (settings.MEM0_MAX_RETRIES)
        """
        max_retries = _max_retries if _max_retries is not None else settings.MEM0_MAX_RETRIES
        base_backoff = settings.MEM0_RETRY_BASE_SECONDS

        def _sync_add():
            client = self._get_client()
            return client.add(content, user_id=user_id, metadata=metadata)

        last_err: Optional[str] = None

        for attempt in range(1, max_retries + 1):
            # ---- throttle: wait for our turn ----
            await _llm_throttle.acquire()

            try:
                result = await asyncio.to_thread(_sync_add)
            except Exception as e:
                err_text = str(e)
                if _is_rate_limit_error(err_text):
                    retry_after = _extract_retry_seconds(err_text)
                    wait = max(retry_after, base_backoff * attempt) + random.uniform(0.5, 1.5)
                    logger.warning(
                        "LLM 429 during Mem0 add for user %s (attempt %s/%s). "
                        "Backing off %.1fs",
                        user_id, attempt, max_retries, wait,
                    )
                    await _llm_throttle.backoff(wait)
                    await asyncio.sleep(wait)
                    last_err = err_text
                    continue
                # Non-rate-limit error → don't retry
                logger.error("Error adding memory for user %s: %s", user_id, e)
                self._set_error(err_text)
                return {"error": err_text}

            # Mem0 may return success dict but with error payload
            if isinstance(result, dict) and result.get("error"):
                err_text = str(result["error"])
                if _is_rate_limit_error(err_text) and attempt < max_retries:
                    retry_after = _extract_retry_seconds(err_text)
                    wait = max(retry_after, base_backoff * attempt) + random.uniform(0.5, 1.5)
                    logger.warning(
                        "LLM 429 in Mem0 result for user %s (attempt %s/%s). "
                        "Backing off %.1fs",
                        user_id, attempt, max_retries, wait,
                    )
                    await _llm_throttle.backoff(wait)
                    await asyncio.sleep(wait)
                    last_err = err_text
                    continue
                # Non-retryable error in result
                self._set_error(err_text)
                return result

            # ---- success ----
            self._clear_error()
            return result

        # Exhausted all retries
        logger.error(
            "Mem0 add exhausted %s retries for user %s. Last error: %s",
            max_retries, user_id, last_err,
        )
        self._set_error(last_err or "Rate limit retries exhausted")
        return {"error": last_err or "Rate limit retries exhausted"}

    async def add_batch(
        self,
        items: List[Dict[str, Any]],
        user_id: str,
        *,
        inter_call_delay: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Add multiple memories sequentially with throttling between each.

        Each item dict must have at minimum ``content`` (str).
        Optional keys: ``metadata`` (dict).

        Returns a list of results (one per item).
        """
        delay = inter_call_delay if inter_call_delay is not None else settings.MEM0_BATCH_DELAY_SECONDS
        results: List[Dict[str, Any]] = []
        for idx, item in enumerate(items):
            result = await self.add(
                content=item["content"],
                user_id=user_id,
                metadata=item.get("metadata"),
            )
            results.append(result)
            # Proactive delay between items (throttle.acquire also enforces min interval)
            if idx < len(items) - 1 and delay > 0:
                await asyncio.sleep(delay)
        return results

    async def search(self, query: str, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search memories for a user asynchronously.

        Throttled to respect Groq TPM limits (search also triggers LLM calls
        inside Mem0 for query expansion).

        Args:
            query: Search query
            user_id: The user ID to scope search to
            limit: Max results to return
        """
        def _sync_search():
            client = self._get_client()
            return client.search(query, user_id=user_id, limit=limit)

        await _llm_throttle.acquire()
        try:
            result = await asyncio.to_thread(_sync_search)
            self._clear_error()
            return result
        except Exception as e:
            err_text = str(e)
            if _is_rate_limit_error(err_text):
                retry_after = _extract_retry_seconds(err_text)
                wait = max(retry_after, settings.MEM0_RETRY_BASE_SECONDS) + random.uniform(0.5, 1.5)
                logger.warning(
                    "LLM 429 during Mem0 search for user %s — backing off %.1fs and retrying once",
                    user_id, wait,
                )
                await _llm_throttle.backoff(wait)
                await asyncio.sleep(wait)
                await _llm_throttle.acquire()
                try:
                    result = await asyncio.to_thread(_sync_search)
                    self._clear_error()
                    return result
                except Exception as e2:
                    logger.error("Mem0 search retry also failed for user %s: %s", user_id, e2)
                    self._set_error(str(e2))
                    return []
            logger.error("Error searching memories for user %s: %s", user_id, e)
            self._set_error(err_text)
            return []

    async def get_all(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all memories for a user asynchronously.
        """
        def _sync_get_all():
            client = self._get_client()
            return client.get_all(user_id=user_id)

        try:
            result = await asyncio.to_thread(_sync_get_all)
            self._clear_error()
            return result
        except Exception as e:
            logger.error(f"Error getting all memories for user {user_id}: {e}")
            self._set_error(str(e))
            return []

    async def delete(self, memory_id: str) -> bool:
        """
        Delete a specific memory by ID asynchronously.
        """
        def _sync_delete():
            client = self._get_client()
            client.delete(memory_id)
            return True

        try:
            result = await asyncio.to_thread(_sync_delete)
            self._clear_error()
            return result
        except Exception as e:
            logger.error(f"Error deleting memory {memory_id}: {e}")
            self._set_error(str(e))
            return False

    async def delete_all(self, user_id: str) -> bool:
        """
        Delete all memories for a user asynchronously.
        """
        def _sync_delete_all():
            client = self._get_client()
            client.delete_all(user_id=user_id)
            return True

        try:
            result = await asyncio.to_thread(_sync_delete_all)
            self._clear_error()
            return result
        except Exception as e:
            logger.error(f"Error deleting all memories for user {user_id}: {e}")
            self._set_error(str(e))
            return False

# Global instance
memory_service = MemoryService()

def get_memory_service() -> MemoryService:
    return memory_service
