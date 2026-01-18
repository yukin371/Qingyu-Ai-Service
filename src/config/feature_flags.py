"""
Feature Flags

This module defines feature flags for the application, allowing
runtime control over feature availability.
"""

from functools import lru_cache
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class FeatureFlags(BaseModel):
    """
    Feature flags configuration.

    Feature flags allow runtime control over feature availability,
    enabling gradual rollouts and A/B testing.
    """

    # =============================================================================
    # LLM Features
    # =============================================================================

    langchain_tracing: bool = Field(
        default=False,
        description="Enable LangChain tracing"
    )
    langchain_debug: bool = Field(
        default=False,
        description="Enable LangChain debug mode"
    )

    # =============================================================================
    # Memory Features
    # =============================================================================

    enable_embeddings: bool = Field(
        default=False,
        description="Enable vector embeddings"
    )
    enable_vector_search: bool = Field(
        default=False,
        description="Enable vector similarity search"
    )
    enable_semantic_search: bool = Field(
        default=False,
        description="Enable semantic search"
    )

    # =============================================================================
    # Workflow Features
    # =============================================================================

    enable_workflows: bool = Field(
        default=True,
        description="Enable workflow engine"
    )
    enable_parallel_execution: bool = Field(
        default=False,
        description="Enable parallel workflow step execution"
    )
    enable_workflow_retry: bool = Field(
        default=True,
        description="Enable automatic workflow retry"
    )

    # =============================================================================
    # Agent Features
    # =============================================================================

    enable_multi_modal: bool = Field(
        default=False,
        description="Enable multi-modal agents"
    )
    enable_code_execution: bool = Field(
        default=False,
        description="Enable code execution agents"
    )
    enable_web_browsing: bool = Field(
        default=False,
        description="Enable web browsing capability"
    )

    # =============================================================================
    # Tool Features
    # =============================================================================

    enable_tool_validation: bool = Field(
        default=True,
        description="Enable strict tool input/output validation"
    )
    enable_tool_caching: bool = Field(
        default=True,
        description="Enable tool result caching"
    )

    # =============================================================================
    # RAG Features
    # =============================================================================

    enable_rag: bool = Field(
        default=False,
        description="Enable RAG (Retrieval Augmented Generation)"
    )
    enable_hybrid_search: bool = Field(
        default=False,
        description="Enable hybrid vector + keyword search"
    )

    # =============================================================================
    # API Features
    # =============================================================================

    enable_rate_limiting: bool = Field(
        default=True,
        description="Enable API rate limiting"
    )
    enable_caching: bool = Field(
        default=True,
        description="Enable API response caching"
    )
    enable_streaming: bool = Field(
        default=True,
        description="Enable streaming responses"
    )

    # =============================================================================
    # Experimental Features
    # =============================================================================

    enable_experimental_features: bool = Field(
        default=False,
        description="Enable experimental features"
    )
    experimental_agent_types: List[str] = Field(
        default_factory=list,
        description="List of experimental agent types to enable"
    )

    # =============================================================================
    # Beta Features
    # =============================================================================

    enable_beta_features: bool = Field(
        default=False,
        description="Enable beta features"
    )
    beta_features: List[str] = Field(
        default_factory=list,
        description="List of beta features to enable"
    )

    def is_enabled(self, flag_name: str) -> bool:
        """
        Check if a feature flag is enabled.

        Args:
            flag_name: Name of the feature flag

        Returns:
            bool: True if the feature is enabled
        """
        return getattr(self, flag_name, False)

    def enable(self, flag_name: str) -> None:
        """
        Enable a feature flag.

        Args:
            flag_name: Name of the feature flag to enable
        """
        if hasattr(self, flag_name):
            setattr(self, flag_name, True)

    def disable(self, flag_name: str) -> None:
        """
        Disable a feature flag.

        Args:
            flag_name: Name of the feature flag to disable
        """
        if hasattr(self, flag_name):
            setattr(self, flag_name, False)

    def get_enabled_features(self) -> Dict[str, bool]:
        """
        Get all enabled features.

        Returns:
            Dict[str, bool]: Dictionary of feature names and their enabled status
        """
        return {
            name: getattr(self, name)
            for name in self.__class__.model_fields
            if name.startswith("enable_") and getattr(self, name)
        }


@lru_cache()
def get_feature_flags() -> FeatureFlags:
    """
    Get cached feature flags instance.

    Returns:
        FeatureFlags: Application feature flags
    """
    return FeatureFlags()


def configure_feature_flags(**kwargs) -> FeatureFlags:
    """
    Create a new FeatureFlags instance with custom values.

    Args:
        **kwargs: Feature flag values to override

    Returns:
        FeatureFlags: Configured feature flags
    """
    return FeatureFlags(**kwargs)
