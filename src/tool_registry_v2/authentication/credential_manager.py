"""
Credential Manager

This module provides credential management for tool authentication:
- Store and retrieve user credentials
- Inject credentials into tools
- OAuth token management (MVP: basic implementation)
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from src.common.exceptions import ToolExecutionError
from src.common.interfaces.tool_interface import ITool
from src.common.types.tool_types import Credential, CredentialType


# =============================================================================
# Credential Manager
# =============================================================================

class CredentialManager:
    """
    Credential management for tool authentication.

    Features:
    - Store and retrieve user credentials
    - Inject credentials into tools
    - OAuth token management (basic)
    - Credential expiration checking

    MVP: Uses in-memory storage. Future: Use secure database or key store.

    Example:
        ```python
        manager = CredentialManager()

        # Store a credential
        cred = Credential(
            user_id="user_123",
            service="openai",
            credential_type=CredentialType.API_KEY,
            token="sk-...",
        )
        await manager.store_credential(cred)

        # Get credential
        cred = await manager.get_credential("user_123", "openai")

        # Inject into tool
        await manager.inject_credential(tool, cred)
        ```
    """

    def __init__(self):
        """Initialize the credential manager."""
        # In-memory storage (MVP)
        # Future: Use secure database or key store
        self._credentials: Dict[tuple, Credential] = {}
        self._lock = asyncio.Lock()

    # -------------------------------------------------------------------------
    # Credential Storage
    # -------------------------------------------------------------------------

    async def store_credential(
        self,
        credential: Credential,
        encrypt: bool = False,
    ) -> None:
        """
        Store a credential.

        Args:
            credential: Credential to store
            encrypt: Whether to encrypt the credential (MVP: not implemented)

        Raises:
            MemoryStorageError: If storage fails
        """
        async with self._lock:
            key = (credential.user_id, credential.service)

            # MVP: No encryption
            # Future: Implement encryption using cryptography library
            # if encrypt:
            #     credential = self._encrypt_credential(credential)

            self._credentials[key] = credential

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
        async with self._lock:
            key = (user_id, service)
            credential = self._credentials.get(key)

            # MVP: No decryption
            # Future: Implement decryption
            # if credential and credential.encrypted:
            #     credential = self._decrypt_credential(credential)

            return credential

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
            MemoryNotFoundError: If credential is not found (soft fail in MVP)
        """
        async with self._lock:
            key = (user_id, service)
            if key in self._credentials:
                del self._credentials[key]

    async def list_user_credentials(self, user_id: str) -> List[Credential]:
        """
        List all credentials for a user.

        Args:
            user_id: ID of the user

        Returns:
            List[Credential]: List of credentials
        """
        async with self._lock:
            return [
                cred for (uid, _), cred in self._credentials.items()
                if uid == user_id
            ]

    async def list_service_credentials(self, service: str) -> List[Credential]:
        """
        List all credentials for a service.

        Args:
            service: Service name

        Returns:
            List[Credential]: List of credentials
        """
        async with self._lock:
            return [
                cred for (_, svc), cred in self._credentials.items()
                if svc == service
            ]

    # -------------------------------------------------------------------------
    # Credential Injection
    # -------------------------------------------------------------------------

    async def inject_credential(
        self,
        tool: ITool,
        credential: Credential,
    ) -> None:
        """
        Inject a credential into a tool.

        This method attempts to set the credential on the tool instance.
        The tool should have attributes that match the credential type.

        Args:
            tool: Tool to inject credential into
            credential: Credential to inject

        Raises:
            ToolExecutionError: If injection fails
        """
        try:
            # Inject based on credential type
            if credential.credential_type == CredentialType.API_KEY:
                # Try common attribute names
                for attr in ["api_key", "apiKey", "key"]:
                    if hasattr(tool, attr):
                        setattr(tool, attr, credential.token)
                        return

            elif credential.credential_type == CredentialType.BEARER_TOKEN:
                # Try common attribute names
                for attr in ["bearer_token", "bearerToken", "token", "access_token"]:
                    if hasattr(tool, attr):
                        setattr(tool, attr, credential.token)
                        return

            elif credential.credential_type == CredentialType.OAUTH2:
                # Try common attribute names
                if hasattr(tool, "access_token"):
                    tool.access_token = credential.token
                if hasattr(tool, "refresh_token") and credential.refresh_token:
                    tool.refresh_token = credential.refresh_token
                return

            elif credential.credential_type == CredentialType.BASIC_AUTH:
                # Parse token as "username:password"
                if ":" in credential.token:
                    username, password = credential.token.split(":", 1)
                    if hasattr(tool, "username"):
                        tool.username = username
                    if hasattr(tool, "password"):
                        tool.password = password
                return

            # If no matching attribute found, raise error
            # Note: Some tools might handle credentials differently
            # This is a best-effort approach

        except Exception as e:
            raise ToolExecutionError(
                tool_name=tool.get_metadata().name if hasattr(tool, 'get_metadata') else 'unknown',
                reason=f"Failed to inject credential: {str(e)}",
            )

    # -------------------------------------------------------------------------
    # OAuth Token Management
    # -------------------------------------------------------------------------

    async def refresh_oauth_token(
        self,
        user_id: str,
        service: str,
    ) -> Credential:
        """
        Refresh an OAuth token.

        MVP: Not implemented. This requires OAuth provider-specific logic.

        Args:
            user_id: ID of the user
            service: Service name

        Returns:
            Credential: Updated credential with new token

        Raises:
            NotImplementedError: In MVP
        """
        # MVP: Not implemented
        # Future: Implement OAuth refresh flow
        raise NotImplementedError(
            "OAuth token refresh not implemented in MVP. "
            "This requires service-specific OAuth client configuration."
        )

    async def rotate_token(
        self,
        user_id: str,
        service: str,
        new_token: str,
    ) -> None:
        """
        Rotate a token (replace old token with new one).

        Args:
            user_id: ID of the user
            service: Service name
            new_token: New token value
        """
        credential = await self.get_credential(user_id, service)
        if credential:
            credential.token = new_token
            credential.updated_at = datetime.utcnow()
            await self.store_credential(credential)

    # -------------------------------------------------------------------------
    # Credential Cleanup
    # -------------------------------------------------------------------------

    async def cleanup_expired_credentials(self) -> int:
        """
        Remove all expired credentials.

        Returns:
            int: Number of credentials removed
        """
        async with self._lock:
            now = datetime.utcnow()
            expired_keys = [
                key for key, cred in self._credentials.items()
                if cred.expires_at and cred.expires_at < now
            ]

            for key in expired_keys:
                del self._credentials[key]

            return len(expired_keys)

    async def cleanup_user_credentials(self, user_id: str) -> int:
        """
        Remove all credentials for a user.

        Args:
            user_id: ID of the user

        Returns:
            int: Number of credentials removed
        """
        async with self._lock:
            keys_to_remove = [
                key for key in self._credentials.keys()
                if key[0] == user_id
            ]

            for key in keys_to_remove:
                del self._credentials[key]

            return len(keys_to_remove)

    # -------------------------------------------------------------------------
    # Encryption (Future)
    # -------------------------------------------------------------------------

    def _encrypt_credential(self, credential: Credential) -> Credential:
        """
        Encrypt a credential.

        Future: Implement using cryptography library.

        Args:
            credential: Credential to encrypt

        Returns:
            Credential: Encrypted credential
        """
        # TODO: Implement encryption
        raise NotImplementedError("Credential encryption not implemented")

    def _decrypt_credential(self, credential: Credential) -> Credential:
        """
        Decrypt a credential.

        Future: Implement using cryptography library.

        Args:
            credential: Credential to decrypt

        Returns:
            Credential: Decrypted credential
        """
        # TODO: Implement decryption
        raise NotImplementedError("Credential decryption not implemented")
