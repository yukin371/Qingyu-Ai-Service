"""
Tests for feature flags
"""

import pytest

from src.config.feature_flags import FeatureFlags, get_feature_flags, configure_feature_flags


class TestFeatureFlags:
    """Test FeatureFlags class."""

    def test_default_flags(self):
        """Test default feature flag values."""
        flags = FeatureFlags()
        assert flags.langchain_tracing is False
        assert flags.enable_workflows is True
        assert flags.enable_embeddings is False

    def test_is_enabled(self):
        """Test is_enabled method."""
        flags = FeatureFlags(enable_workflows=True)
        assert flags.is_enabled("enable_workflows") is True
        assert flags.is_enabled("enable_embeddings") is False

    def test_enable_disable(self):
        """Test enable and disable methods."""
        flags = FeatureFlags()
        assert flags.enable_embeddings is False

        flags.enable("enable_embeddings")
        assert flags.enable_embeddings is True

        flags.disable("enable_embeddings")
        assert flags.enable_embeddings is False

    def test_get_enabled_features(self):
        """Test get_enabled_features method."""
        flags = FeatureFlags(
            enable_workflows=True,
            enable_embeddings=True,
            enable_caching=True
        )
        enabled = flags.get_enabled_features()
        # Check that our explicitly enabled features are in the list
        assert "enable_workflows" in enabled
        assert "enable_embeddings" in enabled
        assert "enable_caching" in enabled
        # Note: There are other default enabled features (enable_rate_limiting, etc.)


class TestConfigureFeatureFlags:
    """Test configure_feature_flags function."""

    def test_configure_flags(self):
        """Test configuring feature flags."""
        flags = configure_feature_flags(
            enable_workflows=False,
            enable_embeddings=True
        )
        assert flags.enable_workflows is False
        assert flags.enable_embeddings is True


class TestGetFeatureFlags:
    """Test get_feature_flags function."""

    def test_get_flags_cached(self):
        """Test that get_feature_flags returns cached instance."""
        flags1 = get_feature_flags()
        flags2 = get_feature_flags()
        assert flags1 is flags2
