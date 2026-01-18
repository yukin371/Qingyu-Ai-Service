"""
YAML Workflow Loader

Load workflow definitions from YAML files.
"""
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field
import yaml
import os
from pathlib import Path

from ..builder import CompiledWorkflow, WorkflowNode, WorkflowEdge
from ..schema.state_definition import create_state_schema


class YamlNodeSchema(BaseModel):
    """Node schema from YAML"""
    name: str
    action: str
    metadata: Optional[Dict[str, Any]] = None


class YamlEdgeSchema(BaseModel):
    """Edge schema from YAML"""
    from_node: str = Field(alias="from")
    to_node: str = Field(alias="to")
    condition: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class YamlStateSchema(BaseModel):
    """State schema from YAML"""
    name: str
    fields: Dict[str, Dict[str, Any]] = {}
    description: Optional[str] = None
    version: str = "1.0"


class YamlWorkflowSchema(BaseModel):
    """Workflow schema from YAML"""
    name: str
    version: str = "1.0"
    entry_point: str
    description: Optional[str] = None
    author: Optional[str] = None
    nodes: List[YamlNodeSchema] = []
    edges: List[YamlEdgeSchema] = []
    state_schema: Optional[YamlStateSchema] = None
    metadata: Dict[str, Any] = {}


class YamlWorkflowLoader:
    """
    Load workflows from YAML files

    Supports loading single workflows or directories of workflows.
    """

    def __init__(self):
        """Initialize YAML loader"""
        self.import_cache: Dict[str, Any] = {}

    async def load_from_yaml(self, yaml_path: str) -> CompiledWorkflow:
        """
        Load a workflow from YAML file

        Args:
            yaml_path: Path to YAML file

        Returns:
            CompiledWorkflow instance

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If YAML is invalid
        """
        if not os.path.exists(yaml_path):
            raise FileNotFoundError(f"YAML file not found: {yaml_path}")

        with open(yaml_path, 'r', encoding='utf-8') as f:
            yaml_content = f.read()

        # Parse YAML
        try:
            yaml_data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax: {e}")

        # Validate schema
        schema = YamlWorkflowSchema(**yaml_data)

        # Build workflow
        return await self._build_workflow(schema)

    async def load_from_directory(
        self,
        directory: str,
        pattern: str = "*.yaml"
    ) -> List[CompiledWorkflow]:
        """
        Load all workflows from a directory

        Args:
            directory: Directory path
            pattern: File pattern (default: *.yaml)

        Returns:
            List of compiled workflows
        """
        workflows = []
        dir_path = Path(directory)

        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        for yaml_file in dir_path.glob(pattern):
            try:
                workflow = await self.load_from_yaml(str(yaml_file))
                workflows.append(workflow)
            except Exception as e:
                # Log error but continue loading other files
                print(f"Warning: Failed to load {yaml_file}: {e}")

        return workflows

    async def validate_schema(self, yaml_content: str) -> bool:
        """
        Validate YAML workflow schema

        Args:
            yaml_content: YAML content as string

        Returns:
            True if valid, False otherwise
        """
        try:
            yaml_data = yaml.safe_load(yaml_content)
            YamlWorkflowSchema(**yaml_data)
            return True
        except Exception:
            return False

    async def _build_workflow(
        self,
        schema: YamlWorkflowSchema
    ) -> CompiledWorkflow:
        """
        Build workflow from schema

        Args:
            schema: Parsed YAML schema

        Returns:
            Compiled workflow
        """
        from ..builder import WorkflowBuilder

        # Determine state schema
        state_schema_class = self._get_or_create_state_schema(schema)

        # Create builder
        builder = WorkflowBuilder(
            name=schema.name,
            state_schema=state_schema_class,
            description=schema.description
        )

        # Add nodes
        for node_def in schema.nodes:
            action_func = self._load_action_function(node_def.action)
            builder.add_node(
                name=node_def.name,
                action=action_func,
                metadata=node_def.metadata
            )

        # Add edges
        for edge_def in schema.edges:
            condition_func = None
            if edge_def.condition:
                condition_func = self._create_condition_function(edge_def.condition)

            builder.add_edge(
                from_node=edge_def.from_node,
                to_node=edge_def.to_node,
                condition=condition_func,
                metadata=edge_def.metadata
            )

        # Set entry point
        builder.set_entry_point(schema.entry_point)

        # Add metadata
        if schema.author:
            builder.set_metadata("author", schema.author)
        builder.set_metadata("version", schema.version)

        for key, value in schema.metadata.items():
            builder.set_metadata(key, value)

        # Build and return
        return builder.build()

    def _get_or_create_state_schema(
        self,
        schema: YamlWorkflowSchema
    ) -> Type[BaseModel]:
        """
        Get or create state schema class

        Args:
            schema: Workflow schema

        Returns:
            State schema class
        """
        if schema.state_schema:
            # Create dynamic state schema
            return create_state_schema(
                name=schema.state_schema.name,
                fields=schema.state_schema.fields,
                description=schema.state_schema.description,
                version=schema.state_schema.version
            )
        else:
            # Default state schema
            from pydantic import BaseModel

            class DefaultState(BaseModel):
                """Default workflow state"""
                pass

            return DefaultState

    def _load_action_function(self, action_path: str):
        """
        Load action function from module path

        Args:
            action_path: Module.function path

        Returns:
            Function object

        Note:
            For now, returns a mock function. In production, this would
            dynamically import and return the actual function.
        """
        # Check cache first
        if action_path in self.import_cache:
            return self.import_cache[action_path]

        # For now, create a mock function
        # In production, this would do actual module importing
        def mock_action(state):
            """Mock action for {action_path}"""
            return {}

        mock_action.__name__ = action_path
        self.import_cache[action_path] = mock_action

        return mock_action

    def _create_condition_function(self, condition_expr: str):
        """
        Create condition function from expression

        Args:
            condition_expr: Python expression string

        Returns:
            Condition function
        """
        def condition_func(state):
            """Evaluate condition expression"""
            try:
                context = {"state": state.model_dump() if hasattr(state, "model_dump") else state}
                return eval(condition_expr, {"__builtins__": {}}, context)
            except Exception:
                return False

        return condition_func

    async def load_template(self, template_path: str) -> Dict[str, Any]:
        """
        Load workflow template

        Args:
            template_path: Path to template file

        Returns:
            Template dictionary
        """
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template file not found: {template_path}")

        with open(template_path, 'r', encoding='utf-8') as f:
            yaml_content = f.read()

        yaml_data = yaml.safe_load(yaml_content)
        return yaml_data

    async def save_template(
        self,
        workflow: CompiledWorkflow,
        template_path: str
    ):
        """
        Save workflow as YAML template

        Args:
            workflow: Workflow to save
            template_path: Path to save template
        """
        # Convert workflow to YAML structure
        yaml_data = {
            "name": workflow.name,
            "version": workflow.metadata.get("version", "1.0"),
            "entry_point": workflow.entry_point,
            "description": workflow.metadata.get("description"),
            "nodes": [
                {
                    "name": node.name,
                    "action": node.metadata.get("action", "module.function"),
                    "metadata": node.metadata
                }
                for node in workflow.nodes.values()
            ],
            "edges": [
                {
                    "from": edge.from_node,
                    "to": edge.to_node,
                    "condition": edge.metadata.get("condition"),
                    "metadata": edge.metadata
                }
                for edge in workflow.edges
            ],
            "metadata": workflow.metadata
        }

        # Write to file
        with open(template_path, 'w', encoding='utf-8') as f:
            yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False)
