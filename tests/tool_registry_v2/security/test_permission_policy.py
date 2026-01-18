"""
Tests for PermissionPolicy

This module tests the permission policy functionality.
"""

import pytest

from src.common.types.tool_types import (
    AccessControlEntry,
    PermissionType,
    ToolCategory,
    ToolMetadata,
    ToolRiskLevel,
    ToolStatus,
)
from src.tool_registry_v2.security.permission_policy import PermissionPolicy


# =============================================================================
# PermissionPolicy Tests
# =============================================================================

class TestPermissionPolicy:
    """Test cases for PermissionPolicy."""

    @pytest.fixture
    def policy(self):
        """Create a fresh policy instance for each test."""
        return PermissionPolicy()

    @pytest.fixture
    def sample_metadata(self):
        """Create sample tool metadata."""
        return ToolMetadata(
            name="test_tool",
            display_name="Test Tool",
            description="A test tool",
            category=ToolCategory.CUSTOM,
            risk_level=ToolRiskLevel.LOW,
            status=ToolStatus.ENABLED,
        )

    def test_default_allow_all(self, policy):
        """Test that default policy allows all tools for all users."""
        assert policy.check_access("user_123", "tool_abc") is True

    def test_set_whitelist(self, policy):
        """Test setting whitelist."""
        policy.set_whitelist(["tool1", "tool2"])

        assert policy.check_access("user_123", "tool1") is True
        assert policy.check_access("user_123", "tool2") is True
        assert policy.check_access("user_123", "tool3") is False

    def test_set_blacklist(self, policy):
        """Test setting blacklist."""
        policy.set_blacklist(["tool1", "tool2"])

        assert policy.check_access("user_123", "tool1") is False
        assert policy.check_access("user_123", "tool2") is False
        assert policy.check_access("user_123", "tool3") is True

    def test_whitelist_and_blacklist(self, policy):
        """Test interaction between whitelist and blacklist."""
        policy.set_whitelist(["tool1", "tool2", "tool3"])
        policy.set_blacklist(["tool2"])

        # Whitelist allows, then blacklist denies
        assert policy.check_access("user_123", "tool1") is True
        assert policy.check_access("user_123", "tool2") is False
        assert policy.check_access("user_123", "tool3") is True

    def test_add_acl_entry(self, policy):
        """Test adding ACL entries."""
        entry = AccessControlEntry(
            user_id="user_123",
            tool_name="tool_abc",
            permission=PermissionType.ALLOW,
        )
        policy.add_acl_entry(entry)

        assert policy.check_access("user_123", "tool_abc") is True
        assert policy.check_access("user_456", "tool_abc") is True  # Other users still allowed

    def test_acl_deny(self, policy):
        """Test ACL deny entries."""
        entry = AccessControlEntry(
            user_id="user_123",
            tool_name="tool_abc",
            permission=PermissionType.DENY,
        )
        policy.add_acl_entry(entry)

        assert policy.check_access("user_123", "tool_abc") is False
        assert policy.check_access("user_456", "tool_abc") is True  # Other users still allowed

    def test_acl_wildcard_user(self, policy):
        """Test ACL wildcard user ('*' for all users)."""
        entry = AccessControlEntry(
            user_id="*",
            tool_name="tool_abc",
            permission=PermissionType.DENY,
        )
        policy.add_acl_entry(entry)

        assert policy.check_access("user_123", "tool_abc") is False
        assert policy.check_access("user_456", "tool_abc") is False

    def test_acl_wildcard_tool(self, policy):
        """Test ACL wildcard tool ('*' for all tools)."""
        entry = AccessControlEntry(
            user_id="user_123",
            tool_name="*",
            permission=PermissionType.DENY,
        )
        policy.add_acl_entry(entry)

        assert policy.check_access("user_123", "tool_abc") is False
        assert policy.check_access("user_123", "tool_xyz") is False
        assert policy.check_access("user_456", "tool_abc") is True  # Other users still allowed

    def test_remove_acl_entry(self, policy):
        """Test removing ACL entries."""
        entry = AccessControlEntry(
            user_id="user_123",
            tool_name="tool_abc",
            permission=PermissionType.DENY,
        )
        policy.add_acl_entry(entry)

        assert policy.check_access("user_123", "tool_abc") is False

        policy.remove_acl_entry("user_123", "tool_abc")

        # After removal, default allow applies
        assert policy.check_access("user_123", "tool_abc") is True

    def test_clear_whitelist(self, policy):
        """Test clearing whitelist."""
        policy.set_whitelist(["tool1", "tool2"])
        assert policy.check_access("user_123", "tool1") is True

        policy.clear_whitelist()

        # After clearing, all tools are allowed again
        assert policy.check_access("user_123", "tool1") is True
        assert policy.check_access("user_123", "tool3") is True

    def test_clear_blacklist(self, policy):
        """Test clearing blacklist."""
        policy.set_blacklist(["tool1", "tool2"])
        assert policy.check_access("user_123", "tool1") is False

        policy.clear_blacklist()

        # After clearing, all tools are allowed again
        assert policy.check_access("user_123", "tool1") is True

    def test_get_user_permissions(self, policy):
        """Test getting user permissions."""
        entry1 = AccessControlEntry(
            user_id="user_123",
            tool_name="tool_abc",
            permission=PermissionType.ALLOW,
        )
        entry2 = AccessControlEntry(
            user_id="user_123",
            tool_name="tool_xyz",
            permission=PermissionType.DENY,
        )
        policy.add_acl_entry(entry1)
        policy.add_acl_entry(entry2)

        permissions = policy.get_user_permissions("user_123")

        assert len(permissions) == 2
        assert any(p.tool_name == "tool_abc" for p in permissions)
        assert any(p.tool_name == "tool_xyz" for p in permissions)

    def test_risk_level_filtering(self, policy, sample_metadata):
        """Test risk level filtering."""
        policy.set_max_risk_level(ToolRiskLevel.LOW)

        # Create metadata with different risk levels
        low_risk_tool = ToolMetadata(
            name="low_risk_tool",
            display_name="Low Risk",
            description="Low risk tool",
            category=ToolCategory.CUSTOM,
            risk_level=ToolRiskLevel.LOW,
            status=ToolStatus.ENABLED,
        )

        high_risk_tool = ToolMetadata(
            name="high_risk_tool",
            display_name="High Risk",
            description="High risk tool",
            category=ToolCategory.CUSTOM,
            risk_level=ToolRiskLevel.HIGH,
            status=ToolStatus.ENABLED,
        )

        assert policy.check_access_by_risk(low_risk_tool) is True
        assert policy.check_access_by_risk(high_risk_tool) is False

    def test_rate_limiting(self, policy):
        """Test rate limiting."""
        policy.set_rate_limit("user_123", "tool_abc", max_calls=2, window_seconds=60)

        assert policy.check_rate_limit("user_123", "tool_abc") is True
        policy.record_rate_limit_call("user_123", "tool_abc")

        assert policy.check_rate_limit("user_123", "tool_abc") is True
        policy.record_rate_limit_call("user_123", "tool_abc")

        assert policy.check_rate_limit("user_123", "tool_abc") is False
