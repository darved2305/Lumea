import logging
import asyncio
import inspect
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

try:
    from graphiti_core import Graphiti
    from graphiti_core.llm_client import OpenAIClient, LLMConfig
    from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
    from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
    GRAPHITI_AVAILABLE = True
except ImportError:
    GRAPHITI_AVAILABLE = False
    Graphiti = None
    OpenAIClient = None
    LLMConfig = None
    OpenAIEmbedder = None
    OpenAIEmbedderConfig = None
    OpenAIRerankerClient = None

from app.settings import settings

# Configure logger
logger = logging.getLogger(__name__)

class GraphService:
    """
    Service for interacting with the Graphiti knowledge graph (backed by Neo4j).
    Stores structured medical facts, temporal relationships, and contradictions.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GraphService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.driver = None
        self.client = None
        self._initialized = True
        logger.info("GraphService initialized (lazy loading client)")

    @staticmethod
    def _user_node_label(user_id: str) -> str:
        """Deterministic user node label used for graph tenant scoping."""
        return f"User_{user_id}"

    @classmethod
    def _is_user_scoped_result(cls, result: str, user_id: str) -> bool:
        label = cls._user_node_label(user_id)
        return label.lower() in result.lower()

    async def initialize(self):
        """
        Initialize the Neo4j driver and Graphiti client asynchronously.
        This should be called at application startup.
        """
        if not GRAPHITI_AVAILABLE:
            logger.warning("Graphiti libraries not installed, graph features disabled")
            return

        if self.client is not None:
            return

        try:
            use_groq = self._should_use_groq_llm()
            if use_groq:
                logger.info("Initializing Graphiti with Neo4j and Groq (OpenAI-compatible)...")
                llm_config = LLMConfig(
                    api_key=settings.groq_api_key,
                    base_url=settings.groq_api_base,
                    model=settings.GRAPHITI_GROQ_MODEL,
                    small_model=settings.GRAPHITI_GROQ_MODEL,
                    temperature=0.1,
                    max_tokens=4096,
                )
            else:
                logger.info("Initializing Graphiti with Neo4j and Ollama...")
                # Ollama via OpenAI-compatible endpoint.
                llm_config = LLMConfig(
                    api_key="ollama",  # Dummy key for Ollama
                    base_url=f"{settings.OLLAMA_BASE_URL}/v1",
                    model=settings.OLLAMA_MODEL,
                    small_model=settings.OLLAMA_MODEL,
                    temperature=0.1,
                    max_tokens=4096,
                )

            llm_client = OpenAIClient(
                config=llm_config,
                max_tokens=2048,
            )

            # 2. Initialize embedder explicitly to avoid default OpenAI embedder
            # requiring OPENAI_API_KEY. Use Ollama's OpenAI-compatible embeddings API.
            embedder_client = None
            if OpenAIEmbedder and OpenAIEmbedderConfig:
                embedder_client = OpenAIEmbedder(
                    config=OpenAIEmbedderConfig(
                        embedding_model=settings.MEM0_EMBED_MODEL,
                        embedding_dim=768,  # `nomic-embed-text` dimension
                        api_key="ollama",
                        base_url=f"{settings.OLLAMA_BASE_URL}/v1",
                    )
                )
            else:
                logger.warning(
                    "Graphiti OpenAIEmbedder not available; falling back to Graphiti default embedder"
                )

            cross_encoder_client = None
            if OpenAIRerankerClient:
                cross_encoder_client = OpenAIRerankerClient(config=llm_config)

            # 3. Initialize Graphiti Client with Neo4j connection
            # Pass uri, user, password directly - Graphiti creates the driver internally
            self.client = Graphiti(
                uri=settings.NEO4J_URI,
                user=settings.NEO4J_USER,
                password=settings.NEO4J_PASSWORD,
                llm_client=llm_client,
                embedder=embedder_client,
                cross_encoder=cross_encoder_client,
            )

            # Build indices (this is an async operation)
            await self.client.build_indices_and_constraints()

            logger.info("Graphiti initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize GraphService: {e}")
            # Service will be degraded (graph features won't work)
            self.client = None

    @staticmethod
    def _should_use_groq_llm() -> bool:
        """
        Prefer Groq whenever an API key is configured.
        Ollama remains fallback when no Groq key is present.
        """
        return bool(settings.groq_api_key)

    @staticmethod
    async def _await_if_needed(value: Any) -> Any:
        """
        Graphiti SDK methods differ by version: some are sync, some are async.
        Await only when the returned object is awaitable.
        """
        if inspect.isawaitable(value):
            return await value
        return value

    @staticmethod
    def _coerce_reference_time(timestamp: Optional[str]) -> datetime:
        """
        Graphiti requires a datetime reference_time. Accept optional ISO string
        from callers and default to current UTC when not provided.
        """
        if isinstance(timestamp, str) and timestamp.strip():
            raw = timestamp.strip()
            # Support trailing Z timestamps.
            if raw.endswith("Z"):
                raw = raw[:-1] + "+00:00"
            try:
                parsed = datetime.fromisoformat(raw)
                if parsed.tzinfo is None:
                    return parsed.replace(tzinfo=timezone.utc)
                return parsed
            except Exception:
                logger.warning("Invalid timestamp passed to GraphService.add_episode: %s", timestamp)
        return datetime.now(timezone.utc)

    async def add_episode(
        self,
        content: str,
        source: str = "user_input",
        timestamp: Optional[str] = None,
        group_id: Optional[str] = None,
    ):
        """
        Add a new episode to the knowledge graph.

        Args:
            content: The text content to process into facts
            source: Where this info came from (user, document, system)
            timestamp: ISO timestamp string (optional)
        """
        if not self.client:
            logger.warning("GraphService not initialized, skipping add_episode")
            return

        try:
            reference_time = self._coerce_reference_time(timestamp)
            await self._await_if_needed(
                self.client.add_episode(
                    name=f"Episode from {source}",
                    episode_body=content,
                    source_description=source,
                    reference_time=reference_time,
                    group_id=group_id,
                )
            )
            logger.info(f"Added episode to graph from source: {source}")
        except Exception as e:
            logger.error(f"Error adding episode to graph: {e}")

    async def add_observations(self, observations: List[str], source: str = "medical_inference"):
        """
        Add a list of specific observations (facts) to the graph.
        Useful for adding inferred medical facts.
        """
        if not observations:
            return

        # Combine observations into a coherent narrative for the graph
        content = "Medical System Observations:\n- " + "\n- ".join(observations)
        await self.add_episode(content, source=source)

    async def add_user_episode(
        self,
        user_id: str,
        content: str,
        source: str = "user_input",
        timestamp: Optional[str] = None,
    ) -> None:
        """
        Add an episode that is explicitly scoped to a single user.
        """
        user_label = self._user_node_label(user_id)
        scoped_content = f"[{user_label}] {content}"
        scoped_source = f"{source}|{user_label}"
        await self.add_episode(
            scoped_content,
            source=scoped_source,
            timestamp=timestamp,
            group_id=user_id,
        )

    async def add_user_facts(
        self,
        user_id: str,
        facts: List[str],
        source: str = "profile_sync",
        timestamp: Optional[str] = None,
    ) -> bool:
        """
        Add a batch of user-scoped facts as one episode.
        """
        if not facts:
            return False
        user_label = self._user_node_label(user_id)
        content = f"{user_label} profile facts:\n- " + "\n- ".join(facts)
        await self.add_user_episode(
            user_id=user_id,
            content=content,
            source=source,
            timestamp=timestamp,
        )
        return True

    async def search(
        self,
        query: str,
        limit: int = 10,
        group_ids: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Search the knowledge graph for relevant facts.
        """
        if not self.client:
            return []

        try:
            # Graphiti parameter name changed across versions (`limit` vs `num_results`).
            search_kwargs: Dict[str, Any] = {}
            if group_ids:
                search_kwargs["group_ids"] = group_ids

            try:
                raw_results = self.client.search(query, num_results=limit, **search_kwargs)
            except TypeError:
                raw_results = self.client.search(query, limit=limit, **search_kwargs)

            results = await self._await_if_needed(raw_results)

            formatted_results = []
            if results and hasattr(results, 'edges'):
                for edge in results.edges:
                    formatted_results.append(
                        f"{edge.source_node.name} -> {edge.relation} -> {edge.target_node.name}"
                    )
            elif isinstance(results, list):
                for item in results:
                    # Newer Graphiti search returns EntityEdge objects (no source/target names).
                    if hasattr(item, "fact") and hasattr(item, "name"):
                        relation = getattr(item, "name", "states") or "states"
                        fact = getattr(item, "fact", None)
                        if fact:
                            formatted_results.append(f"System -> {relation} -> {fact}")
                            continue
                    if (
                        hasattr(item, "source_node_uuid")
                        and hasattr(item, "target_node_uuid")
                        and hasattr(item, "name")
                    ):
                        formatted_results.append(
                            f"{item.source_node_uuid} -> {item.name} -> {item.target_node_uuid}"
                        )
                    else:
                        formatted_results.append(str(item))

            return formatted_results
        except Exception as e:
            logger.error(f"Error searching graph: {e}")
            return []

    async def search_user(self, user_id: str, query: str, limit: int = 10) -> List[str]:
        """
        Search graph facts and return only facts scoped to a specific user.

        Uses ``group_ids`` to scope the Graphiti query.  A secondary client-
        side filter removes any leaked cross-user data.  If nothing passes
        the filter, an empty list is returned (never unfiltered results).
        """
        scoped_query = f"{self._user_node_label(user_id)} {query}".strip()
        results = await self.search(scoped_query, limit=limit, group_ids=[user_id])
        filtered = [item for item in results if self._is_user_scoped_result(item, user_id)]
        return filtered[:limit]

    async def close(self):
        """Close the Neo4j driver"""
        if not self.client:
            return

        try:
            # Newer Graphiti versions expose `close()` directly on client.
            if hasattr(self.client, "close"):
                await self._await_if_needed(self.client.close())
            # Backward compatibility for older client shapes.
            elif hasattr(self.client, "graph_driver"):
                graph_driver = self.client.graph_driver
                if hasattr(graph_driver, "close"):
                    await self._await_if_needed(graph_driver.close())
                elif hasattr(graph_driver, "driver"):
                    await self._await_if_needed(graph_driver.driver.close())
            elif hasattr(self.client, "driver") and hasattr(self.client.driver, "close"):
                await self._await_if_needed(self.client.driver.close())
            logger.info("Graphiti driver closed")
        except Exception as e:
            logger.warning(f"Error closing graph driver: {e}")

# Global instance
graph_service = GraphService()

def get_graph_service() -> GraphService:
    return graph_service
