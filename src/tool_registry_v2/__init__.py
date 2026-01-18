"""
Tool Registry V2 Module

This module provides a secure, extensible tool registration and execution system
designed for production use with LangChain 1.2.x.

Key Features:
- Safe execution environment with Docker/E2B sandbox support
- Dynamic user authentication and credential injection
- Tool permission policies (whitelist/blacklist, ACL)
- Input validation and sanitization
- Automatic retry and fallback mechanisms
- Tool dependency isolation

Architecture:
    tool_registry_v2/
    ├── registry.py                  # Central registry
    ├── security/                    # Security controls
    │   ├── sandbox.py              # Sandbox execution
    │   ├── permission_policy.py    # Permission policies
    │   └── input_validator.py      # Input validation
    ├── authentication/              # Dynamic authentication
    │   ├── credential_manager.py   # Credential management
    │   └── oauth_handler.py        # OAuth handling
    ├── execution/                   # Execution layer
    │   ├── execution_engine.py     # Execution engine
    │   └── error_handler.py        # Error handling
    ├── builtin/                     # Built-in tools
    ├── custom/                      # Custom tools
    └── adapters/                    # Adapters for external tools

Example Usage:
    ```python
    from src.tool_registry_v2 import ToolRegistryV2

    # Initialize registry
    registry = ToolRegistryV2()

    # Register a tool
    await registry.register_tool(my_tool)

    # Execute safely with user context
    result = await registry.execute_safe(
        tool_name="search",
        context=AgentContext(
            user_id="user_123",
            session_id="session_abc"
        )
    )
    ```
"""

from src.tool_registry_v2.registry import ToolRegistryV2

__all__ = [
    "ToolRegistryV2",
]
