"""
Assistant API Endpoints
AI Health Assistant chat interface
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import Optional
from datetime import datetime

from app.db import get_db
from app.security import get_current_user
from app.models import User, ChatMessage
from app.schemas import AssistantChatRequest, AssistantChatResponse, Citation
from app.services.assistant_service import AssistantService

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post("/chat", response_model=AssistantChatResponse)
async def chat_with_assistant(
    request: AssistantChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Chat with AI Health Assistant
    
    Assistant provides grounded responses based ONLY on user's own health data:
    - Recent observations
    - Health index and factor contributions
    - Uploaded reports and extracted values
    - Abnormal values and trends
    
    Args:
        request: Chat message and optional session_id
    
    Returns:
        Assistant response with citations
    """
    assistant_service = AssistantService(db)
    
    try:
        response_content, citations, session_id, message_id = await assistant_service.chat(
            user_id=current_user.id,
            message=request.message,
            session_id=request.session_id
        )
        
        # Get the message created_at
        msg_result = await db.execute(
            select(ChatMessage).where(ChatMessage.id == message_id)
        )
        msg = msg_result.scalars().first()
        
        return AssistantChatResponse(
            session_id=session_id,
            message_id=message_id,
            content=response_content,
            citations=citations,
            created_at=msg.created_at if msg else datetime.utcnow()
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.get("/sessions/{session_id}")
async def get_session_history(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get chat history for a session
    
    Returns all messages in chronological order
    """
    assistant_service = AssistantService(db)
    
    try:
        messages = await assistant_service.get_session_history(session_id, current_user.id)

        return {
            "session_id": session_id,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat()
                }
                for msg in messages
            ]
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
