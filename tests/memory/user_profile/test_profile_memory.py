"""
Test suite for User Profile Memory

Tests user profile management including preferences, tags, and behavior tracking.
"""

import pytest
from datetime import datetime
from src.memory.user_profile.profile_memory import (
    UserProfile,
    UserProfileMemory,
    PreferenceUpdateError,
    TagLimitExceededError,
)


@pytest.fixture
def profile_memory():
    """Create a UserProfileMemory instance for testing."""
    memory = UserProfileMemory()
    yield memory
    # Cleanup
    # Note: This is synchronous cleanup for simplicity


class TestUserProfile:
    """Test UserProfile data model."""

    def test_user_profile_creation(self):
        """Test creating a user profile."""
        profile = UserProfile(
            user_id="test_user",
            preferences={"theme": "dark", "language": "zh-CN"},
            tags=["reader", "premium"],
            behavior_stats={"login_count": 10, "last_login": datetime.now().isoformat()},
        )

        assert profile.user_id == "test_user"
        assert profile.preferences["theme"] == "dark"
        assert "reader" in profile.tags
        assert profile.behavior_stats["login_count"] == 10
        assert profile.created_at is not None
        assert profile.updated_at is not None

    def test_user_profile_default_values(self):
        """Test user profile with default values."""
        profile = UserProfile(user_id="test_user")

        assert profile.user_id == "test_user"
        assert profile.preferences == {}
        assert profile.tags == []
        assert profile.behavior_stats == {}


class TestUserProfileMemory:
    """Test UserProfileMemory functionality."""

    @pytest.mark.asyncio
    async def test_create_and_get_profile(self, profile_memory):
        """Test creating and retrieving a user profile."""
        user_id = "test_user_1"

        # Create profile
        profile = await profile_memory.get_profile(user_id)
        assert profile is not None
        assert profile.user_id == user_id
        assert profile.preferences == {}
        assert profile.tags == []

    @pytest.mark.asyncio
    async def test_update_preferences(self, profile_memory):
        """Test updating user preferences."""
        user_id = "test_user_1"

        # Update preferences
        await profile_memory.update_preferences(
            user_id, {"theme": "dark", "language": "zh-CN"}
        )

        # Verify update
        profile = await profile_memory.get_profile(user_id)
        assert profile.preferences["theme"] == "dark"
        assert profile.preferences["language"] == "zh-CN"

        # Partial update
        await profile_memory.update_preferences(user_id, {"theme": "light"})
        profile = await profile_memory.get_profile(user_id)
        assert profile.preferences["theme"] == "light"
        assert profile.preferences["language"] == "zh-CN"  # Should preserve

    @pytest.mark.asyncio
    async def test_add_tags(self, profile_memory):
        """Test adding tags to user profile."""
        user_id = "test_user_1"

        # Add tags
        await profile_memory.add_tags(user_id, ["reader", "writer"])
        profile = await profile_memory.get_profile(user_id)
        assert "reader" in profile.tags
        assert "writer" in profile.tags

        # Add more tags
        await profile_memory.add_tags(user_id, ["premium"])
        profile = await profile_memory.get_profile(user_id)
        assert "premium" in profile.tags
        assert len(profile.tags) == 3

        # Duplicate tag should not be added
        await profile_memory.add_tags(user_id, ["reader"])
        profile = await profile_memory.get_profile(user_id)
        assert len(profile.tags) == 3

    @pytest.mark.asyncio
    async def test_remove_tags(self, profile_memory):
        """Test removing tags from user profile."""
        user_id = "test_user_1"

        # Add tags
        await profile_memory.add_tags(user_id, ["reader", "writer", "premium"])
        profile = await profile_memory.get_profile(user_id)
        assert len(profile.tags) == 3

        # Remove tag
        await profile_memory.remove_tags(user_id, ["writer"])
        profile = await profile_memory.get_profile(user_id)
        assert "writer" not in profile.tags
        assert "reader" in profile.tags
        assert len(profile.tags) == 2

    @pytest.mark.asyncio
    async def test_record_behavior(self, profile_memory):
        """Test recording user behavior."""
        user_id = "test_user_1"

        # Record behaviors
        await profile_memory.record_behavior(
            user_id, {"action": "login", "timestamp": datetime.now().isoformat()}
        )
        await profile_memory.record_behavior(
            user_id, {"action": "view_book", "book_id": "123"}
        )

        # Verify behavior stats
        profile = await profile_memory.get_profile(user_id)
        assert "login_count" in profile.behavior_stats
        assert profile.behavior_stats["login_count"] >= 1

    @pytest.mark.asyncio
    async def test_get_preference(self, profile_memory):
        """Test getting specific preference."""
        user_id = "test_user_1"

        # Set preferences
        await profile_memory.update_preferences(
            user_id, {"theme": "dark", "language": "zh-CN"}
        )

        # Get specific preference
        theme = await profile_memory.get_preference(user_id, "theme")
        assert theme == "dark"

        language = await profile_memory.get_preference(user_id, "language")
        assert language == "zh-CN"

        # Non-existent preference
        nonexistent = await profile_memory.get_preference(user_id, "nonexistent")
        assert nonexistent is None

    @pytest.mark.asyncio
    async def test_increment_stat(self, profile_memory):
        """Test incrementing behavior statistics."""
        user_id = "test_user_1"

        # Increment stat
        await profile_memory.increment_stat(user_id, "login_count")
        profile = await profile_memory.get_profile(user_id)
        assert profile.behavior_stats["login_count"] == 1

        # Increment again
        await profile_memory.increment_stat(user_id, "login_count", 5)
        profile = await profile_memory.get_profile(user_id)
        assert profile.behavior_stats["login_count"] == 6

    @pytest.mark.asyncio
    async def test_get_top_preferences(self, profile_memory):
        """Test getting top preferences by category."""
        user_id = "test_user_1"

        # Add preferences
        await profile_memory.update_preferences(
            user_id,
            {
                "favorite_genres": ["fantasy", "scifi", "romance"],
                "favorite_authors": ["author1", "author2"],
            },
        )

        # Get top genres
        genres = await profile_memory.get_top_preferences(user_id, "favorite_genres", 2)
        assert len(genres) == 2
        assert "fantasy" in genres

    @pytest.mark.asyncio
    async def test_delete_profile(self, profile_memory):
        """Test deleting user profile."""
        user_id = "test_user_2"

        # Create profile
        await profile_memory.update_preferences(user_id, {"theme": "dark"})
        profile = await profile_memory.get_profile(user_id)
        assert profile is not None

        # Delete profile
        await profile_memory.delete_profile(user_id)
        profile = await profile_memory.get_profile(user_id)
        # Should create new empty profile instead of returning None
        assert profile is not None
        assert profile.preferences == {}

    @pytest.mark.asyncio
    async def test_profile_updated_timestamp(self, profile_memory):
        """Test that updated_at timestamp changes on modifications."""
        user_id = "test_user_1"

        # Get profile
        profile = await profile_memory.get_profile(user_id)
        original_time = profile.updated_at

        # Wait a bit (timing might be tricky in tests)
        import asyncio

        await asyncio.sleep(0.01)

        # Update profile
        await profile_memory.update_preferences(user_id, {"theme": "dark"})
        profile = await profile_memory.get_profile(user_id)

        # Updated timestamp should be different
        assert profile.updated_at > original_time

    @pytest.mark.asyncio
    async def test_get_all_tags(self, profile_memory):
        """Test getting all user tags."""
        user_id = "test_user_1"

        # Add tags
        await profile_memory.add_tags(user_id, ["reader", "writer", "premium"])

        # Get all tags
        tags = await profile_memory.get_all_tags(user_id)
        assert set(tags) == {"reader", "writer", "premium"}

    @pytest.mark.asyncio
    async def test_has_tag(self, profile_memory):
        """Test checking if user has specific tag."""
        user_id = "test_user_1"

        # Add tags
        await profile_memory.add_tags(user_id, ["reader", "premium"])

        # Check tags
        assert await profile_memory.has_tag(user_id, "reader") is True
        assert await profile_memory.has_tag(user_id, "premium") is True
        assert await profile_memory.has_tag(user_id, "writer") is False

    @pytest.mark.asyncio
    async def test_merge_preferences(self, profile_memory):
        """Test merging preferences."""
        user_id = "test_user_1"

        # Set initial preferences
        await profile_memory.update_preferences(
            user_id, {"theme": "dark", "language": "zh-CN"}
        )

        # Merge preferences
        await profile_memory.merge_preferences(
            user_id, {"theme": "light", "font_size": 14}
        )

        # Verify merge
        profile = await profile_memory.get_profile(user_id)
        assert profile.preferences["theme"] == "light"  # Overwritten
        assert profile.preferences["language"] == "zh-CN"  # Preserved
        assert profile.preferences["font_size"] == 14  # Added

    @pytest.mark.asyncio
    async def test_clear_preferences(self, profile_memory):
        """Test clearing all preferences."""
        user_id = "test_user_1"

        # Set preferences
        await profile_memory.update_preferences(
            user_id, {"theme": "dark", "language": "zh-CN"}
        )

        # Clear preferences
        await profile_memory.clear_preferences(user_id)
        profile = await profile_memory.get_profile(user_id)

        assert profile.preferences == {}

    @pytest.mark.asyncio
    async def test_tag_limit(self, profile_memory):
        """Test tag limit enforcement."""
        user_id = "test_user_1"

        # Try to add more tags than limit
        tags = [f"tag_{i}" for i in range(100)]  # More than default limit

        with pytest.raises(TagLimitExceededError):
            await profile_memory.add_tags(user_id, tags)

    @pytest.mark.asyncio
    async def test_get_behavior_summary(self, profile_memory):
        """Test getting behavior summary."""
        user_id = "test_user_1"

        # Record behaviors
        await profile_memory.record_behavior(user_id, {"action": "login"})
        await profile_memory.record_behavior(user_id, {"action": "view_book"})
        await profile_memory.record_behavior(user_id, {"action": "login"})

        # Get summary
        summary = await profile_memory.get_behavior_summary(user_id)
        assert summary["stats"]["login_count"] >= 2
        assert "last_activity" in summary["stats"]
