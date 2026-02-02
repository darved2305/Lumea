"""
RAG Service - ChromaDB vector store for medical document retrieval

Handles document embedding, storage, and semantic search for user health data.
Uses shared collection with user_id metadata filtering.
"""
import uuid
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.settings import settings
from app.models import Report, Observation, User

logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG (Retrieval-Augmented Generation) Service.
    
    Uses ChromaDB for vector storage with sentence-transformers embeddings.
    Single collection with user_id metadata for per-user filtering.
    """
    
    COLLECTION_NAME = "health_documents"
    
    def __init__(self):
        self._client = None
        self._collection = None
        self._embedding_model = None
    
    def _get_client(self):
        """Lazy initialization of ChromaDB client."""
        if self._client is None:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            
            self._client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
        return self._client
    
    def _get_collection(self):
        """Get or create the health documents collection."""
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
        return self._collection
    
    def _get_embedding_model(self):
        """Lazy initialization of embedding model."""
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer
            self._embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        return self._embedding_model
    
    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed texts using sentence-transformers."""
        model = self._get_embedding_model()
        embeddings = model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    async def sync_user_reports(self, user_id: uuid.UUID, db: AsyncSession) -> int:
        """
        Sync user's reports from PostgreSQL to ChromaDB.
        
        Extracts raw_text from reports and stores as embedded chunks.
        Returns number of documents added.
        """
        # Fetch reports with raw_text
        result = await db.execute(
            select(Report).where(
                Report.user_id == user_id,
                Report.raw_text.isnot(None),
                Report.raw_text != ""
            )
        )
        reports = result.scalars().all()
        
        if not reports:
            logger.info(f"No reports with text found for user {user_id}")
            return 0
        
        documents = []
        metadatas = []
        ids = []
        
        for report in reports:
            # Split report into chunks (simple paragraph-based for now)
            chunks = self._split_text(report.raw_text, max_length=1000)
            
            for i, chunk in enumerate(chunks):
                doc_id = f"report_{report.id}_chunk_{i}"
                documents.append(chunk)
                metadatas.append({
                    "user_id": str(user_id),
                    "source_type": "report",
                    "report_id": str(report.id),
                    "filename": report.filename,
                    "report_date": report.report_date.isoformat() if report.report_date else None,
                    "chunk_index": i,
                    "indexed_at": datetime.utcnow().isoformat()
                })
                ids.append(doc_id)
        
        if documents:
            # Embed and store
            embeddings = await asyncio.to_thread(self._embed_texts, documents)
            collection = self._get_collection()
            
            # Upsert to handle re-syncing
            await asyncio.to_thread(
                collection.upsert,
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            
            logger.info(f"Synced {len(documents)} chunks from {len(reports)} reports for user {user_id}")
        
        return len(documents)
    
    async def sync_user_observations(self, user_id: uuid.UUID, db: AsyncSession) -> int:
        """
        Sync user's observations to ChromaDB as natural language summaries.
        """
        result = await db.execute(
            select(Observation).where(Observation.user_id == user_id)
        )
        observations = result.scalars().all()
        
        if not observations:
            return 0
        
        # Group observations by metric for cleaner documents
        metrics_summary = {}
        for obs in observations:
            key = obs.metric_name
            if key not in metrics_summary:
                metrics_summary[key] = []
            
            summary = (
                f"{obs.display_name or obs.metric_name}: {obs.value} {obs.unit} "
                f"on {obs.observed_at.strftime('%Y-%m-%d')}"
            )
            if obs.is_abnormal:
                summary += f" (ABNORMAL - {obs.flag})"
            if obs.reference_min and obs.reference_max:
                summary += f" [Reference: {obs.reference_min}-{obs.reference_max}]"
            
            metrics_summary[key].append(summary)
        
        documents = []
        metadatas = []
        ids = []
        
        for metric_name, summaries in metrics_summary.items():
            doc = f"Lab results for {metric_name}:\n" + "\n".join(summaries)
            doc_id = f"observations_{user_id}_{metric_name}"
            
            documents.append(doc)
            metadatas.append({
                "user_id": str(user_id),
                "source_type": "observations",
                "metric_name": metric_name,
                "indexed_at": datetime.utcnow().isoformat()
            })
            ids.append(doc_id)
        
        if documents:
            embeddings = await asyncio.to_thread(self._embed_texts, documents)
            collection = self._get_collection()
            
            await asyncio.to_thread(
                collection.upsert,
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            
            logger.info(f"Synced {len(documents)} observation summaries for user {user_id}")
        
        return len(documents)
    
    async def query(
        self,
        user_id: uuid.UUID,
        query: str,
        k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Query the vector store for relevant documents.
        
        Args:
            user_id: User ID to filter by
            query: Search query
            k: Number of results (default from settings)
            
        Returns:
            List of matching documents with metadata
        """
        if k is None:
            k = settings.RAG_TOP_K
        
        collection = self._get_collection()
        
        # Embed the query
        query_embedding = await asyncio.to_thread(
            lambda: self._embed_texts([query])[0]
        )
        
        # Search with user_id filter
        results = await asyncio.to_thread(
            collection.query,
            query_embeddings=[query_embedding],
            n_results=k,
            where={"user_id": str(user_id)},
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results
        documents = []
        if results and results.get("documents") and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                documents.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    "distance": results["distances"][0][i] if results.get("distances") else None
                })
        
        return documents
    
    async def get_user_context(
        self,
        user_id: uuid.UUID,
        query: str,
        db: Optional[AsyncSession] = None
    ) -> str:
        """
        Get formatted context for the LLM based on user's query.
        
        Combines RAG results with a formatted context string.
        """
        # First, ensure user data is synced (if db provided)
        if db:
            await self.sync_user_reports(user_id, db)
            await self.sync_user_observations(user_id, db)
        
        # Query for relevant documents
        docs = await self.query(user_id, query)
        
        if not docs:
            return "No health data available for this user yet."
        
        # Format context
        context_parts = []
        for doc in docs:
            source = doc["metadata"].get("source_type", "unknown")
            if source == "report":
                filename = doc["metadata"].get("filename", "Unknown report")
                context_parts.append(f"From report '{filename}':\n{doc['content']}")
            elif source == "observations":
                context_parts.append(doc["content"])
            else:
                context_parts.append(doc["content"])
        
        return "\n\n---\n\n".join(context_parts)
    
    async def add_test_document(self, user_id: uuid.UUID) -> str:
        """
        Add a test document for verification purposes.
        Returns the document ID.
        """
        test_doc = """
LABORATORY REPORT - Test Patient
Date: 2024-01-15

COMPLETE BLOOD COUNT (CBC):
- Hemoglobin: 14.2 g/dL (Normal: 12.0-16.0)
- White Blood Cells: 7,500 /μL (Normal: 4,000-11,000)
- Platelets: 250,000 /μL (Normal: 150,000-400,000)

METABOLIC PANEL:
- Glucose (Fasting): 95 mg/dL (Normal: 70-100)
- HbA1c: 5.4% (Normal: <5.7%)
- Total Cholesterol: 185 mg/dL (Desirable: <200)
- LDL Cholesterol: 110 mg/dL (Optimal: <100)
- HDL Cholesterol: 55 mg/dL (Good: >40)
- Triglycerides: 120 mg/dL (Normal: <150)

THYROID FUNCTION:
- TSH: 2.1 mIU/L (Normal: 0.4-4.0)

VITAMIN LEVELS:
- Vitamin D: 35 ng/mL (Sufficient: 30-100)
- Vitamin B12: 450 pg/mL (Normal: 200-900)

Overall health status appears good with all values within normal ranges.
LDL cholesterol is slightly above optimal - consider dietary modifications.
"""
        
        doc_id = f"test_doc_{user_id}_{datetime.utcnow().timestamp()}"
        
        embeddings = await asyncio.to_thread(
            self._embed_texts, [test_doc]
        )
        
        collection = self._get_collection()
        await asyncio.to_thread(
            collection.add,
            ids=[doc_id],
            embeddings=embeddings,
            documents=[test_doc],
            metadatas=[{
                "user_id": str(user_id),
                "source_type": "test",
                "indexed_at": datetime.utcnow().isoformat()
            }]
        )
        
        logger.info(f"Added test document {doc_id} for user {user_id}")
        return doc_id
    
    def _split_text(self, text: str, max_length: int = 1000) -> List[str]:
        """Split text into chunks, trying to preserve paragraph boundaries."""
        if not text:
            return []
        
        # Split by double newlines (paragraphs)
        paragraphs = text.split("\n\n")
        
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            if len(current_chunk) + len(para) + 2 <= max_length:
                current_chunk += ("\n\n" if current_chunk else "") + para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                
                # If single paragraph is too long, split by sentences
                if len(para) > max_length:
                    sentences = para.replace(". ", ".|").split("|")
                    current_chunk = ""
                    for sent in sentences:
                        if len(current_chunk) + len(sent) + 1 <= max_length:
                            current_chunk += (" " if current_chunk else "") + sent
                        else:
                            if current_chunk:
                                chunks.append(current_chunk)
                            current_chunk = sent
                else:
                    current_chunk = para
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    async def delete_user_documents(self, user_id: uuid.UUID) -> int:
        """Delete all documents for a user. Returns count deleted."""
        collection = self._get_collection()
        
        # Get all document IDs for this user
        results = await asyncio.to_thread(
            collection.get,
            where={"user_id": str(user_id)},
            include=[]
        )
        
        if results and results.get("ids"):
            await asyncio.to_thread(
                collection.delete,
                ids=results["ids"]
            )
            return len(results["ids"])
        
        return 0


# Singleton instance
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Get the RAG service singleton."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
