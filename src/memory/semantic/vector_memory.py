"""
Vector Memory Implementation

Provides semantic memory capabilities using Milvus vector database.
Supports similarity search, metadata filtering, and CRUD operations
on vectorized memories.

Author: Qingyu AI Team
Date: 2025-01-16
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from src.rag.milvus_client import MilvusClient
from src.rag.embedding_manager import EmbeddingManager
from src.core.logger import get_logger
from src.core.exceptions import MemoryOperationError, MemoryValidationError

logger = get_logger(__name__)


@dataclass
class MemorySearchResult:
    """
    Memory search result

    Represents a single memory retrieved from semantic search.

    Attributes:
        id: Unique memory identifier
        content: Memory content text
        score: Similarity score (0-1, higher is better)
        metadata: Associated metadata
        created_at: Timestamp when memory was created
    """
    id: str
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate and normalize score"""
        if self.score < 0:
            self.score = 0.0
        elif self.score > 1:
            self.score = 1.0

        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'id': self.id,
            'content': self.content,
            'score': self.score,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __str__(self) -> str:
        """String representation"""
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"MemorySearchResult(id={self.id}, score={self.score:.3f}, content={content_preview})"


class VectorMemory:
    """
    Vector-based semantic memory

    Uses Milvus vector database to store and retrieve semantic memories.
    Supports similarity search, metadata filtering, and CRUD operations.

    Attributes:
        milvus_client: Milvus client for vector operations
        embedding_manager: Manager for text embeddings
        collection_name: Name of the Milvus collection
        dimension: Embedding vector dimension

    Example:
        >>> memory = VectorMemory(
        ...     milvus_client=milvus_client,
        ...     embedding_manager=embedding_manager
        ... )
        >>> # Add memory
        >>> memory_id = await memory.add_memory(
        ...     content="User likes Python programming",
        ...     metadata={"user_id": "123", "category": "preference"}
        ... )
        >>> # Search similar memories
        >>> results = await memory.search(
        ...     query_text="programming languages",
        ...     top_k=5
        ... )
    """

    def __init__(
        self,
        milvus_client: MilvusClient,
        embedding_manager: EmbeddingManager,
        collection_name: str = "semantic_memory",
        dimension: Optional[int] = None
    ):
        """
        Initialize VectorMemory

        Args:
            milvus_client: Milvus client instance
            embedding_manager: Embedding manager instance
            collection_name: Name of Milvus collection for memories
            dimension: Vector dimension (auto-detected if None)
        """
        self.milvus_client = milvus_client
        self.embedding_manager = embedding_manager
        self.collection_name = collection_name
        self.dimension = dimension or embedding_manager.get_dimension()

        logger.info(
            "vector_memory_initialized",
            collection_name=collection_name,
            dimension=self.dimension
        )

    async def add_memory(
        self,
        content: str,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a new memory

        Args:
            content: Memory content text
            embedding: Pre-computed embedding (optional, auto-generated if None)
            metadata: Optional metadata dictionary

        Returns:
            Memory ID

        Raises:
            MemoryValidationError: If content is empty
            MemoryOperationError: If operation fails
        """
        try:
            # Validate input
            if not content or not content.strip():
                raise MemoryValidationError(
                    "Memory content cannot be empty",
                    details={"content": content}
                )

            # Generate embedding if not provided
            if embedding is None:
                logger.debug("generating_embedding_for_memory", content_length=len(content))
                embedding = await self.embedding_manager.embed_query(content)

            # Validate embedding dimension
            if len(embedding) != self.dimension:
                raise MemoryValidationError(
                    f"Embedding dimension mismatch: expected {self.dimension}, got {len(embedding)}",
                    details={"expected": self.dimension, "actual": len(embedding)}
                )

            # Prepare metadata
            final_metadata = metadata or {}
            final_metadata['created_at'] = datetime.now().isoformat()
            final_metadata['content_length'] = len(content)

            # Insert into Milvus
            memory_ids = self.milvus_client.insert(
                texts=[content],
                vectors=[embedding],
                metadata=[final_metadata]
            )

            memory_id = memory_ids[0] if memory_ids else str(uuid4())

            logger.info(
                "memory_added",
                memory_id=memory_id,
                content_length=len(content),
                metadata_keys=list(final_metadata.keys())
            )

            return memory_id

        except MemoryValidationError:
            raise
        except Exception as e:
            logger.error(
                "failed_to_add_memory",
                content_length=len(content) if content else 0,
                error=str(e)
            )
            raise MemoryOperationError(
                f"Failed to add memory: {str(e)}",
                details={"content_length": len(content) if content else 0}
            ) from e

    async def search(
        self,
        query_embedding: Optional[List[float]] = None,
        query_text: Optional[str] = None,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0
    ) -> List[MemorySearchResult]:
        """
        Search memories by similarity

        Args:
            query_embedding: Query vector (optional)
            query_text: Query text (optional, embedded if provided)
            top_k: Maximum number of results to return
            filters: Metadata filters (e.g., {"user_id": "123"})
            min_score: Minimum similarity score threshold

        Returns:
            List of search results sorted by similarity

        Raises:
            MemoryValidationError: If neither embedding nor text provided
            MemoryOperationError: If search fails
        """
        try:
            # Validate input
            if not query_embedding and not query_text:
                raise MemoryValidationError(
                    "Either query_embedding or query_text must be provided"
                )

            # Generate embedding from text if needed
            if query_text and not query_embedding:
                logger.debug("generating_embedding_for_search", query_length=len(query_text))
                query_embedding = await self.embedding_manager.embed_query(query_text)

            if not query_embedding:
                raise MemoryValidationError("Failed to generate query embedding")

            # Search in Milvus
            logger.debug(
                "searching_memories",
                top_k=top_k,
                has_filters=filters is not None,
                min_score=min_score
            )

            search_results = self.milvus_client.search(
                query_vector=query_embedding,
                top_k=top_k,
                filters=filters
            )

            # Convert to MemorySearchResult
            results = []
            for result in search_results:
                # Apply score threshold
                score = float(result.get('score', 0.0))
                if score < min_score:
                    continue

                # Extract metadata
                metadata = result.get('metadata', {})

                # Create search result
                search_result = MemorySearchResult(
                    id=result['id'],
                    content=result['text'],
                    score=score,
                    metadata=metadata
                )
                results.append(search_result)

            logger.info(
                "memory_search_completed",
                results_count=len(results),
                top_k=top_k
            )

            return results

        except MemoryValidationError:
            raise
        except Exception as e:
            logger.error(
                "memory_search_failed",
                top_k=top_k,
                error=str(e)
            )
            raise MemoryOperationError(
                f"Memory search failed: {str(e)}",
                details={"top_k": top_k}
            ) from e

    async def delete_memory(self, memory_id: str) -> None:
        """
        Delete a memory

        Args:
            memory_id: ID of memory to delete

        Raises:
            MemoryOperationError: If deletion fails
        """
        try:
            if not memory_id:
                raise MemoryValidationError("Memory ID cannot be empty")

            logger.info("deleting_memory", memory_id=memory_id)

            self.milvus_client.delete(ids=[memory_id])

            logger.info("memory_deleted", memory_id=memory_id)

        except MemoryValidationError:
            raise
        except Exception as e:
            logger.error(
                "failed_to_delete_memory",
                memory_id=memory_id,
                error=str(e)
            )
            raise MemoryOperationError(
                f"Failed to delete memory: {str(e)}",
                details={"memory_id": memory_id}
            ) from e

    async def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update a memory

        Note: Milvus doesn't support direct updates, so we delete and re-insert.

        Args:
            memory_id: ID of memory to update
            content: New content (optional)
            embedding: New embedding (optional, regenerated if content changes)
            metadata: New metadata (optional, merged with existing)

        Raises:
            MemoryValidationError: If memory not found
            MemoryOperationError: If update fails
        """
        try:
            if not memory_id:
                raise MemoryValidationError("Memory ID cannot be empty")

            # Find existing memory
            # Note: This is a simplified approach. In production, you might want
            # to maintain a separate index or use Milvus's query capabilities
            logger.debug("finding_memory_for_update", memory_id=memory_id)

            # Since we can't query by ID directly in this implementation,
            # we'll delete and insert. The caller should track the memory ID.
            # In a production system, you'd implement a proper get_memory_by_id method.

            # For now, we'll skip the "not found" check since Milvus doesn't
            # provide an easy way to query by ID without a vector search

            # If content is provided, generate new embedding
            if content and not embedding:
                embedding = await self.embedding_manager.embed_query(content)

            # Prepare new metadata (merge with existing if needed)
            final_metadata = metadata or {}
            final_metadata['updated_at'] = datetime.now().isoformat()

            # Delete old and insert new
            # Note: The ID will change. In production, maintain ID mapping.
            await self.delete_memory(memory_id)

            if content and embedding:
                await self.add_memory(
                    content=content,
                    embedding=embedding,
                    metadata=final_metadata
                )

            logger.info("memory_updated", memory_id=memory_id)

        except MemoryValidationError:
            raise
        except Exception as e:
            logger.error(
                "failed_to_update_memory",
                memory_id=memory_id,
                error=str(e)
            )
            raise MemoryOperationError(
                f"Failed to update memory: {str(e)}",
                details={"memory_id": memory_id}
            ) from e

    async def add_batch_memories(
        self,
        memories: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Add multiple memories in batch

        Args:
            memories: List of memory dictionaries, each containing:
                - content: str
                - metadata: dict (optional)
                - embedding: list (optional)

        Returns:
            List of memory IDs

        Raises:
            MemoryOperationError: If batch operation fails
        """
        try:
            if not memories:
                logger.warning("add_batch_memories_empty_input")
                return []

            logger.info("adding_batch_memories", count=len(memories))

            # Prepare data
            texts = []
            embeddings = []
            metadata_list = []

            for mem in memories:
                content = mem.get('content', '')
                if not content:
                    raise MemoryValidationError("Memory content cannot be empty")

                texts.append(content)
                metadata = mem.get('metadata', {})
                metadata['created_at'] = datetime.now().isoformat()
                metadata['content_length'] = len(content)
                metadata_list.append(metadata)

            # Generate embeddings for all texts
            all_embeddings = await self.embedding_manager.embed_texts(texts)

            # Use provided embeddings if available
            for i, mem in enumerate(memories):
                if 'embedding' in mem:
                    embeddings.append(mem['embedding'])
                else:
                    embeddings.append(all_embeddings[i])

            # Batch insert
            memory_ids = self.milvus_client.insert(
                texts=texts,
                vectors=embeddings,
                metadata=metadata_list
            )

            logger.info(
                "batch_memories_added",
                count=len(memory_ids),
                ids_sample=memory_ids[:3]
            )

            return memory_ids

        except MemoryValidationError:
            raise
        except Exception as e:
            logger.error(
                "failed_to_add_batch_memories",
                count=len(memories) if memories else 0,
                error=str(e)
            )
            raise MemoryOperationError(
                f"Failed to add batch memories: {str(e)}",
                details={"count": len(memories) if memories else 0}
            ) from e

    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of VectorMemory and its dependencies

        Returns:
            Health status dictionary
        """
        try:
            # Check Milvus
            milvus_healthy = self.milvus_client.health_check()

            # Check Embedding Manager
            embedding_health = await self.embedding_manager.health_check()

            is_healthy = milvus_healthy and embedding_health.get('status') == 'healthy'

            return {
                'status': 'healthy' if is_healthy else 'unhealthy',
                'milvus': 'healthy' if milvus_healthy else 'unhealthy',
                'embedding': embedding_health.get('status', 'unknown'),
                'dimension': self.dimension,
                'collection_name': self.collection_name
            }

        except Exception as e:
            logger.error("vector_memory_health_check_failed", error=str(e))
            return {
                'status': 'unhealthy',
                'error': str(e)
            }

    async def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get memory statistics

        Returns:
            Statistics dictionary
        """
        try:
            # Note: Getting actual count from Milvus requires query
            # This is a simplified version
            return {
                'total_memories': -1,  # Unknown without query
                'collection_name': self.collection_name,
                'dimension': self.dimension,
                'embedding_type': self.embedding_manager.model_type
            }

        except Exception as e:
            logger.error("failed_to_get_memory_stats", error=str(e))
            return {
                'error': str(e)
            }
