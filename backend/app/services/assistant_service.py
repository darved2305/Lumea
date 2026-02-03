"""
Assistant Service - AI Health Assistant with Memory, Graph, and RAG
"""
import uuid
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models import User, Report, Observation, HealthMetric, ChatSession, ChatMessage
from app.schemas import Citation
from app.services.memory_service import get_memory_service
from app.services.graph_service import get_graph_service
from app.services.rag_service import get_rag_service
from app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)

class AssistantService:
    """
    AI Health Assistant Service

    Integrates:
    1. Mem0: Long-term memory for user preferences and facts
    2. Graphiti: Knowledge graph for medical reasoning and temporal facts
    3. RAG: Retrieval from uploaded reports and observations
    4. LLM: Generative response (Ollama MedGemma / Gemini)
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.memory_service = get_memory_service()
        self.graph_service = get_graph_service()
        self.rag_service = get_rag_service()
        self.llm_service = get_llm_service()

    async def chat(
        self,
        user_id: uuid.UUID,
        message: str,
        session_id: Optional[uuid.UUID] = None
    ) -> Tuple[str, List[Citation], uuid.UUID, uuid.UUID]:
        """
        Process chat message and generate response using full context.
        """
        # 1. Get or create session
        if session_id:
            result = await self.db.execute(
                select(ChatSession).where(
                    ChatSession.id == session_id,
                    ChatSession.user_id == user_id
                )
            )
            session = result.scalar_one_or_none()
            if not session:
                raise ValueError("Session not found")
            session.last_active_at = datetime.utcnow()
        else:
            session = ChatSession(
                user_id=user_id,
                created_at=datetime.utcnow(),
                last_active_at=datetime.utcnow()
            )
            self.db.add(session)
            await self.db.commit()
            await self.db.refresh(session)
            session_id = session.id

        # 2. Save user message
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=message,
            created_at=datetime.utcnow()
        )
        self.db.add(user_msg)
        await self.db.commit()

        # 3. Parallel Retrieval Phase
        # We gather context from RAG, Memory, and Graph
        rag_context, memory_context, graph_context = await self._gather_context(user_id, message)

        # 4. Context Assembly
        full_context = self._assemble_context(
            rag_context=rag_context,
            memory_context=memory_context,
            graph_context=graph_context
        )

        # 5. LLM Generation
        # Get chat history for continuity
        history = await self.get_session_history(session_id, user_id)
        chat_history_dicts = [{"role": m.role, "content": m.content} for m in history[:-1]] # exclude current msg which is already in prompt logic potentially

        response_content = await self.llm_service.generate(
            user_message=message,
            context=full_context,
            chat_history=chat_history_dicts
        )

        # 6. Post-processing & Storage
        # Update Memory & Graph with new interaction
        await self._update_memory_and_graph(user_id, message, response_content)

        # Extract citations (placeholder logic, usually LLM would provide them structured)
        citations = self._extract_citations(rag_context)

        # Save assistant message
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=response_content,
            message_metadata={
                "citations": [c.dict() for c in citations],
                "rag_sources": len(rag_context),
                "memories_used": len(memory_context),
                "graph_facts_used": len(graph_context)
            },
            created_at=datetime.utcnow()
        )
        self.db.add(assistant_msg)
        await self.db.commit()
        await self.db.refresh(assistant_msg)

        return response_content, citations, session_id, assistant_msg.id

    async def _gather_context(self, user_id: uuid.UUID, query: str) -> Tuple[str, List[Dict], List[str]]:
        """
        Retrieve context from all sources.
        Returns: (rag_text, memories, graph_facts)
        """
        # A. RAG Retrieval (Documents & Observations)
        # Note: get_user_context returns a formatted string, we might want raw docs too if we want citations
        # For now, we'll use the service's high-level method for the text, and query again if we need citation metadata
        rag_text = await self.rag_service.get_user_context(user_id, query, self.db)

        # B. Memory Retrieval (User facts/prefs)
        memories = await self.memory_service.search(query, user_id=str(user_id), limit=5)

        # C. Graph Retrieval (Medical knowledge/relationships)
        graph_facts = await self.graph_service.search(query, limit=5)

        return rag_text, memories, graph_facts

    def _assemble_context(self, rag_context: str, memory_context: List[Dict], graph_context: List[str]) -> str:
        """Combine all context sources into a structured string for the LLM."""
        parts = []

        # 1. User Memories (Preferences, facts)
        if memory_context:
            parts.append("--- RELEVANT MEMORIES (User Facts & Preferences) ---")
            for m in memory_context:
                if isinstance(m, str):
                    text = m
                elif isinstance(m, dict):
                    text = (
                        m.get("memory")
                        or m.get("text")
                        or m.get("content")
                        or m.get("value")
                        or ""
                    )
                else:
                    text = str(m)

                text = (text or "").strip()
                if text:
                    parts.append(f"- {text}")

        # 2. Knowledge Graph (Medical connections)
        if graph_context:
            parts.append("\n--- MEDICAL KNOWLEDGE GRAPH (Relationships & Facts) ---")
            for f in graph_context:
                parts.append(f"- {f}")

        # 3. RAG Data (Reports & Lab Results)
        if rag_context:
            parts.append("\n--- MEDICAL DATA & REPORTS ---")
            parts.append(rag_context)

        return "\n".join(parts)

    async def _update_memory_and_graph(self, user_id: uuid.UUID, user_msg: str, assistant_msg: str):
        """
        Background task to update long-term memory and knowledge graph.
        """
        try:
            # Add to Mem0 (unstructured memory)
            # We add the interaction. Mem0 extracts relevant facts automatically.
            await self.memory_service.add(
                f"User: {user_msg}\nAssistant: {assistant_msg}",
                user_id=str(user_id),
                metadata={"source": "chat"}
            )

            # Add to Graphiti (structured episodes)
            await self.graph_service.add_episode(
                f"User asked: {user_msg}\nAssistant answered: {assistant_msg}",
                source="user_chat"
            )
        except Exception as e:
            logger.error(f"Error updating memory/graph: {e}")

    def _extract_citations(self, rag_context_str: str) -> List[Citation]:
        """
        Attempt to reconstruct citations from the RAG context string.
        This is a simplification. Ideally, we pass the raw RAG docs through.
        """
        # Since we only have the string from `get_user_context`, we can't easily rebuild
        # precise Citation objects without parsing or changing RAGService to return structured data.
        # For MVP, we return empty citations or generic ones if we detect report content.
        citations = []
        if "From report" in rag_context_str:
            # Minimal dummy citation to indicate source usage
            citations.append(Citation(
                report_id=None,
                metric_name="General",
                value="Referenced Report",
                excerpt="See context for details"
            ))
        return citations

    async def get_session_history(
        self, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> List[ChatMessage]:
        """Get chat history for a session (scoped to the user)."""
        # Enforce session ownership to prevent leaking chat history across users.
        session_result = await self.db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
            )
        )
        session = session_result.scalar_one_or_none()
        if not session:
            raise ValueError("Session not found")

        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        )
        return result.scalars().all()
