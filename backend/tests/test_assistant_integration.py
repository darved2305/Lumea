import pytest
import uuid
from unittest.mock import MagicMock, patch, AsyncMock
from typing import List, Dict, Any
from app.services.assistant_service import AssistantService
from app.models import ChatSession, ChatMessage
from app.schemas import Citation

# Mock the entire database session
@pytest.fixture
def mock_db():
    session = MagicMock() # Use MagicMock as base for sync methods

    # Async methods need to be AsyncMock
    session.execute = AsyncMock()
    session.commit = AsyncMock()

    # Sync methods
    session.add = MagicMock()

    # Configure refresh to set ID if missing
    async def side_effect_refresh(obj, attribute_names=None, with_for_update=None):
        if not hasattr(obj, 'id') or obj.id is None:
            obj.id = uuid.uuid4()
        return None

    session.refresh = AsyncMock(side_effect=side_effect_refresh)

    return session

@pytest.fixture
def assistant_service(mock_db):
    # Patch all get_service functions
    with patch('app.services.assistant_service.get_memory_service') as mock_mem, \
         patch('app.services.assistant_service.get_graph_service') as mock_graph, \
         patch('app.services.assistant_service.get_rag_service') as mock_rag, \
         patch('app.services.assistant_service.get_llm_service') as mock_llm:

        # Setup service mocks
        mem_service = MagicMock()
        # IMPORTANT: Set return_value for AsyncMocks so they return data, not Mocks
        mem_service.search = AsyncMock(return_value=[{"memory": "User has diabetes"}])
        mem_service.add = AsyncMock(return_value=None)
        mock_mem.return_value = mem_service

        graph_service = MagicMock()
        graph_service.search = AsyncMock(return_value=["HbA1c -> indicates -> Diabetes"])
        graph_service.add_episode = AsyncMock(return_value=None)
        mock_graph.return_value = graph_service

        rag_service = MagicMock()
        rag_service.get_user_context = AsyncMock(return_value="Latest HbA1c: 7.2%")
        mock_rag.return_value = rag_service

        llm_service = MagicMock()
        llm_service.generate = AsyncMock(return_value="Your HbA1c is 7.2%.")
        mock_llm.return_value = llm_service

        service = AssistantService(mock_db)
        yield service

@pytest.mark.asyncio
async def test_chat_new_session(assistant_service, mock_db):
    # Setup inputs
    user_id = uuid.uuid4()
    message = "What is my HbA1c?"

    # Patch get_session_history to avoid DB queries for history in new session
    # (Since new session has no history, but the check for it involves DB calls)
    with patch.object(assistant_service, 'get_session_history', new_callable=AsyncMock) as mock_get_history:
        mock_get_history.return_value = []

        # Execute
        response, citations, session_id, message_id = await assistant_service.chat(
            user_id=user_id,
            message=message
        )

    # Verify Database interactions
    # Should have created a session
    assert mock_db.add.call_count >= 3 # Session, UserMsg, AsstMsg
    assert mock_db.commit.call_count >= 3

    # Verify Output
    assert response == "Your HbA1c is 7.2%."
    assert isinstance(session_id, uuid.UUID)

@pytest.mark.asyncio
async def test_chat_existing_session(assistant_service, mock_db):
    # Setup inputs
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    message = "Follow up question"

    # Setup DB Mock for get_session_history
    # 1. First execute call: Check session exists
    # 2. Second execute call: Get messages
    # We can use side_effect on execute to return different results

    mock_session_result = MagicMock()
    mock_session_result.scalar_one_or_none.return_value = ChatSession(id=session_id, user_id=user_id)

    mock_history_result = MagicMock()
    mock_history_result.scalars.return_value.all.return_value = [
        ChatMessage(role="user", content="prev"),
        ChatMessage(role="assistant", content="prev_resp")
    ]
    # Note: scalar_one_or_none is called on first result, scalars().all() on second.
    # To simplify, we can make one mock that handles both OR use side_effect

    # Let's use patch.object on get_session_history again to isolate 'chat' logic
    # This avoids testing 'get_session_history' logic inside 'test_chat'
    # We should have a separate test for get_session_history if needed

    with patch.object(assistant_service, 'get_session_history', new_callable=AsyncMock) as mock_get_history:
        mock_get_history.return_value = [
            ChatMessage(role="user", content="prev"),
            ChatMessage(role="assistant", content="prev_resp")
        ]

        # We also need to mock the session lookup at start of chat() for existing session
        # session = result.scalar_one_or_none()
        mock_session_lookup = MagicMock()
        mock_session_lookup.scalar_one_or_none.return_value = ChatSession(id=session_id, user_id=user_id)
        mock_db.execute.return_value = mock_session_lookup

        await assistant_service.chat(user_id, message, session_id)

        # Verify session was reused (not added)
        # Check add calls - none should be ChatSession
        added_sessions = [
            args[0] for args in mock_db.add.call_args_list
            if isinstance(args[0], ChatSession)
        ]
        assert len(added_sessions) == 0

@pytest.mark.asyncio
async def test_context_assembly(assistant_service):
    # Test private method _assemble_context
    rag = "RAG Data"
    memories = [{"memory": "User fact 1"}, {"content": "User fact 2"}]
    graph = ["Fact A", "Fact B"]

    context = assistant_service._assemble_context(rag, memories, graph)

    assert "User fact 1" in context
    assert "User fact 2" in context
    assert "Fact A" in context
    assert "Fact B" in context
    assert "RAG Data" in context
    assert "--- RELEVANT MEMORIES" in context
    assert "--- MEDICAL KNOWLEDGE GRAPH" in context

@pytest.mark.asyncio
async def test_citation_extraction(assistant_service):
    # Test _extract_citations
    rag_text = "Some info. From report: Lab Results 2024. More info."
    citations = assistant_service._extract_citations(rag_text)

    assert len(citations) == 1
    assert citations[0].value == "Referenced Report"
