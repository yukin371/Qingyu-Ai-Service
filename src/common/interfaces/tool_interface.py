"""
Tool Interface Definitions

This module defines abstract interfaces for tools and tool registry.
These interfaces enable dependency injection, testing, and multiple implementations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.common.types.agent_types import AgentContext
from src.common.types.tool_types import (
    Credential,
    ToolExecutionContext,
    ToolExecutionResult,
    ToolInfo,
    ToolMetadata,
)


# =============================================================================
# Tool Interface
# =============================================================================

class ITool(ABC):
    """
    Abstract interface for a tool.

    All tools must implement this interface to be compatible with the
    tool registry system.
    """

    @abstractmethod
    async def execute(
        self,
        input_data: Dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        """
        Execute the tool with the given input and context.

        Args:
            input_data: Input data for the tool
            context: Execution context including user info and metadata

        Returns:
            ToolExecutionResult: Result of the execution

        Raises:
            ToolExecutionError: If execution fails
        """
        pass

    @abstractmethod
    def get_metadata(self) -> ToolMetadata:
        """
        Get the tool's metadata.

        Returns:
            ToolMetadata: Tool metadata including name, description, etc.
        """
        pass

    @abstractmethod
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data before execution.

        Args:
            input_data: Input data to validate

        Returns:
            bool: True if valid, False otherwise

        Raises:
            ToolValidationError: If validation fails
        """
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the tool.

        This method is called when the tool is registered.
        Use it to set up resources, connections, etc.
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """
        Clean up tool resources.

        This method is called when the tool is unregistered or the system shuts down.
        """
        pass


# =============================================================================
# Tool Registry Interface
# =============================================================================

class IToolRegistry(ABC):
    """
    Abstract interface for a tool registry.

    The tool registry is responsible for:
    - Registering and unregistering tools
    - Retrieving tools by name
    - Listing available tools
    - Executing tools safely with proper error handling
    """

    @abstractmethod
    async def register_tool(self, tool: ITool) -> None:
        """
        Register a tool.

        Args:
            tool: Tool to register

        Raises:
            ToolRegistrationError: If registration fails
        """
        pass

    @abstractmethod
    async def unregister_tool(self, tool_name: str) -> None:
        """
        Unregister a tool.

        Args:
            tool_name: Name of the tool to unregister

        Raises:
            ToolNotFoundError: If tool is not found
        """
        pass

    @abstractmethod
    async def get_tool(self, tool_name: str, user_id: Optional[str] = None) -> Optional[ITool]:
        """
        Get a tool by name.

        Args:
            tool_name: Name of the tool
            user_id: Optional user ID for permission checking

        Returns:
            ITool: Tool instance if found and accessible, None otherwise
        """
        pass

    @abstractmethod
    async def list_tools(
        self,
        user_id: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[ToolInfo]:
        """
        List all available tools.

        Args:
            user_id: Optional user ID for filtering by permission
            category: Optional category filter

        Returns:
            List[ToolInfo]: List of tool information objects
        """
        pass

    @abstractmethod
    async def execute_safe(
        self,
        tool_name: str,
        input_data: Dict[str, Any],
        context: AgentContext,
    ) -> ToolExecutionResult:
        """
        Safely execute a tool with proper error handling and security checks.

        Args:
            tool_name: Name of the tool to execute
            input_data: Input data for the tool
            context: Agent context including user and session info

        Returns:
            ToolExecutionResult: Result of the execution

        Raises:
            ToolNotFoundError: If tool is not found
            ToolExecutionError: If execution fails
        """
        pass

    @abstractmethod
    async def check_permission(
        self,
        tool_name: str,
        user_id: str,
    ) -> bool:
        """
        Check if a user has permission to use a tool.

        Args:
            tool_name: Name of the tool
            user_id: ID of the user

        Returns:
            bool: True if user has permission, False otherwise
        """
        pass


# =============================================================================
# Credential Manager Interface
# =============================================================================

class ICredentialManager(ABC):
    """
    Abstract interface for credential management.

    The credential manager is responsible for:
    - Storing and retrieving user credentials
    - Injecting credentials into tools
    - Refreshing OAuth tokens
    """

    @abstractmethod
    async def get_credential(
        self,
        user_id: str,
        service: str,
    ) -> Optional[Credential]:
        """
        Get a credential for a user and service.

        Args:
            user_id: ID of the user
            service: Service name (e.g., "openai", "github")

        Returns:
            Credential: Credential if found, None otherwise
        """
        pass

    @abstractmethod
    async def store_credential(self, credential: Credential) -> None:
        """
        Store a credential.

        Args:
            credential: Credential to store

        Raises:
            MemoryStorageError: If storage fails
        """
        pass

    @abstractmethod
    async def delete_credential(
        self,
        user_id: str,
        service: str,
    ) -> None:
        """
        Delete a credential.

        Args:
            user_id: ID of the user
            service: Service name

        Raises:
            MemoryNotFoundError: If credential is not found
        """
        pass

    @abstractmethod
    async def inject_credential(
        self,
        tool: ITool,
        credential: Credential,
    ) -> None:
        """
        Inject a credential into a tool.

        Args:
            tool: Tool to inject credential into
            credential: Credential to inject

        Raises:
            ToolExecutionError: If injection fails
        """
        pass

    @abstractmethod
    async def refresh_oauth_token(
        self,
        user_id: str,
        service: str,
    ) -> Credential:
        """
        Refresh an OAuth token.

        Args:
            user_id: ID of the user
            service: Service name

        Returns:
            Credential: Updated credential with new token

        Raises:
            MemoryStorageError: If refresh fails
        """
        pass


# =============================================================================
# Export all interfaces
# =============================================================================

__all__ = [
    "ITool",
    "IToolRegistry",
    "ICredentialManager",
]
