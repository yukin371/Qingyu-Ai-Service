"""
Tests for dynamic workflow state definition
"""
import pytest
from typing import TypedDict
from pydantic import BaseModel, Field

from src.dynamic_workflows.schema.state_definition import (
    DynamicStateDefinition,
    StateSchemaGenerator,
    create_state_schema,
    create_typeddict_schema,
)


class TestDynamicStateDefinition:
    """Test DynamicStateDefinition"""

    def test_create_state_definition(self):
        """Test creating a state definition"""
        definition = DynamicStateDefinition(
            name="TestState",
            description="Test state for workflow",
            fields={
                "messages": {"type": "list", "default": []},
                "user_input": {"type": "str", "default": ""},
                "count": {"type": "int", "default": 0},
            }
        )

        assert definition.name == "TestState"
        assert definition.description == "Test state for workflow"
        assert "messages" in definition.fields
        assert definition.fields["messages"]["type"] == "list"

    def test_state_definition_with_nested_fields(self):
        """Test state definition with nested fields"""
        definition = DynamicStateDefinition(
            name="NestedState",
            fields={
                "user": {
                    "type": "dict",
                    "fields": {
                        "name": {"type": "str", "default": "Anonymous"},
                        "age": {"type": "int", "default": 0}
                    }
                }
            }
        )

        assert "user" in definition.fields
        assert definition.fields["user"]["type"] == "dict"


class TestStateSchemaGenerator:
    """Test StateSchemaGenerator"""

    def test_generate_pydantic_schema(self):
        """Test generating Pydantic schema"""
        definition = DynamicStateDefinition(
            name="GeneratedState",
            fields={
                "query": {"type": "str", "default": "", "description": "User query"},
                "results": {"type": "list", "default": []},
            }
        )

        generator = StateSchemaGenerator()
        schema_class = generator.generate_pydantic_schema(definition)

        # Verify the generated class
        assert schema_class.__name__ == "GeneratedState"

        # Test instantiation
        instance = schema_class(query="test", results=["a", "b"])
        assert instance.query == "test"
        assert instance.results == ["a", "b"]

    def test_generate_typeddict_schema(self):
        """Test generating TypedDict schema"""
        definition = DynamicStateDefinition(
            name="TypedDictState",
            fields={
                "input": {"type": "str"},
                "output": {"type": "str", "default": ""},
            }
        )

        generator = StateSchemaGenerator()
        schema_class = generator.generate_typeddict_schema(definition)

        # Verify it's a TypedDict
        assert hasattr(schema_class, "__annotations__")

        # Test usage
        instance = schema_class(input="test", output="result")
        assert instance["input"] == "test"
        assert instance["output"] == "result"

    def test_generate_pydantic_with_validation(self):
        """Test generating schema with validation rules"""
        definition = DynamicStateDefinition(
            name="ValidatedState",
            fields={
                "age": {
                    "type": "int",
                    "default": 0,
                    "ge": 0,
                    "le": 150,
                    "description": "User age"
                },
                "email": {
                    "type": "str",
                    "default": "",
                    "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                }
            }
        )

        generator = StateSchemaGenerator()
        schema_class = generator.generate_pydantic_schema(definition)

        # Valid data
        instance = schema_class(age=25, email="test@example.com")
        assert instance.age == 25

        # Invalid age
        with pytest.raises(Exception):
            schema_class(age=-5)

        # Invalid age (too high)
        with pytest.raises(Exception):
            schema_class(age=200)


class TestConvenienceFunctions:
    """Test convenience functions"""

    def test_create_state_schema(self):
        """Test create_state_schema convenience function"""
        schema = create_state_schema(
            name="ConvenienceState",
            fields={
                "value": {"type": "str", "default": "hello"},
                "items": {"type": "list", "default": []}
            }
        )

        instance = schema(value="world")
        assert instance.value == "world"
        assert instance.items == []

    def test_create_typeddict_schema(self):
        """Test create_typeddict_schema convenience function"""
        schema = create_typeddict_schema(
            name="ConvenienceTypedDict",
            fields={
                "key": {"type": "str"},
                "value": {"type": "int", "default": 0}
            }
        )

        instance = schema(key="test", value=42)
        assert instance["key"] == "test"
        assert instance["value"] == 42

    def test_schema_from_dict(self):
        """Test creating schema from dictionary definition"""
        definition = {
            "name": "DictBasedState",
            "description": "State created from dict",
            "fields": {
                "field1": {"type": "str"},
                "field2": {"type": "int", "default": 10}
            }
        }

        schema = create_state_schema(**definition)
        instance = schema(field1="test")
        assert instance.field1 == "test"
        assert instance.field2 == 10
