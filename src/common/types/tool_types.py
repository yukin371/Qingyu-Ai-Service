"""
Tool Type Definitions

This module defines all types related to tool registration and execution.
All types are compatible with LangChain 1.2.x and Pydantic v2.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Enums
# =============================================================================

class ToolCategory(str, Enum):
    """Category of a tool."""

    SEARCH = "search"
    DATABASE = "database"
    FILESYSTEM = "filesystem"
    API = "api"
    CODE_EXECUTION = "code_execution"
    WEB_SCrapING = "web_scraping"
    DATA_PROCESSING = "data_processing"
    COMMUNICATION = "communication"
    CUSTOM = "custom"


class ToolRiskLevel(str, Enum):
    """Risk level of a tool for security assessment."""

    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ToolStatus(str, Enum):
    """Operational status of a tool."""

    ENABLED = "enabled"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"


# =============================================================================
# Tool Metadata
# =============================================================================

class ToolMetadata(BaseModel):
    """
    Metadata about a tool.

    Attributes:
        name: Unique name identifier for the tool
        display_name: Human-readable display name
        description: Detailed description of what the tool does
        category: Category of the tool
        version: Tool version
        author: Tool author
        risk_level: Security risk level
        status: Operational status
        tags: List of tags for search and filtering
        requires_auth: Whether the tool requires authentication
        auth_providers: List of supported auth providers
        dependencies: List of tool dependencies
        rate_limit: Rate limit (calls per minute)
        timeout: Default timeout in seconds
        created_at: When the tool was registered
        updated_at: When the tool was last updated
    """

    name: str
    display_name: str
    description: str
    category: ToolCategory
    version: str = "1.0.0"
    author: str = "system"
    risk_level: ToolRiskLevel = ToolRiskLevel.MEDIUM
    status: ToolStatus = ToolStatus.ENABLED
    tags: List[str] = Field(default_factory=list)
    requires_auth: bool = False
    auth_providers: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    rate_limit: Optional[int] = None
    timeout: int = Field(default=30)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(use_enum_values=False)


# =============================================================================
# Tool Schema
# =============================================================================

class ToolParameter(BaseModel):
    """
    Definition of a tool parameter.

    Attributes:
        name: Parameter name
        type: Parameter type (string, number, boolean, etc.)
        description: Parameter description
        required: Whether the parameter is required
        default: Default value
        enum: Allowed values (for enum parameters)
        format: Format specification (e.g., "email", "uri")
    """

    name: str
    type: str
    description: str
    required: bool = False
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None
    format: Optional[str] = None


class ToolSchema(BaseModel):
    """
    Schema defining tool inputs and outputs.

    Attributes:
        input_schema: Pydantic schema or JSON schema for input validation
        output_schema: Pydantic schema or JSON schema for output validation
        parameters: List of parameter definitions
    """

    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    parameters: List[ToolParameter] = Field(default_factory=list)


# =============================================================================
# Tool Info
# =============================================================================

class ToolInfo(BaseModel):
    """
    Complete information about a registered tool.

    Attributes:
        metadata: Tool metadata
        tool_schema: Tool schema
        stats: Tool usage statistics
        is_builtin: Whether this is a built-in tool
    """

    metadata: ToolMetadata
    tool_schema: ToolSchema
    stats: "ToolStats"
    is_builtin: bool = False


class ToolStats(BaseModel):
    """
    Usage statistics for a tool.

    Attributes:
        total_calls: Total number of calls
        successful_calls: Number of successful calls
        failed_calls: Number of failed calls
        avg_execution_time: Average execution time in seconds
        last_called_at: When the tool was last called
        last_error: Last error message (if any)
    """

    total_calls: int = Field(default=0)
    successful_calls: int = Field(default=0)
    failed_calls: int = Field(default=0)
    avg_execution_time: float = Field(default=0.0)
    last_called_at: Optional[datetime] = None
    last_error: Optional[str] = None


# =============================================================================
# Tool Execution Context
# =============================================================================

class ToolExecutionContext(BaseModel):
    """
    Context for tool execution.

    Attributes:
        tool_name: Name of the tool being executed
        user_id: ID of the user requesting execution
        session_id: ID of the current session
        agent_id: ID of the agent (if applicable)
        input_data: Input data for the tool
        timeout: Execution timeout in seconds
        use_sandbox: Whether to use sandbox execution
        retry_count: Number of retries attempted
        metadata: Additional metadata
    """

    tool_name: str
    user_id: str
    session_id: str
    agent_id: Optional[str] = None
    input_data: Dict[str, Any] = Field(default_factory=dict)
    timeout: int = Field(default=30)
    use_sandbox: bool = False
    retry_count: int = Field(default=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Tool Execution Result
# =============================================================================

class ToolExecutionResult(BaseModel):
    """
    Result of tool execution.

    Attributes:
        success: Whether execution was successful
        output: Output data from the tool
        error: Error message if execution failed
        execution_time: Time taken to execute in seconds
        tool_name: Name of the tool that was executed
        user_id: ID of the user who requested execution
        metadata: Additional metadata
    """

    success: bool
    output: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = Field(default=0.0)
    tool_name: str
    user_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Credential Types
# =============================================================================

class CredentialType(str, Enum):
    """Type of credential."""

    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    BEARER_TOKEN = "bearer_token"
    BASIC_AUTH = "basic_auth"
    CUSTOM = "custom"


class Credential(BaseModel):
    """
    User credential for a service.

    Attributes:
        user_id: ID of the user
        service: Service name (e.g., "openai", "github")
        credential_type: Type of credential
        token: Access token or API key
        refresh_token: Refresh token (for OAuth2)
        expires_at: Token expiration time (for OAuth2)
        metadata: Additional metadata
        created_at: When the credential was created
        updated_at: When the credential was last updated
    """

    user_id: str
    service: str
    credential_type: CredentialType
    token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(use_enum_values=False)

    def is_expired(self) -> bool:
        """Check if the credential is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


# =============================================================================
# Permission Policy Types
# =============================================================================

class PermissionType(str, Enum):
    """Type of permission."""

    ALLOW = "allow"
    DENY = "deny"


class AccessControlEntry(BaseModel):
    """
    Access control entry for a tool.

    Attributes:
        user_id: ID of the user (or "*" for all users)
        tool_name: Name of the tool (or "*" for all tools)
        permission: Permission type (allow/deny)
        reason: Reason for the permission
    """

    user_id: str
    tool_name: str
    permission: PermissionType
    reason: Optional[str] = None

    model_config = ConfigDict(use_enum_values=False)


# =============================================================================
# Export all types
# =============================================================================

__all__ = [
    # Enums
    "ToolCategory",
    "ToolRiskLevel",
    "ToolStatus",
    "CredentialType",
    "PermissionType",
    # Metadata
    "ToolMetadata",
    "ToolParameter",
    "ToolSchema",
    "ToolInfo",
    "ToolStats",
    # Execution
    "ToolExecutionContext",
    "ToolExecutionResult",
    # Authentication
    "Credential",
    # Permissions
    "AccessControlEntry",
]
