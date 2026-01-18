"""
Tests for configuration settings
"""

import pytest

from src.config.settings import Settings, get_settings


class TestSettings:
    """Test Settings class."""

    def test_create_default_settings(self):
        """Test creating settings with defaults."""
        settings = Settings()
        assert settings.app_name == "Qingyu AI Service"
        assert settings.app_version == "0.1.0"
        assert settings.debug is False
        assert settings.environment == "development"

    def test_server_settings(self):
        """Test server settings."""
        settings = Settings()
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.workers == 1

    def test_llm_settings(self):
        """Test LLM settings."""
        settings = Settings()
        assert settings.llm_provider == "openai"
        assert settings.llm_model == "gpt-4"
        assert settings.llm_temperature == 0.7

    def test_validate_log_level(self):
        """Test log level validation."""
        settings = Settings(log_level="debug")
        assert settings.log_level == "DEBUG"

        with pytest.raises(ValueError):
            Settings(log_level="invalid")

    def test_validate_environment(self):
        """Test environment validation."""
        settings = Settings(environment="production")
        assert settings.environment == "production"

        with pytest.raises(ValueError):
            Settings(environment="invalid")


class TestGetSettings:
    """Test get_settings function."""

    def test_get_settings_cached(self):
        """Test that get_settings returns cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2
