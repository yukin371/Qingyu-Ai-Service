"""
Tests for CredentialManager

This module tests the credential management functionality.
"""

import pytest
from datetime import datetime, timedelta

from src.common.interfaces.tool_interface import ITool
from src.common.types.tool_types import (
    Credential,
    CredentialType,
    ToolCategory,
    ToolExecutionContext,
    ToolExecutionResult,
    ToolMetadata,
    ToolRiskLevel,
    ToolStatus,
)
from src.tool_registry_v2.authentication.credential_manager import CredentialManager


# =============================================================================
# Mock Tool for Testing
# =============================================================================

class APIKeyTool(ITool):
    """Tool that requires API key."""

    def __init__(self, name: str = "api_tool"):
        self.name = name
        self.api_key = None

    async def execute(
        self,
        input_data: dict,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        if not self.api_key:
            raise Exception("API key not set")

        return ToolExecutionResult(
            success=True,
            output=f"Executed with API key: {self.api_key[:10]}...",
            tool_name=self.name,
            user_id=context.user_id,
            execution_time=0.01,
        )

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name=self.name,
            display_name=self.name.title(),
            description=f"Tool requiring API key: {self.name}",
            category=ToolCategory.API,
            risk_level=ToolRiskLevel.LOW,
            status=ToolStatus.ENABLED,
            requires_auth=True,
            auth_providers=["api_key"],
        )

    def validate_input(self, input_data: dict) -> bool:
        return isinstance(input_data, dict)

    async def initialize(self) -> None:
        pass

    async def cleanup(self) -> None:
        pass


# =============================================================================
# CredentialManager Tests
# =============================================================================

class TestCredentialManager:
    """Test cases for CredentialManager."""

    @pytest.fixture
    def manager(self):
        """Create a fresh manager instance for each test."""
        return CredentialManager()

    @pytest.fixture
    def sample_credential(self):
        """Create a sample credential."""
        return Credential(
            user_id="user_123",
            service="openai",
            credential_type=CredentialType.API_KEY,
            token="sk-test-key-12345",
        )

    @pytest.mark.asyncio
    async def test_store_and_get_credential(self, manager, sample_credential):
        """Test storing and retrieving a credential."""
        await manager.store_credential(sample_credential)

        retrieved = await manager.get_credential("user_123", "openai")

        assert retrieved is not None
        assert retrieved.user_id == "user_123"
        assert retrieved.service == "openai"
        assert retrieved.token == "sk-test-key-12345"

    @pytest.mark.asyncio
    async def test_get_nonexistent_credential(self, manager):
        """Test getting a nonexistent credential returns None."""
        retrieved = await manager.get_credential("user_999", "nonexistent")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_credential(self, manager, sample_credential):
        """Test deleting a credential."""
        await manager.store_credential(sample_credential)

        # Verify it exists
        retrieved = await manager.get_credential("user_123", "openai")
        assert retrieved is not None

        # Delete it
        await manager.delete_credential("user_123", "openai")

        # Verify it's gone
        retrieved = await manager.get_credential("user_123", "openai")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_credential(self, manager):
        """Test deleting a nonexistent credential raises no error."""
        # Should not raise
        await manager.delete_credential("user_999", "nonexistent")

    @pytest.mark.asyncio
    async def test_inject_credential(self, manager, sample_credential):
        """Test injecting credential into tool."""
        tool = APIKeyTool("test_tool")

        await manager.store_credential(sample_credential)
        await manager.inject_credential(tool, sample_credential)

        assert tool.api_key == "sk-test-key-12345"

    @pytest.mark.asyncio
    async def test_list_user_credentials(self, manager):
        """Test listing all credentials for a user."""
        cred1 = Credential(
            user_id="user_123",
            service="openai",
            credential_type=CredentialType.API_KEY,
            token="key1",
        )
        cred2 = Credential(
            user_id="user_123",
            service="github",
            credential_type=CredentialType.API_KEY,
            token="key2",
        )
        cred3 = Credential(
            user_id="user_456",  # Different user
            service="openai",
            credential_type=CredentialType.API_KEY,
            token="key3",
        )

        await manager.store_credential(cred1)
        await manager.store_credential(cred2)
        await manager.store_credential(cred3)

        credentials = await manager.list_user_credentials("user_123")

        assert len(credentials) == 2
        services = {cred.service for cred in credentials}
        assert "openai" in services
        assert "github" in services

    @pytest.mark.asyncio
    async def test_credential_expiration(self, manager):
        """Test credential expiration checking."""
        # Create expired credential
        expired_cred = Credential(
            user_id="user_123",
            service="openai",
            credential_type=CredentialType.OAUTH2,
            token="expired_token",
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )

        await manager.store_credential(expired_cred)

        retrieved = await manager.get_credential("user_123", "openai")
        assert retrieved.is_expired() is True

    @pytest.mark.asyncio
    async def test_refresh_oauth_token_not_implemented(self, manager):
        """Test OAuth token refresh (not implemented in MVP)."""
        with pytest.raises(NotImplementedError):
            await manager.refresh_oauth_token("user_123", "openai")

    @pytest.mark.asyncio
    async def test_store_encrypted_credential(self, manager):
        """Test storing encrypted credential (MVP: no encryption)."""
        cred = Credential(
            user_id="user_123",
            service="openai",
            credential_type=CredentialType.API_KEY,
            token="sensitive_key",
        )

        await manager.store_credential(cred, encrypt=True)

        retrieved = await manager.get_credential("user_123", "openai")
        assert retrieved.token == "sensitive_key"
