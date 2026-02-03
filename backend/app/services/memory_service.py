import logging
import asyncio
import threading
from typing import List, Dict, Any, Optional
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


class MemoryService:
    """
    Service for interacting with Mem0 memory layer.
    Stores unstructured user preferences, facts, and conversation history.
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

        self.config = {
            "vector_store": {
                "provider": "chroma",
                "config": {
                    "collection_name": settings.MEM0_COLLECTION,
                    "path": settings.CHROMA_PERSIST_DIR,
                }
            },
            "llm": {
                "provider": "ollama",
                "config": {
                    "model": settings.OLLAMA_MODEL,
                    "base_url": settings.OLLAMA_BASE_URL,
                    "timeout": settings.OLLAMA_TIMEOUT,
                }
            },
            "graph_store": {
                "provider": "neo4j",
                "config": {
                    "url": settings.NEO4J_URI,
                    "username": settings.NEO4J_USER,
                    "password": settings.NEO4J_PASSWORD
                }
            }
        }

        # Lazy initialization of the Memory client
        self._memory_cls = _import_mem0_memory()
        self.memory_client = None
        self._client_lock = threading.Lock()
        self._initialized = True
        logger.info("MemoryService initialized (lazy loading client)")

    @property
    def is_available(self) -> bool:
        return self._memory_cls is not None

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
                    try:
                        logger.info("Initializing Mem0 client connection...")
                        self.memory_client = self._memory_cls.from_config(self.config)
                        logger.info("Mem0 client initialized successfully")
                    except Exception as e:
                        logger.error(f"Failed to initialize Mem0 client: {e}")
                        raise
        return self.memory_client

    async def add(self, content: str, user_id: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Add a memory for a user asynchronously.

        Args:
            content: The text content to remember
            user_id: The user ID (will be used as user_id in Mem0)
            metadata: Optional metadata to attach
        """
        def _sync_add():
            client = self._get_client()
            return client.add(content, user_id=user_id, metadata=metadata)

        try:
            return await asyncio.to_thread(_sync_add)
        except Exception as e:
            logger.error(f"Error adding memory for user {user_id}: {e}")
            return {"error": str(e)}

    async def search(self, query: str, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search memories for a user asynchronously.

        Args:
            query: Search query
            user_id: The user ID to scope search to
            limit: Max results to return
        """
        def _sync_search():
            client = self._get_client()
            return client.search(query, user_id=user_id, limit=limit)

        try:
            return await asyncio.to_thread(_sync_search)
        except Exception as e:
            logger.error(f"Error searching memories for user {user_id}: {e}")
            return []

    async def get_all(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all memories for a user asynchronously.
        """
        def _sync_get_all():
            client = self._get_client()
            return client.get_all(user_id=user_id)

        try:
            return await asyncio.to_thread(_sync_get_all)
        except Exception as e:
            logger.error(f"Error getting all memories for user {user_id}: {e}")
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
            return await asyncio.to_thread(_sync_delete)
        except Exception as e:
            logger.error(f"Error deleting memory {memory_id}: {e}")
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
            return await asyncio.to_thread(_sync_delete_all)
        except Exception as e:
            logger.error(f"Error deleting all memories for user {user_id}: {e}")
            return False

# Global instance
memory_service = MemoryService()

def get_memory_service() -> MemoryService:
    return memory_service
