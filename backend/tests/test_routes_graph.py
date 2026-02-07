"""
Tests for Graph API Routes

Tests the /api/graph endpoints for knowledge graph queries.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock


class TestGraphRoutes:
    """Test suite for graph API routes."""
    
    @pytest.fixture
    def mock_graph_service(self):
        """Create a mock graph service."""
        mock_service = MagicMock()
        mock_service.client = MagicMock()  # Service is available
        mock_service.search_user = AsyncMock(return_value=[
            "High LDL -> leads_to -> Cardiovascular Risk",
            "Diabetes -> requires -> Blood Sugar Monitoring",
            "Exercise -> improves -> Cardiovascular Health",
        ])
        return mock_service

    @pytest.fixture
    def mock_graph_service_unavailable(self):
        """Create a mock graph service that's unavailable."""
        mock_service = MagicMock()
        mock_service.client = None  # Service unavailable
        return mock_service

    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        user = MagicMock()
        user.id = "test-user-123"
        return user

    @pytest.mark.asyncio
    async def test_get_user_graph_facts_success(self, mock_graph_service, mock_user):
        """Test successful retrieval of graph facts."""
        with patch('app.routes.graph.get_graph_service', return_value=mock_graph_service):
            from app.routes.graph import get_user_graph_facts
            
            result = await get_user_graph_facts(
                query="health conditions",
                limit=20,
                current_user=mock_user
            )
            
            assert result.available is True
            assert result.count == 3
            assert len(result.facts) == 3
            mock_graph_service.search_user.assert_called_once_with(
                user_id="test-user-123",
                query="health conditions",
                limit=20,
            )

    @pytest.mark.asyncio
    async def test_get_user_graph_facts_unavailable(self, mock_graph_service_unavailable, mock_user):
        """Test handling when graph service is unavailable."""
        with patch('app.routes.graph.get_graph_service', return_value=mock_graph_service_unavailable):
            from app.routes.graph import get_user_graph_facts
            
            result = await get_user_graph_facts(
                query="health",
                limit=20,
                current_user=mock_user
            )
            
            assert result.available is False
            assert result.count == 0
            assert len(result.facts) == 0
            assert "not available" in result.message.lower()

    @pytest.mark.asyncio
    async def test_search_graph_success(self, mock_graph_service, mock_user):
        """Test successful graph search."""
        with patch('app.routes.graph.get_graph_service', return_value=mock_graph_service):
            from app.routes.graph import search_graph
            from app.schemas_memory import GraphSearchRequest
            
            request = GraphSearchRequest(query="cardiovascular", limit=10)
            result = await search_graph(request=request, current_user=mock_user)
            
            assert result.available is True
            assert result.count == 3
            mock_graph_service.search_user.assert_called_once_with(
                user_id="test-user-123",
                query="cardiovascular",
                limit=10
            )

    @pytest.mark.asyncio
    async def test_get_graph_visualization_data_success(self, mock_graph_service, mock_user):
        """Test successful retrieval of graph visualization data."""
        with patch('app.routes.graph.get_graph_service', return_value=mock_graph_service):
            from app.routes.graph import get_graph_visualization_data
            
            result = await get_graph_visualization_data(
                query="health",
                limit=30,
                current_user=mock_user
            )
            
            assert result.available is True
            assert result.total_relationships == 3
            assert result.total_nodes > 0  # Should have created nodes from relationships
            assert len(result.nodes) > 0
            assert len(result.relationships) == 3

    @pytest.mark.asyncio
    async def test_relationship_parsing(self, mock_graph_service, mock_user):
        """Test that relationships are correctly parsed from search results."""
        with patch('app.routes.graph.get_graph_service', return_value=mock_graph_service):
            from app.routes.graph import get_user_graph_facts
            
            result = await get_user_graph_facts(
                query="test",
                limit=10,
                current_user=mock_user
            )
            
            # Check first relationship is parsed correctly
            rel = result.facts[0]
            assert rel.source == "High LDL"
            assert rel.relation == "leads_to"
            assert rel.target == "Cardiovascular Risk"

    @pytest.mark.asyncio
    async def test_graph_error_handling(self, mock_user):
        """Test error handling in graph routes."""
        mock_service = MagicMock()
        mock_service.client = MagicMock()  # Service available
        mock_service.search_user = AsyncMock(side_effect=Exception("Neo4j connection error"))
        
        with patch('app.routes.graph.get_graph_service', return_value=mock_service):
            from app.routes.graph import get_user_graph_facts
            
            result = await get_user_graph_facts(
                query="test",
                limit=10,
                current_user=mock_user
            )
            
            # Should return empty list with error message, not raise
            assert result.count == 0
            assert "error" in result.message.lower()

    @pytest.mark.asyncio
    async def test_node_type_inference(self, mock_graph_service, mock_user):
        """Test that node types are correctly inferred."""
        with patch('app.routes.graph.get_graph_service', return_value=mock_graph_service):
            from app.routes.graph import get_graph_visualization_data
            
            result = await get_graph_visualization_data(
                query="test",
                limit=10,
                current_user=mock_user
            )
            
            # Check that nodes have types
            node_types = {node.type for node in result.nodes}
            # Should have at least some type variety
            assert len(node_types) >= 1
