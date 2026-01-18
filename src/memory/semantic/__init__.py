"""
Semantic Memory Submodule

This module provides semantic memory capabilities using vector embeddings.

Features:
- VectorMemory: Semantic search using Milvus
- Knowledge storage and retrieval
- Similarity-based search
"""

from src.memory.semantic.vector_memory import VectorMemory, MemorySearchResult

__all__ = ['VectorMemory', 'MemorySearchResult']
