"""
Dynamic Workflow State Definition

Provides dynamic state schema generation for LangGraph workflows.
Supports both TypedDict and Pydantic models.
"""
from typing import Any, Dict, List, Optional, Type, TypedDict as TypedDictType
from pydantic import BaseModel, Field
import inspect


class DynamicStateDefinition:
    """
    Dynamic state definition for workflows

    Allows defining state schemas at runtime instead of hardcoding them.
    """

    def __init__(
        self,
        name: str,
        fields: Dict[str, Dict[str, Any]],
        description: Optional[str] = None,
        version: str = "1.0"
    ):
        """
        Initialize state definition

        Args:
            name: Name of the state class
            fields: Dictionary of field definitions
                Each field should have:
                - type: Field type (str, int, list, dict, etc.)
                - default: Default value (optional)
                - description: Field description (optional)
                - validation: Validation rules (optional)
            description: Description of the state
            version: Schema version
        """
        self.name = name
        self.fields = fields
        self.description = description
        self.version = version

    def to_dict(self) -> Dict[str, Any]:
        """Convert definition to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "fields": self.fields
        }


class StateSchemaGenerator:
    """
    Generate state schemas from definitions

    Supports both Pydantic and TypedDict schemas.
    """

    def __init__(self):
        """Initialize schema generator"""
        self._type_mapping = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "Any": Any,
        }

    def generate_pydantic_schema(
        self,
        definition: DynamicStateDefinition
    ) -> Type[BaseModel]:
        """
        Generate a Pydantic model from state definition

        Args:
            definition: State definition

        Returns:
            Generated Pydantic model class
        """
        # Prepare field definitions
        fields = {}
        for field_name, field_def in definition.fields.items():
            field_type = self._resolve_type(field_def.get("type", "Any"))
            default_value = field_def.get("default", ...)

            # Build Field with validation
            field_kwargs = {"default": default_value}

            # Add description
            if "description" in field_def:
                field_kwargs["description"] = field_def["description"]

            # Add validation rules
            for key in ["ge", "le", "gt", "lt", "multiple_of"]:
                if key in field_def:
                    field_kwargs[key] = field_def[key]

            # Add pattern for strings
            if "pattern" in field_def:
                field_kwargs["pattern"] = field_def["pattern"]

            # Add min/max for strings/lists
            if "min_length" in field_def:
                field_kwargs["min_length"] = field_def["min_length"]
            if "max_length" in field_def:
                field_kwargs["max_length"] = field_def["max_length"]

            fields[field_name] = (field_type, Field(**field_kwargs))

        # Create the model class dynamically
        model_class = type(
            definition.name,
            (BaseModel,),
            {
                "__annotations__": {name: field_type for name, (field_type, _) in fields.items()},
                **{name: field_def for name, (_, field_def) in fields.items()}
            }
        )

        # Add docstring
        if definition.description:
            model_class.__doc__ = definition.description

        return model_class

    def generate_typeddict_schema(
        self,
        definition: DynamicStateDefinition
    ) -> Type[TypedDictType]:
        """
        Generate a TypedDict from state definition

        Args:
            definition: State definition

        Returns:
            Generated TypedDict class
        """
        # Prepare annotations
        annotations = {}
        for field_name, field_def in definition.fields.items():
            field_type = self._resolve_type(field_def.get("type", "Any"))
            annotations[field_name] = field_type

        # Create the TypedDict class
        typed_dict_class = TypedDictType(
            definition.name,
            annotations,
            total=sum(
                "default" not in field_def
                for field_def in definition.fields.values()
            )
        )

        # Add docstring
        if definition.description:
            typed_dict_class.__doc__ = definition.description

        return typed_dict_class

    def _resolve_type(self, type_str: str) -> Type:
        """
        Resolve type string to actual type

        Args:
            type_str: Type string (e.g., "str", "int", "list[str]")

        Returns:
            Resolved type
        """
        # Simple types
        if type_str in self._type_mapping:
            return self._type_mapping[type_str]

        # List types
        if type_str.startswith("list[") and type_str.endswith("]"):
            inner_type = type_str[5:-1]
            inner = self._resolve_type(inner_type)
            return List[inner]

        # Dict types
        if type_str.startswith("dict[") and type_str.endswith("]"):
            # dict[key, value] format
            parts = type_str[5:-1].split(",")
            if len(parts) == 2:
                key_type = self._resolve_type(parts[0].strip())
                value_type = self._resolve_type(parts[1].strip())
                return Dict[key_type, value_type]

        # Default to Any
        return Any


def create_state_schema(
    name: str,
    fields: Dict[str, Dict[str, Any]],
    description: Optional[str] = None,
    version: str = "1.0",
    use_pydantic: bool = True
) -> Type:
    """
    Convenience function to create a state schema

    Args:
        name: Name of the state class
        fields: Field definitions
        description: Description of the state
        version: Schema version
        use_pydantic: If True, use Pydantic; otherwise use TypedDict

    Returns:
        Generated schema class
    """
    definition = DynamicStateDefinition(
        name=name,
        fields=fields,
        description=description,
        version=version
    )

    generator = StateSchemaGenerator()

    if use_pydantic:
        return generator.generate_pydantic_schema(definition)
    else:
        return generator.generate_typeddict_schema(definition)


def create_typeddict_schema(
    name: str,
    fields: Dict[str, Dict[str, Any]],
    description: Optional[str] = None,
    version: str = "1.0"
) -> Type[TypedDictType]:
    """
    Convenience function to create a TypedDict schema

    Args:
        name: Name of the state class
        fields: Field definitions
        description: Description of the state
        version: Schema version

    Returns:
        Generated TypedDict class
    """
    return create_state_schema(
        name=name,
        fields=fields,
        description=description,
        version=version,
        use_pydantic=False
    )
