"""
Graph API Routes

Exposes Neo4j/Graphiti knowledge graph to frontend for viewing health relationships
and facts.
"""
import logging
import re
from fastapi import APIRouter, Depends, Query
from app.models import User
from app.security import get_current_user
from app.services.graph_service import get_graph_service
from app.services.llm_service import LLMService
from app.schemas_memory import (
    GraphDataResponse,
    GraphNode,
    GraphRelationship,
    GraphFactsResponse,
    GraphSearchRequest,
    GraphSearchResponse,
    InsightType,
    InsightRequest,
    InsightResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/graph", tags=["graph"])


def _normalize_node_id(name: str) -> str:
    return re.sub(r"\s+", "_", name.strip().lower())


def _sanitize_user_label(value: str) -> str:
    # Hide internal user scoping labels from API consumers.
    return re.sub(r"User_[0-9a-fA-F-]{36}", "You", value)


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
                    source=_sanitize_user_label(parts[0].strip()),
                    relation=parts[1].strip(),
                    target=_sanitize_user_label(parts[2].strip()),
                    properties={}
                )
        
        # Fallback: treat entire string as a single fact
        return GraphRelationship(
            source="System",
            relation="states",
            target=_sanitize_user_label(result.strip()),
            properties={}
        )
    except Exception:
        return GraphRelationship(
            source="Unknown",
            relation="related_to",
            target=_sanitize_user_label(result if isinstance(result, str) else str(result)),
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
        results = await graph_service.search_user(
            user_id=str(current_user.id),
            query=query,
            limit=limit,
        )
        
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
        results = await graph_service.search_user(
            user_id=str(current_user.id),
            query=request.query,
            limit=request.limit
        )
        
        return GraphSearchResponse(
            results=[_sanitize_user_label(item) for item in results] if isinstance(results, list) else [],
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
        results = await graph_service.search_user(
            user_id=str(current_user.id),
            query=query,
            limit=limit,
        )
        
        # Build nodes and relationships from search results
        nodes_dict = {}  # Use dict to avoid duplicates
        relationships = []
        
        for result in results:
            rel = _parse_graph_result_to_relationship(result)
            relationships.append(rel)
            
            # Add source node
            if rel.source not in nodes_dict:
                nodes_dict[rel.source] = GraphNode(
                    id=_normalize_node_id(rel.source),
                    name=rel.source,
                    type=_infer_node_type(rel.source),
                    properties={}
                )
            
            # Add target node
            if rel.target not in nodes_dict:
                nodes_dict[rel.target] = GraphNode(
                    id=_normalize_node_id(rel.target),
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


# ============================================================================
# INSIGHT PROMPTS
# ============================================================================

INSIGHT_PROMPTS = {
    InsightType.TEMPORAL: """You are a health data analyst. Analyze these health facts and describe how the user's metrics have changed over time.

**Health Data:**
{facts}

**Instructions:**
- Identify any temporal trends (improving, worsening, stable)
- Highlight significant changes between readings
- Note dates/timestamps when available
- Be clear and concise (2-3 paragraphs max)
- If no temporal data is available, say so clearly""",

    InsightType.RELATIONSHIPS: """You are a health data analyst. Explain the connections between conditions, medications, and health factors in this user's data.

**Health Data:**
{facts}

**Instructions:**
- Identify how conditions relate to each other
- Explain medication-condition relationships
- Highlight any lifestyle factors and their connections
- Keep explanations patient-friendly (2-3 paragraphs max)
- If relationships are unclear, note what additional data would help""",

    InsightType.CONTRADICTIONS: """You are a health data analyst. Look for any data conflicts or inconsistencies in this user's health information.

**Health Data:**
{facts}

**Instructions:**
- Identify any values that seem inconsistent with each other
- Note any concerning changes between readings
- Flag potential data entry errors
- Be specific but non-alarming (2-3 paragraphs max)
- If no contradictions are found, say "No obvious data conflicts detected" """,
}

INSIGHT_QUERIES = {
    InsightType.TEMPORAL: "health metrics changes values dates time readings results",
    InsightType.RELATIONSHIPS: "conditions medications relationships interactions causes effects",
    InsightType.CONTRADICTIONS: "health values changes abnormal conflicts inconsistent readings",
}


# Singleton LLM service for insights
_llm_service: LLMService | None = None


def _get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


@router.post("/insights", response_model=InsightResponse)
async def generate_graph_insight(
    request: InsightRequest,
    current_user: User = Depends(get_current_user),
) -> InsightResponse:
    """
    Generate LLM-powered insights from the user's knowledge graph.
    
    Queries Graphiti for relevant facts, then uses LLM to generate
    human-readable analysis based on the insight type:
    - temporal: Timeline and trend analysis
    - relationships: Health factor connections
    - contradictions: Data inconsistencies
    """
    graph_service = get_graph_service()
    llm_service = _get_llm_service()
    
    # Check if Graphiti is available
    if graph_service.client is None:
        return InsightResponse(
            insight_type=request.insight_type,
            content="",
            sources=[],
            available=False,
            message="Knowledge graph service is not available"
        )
    
    try:
        # 1. Get relevant facts from the graph
        query = INSIGHT_QUERIES.get(request.insight_type, "health data")
        facts = await graph_service.search_user(
            user_id=str(current_user.id),
            query=query,
            limit=request.context_limit,
        )
        
        if not facts:
            return InsightResponse(
                insight_type=request.insight_type,
                content="No health data found in your knowledge graph yet. Upload reports or sync your profile to build your health graph.",
                sources=[],
                available=True,
                message=None
            )
        
        # 2. Sanitize user labels from facts
        sanitized_facts = [_sanitize_user_label(f) for f in facts]
        facts_text = "\n".join(f"• {fact}" for fact in sanitized_facts)
        
        # 3. Build prompt and generate insight
        prompt_template = INSIGHT_PROMPTS.get(request.insight_type)
        if not prompt_template:
            return InsightResponse(
                insight_type=request.insight_type,
                content="Unknown insight type",
                sources=[],
                available=True,
                message="Invalid insight type"
            )
        
        prompt = prompt_template.format(facts=facts_text)
        
        # 4. Generate insight using LLM
        insight_content = await llm_service.generate(
            user_message=prompt,
            context="",  # Context is already in the prompt
            chat_history=None,
        )
        
        return InsightResponse(
            insight_type=request.insight_type,
            content=insight_content,
            sources=sanitized_facts,
            available=True,
            message=None
        )
        
    except Exception as e:
        logger.error(f"Error generating insight for user {current_user.id}: {e}")
        return InsightResponse(
            insight_type=request.insight_type,
            content="",
            sources=[],
            available=True,
            message=f"Error generating insight: {str(e)}"
        )
