"""
Tests for InputValidator

This module tests the input validation functionality.
"""

import pytest
from pydantic import BaseModel, Field, ValidationError

from src.common.types.tool_types import ToolParameter, ToolSchema
from src.tool_registry_v2.security.input_validator import InputValidator


# =============================================================================
# Test Schemas
# =============================================================================

class TestInputSchema(BaseModel):
    """Test input schema."""
    name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=0, le=150)
    email: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    optional_field: str = Field(default="default_value")


class DangerousInputSchema(BaseModel):
    """Schema for testing dangerous input detection."""
    command: str


# =============================================================================
# InputValidator Tests
# =============================================================================

class TestInputValidator:
    """Test cases for InputValidator."""

    @pytest.fixture
    def validator(self):
        """Create a fresh validator instance for each test."""
        return InputValidator()

    def test_validate_with_schema_success(self, validator):
        """Test validation with valid input."""
        input_data = {
            "name": "John Doe",
            "age": 30,
            "email": "john@example.com",
        }

        result = validator.validate_with_schema(
            input_data=input_data,
            schema_class=TestInputSchema,
        )

        assert result.is_valid is True
        assert result.validated_data is not None
        assert result.validated_data["name"] == "John Doe"
        assert result.validated_data["age"] == 30

    def test_validate_with_schema_failure(self, validator):
        """Test validation with invalid input."""
        input_data = {
            "name": "",  # Too short
            "age": 200,  # Too high
            "email": "invalid-email",  # Invalid format
        }

        result = validator.validate_with_schema(
            input_data=input_data,
            schema_class=TestInputSchema,
        )

        assert result.is_valid is False
        assert result.errors is not None
        assert len(result.errors) > 0

    def test_validate_with_optional_field(self, validator):
        """Test validation with optional field."""
        input_data = {
            "name": "Jane Doe",
            "age": 25,
            "email": "jane@example.com",
        }

        result = validator.validate_with_schema(
            input_data=input_data,
            schema_class=TestInputSchema,
        )

        assert result.is_valid is True
        assert result.validated_data["optional_field"] == "default_value"

    def test_sanitize_input(self, validator):
        """Test input sanitization."""
        input_data = {
            "name": "  John Doe  ",
            "description": "<script>alert('xss')</script>",
        }

        sanitized = validator.sanitize_input(input_data)

        # Whitespace should be stripped
        assert sanitized["name"] == "John Doe"
        # HTML tags should be removed
        assert "<script>" not in sanitized["description"]

    def test_detect_injection_attack_sql(self, validator):
        """Test SQL injection detection."""
        dangerous_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "admin'/*",
        ]

        for dangerous_input in dangerous_inputs:
            is_dangerous = validator.detect_injection_attack(dangerous_input)
            assert is_dangerous is True

    def test_detect_injection_attack_xss(self, validator):
        """Test XSS attack detection."""
        dangerous_inputs = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "<svg onload=alert('xss')>",
            "javascript:alert('xss')",
        ]

        for dangerous_input in dangerous_inputs:
            is_dangerous = validator.detect_injection_attack(dangerous_input)
            assert is_dangerous is True

    def test_detect_injection_attack_command(self, validator):
        """Test command injection detection."""
        dangerous_inputs = [
            "; rm -rf /",
            "| cat /etc/passwd",
            "$(whoami)",
            "`ls -la`",
        ]

        for dangerous_input in dangerous_inputs:
            is_dangerous = validator.detect_injection_attack(dangerous_input)
            assert is_dangerous is True

    def test_detect_injection_attack_safe_input(self, validator):
        """Test that safe input is not flagged."""
        safe_inputs = [
            "This is a safe string",
            "Email: user@example.com",
            "Age: 30",
            "Hello, World!",
        ]

        for safe_input in safe_inputs:
            is_dangerous = validator.detect_injection_attack(safe_input)
            assert is_dangerous is False

    def test_validate_json_schema(self, validator):
        """Test validation with JSON schema."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "number", "minimum": 0},
            },
            "required": ["name", "age"],
        }

        # Valid input
        valid_input = {"name": "John", "age": 30}
        result = validator.validate_json_schema(valid_input, schema)
        assert result.is_valid is True

        # Invalid input
        invalid_input = {"name": "John", "age": -1}
        result = validator.validate_json_schema(invalid_input, schema)
        assert result.is_valid is False

    def test_validate_tool_parameters(self, validator):
        """Test tool parameter validation."""
        parameters = [
            ToolParameter(
                name="query",
                type="string",
                description="Search query",
                required=True,
                min_length=1,
                max_length=100,
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="Result limit",
                required=False,
                default=10,
                minimum=1,
                maximum=100,
            ),
        ]

        # Valid input
        valid_input = {"query": "test", "limit": 20}
        result = validator.validate_parameters(valid_input, parameters)
        assert result.is_valid is True

        # Invalid input (missing required field)
        invalid_input = {"limit": 20}
        result = validator.validate_parameters(invalid_input, parameters)
        assert result.is_valid is False
