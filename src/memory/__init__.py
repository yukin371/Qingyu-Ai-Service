"""
Memory Module

This module provides comprehensive memory management capabilities for AI agents,
including conversation memory, semantic memory, user profiles, and persistent storage.

Components:
- conversation: Conversation memory implementations (Buffer, Summary, Entity)
- semantic: Semantic vector memory for knowledge retrieval
- user_profile: User profile and preference management
- checkpoint: Checkpoint management for conversation state
- store: Persistent storage backends (Redis, PostgreSQL)

Design Principles:
- Compatibility with LangChain 1.2.x memory interfaces
- Support for multiple storage backends
- Efficient retrieval and search
- Scalability and performance
"""

__all__ = []
