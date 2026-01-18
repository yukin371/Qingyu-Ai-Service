"""
Authentication Submodule

This submodule provides dynamic authentication and credential management:
- User credential storage and retrieval
- OAuth token management
- Dynamic credential injection into tools
"""

from src.tool_registry_v2.authentication.credential_manager import CredentialManager

# TODO: Implement OAuth handler in future
# from src.tool_registry_v2.authentication.oauth_handler import OAuthHandler

__all__ = [
    "CredentialManager",
    # "OAuthHandler",
]
