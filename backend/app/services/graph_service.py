import logging
import asyncio
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase
try:
    from graphiti_core import Graphiti as GraphitiClient
except ImportError:
    try:
        from graphiti_core import GraphitiClient
    except ImportError:
        GraphitiClient = None
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
        if GraphitiClient is None:
            logger.warning("GraphitiClient not available, graph features disabled")
            return
            
        if self.client is not None:
            return

        def _sync_init():
            try:
                # 1. Initialize Neo4j Driver
                self.driver = GraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
                )

                # Verify connection
                self.driver.verify_connectivity()
                logger.info("Neo4j connection verified successfully")

                # 2. Initialize Graphiti Client
                # Graphiti uses the Neo4j driver and an LLM for extraction
                # We'll use Ollama as the LLM provider via the client configuration
                self.client = GraphitiClient(
                    driver=self.driver,
                    llm_config={
                        "provider": "ollama",
                        "config": {
                            "model": settings.OLLAMA_MODEL,
                            "base_url": settings.OLLAMA_BASE_URL,
                            "timeout": settings.OLLAMA_TIMEOUT,
                        }
                    },
                    schema_config={
                        "database": settings.GRAPHITI_DATABASE
                    }
                )

                # Initialize indices and constraints
                self.client.build_indices()
                logger.info("Graphiti client initialized successfully")

            except Exception as e:
                logger.error(f"Failed to initialize GraphService: {e}")
                # Don't raise here to prevent app crash, but log heavily
                # Service will be degraded (graph features won't work)

        await asyncio.to_thread(_sync_init)

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
                text=content,
                source=source,
                timestamp=timestamp
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
            results = self.client.search(query, limit=limit)
            return results

        try:
            return await asyncio.to_thread(_sync_search)
        except Exception as e:
            logger.error(f"Error searching graph: {e}")
            return []

    async def close(self):
        """Close the Neo4j driver"""
        if self.driver:
            await asyncio.to_thread(self.driver.close)
            logger.info("Neo4j driver closed")

# Global instance
graph_service = GraphService()

def get_graph_service() -> GraphService:
    return graph_service
