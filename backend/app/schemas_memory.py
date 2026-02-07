"""
Memory and Graph API Schemas

Pydantic models for memory (Mem0) and knowledge graph (Neo4j/Graphiti) endpoints.
"""
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID


# ============================================================================
# MEMORY (Mem0) SCHEMAS
# ============================================================================

class MemoryFact(BaseModel):
    """Single memory item from Mem0."""
    id: str = Field(..., description="Unique memory ID")
    memory: str = Field(..., description="The stored memory/fact text")
    created_at: Optional[datetime] = Field(None, description="When the memory was created")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    model_config = ConfigDict(from_attributes=True)


class MemoryListResponse(BaseModel):
    """Response containing list of user memories."""
    facts: List[MemoryFact] = Field(default_factory=list, description="List of memory facts")
    total_count: int = Field(0, description="Total number of memories")
    available: bool = Field(True, description="Whether Mem0 service is available")
    message: Optional[str] = Field(None, description="Optional status message")


class MemoryCreateRequest(BaseModel):
    """Request to create a new memory."""
    content: str = Field(..., min_length=1, max_length=5000, description="Memory content to store")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional metadata")


class MemoryCreateResponse(BaseModel):
    """Response after creating a memory."""
    success: bool = Field(..., description="Whether creation succeeded")
    id: Optional[str] = Field(None, description="ID of created memory")
    message: Optional[str] = Field(None, description="Status message")


class MemoryDeleteResponse(BaseModel):
    """Response after deleting memory/memories."""
    success: bool = Field(..., description="Whether deletion succeeded")
    deleted_count: int = Field(0, description="Number of memories deleted")
    message: Optional[str] = Field(None, description="Status message")


class MemorySearchRequest(BaseModel):
    """Request to search memories."""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    limit: int = Field(5, ge=1, le=20, description="Max results to return")


# ============================================================================
# KNOWLEDGE GRAPH (Neo4j/Graphiti) SCHEMAS
# ============================================================================

class GraphNode(BaseModel):
    """A node in the knowledge graph."""
    id: str = Field(..., description="Node identifier")
    name: str = Field(..., description="Node name/label")
    type: str = Field("entity", description="Node type (condition, metric, recommendation, etc.)")
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Node properties")


class GraphRelationship(BaseModel):
    """A relationship/edge in the knowledge graph."""
    source: str = Field(..., description="Source node name")
    relation: str = Field(..., description="Relationship type")
    target: str = Field(..., description="Target node name")
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Relationship properties")


class GraphDataResponse(BaseModel):
    """Full graph data for visualization."""
    nodes: List[GraphNode] = Field(default_factory=list, description="Graph nodes")
    relationships: List[GraphRelationship] = Field(default_factory=list, description="Graph edges")
    total_nodes: int = Field(0, description="Total node count")
    total_relationships: int = Field(0, description="Total relationship count")
    available: bool = Field(True, description="Whether graph service is available")
    message: Optional[str] = Field(None, description="Optional status message")


class GraphSearchRequest(BaseModel):
    """Request to search the knowledge graph."""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    limit: int = Field(10, ge=1, le=50, description="Max results to return")


class GraphSearchResponse(BaseModel):
    """Response from graph search."""
    results: List[str] = Field(default_factory=list, description="Search results as formatted strings")
    count: int = Field(0, description="Number of results")
    available: bool = Field(True, description="Whether graph service is available")
    message: Optional[str] = Field(None, description="Optional status message")


class GraphFactsResponse(BaseModel):
    """User's health facts from the knowledge graph."""
    facts: List[GraphRelationship] = Field(default_factory=list, description="Health relationships/facts")
    count: int = Field(0, description="Number of facts")
    available: bool = Field(True, description="Whether graph service is available")
    message: Optional[str] = Field(None, description="Optional status message")


# ============================================================================
# GRAPH INSIGHTS (LLM-powered analysis) SCHEMAS
# ============================================================================

from enum import Enum


class InsightType(str, Enum):
    """Types of AI-powered graph insights."""
    TEMPORAL = "temporal"           # Timeline analysis - trends over time
    RELATIONSHIPS = "relationships"  # Health connections - conditions/meds/factors
    CONTRADICTIONS = "contradictions"  # Data conflicts - inconsistencies


class InsightRequest(BaseModel):
    """Request for LLM-powered graph insight."""
    insight_type: InsightType = Field(..., description="Type of insight to generate")
    context_limit: int = Field(default=10, ge=1, le=20, description="Max graph facts to use as context")


class InsightResponse(BaseModel):
    """Response containing LLM-generated insight."""
    insight_type: InsightType = Field(..., description="Type of insight generated")
    content: str = Field(..., description="LLM-generated insight text")
    sources: List[str] = Field(default_factory=list, description="Graph facts used as context")
    available: bool = Field(True, description="Whether service is available")
    message: Optional[str] = Field(None, description="Optional status/error message")
