"""
Vector Memory Usage Example

This example demonstrates how to use the VectorMemory class
for semantic memory operations with Milvus.

Author: Qingyu AI Team
Date: 2025-01-16
"""

import asyncio
from src.memory.semantic.vector_memory import VectorMemory
from src.rag.milvus_client import MilvusClient
from src.rag.embedding_manager import EmbeddingManager


async def main():
    """Demonstrate VectorMemory usage"""

    # Initialize dependencies
    milvus_client = MilvusClient()
    milvus_client.connect()

    embedding_manager = EmbeddingManager()

    # Create VectorMemory instance
    memory = VectorMemory(
        milvus_client=milvus_client,
        embedding_manager=embedding_manager,
        collection_name="demo_memory"
    )

    print("=== Vector Memory Demo ===\n")

    # 1. Add memories
    print("1. Adding memories...")
    memory_id_1 = await memory.add_memory(
        content="User enjoys reading science fiction novels",
        metadata={"category": "preference", "user_id": "user123"}
    )
    print(f"   Added memory: {memory_id_1}")

    memory_id_2 = await memory.add_memory(
        content="User is learning Python programming",
        metadata={"category": "activity", "user_id": "user123"}
    )
    print(f"   Added memory: {memory_id_2}")

    memory_id_3 = await memory.add_memory(
        content="User likes listening to jazz music",
        metadata={"category": "preference", "user_id": "user123"}
    )
    print(f"   Added memory: {memory_id_3}")

    # 2. Search by text
    print("\n2. Searching for 'programming'...")
    results = await memory.search(
        query_text="What programming languages does the user know?",
        top_k=3
    )
    print(f"   Found {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"   [{i}] Score: {result.score:.3f}")
        print(f"       Content: {result.content}")
        print(f"       Metadata: {result.metadata}")
        print()

    # 3. Search with filters
    print("3. Searching with filters (category=preference)...")
    results = await memory.search(
        query_text="What does the user like?",
        top_k=5,
        filters={"category": "preference"}
    )
    print(f"   Found {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"   [{i}] Score: {result.score:.3f}")
        print(f"       Content: {result.content}")
        print()

    # 4. Batch add memories
    print("\n4. Adding memories in batch...")
    batch_memories = [
        {"content": "User has a cat named Luna", "metadata": {"category": "personal"}},
        {"content": "User lives in Beijing", "metadata": {"category": "location"}},
        {"content": "User works as a software engineer", "metadata": {"category": "work"}},
    ]
    memory_ids = await memory.add_batch_memories(batch_memories)
    print(f"   Added {len(memory_ids)} memories in batch")

    # 5. Health check
    print("\n5. Health check...")
    health = await memory.health_check()
    print(f"   Status: {health['status']}")
    print(f"   Milvus: {health['milvus']}")
    print(f"   Embedding: {health['embedding']}")
    print(f"   Dimension: {health['dimension']}")

    # 6. Get statistics
    print("\n6. Memory statistics...")
    stats = await memory.get_memory_stats()
    print(f"   Collection: {stats['collection_name']}")
    print(f"   Dimension: {stats['dimension']}")
    print(f"   Embedding type: {stats['embedding_type']}")

    print("\n=== Demo Complete ===")

    # Cleanup
    milvus_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
