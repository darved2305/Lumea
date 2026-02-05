import logging
import asyncio
from typing import List, Dict, Any, Optional

try:
    from graphiti_core import Graphiti
    from graphiti_core.llm_client import OpenAIClient, LLMConfig
    GRAPHITI_AVAILABLE = True
except ImportError:
    GRAPHITI_AVAILABLE = False
    Graphiti = None
    OpenAIClient = None
    LLMConfig = None

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
            logger.info("Initializing Graphiti with Neo4j and Ollama...")

            # 1. Initialize LLM Client (Ollama via OpenAI compatible endpoint)
            llm_config = LLMConfig(
                api_key="ollama",  # Dummy key for Ollama
                base_url=f"{settings.OLLAMA_BASE_URL}/v1",
                model=settings.OLLAMA_MODEL,
                temperature=0.1,
                max_tokens=4096
            )

            llm_client = OpenAIClient(
                config=llm_config
            )

            # 2. Initialize Graphiti Client with Neo4j connection
            # Pass uri, user, password directly - Graphiti creates the driver internally
            self.client = Graphiti(
                uri=settings.NEO4J_URI,
                user=settings.NEO4J_USER,
                password=settings.NEO4J_PASSWORD,
                llm_client=llm_client
            )

            # Build indices (this is an async operation)
            await self.client.build_indices_and_constraints()

            logger.info("Graphiti initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize GraphService: {e}")
            # Service will be degraded (graph features won't work)
            self.client = None

    async def add_episode(self, content: str, source: str = "user_input", timestamp: Optional[str] = None):
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

        def _sync_add():
            self.client.add_episode(
                name=f"Episode from {source}",
                episode_body=content,
                source_description=source,
                reference_time=timestamp
            )

        try:
            await asyncio.to_thread(_sync_add)
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

    async def search(self, query: str, limit: int = 10) -> List[str]:
        """
        Search the knowledge graph for relevant facts.
        """
        if not self.client:
            return []

        def _sync_search():
            # Graphiti search returns SearchResult objects
            results = self.client.search(query, limit=limit)

            # Format results into strings
            formatted_results = []
            if results and hasattr(results, 'edges'):
                for edge in results.edges:
                    formatted_results.append(
                        f"{edge.source_node.name} -> {edge.relation} -> {edge.target_node.name}"
                    )
            elif isinstance(results, list):
                # Handle case where it might return a list directly
                for item in results:
                    formatted_results.append(str(item))

            return formatted_results

        try:
            return await asyncio.to_thread(_sync_search)
        except Exception as e:
            logger.error(f"Error searching graph: {e}")
            return []

    async def close(self):
        """Close the Neo4j driver"""
        # Graphiti driver doesn't explicitly expose close, but we can try
        if self.client and self.client.graph_driver:
            try:
                if hasattr(self.client.graph_driver, 'close'):
                    await asyncio.to_thread(self.client.graph_driver.close)
                elif hasattr(self.client.graph_driver, 'driver'):
                     await asyncio.to_thread(self.client.graph_driver.driver.close)
                logger.info("Graphiti driver closed")
            except Exception as e:
                logger.warning(f"Error closing graph driver: {e}")

# Global instance
graph_service = GraphService()

def get_graph_service() -> GraphService:
    return graph_service
