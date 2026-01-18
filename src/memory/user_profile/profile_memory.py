"""
User Profile Memory Implementation

Manages user profiles including preferences, tags, and behavior tracking.
Compatible with LangChain 1.2.x memory architecture.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
import json
from collections import defaultdict


class PreferenceUpdateError(Exception):
    """Raised when preference update fails."""

    pass


class TagLimitExceededError(Exception):
    """Raised when tag limit is exceeded."""

    pass


class UserProfile(BaseModel):
    """
    User profile model.

    Attributes:
        user_id: Unique user identifier
        preferences: User preferences and settings
        tags: User tags for categorization
        behavior_stats: User behavior statistics
        created_at: Profile creation timestamp
        updated_at: Last update timestamp
    """

    user_id: str = Field(..., description="Unique user identifier")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences")
    tags: List[str] = Field(default_factory=list, description="User tags")
    behavior_stats: Dict[str, Any] = Field(default_factory=dict, description="Behavior statistics")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class UserProfileMemory:
    """
    User profile memory manager.

    Provides comprehensive user profile management including:
    - Preference management (get, set, update, merge)
    - Tag management (add, remove, check)
    - Behavior tracking and statistics
    - Profile persistence

    Example:
        ```python
        memory = UserProfileMemory()

        # Update preferences
        await memory.update_preferences("user123", {"theme": "dark"})

        # Add tags
        await memory.add_tags("user123", ["reader", "premium"])

        # Record behavior
        await memory.record_behavior("user123", {"action": "login"})

        # Get profile
        profile = await memory.get_profile("user123")
        ```
    """

    def __init__(self, max_tags: int = 50):
        """
        Initialize UserProfileMemory.

        Args:
            max_tags: Maximum number of tags per user
        """
        self.max_tags = max_tags
        self._profiles: Dict[str, UserProfile] = {}
        self._behavior_history: Dict[str, List[Dict]] = defaultdict(list)

    async def get_profile(self, user_id: str) -> UserProfile:
        """
        Get user profile, creating if doesn't exist.

        Args:
            user_id: User identifier

        Returns:
            UserProfile object
        """
        if user_id not in self._profiles:
            self._profiles[user_id] = UserProfile(user_id=user_id)
        return self._profiles[user_id]

    async def update_preferences(
        self, user_id: str, preferences: Dict[str, Any], merge: bool = True
    ) -> UserProfile:
        """
        Update user preferences.

        Args:
            user_id: User identifier
            preferences: Preferences to update
            merge: If True, merge with existing preferences; if False, replace

        Returns:
            Updated UserProfile

        Raises:
            PreferenceUpdateError: If update fails
        """
        try:
            profile = await self.get_profile(user_id)

            if merge:
                profile.preferences.update(preferences)
            else:
                profile.preferences = preferences.copy()

            profile.updated_at = datetime.now()
            return profile

        except Exception as e:
            raise PreferenceUpdateError(f"Failed to update preferences: {e}") from e

    async def merge_preferences(self, user_id: str, preferences: Dict[str, Any]) -> UserProfile:
        """
        Merge preferences with existing ones.

        Args:
            user_id: User identifier
            preferences: Preferences to merge

        Returns:
            Updated UserProfile
        """
        return await self.update_preferences(user_id, preferences, merge=True)

    async def get_preference(self, user_id: str, key: str) -> Optional[Any]:
        """
        Get specific preference value.

        Args:
            user_id: User identifier
            key: Preference key

        Returns:
            Preference value or None if not found
        """
        profile = await self.get_profile(user_id)
        return profile.preferences.get(key)

    async def get_top_preferences(
        self, user_id: str, category: str, limit: int = 5
    ) -> List[Any]:
        """
        Get top preferences from a category.

        Args:
            user_id: User identifier
            category: Preference category (e.g., "favorite_genres")
            limit: Maximum number to return

        Returns:
            List of preference values
        """
        profile = await self.get_profile(user_id)
        values = profile.preferences.get(category, [])

        if isinstance(values, list):
            return values[:limit]
        return [values] if values else []

    async def clear_preferences(self, user_id: str) -> UserProfile:
        """
        Clear all user preferences.

        Args:
            user_id: User identifier

        Returns:
            Updated UserProfile
        """
        profile = await self.get_profile(user_id)
        profile.preferences = {}
        profile.updated_at = datetime.now()
        return profile

    async def add_tags(self, user_id: str, tags: List[str]) -> UserProfile:
        """
        Add tags to user profile.

        Args:
            user_id: User identifier
            tags: Tags to add

        Returns:
            Updated UserProfile

        Raises:
            TagLimitExceededError: If tag limit exceeded
        """
        profile = await self.get_profile(user_id)

        # Check limit
        current_tags = set(profile.tags)
        new_tags = set(tags) - current_tags

        if len(current_tags) + len(new_tags) > self.max_tags:
            raise TagLimitExceededError(
                f"Cannot add {len(new_tags)} tags. "
                f"Maximum {self.max_tags} tags allowed. "
                f"Current: {len(current_tags)}"
            )

        # Add new tags
        for tag in tags:
            if tag not in profile.tags:
                profile.tags.append(tag)

        profile.updated_at = datetime.now()
        return profile

    async def remove_tags(self, user_id: str, tags: List[str]) -> UserProfile:
        """
        Remove tags from user profile.

        Args:
            user_id: User identifier
            tags: Tags to remove

        Returns:
            Updated UserProfile
        """
        profile = await self.get_profile(user_id)

        for tag in tags:
            if tag in profile.tags:
                profile.tags.remove(tag)

        profile.updated_at = datetime.now()
        return profile

    async def get_all_tags(self, user_id: str) -> List[str]:
        """
        Get all user tags.

        Args:
            user_id: User identifier

        Returns:
            List of tags
        """
        profile = await self.get_profile(user_id)
        return profile.tags.copy()

    async def has_tag(self, user_id: str, tag: str) -> bool:
        """
        Check if user has specific tag.

        Args:
            user_id: User identifier
            tag: Tag to check

        Returns:
            True if user has tag
        """
        profile = await self.get_profile(user_id)
        return tag in profile.tags

    async def record_behavior(self, user_id: str, behavior: Dict[str, Any]) -> UserProfile:
        """
        Record user behavior.

        Args:
            user_id: User identifier
            behavior: Behavior data (e.g., {"action": "login", "timestamp": ...})

        Returns:
            Updated UserProfile
        """
        profile = await self.get_profile(user_id)

        # Store in history
        self._behavior_history[user_id].append(behavior)

        # Update stats
        action = behavior.get("action", "unknown")
        stat_key = f"{action}_count"
        profile.behavior_stats[stat_key] = profile.behavior_stats.get(stat_key, 0) + 1
        profile.behavior_stats["last_activity"] = datetime.now().isoformat()

        profile.updated_at = datetime.now()
        return profile

    async def increment_stat(
        self, user_id: str, stat_key: str, amount: int = 1
    ) -> UserProfile:
        """
        Increment behavior statistic.

        Args:
            user_id: User identifier
            stat_key: Statistic key
            amount: Amount to increment

        Returns:
            Updated UserProfile
        """
        profile = await self.get_profile(user_id)
        profile.behavior_stats[stat_key] = profile.behavior_stats.get(stat_key, 0) + amount
        profile.updated_at = datetime.now()
        return profile

    async def get_behavior_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get behavior summary.

        Args:
            user_id: User identifier

        Returns:
            Behavior summary dict
        """
        profile = await self.get_profile(user_id)
        return {
            "stats": profile.behavior_stats.copy(),
            "total_actions": sum(
                v for k, v in profile.behavior_stats.items() if k.endswith("_count")
            ),
            "last_activity": profile.behavior_stats.get("last_activity"),
            "history_count": len(self._behavior_history.get(user_id, [])),
        }

    async def delete_profile(self, user_id: str) -> bool:
        """
        Delete user profile.

        Args:
            user_id: User identifier

        Returns:
            True if deleted
        """
        if user_id in self._profiles:
            del self._profiles[user_id]
        if user_id in self._behavior_history:
            del self._behavior_history[user_id]
        return True

    async def get_all_profiles(self) -> List[UserProfile]:
        """
        Get all user profiles.

        Returns:
            List of all profiles
        """
        return list(self._profiles.values())

    async def search_by_tag(self, tag: str) -> List[UserProfile]:
        """
        Search users by tag.

        Args:
            tag: Tag to search for

        Returns:
            List of profiles with the tag
        """
        return [p for p in self._profiles.values() if tag in p.tags]

    async def search_by_preference(
        self, preference_key: str, preference_value: Any
    ) -> List[UserProfile]:
        """
        Search users by preference.

        Args:
            preference_key: Preference key
            preference_value: Preference value to match

        Returns:
            List of matching profiles
        """
        return [
            p
            for p in self._profiles.values()
            if p.preferences.get(preference_key) == preference_value
        ]

    def to_dict(self, profile: UserProfile) -> Dict[str, Any]:
        """
        Convert profile to dictionary.

        Args:
            profile: UserProfile to convert

        Returns:
            Dictionary representation
        """
        return profile.model_dump()

    def from_dict(self, data: Dict[str, Any]) -> UserProfile:
        """
        Create profile from dictionary.

        Args:
            data: Dictionary data

        Returns:
            UserProfile object
        """
        return UserProfile(**data)
