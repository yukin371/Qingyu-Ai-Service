"""
Input Validator

This module provides input validation and sanitization for tool execution:
- Pydantic schema validation
- Input sanitization
- Injection attack detection (SQL, XSS, command injection)
"""

import html
import re
import json
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, ValidationError

from src.common.types.tool_types import ToolParameter


# =============================================================================
# Validation Result
# =============================================================================

class ValidationResult:
    """
    Result of input validation.

    Attributes:
        is_valid: Whether validation passed
        validated_data: Validated and sanitized data
        errors: List of validation errors
    """

    def __init__(
        self,
        is_valid: bool,
        validated_data: Optional[Dict[str, Any]] = None,
        errors: Optional[List[str]] = None,
    ):
        self.is_valid = is_valid
        self.validated_data = validated_data
        self.errors = errors or []


# =============================================================================
# Input Validator
# =============================================================================

class InputValidator:
    """
    Input validation and sanitization manager.

    Features:
    - Pydantic schema validation
    - JSON schema validation
    - Input sanitization (HTML stripping, whitespace trimming)
    - Injection attack detection (SQL, XSS, command injection)

    Example:
        ```python
        validator = InputValidator()

        # Validate with Pydantic schema
        result = validator.validate_with_schema(
            input_data={"name": "John", "age": 30},
            schema_class=UserInputSchema,
        )

        if result.is_valid:
            # Use validated data
            pass
        ```
    """

    # Injection attack patterns
    SQL_INJECTION_PATTERNS = [
        r";\s*DROP\s+TABLE",
        r";\s*DELETE\s+FROM",
        r"'\s*OR\s+'",
        r"'\s*OR\s*1=1",
        r"--",
        r"/\*",
        r"UNION\s+SELECT",
        r"='.*'",  # Generic OR pattern
    ]

    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"<iframe[^>]*>.*?</iframe>",
        r"<object[^>]*>.*?</object>",
        r"<embed[^>]*>.*?</embed>",
        r"javascript:",
        r"onerror\s*=",
        r"onload\s*=",
        r"onclick\s*=",
        r"<svg[^>]*>.*?</svg>",
    ]

    COMMAND_INJECTION_PATTERNS = [
        r";\s*(rm|del|format|shutdown)",
        r"\|\s*(cat|type|ls|dir)",
        r"\$\([^)]*\)",
        r"`[^`]*`",
        r"&\s*(rm|del|format)",
        r">\s*/dev/",
    ]

    def __init__(self):
        """Initialize the input validator."""
        # Compile regex patterns for performance
        self._sql_patterns = [re.compile(p, re.IGNORECASE) for p in self.SQL_INJECTION_PATTERNS]
        self._xss_patterns = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in self.XSS_PATTERNS]
        self._cmd_patterns = [re.compile(p, re.IGNORECASE) for p in self.COMMAND_INJECTION_PATTERNS]

    # -------------------------------------------------------------------------
    # Schema Validation
    # -------------------------------------------------------------------------

    def validate_with_schema(
        self,
        input_data: Dict[str, Any],
        schema_class: Type[BaseModel],
    ) -> ValidationResult:
        """
        Validate input data using a Pydantic schema.

        Args:
            input_data: Input data to validate
            schema_class: Pydantic BaseModel class

        Returns:
            ValidationResult: Validation result
        """
        try:
            validated = schema_class(**input_data)
            return ValidationResult(
                is_valid=True,
                validated_data=validated.model_dump(),
            )
        except ValidationError as e:
            errors = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
            return ValidationResult(
                is_valid=False,
                errors=errors,
            )

    def validate_json_schema(
        self,
        input_data: Dict[str, Any],
        json_schema: Dict[str, Any],
    ) -> ValidationResult:
        """
        Validate input data using a JSON schema.

        Args:
            input_data: Input data to validate
            json_schema: JSON schema definition

        Returns:
            ValidationResult: Validation result
        """
        try:
            # Use jsonschema library if available
            try:
                from jsonschema import validate as jsonschema_validate
                from jsonschema.exceptions import ValidationError as JSONSchemaValidationError

                jsonschema_validate(instance=input_data, schema=json_schema)
                return ValidationResult(
                    is_valid=True,
                    validated_data=input_data,
                )
            except ImportError:
                # Fallback: Basic validation
                return self._basic_json_schema_validation(input_data, json_schema)
            except JSONSchemaValidationError as e:
                return ValidationResult(
                    is_valid=False,
                    errors=[str(e)],
                )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
            )

    def _basic_json_schema_validation(
        self,
        input_data: Dict[str, Any],
        json_schema: Dict[str, Any],
    ) -> ValidationResult:
        """Basic JSON schema validation (fallback)."""
        errors = []

        # Check required fields
        required = json_schema.get("required", [])
        for field in required:
            if field not in input_data:
                errors.append(f"Missing required field: {field}")

        # Check types
        properties = json_schema.get("properties", {})
        for field, value in input_data.items():
            if field in properties:
                field_schema = properties[field]
                expected_type = field_schema.get("type")

                if expected_type == "string" and not isinstance(value, str):
                    errors.append(f"Field '{field}' must be a string")
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    errors.append(f"Field '{field}' must be a number")
                elif expected_type == "integer" and not isinstance(value, int):
                    errors.append(f"Field '{field}' must be an integer")
                elif expected_type == "boolean" and not isinstance(value, bool):
                    errors.append(f"Field '{field}' must be a boolean")

                # Check minimum/maximum for numbers
                if expected_type in ["number", "integer"]:
                    if "minimum" in field_schema and value < field_schema["minimum"]:
                        errors.append(f"Field '{field}' is below minimum")
                    if "maximum" in field_schema and value > field_schema["maximum"]:
                        errors.append(f"Field '{field}' is above maximum")

        if errors:
            return ValidationResult(is_valid=False, errors=errors)
        return ValidationResult(is_valid=True, validated_data=input_data)

    def validate_parameters(
        self,
        input_data: Dict[str, Any],
        parameters: List[ToolParameter],
    ) -> ValidationResult:
        """
        Validate input data against tool parameter definitions.

        Args:
            input_data: Input data to validate
            parameters: List of tool parameter definitions

        Returns:
            ValidationResult: Validation result
        """
        errors = []
        validated_data = {}

        for param in parameters:
            param_name = param.name

            # Check required fields
            if param.required and param_name not in input_data:
                errors.append(f"Missing required parameter: {param_name}")
                continue

            # Skip validation for missing optional fields
            if param_name not in input_data:
                if param.default is not None:
                    validated_data[param_name] = param.default
                continue

            value = input_data[param_name]

            # Type validation
            if param.type == "string":
                if not isinstance(value, str):
                    errors.append(f"Parameter '{param_name}' must be a string")
                else:
                    # Check length constraints
                    if hasattr(param, 'min_length') and len(value) < param.min_length:
                        errors.append(f"Parameter '{param_name}' is too short")
                    if hasattr(param, 'max_length') and len(value) > param.max_length:
                        errors.append(f"Parameter '{param_name}' is too long")
                    validated_data[param_name] = value

            elif param.type == "integer":
                if not isinstance(value, int):
                    errors.append(f"Parameter '{param_name}' must be an integer")
                else:
                    # Check range constraints
                    if hasattr(param, 'minimum') and value < param.minimum:
                        errors.append(f"Parameter '{param_name}' is below minimum")
                    if hasattr(param, 'maximum') and value > param.maximum:
                        errors.append(f"Parameter '{param_name}' is above maximum")
                    validated_data[param_name] = value

            elif param.type == "number":
                if not isinstance(value, (int, float)):
                    errors.append(f"Parameter '{param_name}' must be a number")
                else:
                    validated_data[param_name] = value

            elif param.type == "boolean":
                if not isinstance(value, bool):
                    errors.append(f"Parameter '{param_name}' must be a boolean")
                else:
                    validated_data[param_name] = value

            else:
                # Unknown type, pass through
                validated_data[param_name] = value

        if errors:
            return ValidationResult(is_valid=False, errors=errors)
        return ValidationResult(is_valid=True, validated_data=validated_data)

    # -------------------------------------------------------------------------
    # Input Sanitization
    # -------------------------------------------------------------------------

    def sanitize_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize input data by removing potentially dangerous content.

        Args:
            input_data: Input data to sanitize

        Returns:
            Dict[str, Any]: Sanitized input data
        """
        sanitized = {}

        for key, value in input_data.items():
            if isinstance(value, str):
                # Strip whitespace
                value = value.strip()

                # Escape HTML
                value = html.escape(value)

                # Remove HTML tags
                value = re.sub(r'<[^>]+>', '', value)

                sanitized[key] = value
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_input(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self.sanitize_item(item) for item in value
                ]
            else:
                sanitized[key] = value

        return sanitized

    def sanitize_item(self, item: Any) -> Any:
        """Sanitize a single item."""
        if isinstance(item, str):
            item = item.strip()
            item = html.escape(item)
            item = re.sub(r'<[^>]+>', '', item)
            return item
        elif isinstance(item, dict):
            return self.sanitize_input(item)
        elif isinstance(item, list):
            return [self.sanitize_item(i) for i in item]
        return item

    # -------------------------------------------------------------------------
    # Injection Attack Detection
    # -------------------------------------------------------------------------

    def detect_injection_attack(self, input_string: str) -> bool:
        """
        Detect if input string contains injection attacks.

        Args:
            input_string: Input string to check

        Returns:
            bool: True if injection attack is detected
        """
        if not isinstance(input_string, str):
            return False

        # Check SQL injection
        for pattern in self._sql_patterns:
            if pattern.search(input_string):
                return True

        # Check XSS
        for pattern in self._xss_patterns:
            if pattern.search(input_string):
                return True

        # Check command injection
        for pattern in self._cmd_patterns:
            if pattern.search(input_string):
                return True

        return False
