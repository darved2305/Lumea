"""
Tests for Memory API Routes

Tests the /api/memory endpoints for CRUD operations on user memories.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock


class TestMemoryRoutes:
    """Test suite for memory API routes."""
    
    @pytest.fixture
    def mock_memory_service(self):
        """Create a mock memory service."""
        mock_service = MagicMock()
        mock_service.is_available = True
        mock_service.get_all = AsyncMock(return_value=[
            {"id": "mem-1", "memory": "User prefers vegetarian diet", "created_at": None, "metadata": {}},
            {"id": "mem-2", "memory": "User exercises in the morning", "created_at": None, "metadata": {}},
        ])
        mock_service.search = AsyncMock(return_value=[
            {"id": "mem-1", "memory": "User prefers vegetarian diet", "created_at": None, "metadata": {}},
        ])
        mock_service.add = AsyncMock(return_value={"id": "mem-new", "memory": "New preference"})
        mock_service.delete = AsyncMock(return_value=True)
        mock_service.delete_all = AsyncMock(return_value=True)
        return mock_service

    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        user = MagicMock()
        user.id = "test-user-123"
        return user

    @pytest.mark.asyncio
    async def test_get_user_memories_success(self, mock_memory_service, mock_user):
        """Test successful retrieval of user memories."""
        with patch('app.routes.memory.get_memory_service', return_value=mock_memory_service):
            from app.routes.memory import get_user_memories
            
            result = await get_user_memories(current_user=mock_user)
            
            assert result.available is True
            assert result.total_count == 2
            assert len(result.facts) == 2
            mock_memory_service.get_all.assert_called_once_with(user_id="test-user-123")

    @pytest.mark.asyncio
    async def test_get_user_memories_service_unavailable(self, mock_user):
        """Test handling when memory service is unavailable."""
        mock_service = MagicMock()
        mock_service.is_available = False
        
        with patch('app.routes.memory.get_memory_service', return_value=mock_service):
            from app.routes.memory import get_user_memories
            
            result = await get_user_memories(current_user=mock_user)
            
            assert result.available is False
            assert result.total_count == 0
            assert len(result.facts) == 0
            assert "not available" in result.message.lower()

    @pytest.mark.asyncio
    async def test_search_memories_success(self, mock_memory_service, mock_user):
        """Test successful memory search."""
        with patch('app.routes.memory.get_memory_service', return_value=mock_memory_service):
            from app.routes.memory import search_memories
            from app.schemas_memory import MemorySearchRequest
            
            request = MemorySearchRequest(query="diet", limit=5)
            result = await search_memories(request=request, current_user=mock_user)
            
            assert result.available is True
            assert result.total_count == 1
            mock_memory_service.search.assert_called_once_with(
                query="diet",
                user_id="test-user-123",
                limit=5
            )

    @pytest.mark.asyncio
    async def test_create_memory_success(self, mock_memory_service, mock_user):
        """Test successful memory creation."""
        with patch('app.routes.memory.get_memory_service', return_value=mock_memory_service):
            from app.routes.memory import create_memory
            from app.schemas_memory import MemoryCreateRequest
            
            request = MemoryCreateRequest(content="I prefer low sodium diet")
            result = await create_memory(request=request, current_user=mock_user)
            
            assert result.success is True
            mock_memory_service.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_memory_success(self, mock_memory_service, mock_user):
        """Test successful memory deletion."""
        with patch('app.routes.memory.get_memory_service', return_value=mock_memory_service):
            from app.routes.memory import delete_memory
            
            result = await delete_memory(memory_id="mem-1", current_user=mock_user)
            
            assert result.success is True
            assert result.deleted_count == 1
            mock_memory_service.delete.assert_called_once_with("mem-1")

    @pytest.mark.asyncio
    async def test_delete_all_memories_success(self, mock_memory_service, mock_user):
        """Test successful deletion of all memories."""
        with patch('app.routes.memory.get_memory_service', return_value=mock_memory_service):
            from app.routes.memory import delete_all_memories
            
            result = await delete_all_memories(current_user=mock_user)
            
            assert result.success is True
            mock_memory_service.delete_all.assert_called_once_with(user_id="test-user-123")

    @pytest.mark.asyncio
    async def test_memory_error_handling(self, mock_user):
        """Test error handling in memory routes."""
        mock_service = MagicMock()
        mock_service.is_available = True
        mock_service.get_all = AsyncMock(side_effect=Exception("Database error"))
        
        with patch('app.routes.memory.get_memory_service', return_value=mock_service):
            from app.routes.memory import get_user_memories
            
            result = await get_user_memories(current_user=mock_user)
            
            # Should return empty list with error message, not raise
            assert result.total_count == 0
            assert "error" in result.message.lower()
