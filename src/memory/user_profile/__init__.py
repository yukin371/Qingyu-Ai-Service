"""
User Profile Submodule

This module provides user profile and preference management.

Features:
- UserProfileMemory: User profile storage and management
- UserProfile: User profile data model
- Preference tracking and learning
- Behavior statistics
- Tag management
"""

from src.memory.user_profile.profile_memory import (
    UserProfile,
    UserProfileMemory,
    PreferenceUpdateError,
    TagLimitExceededError,
)

__all__ = [
    "UserProfile",
    "UserProfileMemory",
    "PreferenceUpdateError",
    "TagLimitExceededError",
]
