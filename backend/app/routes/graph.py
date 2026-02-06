"""
Graph API Routes

Exposes Neo4j/Graphiti knowledge graph to frontend for viewing health relationships
and facts.
"""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db import get_db
from app.models import User
from app.security import get_current_user
from app.services.graph_service import get_graph_service
from app.schemas_memory import (
    GraphDataResponse,
    GraphNode,
    GraphRelationship,
    GraphFactsResponse,
    GraphSearchRequest,
    GraphSearchResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/graph", tags=["graph"])


def _parse_graph_result_to_relationship(result: str) -> GraphRelationship:
    """
    Parse a Graphiti search result string into a GraphRelationship.
    
    Format: "Source -> relation -> Target"
    """
    try:
        if " -> " in result:
            parts = result.split(" -> ")
            if len(parts) >= 3:
                return GraphRelationship(
                    source=parts[0].strip(),
                    relation=parts[1].strip(),
                    target=parts[2].strip(),
                    properties={}
                )
        
        # Fallback: treat entire string as a single fact
        return GraphRelationship(
            source="System",
            relation="states",
            target=result.strip(),
            properties={}
        )
    except Exception:
        return GraphRelationship(
            source="Unknown",
            relation="related_to",
            target=result if isinstance(result, str) else str(result),
            properties={}
        )


@router.get("/facts", response_model=GraphFactsResponse)
async def get_user_graph_facts(
    query: str = Query("health conditions medications recommendations", description="Search query for facts"),
    limit: int = Query(20, ge=1, le=50, description="Max results"),
    current_user: User = Depends(get_current_user),
) -> GraphFactsResponse:
    """
    Get health facts/relationships from the knowledge graph for the current user.
    
    Returns structured relationships like:
    - "High LDL -> leads_to -> Cardiovascular Risk"
    - "User -> has_condition -> Diabetes"
    """
    graph_service = get_graph_service()
    
    # Check if Graphiti is available
    if graph_service.client is None:
        return GraphFactsResponse(
            facts=[],
            count=0,
            available=False,
            message="Knowledge graph service is not available"
        )
    
    try:
        # Search for user-relevant facts
        results = await graph_service.search(query=query, limit=limit)
        
        facts = []
        for result in results:
            try:
                facts.append(_parse_graph_result_to_relationship(result))
            except Exception as e:
                logger.warning(f"Failed to parse graph result: {e}")
                continue
        
        return GraphFactsResponse(
            facts=facts,
            count=len(facts),
            available=True,
            message=None
        )
        
    except Exception as e:
        logger.error(f"Error fetching graph facts for user {current_user.id}: {e}")
        return GraphFactsResponse(
            facts=[],
            count=0,
            available=True,
            message=f"Error fetching graph facts: {str(e)}"
        )


@router.post("/search", response_model=GraphSearchResponse)
async def search_graph(
    request: GraphSearchRequest,
    current_user: User = Depends(get_current_user),
) -> GraphSearchResponse:
    """
    Search the knowledge graph for relevant health information.
    
    Uses semantic search to find relationships and facts.
    """
    graph_service = get_graph_service()
    
    if graph_service.client is None:
        return GraphSearchResponse(
            results=[],
            count=0,
            available=False,
            message="Knowledge graph service is not available"
        )
    
    try:
        results = await graph_service.search(
            query=request.query,
            limit=request.limit
        )
        
        return GraphSearchResponse(
            results=results if isinstance(results, list) else [],
            count=len(results) if isinstance(results, list) else 0,
            available=True,
            message=None
        )
        
    except Exception as e:
        logger.error(f"Error searching graph for user {current_user.id}: {e}")
        return GraphSearchResponse(
            results=[],
            count=0,
            available=True,
            message=f"Error searching graph: {str(e)}"
        )


@router.get("/relationships", response_model=GraphDataResponse)
async def get_graph_visualization_data(
    query: str = Query("health metrics conditions recommendations", description="Search query"),
    limit: int = Query(30, ge=1, le=100, description="Max relationships to return"),
    current_user: User = Depends(get_current_user),
) -> GraphDataResponse:
    """
    Get graph data formatted for visualization.
    
    Returns nodes and relationships that can be rendered as an interactive graph.
    """
    graph_service = get_graph_service()
    
    if graph_service.client is None:
        return GraphDataResponse(
            nodes=[],
            relationships=[],
            total_nodes=0,
            total_relationships=0,
            available=False,
            message="Knowledge graph service is not available"
        )
    
    try:
        results = await graph_service.search(query=query, limit=limit)
        
        # Build nodes and relationships from search results
        nodes_dict = {}  # Use dict to avoid duplicates
        relationships = []
        
        for result in results:
            rel = _parse_graph_result_to_relationship(result)
            relationships.append(rel)
            
            # Add source node
            if rel.source not in nodes_dict:
                nodes_dict[rel.source] = GraphNode(
                    id=rel.source.lower().replace(" ", "_"),
                    name=rel.source,
                    type=_infer_node_type(rel.source),
                    properties={}
                )
            
            # Add target node
            if rel.target not in nodes_dict:
                nodes_dict[rel.target] = GraphNode(
                    id=rel.target.lower().replace(" ", "_"),
                    name=rel.target,
                    type=_infer_node_type(rel.target),
                    properties={}
                )
        
        nodes = list(nodes_dict.values())
        
        return GraphDataResponse(
            nodes=nodes,
            relationships=relationships,
            total_nodes=len(nodes),
            total_relationships=len(relationships),
            available=True,
            message=None
        )
        
    except Exception as e:
        logger.error(f"Error fetching graph visualization data: {e}")
        return GraphDataResponse(
            nodes=[],
            relationships=[],
            total_nodes=0,
            total_relationships=0,
            available=True,
            message=f"Error fetching graph data: {str(e)}"
        )


def _infer_node_type(node_name: str) -> str:
    """
    Infer the type of a node based on its name.
    
    Used for styling in the frontend visualization.
    """
    name_lower = node_name.lower()
    
    if any(kw in name_lower for kw in ["diabetes", "hypertension", "disease", "condition", "syndrome"]):
        return "condition"
    elif any(kw in name_lower for kw in ["cholesterol", "glucose", "ldl", "hdl", "triglyceride", "hba1c", "vitamin"]):
        return "metric"
    elif any(kw in name_lower for kw in ["medication", "drug", "metformin", "statin"]):
        return "medication"
    elif any(kw in name_lower for kw in ["recommend", "risk", "alert", "warning"]):
        return "recommendation"
    elif any(kw in name_lower for kw in ["user", "patient"]):
        return "user"
    else:
        return "entity"
