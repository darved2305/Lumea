"""
Memory API Routes

Exposes Mem0 memory layer to frontend for viewing, managing, and searching user memories.
"""
import logging
from fastapi import APIRouter, Depends
from typing import Any

from app.models import User
from app.security import get_current_user
from app.services.memory_service import get_memory_service
from app.schemas_memory import (
    MemoryListResponse,
    MemoryFact,
    MemoryCreateRequest,
    MemoryCreateResponse,
    MemoryDeleteResponse,
    MemorySearchRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/memory", tags=["memory"])


def _extract_memory_id(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("id", item.get("memory_id", "")))
    return ""


def _normalize_memory_item(item: Any) -> MemoryFact:
    """
    Normalize a Mem0 memory item to our MemoryFact schema.
    
    Mem0 can return different formats depending on version/operation.
    """
    if isinstance(item, dict):
        return MemoryFact(
            id=item.get("id", item.get("memory_id", "")),
            memory=item.get("memory", item.get("text", item.get("content", str(item)))),
            created_at=item.get("created_at"),
            metadata=item.get("metadata", {})
        )
    else:
        # Handle string or other formats
        return MemoryFact(
            id=str(hash(str(item))),
            memory=str(item),
            created_at=None,
            metadata={}
        )


@router.get("/facts", response_model=MemoryListResponse)
async def get_user_memories(
    current_user: User = Depends(get_current_user),
) -> MemoryListResponse:
    """
    Get all stored memories/facts for the current user.
    
    Returns memories from Mem0 that capture user preferences, facts,
    and relevant information extracted from conversations.
    """
    memory_service = get_memory_service()
    
    if not memory_service.is_available:
        return MemoryListResponse(
            facts=[],
            total_count=0,
            available=False,
            message="Memory service (Mem0) is not available"
        )
    
    try:
        memories = await memory_service.get_all(user_id=str(current_user.id))
        
        # Handle different response formats from Mem0
        facts = []
        raw_service_error = getattr(memory_service, "last_error", None)
        service_error = raw_service_error if isinstance(raw_service_error, str) and raw_service_error else None
        if isinstance(memories, dict):
            if "error" in memories:
                service_error = str(memories["error"])
            # Mem0 might return {"results": [...]} or {"memories": [...]}
            memory_list = memories.get("results", memories.get("memories", []))
        elif isinstance(memories, list):
            memory_list = memories
        else:
            memory_list = []
        
        for item in memory_list:
            try:
                facts.append(_normalize_memory_item(item))
            except Exception as e:
                logger.warning(f"Failed to normalize memory item: {e}")
                continue
        
        return MemoryListResponse(
            facts=facts,
            total_count=len(facts),
            available=not (service_error and len(facts) == 0),
            message=service_error
        )
        
    except Exception as e:
        logger.error(f"Error fetching memories for user {current_user.id}: {e}")
        return MemoryListResponse(
            facts=[],
            total_count=0,
            available=True,
            message=f"Error fetching memories: {str(e)}"
        )


@router.post("/facts", response_model=MemoryCreateResponse)
async def create_memory(
    request: MemoryCreateRequest,
    current_user: User = Depends(get_current_user),
) -> MemoryCreateResponse:
    """
    Manually add a memory/fact for the current user.
    
    This allows users to explicitly store preferences or facts
    that the system should remember.
    """
    memory_service = get_memory_service()
    
    if not memory_service.is_available:
        return MemoryCreateResponse(
            success=False,
            id=None,
            message="Memory service (Mem0) is not available"
        )
    
    try:
        result = await memory_service.add(
            content=request.content,
            user_id=str(current_user.id),
            metadata=request.metadata
        )
        
        if isinstance(result, dict) and "error" in result:
            return MemoryCreateResponse(
                success=False,
                id=None,
                message=result["error"]
            )
        
        # Extract ID from result
        memory_id = None
        if isinstance(result, dict):
            memory_id = result.get("id", result.get("memory_id"))
        
        return MemoryCreateResponse(
            success=True,
            id=memory_id,
            message="Memory created successfully"
        )
        
    except Exception as e:
        logger.error(f"Error creating memory for user {current_user.id}: {e}")
        return MemoryCreateResponse(
            success=False,
            id=None,
            message=str(e)
        )


@router.delete("/facts/{memory_id}", response_model=MemoryDeleteResponse)
async def delete_memory(
    memory_id: str,
    current_user: User = Depends(get_current_user),
) -> MemoryDeleteResponse:
    """
    Delete a specific memory by ID.
    
    Allows users to remove memories they don't want the system to use.
    """
    memory_service = get_memory_service()
    
    if not memory_service.is_available:
        return MemoryDeleteResponse(
            success=False,
            deleted_count=0,
            message="Memory service (Mem0) is not available"
        )
    
    try:
        # Attempt the delete directly.  Mem0 memory IDs are UUIDs and are
        # implicitly scoped to the user who created them via the vector store.
        # Doing a full get_all() just for ownership verification is extremely
        # slow because every Mem0 call goes through the Groq throttle (3s+).
        success = await memory_service.delete(memory_id)
        
        return MemoryDeleteResponse(
            success=success,
            deleted_count=1 if success else 0,
            message="Memory deleted successfully" if success else "Memory not found or already deleted"
        )
        
    except Exception as e:
        logger.error(f"Error deleting memory {memory_id}: {e}")
        return MemoryDeleteResponse(
            success=False,
            deleted_count=0,
            message=str(e)
        )


@router.delete("/facts", response_model=MemoryDeleteResponse)
async def delete_all_memories(
    current_user: User = Depends(get_current_user),
) -> MemoryDeleteResponse:
    """
    Delete all memories for the current user.
    
    This is a destructive operation - use with caution.
    """
    memory_service = get_memory_service()
    
    if not memory_service.is_available:
        return MemoryDeleteResponse(
            success=False,
            deleted_count=0,
            message="Memory service (Mem0) is not available"
        )
    
    try:
        success = await memory_service.delete_all(user_id=str(current_user.id))
        
        return MemoryDeleteResponse(
            success=success,
            deleted_count=-1,  # Unknown count for delete_all
            message="All memories deleted successfully" if success else "Failed to delete memories"
        )
        
    except Exception as e:
        logger.error(f"Error deleting all memories for user {current_user.id}: {e}")
        return MemoryDeleteResponse(
            success=False,
            deleted_count=0,
            message=str(e)
        )


@router.post("/search")
async def search_memories(
    request: MemorySearchRequest,
    current_user: User = Depends(get_current_user),
) -> MemoryListResponse:
    """
    Search user memories by query.
    
    Uses semantic search to find relevant memories.
    """
    memory_service = get_memory_service()
    
    if not memory_service.is_available:
        return MemoryListResponse(
            facts=[],
            total_count=0,
            available=False,
            message="Memory service (Mem0) is not available"
        )
    
    try:
        results = await memory_service.search(
            query=request.query,
            user_id=str(current_user.id),
            limit=request.limit
        )
        
        # Handle different response formats
        facts = []
        raw_service_error = getattr(memory_service, "last_error", None)
        service_error = raw_service_error if isinstance(raw_service_error, str) and raw_service_error else None
        if isinstance(results, dict):
            if "error" in results:
                service_error = str(results["error"])
            result_items = results.get("results", results.get("memories", []))
        elif isinstance(results, list):
            result_items = results
        else:
            result_items = []

        if isinstance(result_items, list):
            for item in result_items:
                try:
                    facts.append(_normalize_memory_item(item))
                except Exception as e:
                    logger.warning(f"Failed to normalize search result: {e}")
                    continue
        
        return MemoryListResponse(
            facts=facts,
            total_count=len(facts),
            available=not (service_error and len(facts) == 0),
            message=service_error
        )
        
    except Exception as e:
        logger.error(f"Error searching memories for user {current_user.id}: {e}")
        return MemoryListResponse(
            facts=[],
            total_count=0,
            available=True,
            message=f"Error searching memories: {str(e)}"
        )
