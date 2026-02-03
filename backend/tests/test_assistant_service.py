"""
AssistantService unit tests (v2).

Tests the orchestration between Memory, Graph, RAG, and LLM services.
Uses mocks to avoid needing actual Neo4j/Chroma/Ollama instances.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
from datetime import datetime

from app.services.assistant_service import AssistantService
from app.models import ChatSession, ChatMessage

@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock()

    # Mock execute/scalars/one_or_none pattern
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None  # Default: no session found
    result_mock.scalars.return_value.all.return_value = [] # Default: empty history
    session.execute.return_value = result_mock

    # AsyncSession.add is synchronous
    session.add = MagicMock()

    # AsyncSession.refresh is async
    # We need it to assign an ID to the object if it doesn't have one
    async def side_effect_refresh(obj, attribute_names=None, with_for_update=None):
        if not hasattr(obj, 'id') or obj.id is None:
            obj.id = uuid.uuid4()
        return None

    session.refresh = AsyncMock(side_effect=side_effect_refresh)

    return session

@pytest.fixture
def mock_services():
    """Mock all dependent services."""
    with patch("app.services.assistant_service.get_memory_service") as mock_mem, \
         patch("app.services.assistant_service.get_graph_service") as mock_graph, \
         patch("app.services.assistant_service.get_rag_service") as mock_rag, \
         patch("app.services.assistant_service.get_llm_service") as mock_llm:

        # Setup Memory Service mocks
        mem_svc = AsyncMock()
        mem_svc.search.return_value = [{"memory": "User likes concise answers"}]
        mock_mem.return_value = mem_svc

        # Setup Graph Service mocks
        graph_svc = AsyncMock()
        graph_svc.search.return_value = ["Diabetes relates to High Glucose"]
        mock_graph.return_value = graph_svc

        # Setup RAG Service mocks
        rag_svc = AsyncMock()
        rag_svc.get_user_context.return_value = "From report: Glucose 105 mg/dL"
        mock_rag.return_value = rag_svc

        # Setup LLM Service mocks
        llm_svc = AsyncMock()
        llm_svc.generate.return_value = "Based on your glucose of 105..."
        mock_llm.return_value = llm_svc

        yield {
            "memory": mem_svc,
            "graph": graph_svc,
            "rag": rag_svc,
            "llm": llm_svc
        }

@pytest.mark.asyncio
async def test_chat_creates_new_session(mock_db_session, mock_services):
    """Test that chat creates a new session if none provided."""
    service = AssistantService(mock_db_session)
    user_id = uuid.uuid4()
    message = "Hello doctor"

    response, citations, session_id, msg_id = await service.chat(user_id, message)

    # Verify session creation
    assert mock_db_session.add.call_count >= 3  # Session, UserMsg, AsstMsg
    # Verify we got a UUID back
    assert isinstance(session_id, uuid.UUID)
    assert response == "Based on your glucose of 105..."

@pytest.mark.asyncio
async def test_chat_uses_all_contexts(mock_db_session, mock_services):
    """Test that the service gathers context from all 3 sources and passes to LLM."""
    service = AssistantService(mock_db_session)
    user_id = uuid.uuid4()
    message = "Analyze my bloodwork"

    await service.chat(user_id, message)

    # 1. Verify RAG called
    mock_services["rag"].get_user_context.assert_called_once()

    # 2. Verify Memory Search called
    mock_services["memory"].search.assert_called_once_with(message, user_id=str(user_id), limit=5)

    # 3. Verify Graph Search called
    mock_services["graph"].search.assert_called_once_with(message, limit=5)

    # 4. Verify LLM called with combined context
    call_args = mock_services["llm"].generate.call_args
    assert call_args is not None
    _, kwargs = call_args

    context_sent = kwargs["context"]
    assert "User likes concise answers" in context_sent  # From Memory
    assert "Diabetes relates to High Glucose" in context_sent  # From Graph
    assert "From report: Glucose 105 mg/dL" in context_sent  # From RAG

@pytest.mark.asyncio
async def test_chat_updates_memory_and_graph(mock_db_session, mock_services):
    """Test that the conversation is saved back to Memory and Graph."""
    service = AssistantService(mock_db_session)
    user_id = uuid.uuid4()
    message = "I feel tired"

    await service.chat(user_id, message)

    # Verify Memory Update
    mock_services["memory"].add.assert_called_once()
    args, _ = mock_services["memory"].add.call_args
    content = args[0]
    assert "User: I feel tired" in content
    assert "Assistant: Based on" in content

    # Verify Graph Update
    mock_services["graph"].add_episode.assert_called_once()
    args, _ = mock_services["graph"].add_episode.call_args
    assert "User asked: I feel tired" in args[0]
