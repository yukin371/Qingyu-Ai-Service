"""
Permission Policy

This module provides permission policies for tool access control:
- Whitelist/blacklist
- Access Control Lists (ACL)
- Risk level filtering
- Rate limiting
"""

import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from src.common.types.tool_types import (
    AccessControlEntry,
    PermissionType,
    ToolMetadata,
    ToolRiskLevel,
)


# =============================================================================
# Permission Policy
# =============================================================================

class PermissionPolicy:
    """
    Permission policy manager for tool access control.

    Features:
    - Whitelist/blacklist management
    - Access Control Lists (ACL) with wildcard support
    - Risk level filtering
    - Rate limiting per user and tool

    Example:
        ```python
        policy = PermissionPolicy()

        # Set whitelist
        policy.set_whitelist(["tool1", "tool2"])

        # Add ACL entry
        entry = AccessControlEntry(
            user_id="user_123",
            tool_name="tool_abc",
            permission=PermissionType.ALLOW,
        )
        policy.add_acl_entry(entry)

        # Check access
        if policy.check_access("user_123", "tool_abc"):
            # Tool access granted
            pass
        ```
    """

    def __init__(self):
        """Initialize the permission policy manager."""
        # Whitelist (None means allow all)
        self._whitelist: Optional[List[str]] = None

        # Blacklist
        self._blacklist: List[str] = []

        # ACL: (user_id, tool_name) -> AccessControlEntry
        self._acl: Dict[tuple, AccessControlEntry] = {}

        # Maximum risk level allowed
        self._max_risk_level: Optional[ToolRiskLevel] = None

        # Rate limiting: (user_id, tool_name) -> [(timestamp, ...), ...]
        self._rate_limits: Dict[tuple, Dict] = {}
        self._rate_limit_calls: Dict[tuple, List[datetime]] = defaultdict(list)

    # -------------------------------------------------------------------------
    # Whitelist/Blacklist
    # -------------------------------------------------------------------------

    def set_whitelist(self, tool_names: Optional[List[str]]) -> None:
        """
        Set the whitelist of allowed tools.

        Args:
            tool_names: List of tool names to allow, or None to allow all
        """
        self._whitelist = tool_names

    def clear_whitelist(self) -> None:
        """Clear the whitelist (allow all tools)."""
        self._whitelist = None

    def set_blacklist(self, tool_names: List[str]) -> None:
        """
        Set the blacklist of forbidden tools.

        Args:
            tool_names: List of tool names to deny
        """
        self._blacklist = tool_names

    def clear_blacklist(self) -> None:
        """Clear the blacklist."""
        self._blacklist = []

    # -------------------------------------------------------------------------
    # Access Control Lists (ACL)
    # -------------------------------------------------------------------------

    def add_acl_entry(self, entry: AccessControlEntry) -> None:
        """
        Add an ACL entry.

        Args:
            entry: Access control entry
        """
        key = (entry.user_id, entry.tool_name)
        self._acl[key] = entry

    def remove_acl_entry(self, user_id: str, tool_name: str) -> None:
        """
        Remove an ACL entry.

        Args:
            user_id: User ID
            tool_name: Tool name
        """
        key = (user_id, tool_name)
        self._acl.pop(key, None)

    def get_user_permissions(self, user_id: str) -> List[AccessControlEntry]:
        """
        Get all permissions for a user.

        Args:
            user_id: User ID

        Returns:
            List[AccessControlEntry]: List of ACL entries for the user
        """
        return [
            entry for key, entry in self._acl.items()
            if key[0] == user_id or key[0] == "*"
        ]

    # -------------------------------------------------------------------------
    # Risk Level Filtering
    # -------------------------------------------------------------------------

    def set_max_risk_level(self, max_risk: ToolRiskLevel) -> None:
        """
        Set the maximum risk level allowed.

        Args:
            max_risk: Maximum risk level
        """
        self._max_risk_level = max_risk

    def check_access_by_risk(self, metadata: ToolMetadata) -> bool:
        """
        Check access based on risk level.

        Args:
            metadata: Tool metadata

        Returns:
            bool: True if tool risk level is acceptable
        """
        if self._max_risk_level is None:
            return True

        # Define risk level hierarchy (higher is more risky)
        risk_levels = {
            ToolRiskLevel.SAFE: 0,
            ToolRiskLevel.LOW: 1,
            ToolRiskLevel.MEDIUM: 2,
            ToolRiskLevel.HIGH: 3,
            ToolRiskLevel.CRITICAL: 4,
        }

        tool_risk = risk_levels.get(metadata.risk_level, 2)
        max_risk = risk_levels.get(self._max_risk_level, 2)

        return tool_risk <= max_risk

    # -------------------------------------------------------------------------
    # Rate Limiting
    # -------------------------------------------------------------------------

    def set_rate_limit(
        self,
        user_id: str,
        tool_name: str,
        max_calls: int,
        window_seconds: int = 60,
    ) -> None:
        """
        Set rate limit for a user and tool.

        Args:
            user_id: User ID
            tool_name: Tool name
            max_calls: Maximum number of calls allowed
            window_seconds: Time window in seconds
        """
        key = (user_id, tool_name)
        self._rate_limits[key] = {
            "max_calls": max_calls,
            "window_seconds": window_seconds,
        }

    def check_rate_limit(
        self,
        user_id: str,
        tool_name: str,
    ) -> bool:
        """
        Check if rate limit allows execution.

        Args:
            user_id: User ID
            tool_name: Tool name

        Returns:
            bool: True if rate limit allows execution
        """
        key = (user_id, tool_name)

        # No rate limit set
        if key not in self._rate_limits:
            return True

        limit = self._rate_limits[key]
        max_calls = limit["max_calls"]
        window_seconds = limit["window_seconds"]

        # Get current time
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window_seconds)

        # Filter old calls
        calls = self._rate_limit_calls[key]
        calls[:] = [call for call in calls if call > window_start]

        # Check if limit exceeded
        return len(calls) < max_calls

    def record_rate_limit_call(
        self,
        user_id: str,
        tool_name: str,
    ) -> None:
        """
        Record a call for rate limiting.

        Args:
            user_id: User ID
            tool_name: Tool name
        """
        key = (user_id, tool_name)
        self._rate_limit_calls[key].append(datetime.utcnow())

    # -------------------------------------------------------------------------
    # Access Checking
    # -------------------------------------------------------------------------

    def check_access(
        self,
        user_id: str,
        tool_name: str,
        metadata: Optional[ToolMetadata] = None,
    ) -> bool:
        """
        Check if a user has access to a tool.

        This checks in order:
        1. Blacklist (deny if tool is blacklisted)
        2. Whitelist (deny if whitelist is set and tool not in it)
        3. ACL (deny if ACL entry denies, allow if ACL entry allows)
        4. Risk level (deny if tool risk level is too high)
        5. Default allow

        Args:
            user_id: User ID
            tool_name: Tool name
            metadata: Optional tool metadata for risk level checking

        Returns:
            bool: True if access is granted
        """
        # Check blacklist first
        if tool_name in self._blacklist:
            return False

        # Check whitelist
        if self._whitelist is not None and tool_name not in self._whitelist:
            return False

        # Check ACL (wildcard user)
        acl_key_wildcard_user = ("*", tool_name)
        if acl_key_wildcard_user in self._acl:
            entry = self._acl[acl_key_wildcard_user]
            if entry.permission == PermissionType.DENY:
                return False
            if entry.permission == PermissionType.ALLOW:
                # Continue checking other rules
                pass

        # Check ACL (wildcard tool)
        acl_key_wildcard_tool = (user_id, "*")
        if acl_key_wildcard_tool in self._acl:
            entry = self._acl[acl_key_wildcard_tool]
            if entry.permission == PermissionType.DENY:
                return False
            if entry.permission == PermissionType.ALLOW:
                # Continue checking other rules
                pass

        # Check ACL (specific user and tool)
        acl_key = (user_id, tool_name)
        if acl_key in self._acl:
            entry = self._acl[acl_key]
            if entry.permission == PermissionType.DENY:
                return False
            if entry.permission == PermissionType.ALLOW:
                return True

        # Check risk level
        if metadata and not self.check_access_by_risk(metadata):
            return False

        # Default allow
        return True

    # -------------------------------------------------------------------------
    # Management
    # -------------------------------------------------------------------------

    def clear_all(self) -> None:
        """Clear all policies."""
        self._whitelist = None
        self._blacklist = []
        self._acl = {}
        self._max_risk_level = None
        self._rate_limits = {}
        self._rate_limit_calls = defaultdict(list)
