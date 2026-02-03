import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.memory_service import MemoryService

@pytest.fixture
def memory_service():
    # Reset singleton
    MemoryService._instance = None
    with patch('app.services.memory_service._import_mem0_memory') as mock_import:
        # Mock the Memory class and its instance
        mock_memory_cls = MagicMock()
        mock_memory_instance = MagicMock()
        mock_memory_cls.from_config.return_value = mock_memory_instance
        mock_import.return_value = mock_memory_cls

        service = MemoryService()
        service.memory_client = mock_memory_instance
        yield service

@pytest.mark.asyncio
async def test_add_memory(memory_service):
    # Setup
    user_id = "test_user"
    content = "test content"
    metadata = {"key": "value"}

    memory_service.memory_client.add.return_value = {"id": "mem1"}

    # Execute
    result = await memory_service.add(content, user_id, metadata)

    # Verify
    memory_service.memory_client.add.assert_called_once_with(
        content, user_id=user_id, metadata=metadata
    )
    assert result == {"id": "mem1"}

@pytest.mark.asyncio
async def test_search_memory(memory_service):
    # Setup
    user_id = "test_user"
    query = "test query"
    expected_results = [{"id": "mem1", "text": "result"}]

    memory_service.memory_client.search.return_value = expected_results

    # Execute
    results = await memory_service.search(query, user_id)

    # Verify
    memory_service.memory_client.search.assert_called_once_with(
        query, user_id=user_id, limit=5
    )
    assert results == expected_results

@pytest.mark.asyncio
async def test_get_all_memories(memory_service):
    # Setup
    user_id = "test_user"
    expected_results = [{"id": "mem1"}, {"id": "mem2"}]

    memory_service.memory_client.get_all.return_value = expected_results

    # Execute
    results = await memory_service.get_all(user_id)

    # Verify
    memory_service.memory_client.get_all.assert_called_once_with(user_id=user_id)
    assert results == expected_results

@pytest.mark.asyncio
async def test_delete_memory(memory_service):
    # Setup
    memory_id = "mem1"

    # Execute
    result = await memory_service.delete(memory_id)

    # Verify
    memory_service.memory_client.delete.assert_called_once_with(memory_id)
    assert result is True

@pytest.mark.asyncio
async def test_delete_all_memories(memory_service):
    # Setup
    user_id = "test_user"

    # Execute
    result = await memory_service.delete_all(user_id)

    # Verify
    memory_service.memory_client.delete_all.assert_called_once_with(user_id=user_id)
    assert result is True

@pytest.mark.asyncio
async def test_error_handling(memory_service):
    # Setup
    memory_service.memory_client.add.side_effect = Exception("Test error")

    # Execute
    result = await memory_service.add("content", "user")

    # Verify
    assert "error" in result
    assert result["error"] == "Test error"
