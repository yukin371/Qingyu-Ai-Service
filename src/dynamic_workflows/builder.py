"""
Workflow Builder for Dynamic Workflows

Provides a fluent API for building LangGraph-compatible workflows.
Supports chaining, conditional routing, and dynamic composition.
"""
from typing import Any, Dict, List, Optional, Type, Callable
from pydantic import BaseModel


class WorkflowNode:
    """
    Represents a node in a workflow

    A node contains an action/function that processes the workflow state.
    """

    def __init__(
        self,
        name: str,
        action: Callable,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a workflow node

        Args:
            name: Unique node name
            action: Function that processes state and returns updates
            metadata: Optional metadata (description, timeout, etc.)
        """
        self.name = name
        self.action = action
        self.metadata = metadata or {}

    def execute(self, state: BaseModel) -> Dict[str, Any]:
        """
        Execute the node's action

        Args:
            state: Current workflow state

        Returns:
            Dictionary of state updates
        """
        return self.action(state)

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary"""
        return {
            "name": self.name,
            "metadata": self.metadata
        }


class WorkflowEdge:
    """
    Represents an edge (connection) between nodes

    Edges can be conditional or unconditional.
    """

    def __init__(
        self,
        from_node: str,
        to_node: str,
        condition: Optional[Callable[[Dict[str, Any]], bool]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a workflow edge

        Args:
            from_node: Source node name
            to_node: Target node name
            condition: Optional condition function (returns bool)
            metadata: Optional metadata
        """
        self.from_node = from_node
        self.to_node = to_node
        self.condition = condition
        self.metadata = metadata or {}

    def can_traverse(self, state: Dict[str, Any]) -> bool:
        """
        Check if edge can be traversed

        Args:
            state: Current workflow state

        Returns:
            True if edge can be traversed
        """
        if self.condition is None:
            return True

        try:
            return self.condition(state)
        except Exception:
            # If condition fails, don't traverse
            return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert edge to dictionary"""
        return {
            "from": self.from_node,
            "to": self.to_node,
            "has_condition": self.condition is not None,
            "metadata": self.metadata
        }


class CompiledWorkflow:
    """
    A compiled workflow ready for execution

    Contains nodes, edges, and metadata for running a workflow.
    """

    def __init__(
        self,
        name: str,
        nodes: Dict[str, WorkflowNode],
        edges: List[WorkflowEdge],
        entry_point: str,
        state_schema: Type[BaseModel],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize compiled workflow

        Args:
            name: Workflow name
            nodes: Dictionary of nodes
            edges: List of edges
            entry_point: Entry point node name
            state_schema: State schema class
            metadata: Optional metadata
        """
        self.name = name
        self.nodes = nodes
        self.edges = edges
        self.entry_point = entry_point
        self.state_schema = state_schema
        self.metadata = metadata or {}

        # Build adjacency list for quick lookup
        self._adjacency = self._build_adjacency()

    def _build_adjacency(self) -> Dict[str, List[str]]:
        """Build adjacency list for graph traversal"""
        adjacency = {node_name: [] for node_name in self.nodes}

        for edge in self.edges:
            if edge.from_node in adjacency:
                adjacency[edge.from_node].append(edge.to_node)

        return adjacency

    def get_next_nodes(self, node_name: str) -> List[str]:
        """
        Get next nodes from a given node

        Args:
            node_name: Current node name

        Returns:
            List of next node names
        """
        return self._adjacency.get(node_name, [])

    def execute_node(self, node_name: str, state: BaseModel) -> Dict[str, Any]:
        """
        Execute a specific node

        Args:
            node_name: Node to execute
            state: Current state

        Returns:
            State updates from node execution
        """
        if node_name not in self.nodes:
            raise ValueError(f"Node '{node_name}' not found in workflow")

        node = self.nodes[node_name]
        return node.execute(state)

    def to_dict(self) -> Dict[str, Any]:
        """Convert workflow to dictionary"""
        return {
            "name": self.name,
            "entry_point": self.entry_point,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges],
            "metadata": self.metadata
        }

    def validate(self) -> List[str]:
        """
        Validate workflow structure

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check entry point exists
        if self.entry_point not in self.nodes:
            errors.append(f"Entry point '{self.entry_point}' not found in nodes")

        # Check all edge endpoints exist
        for edge in self.edges:
            if edge.from_node not in self.nodes:
                errors.append(f"Edge from non-existent node '{edge.from_node}'")
            if edge.to_node not in self.nodes:
                errors.append(f"Edge to non-existent node '{edge.to_node}'")

        return errors


class WorkflowBuilder:
    """
    Fluent workflow builder

    Provides a chainable API for building workflows.
    """

    def __init__(
        self,
        name: str,
        state_schema: Type[BaseModel],
        description: Optional[str] = None
    ):
        """
        Initialize workflow builder

        Args:
            name: Workflow name
            state_schema: State schema class (BaseModel subclass)
            description: Optional description
        """
        self.name = name
        self.state_schema = state_schema
        self.description = description

        self.nodes: Dict[str, WorkflowNode] = {}
        self.edges: List[WorkflowEdge] = []
        self.conditions: Dict[str, Callable] = {}
        self.entry_point: Optional[str] = None
        self.metadata: Dict[str, Any] = {}

    def add_node(
        self,
        name: str,
        action: Callable,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "WorkflowBuilder":
        """
        Add a node to the workflow

        Args:
            name: Node name
            action: Node action function
            metadata: Optional metadata

        Returns:
            Self for chaining

        Raises:
            ValueError: If node name already exists
        """
        if name in self.nodes:
            raise ValueError(f"Node '{name}' already exists in workflow")

        node = WorkflowNode(name, action, metadata)
        self.nodes[name] = node

        return self

    def add_edge(
        self,
        from_node: str,
        to_node: str,
        condition: Optional[Callable] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "WorkflowBuilder":
        """
        Add an edge between nodes

        Args:
            from_node: Source node name
            to_node: Target node name
            condition: Optional condition function
            metadata: Optional metadata

        Returns:
            Self for chaining

        Raises:
            ValueError: If nodes don't exist
        """
        if from_node not in self.nodes:
            raise ValueError(f"Source node '{from_node}' does not exist")
        if to_node not in self.nodes:
            raise ValueError(f"Target node '{to_node}' does not exist")

        edge = WorkflowEdge(from_node, to_node, condition, metadata)
        self.edges.append(edge)

        return self

    def set_entry_point(self, node_name: str) -> "WorkflowBuilder":
        """
        Set the workflow entry point

        Args:
            node_name: Entry point node name

        Returns:
            Self for chaining

        Raises:
            ValueError: If node doesn't exist
        """
        if node_name not in self.nodes:
            raise ValueError(f"Entry point node '{node_name}' does not exist")

        self.entry_point = node_name
        return self

    def set_condition(
        self,
        name: str,
        condition: Callable
    ) -> "WorkflowBuilder":
        """
        Register a named condition for reuse

        Args:
            name: Condition name
            condition: Condition function

        Returns:
            Self for chaining
        """
        self.conditions[name] = condition
        return self

    def set_metadata(self, key: str, value: Any) -> "WorkflowBuilder":
        """
        Set workflow metadata

        Args:
            key: Metadata key
            value: Metadata value

        Returns:
            Self for chaining
        """
        self.metadata[key] = value
        return self

    def build(self) -> CompiledWorkflow:
        """
        Build the compiled workflow

        Returns:
            CompiledWorkflow instance

        Raises:
            ValueError: If workflow is invalid
        """
        if self.entry_point is None:
            raise ValueError("Cannot build workflow without entry point")

        # Create compiled workflow
        workflow = CompiledWorkflow(
            name=self.name,
            nodes=self.nodes.copy(),
            edges=self.edges.copy(),
            entry_point=self.entry_point,
            state_schema=self.state_schema,
            metadata={
                "description": self.description,
                **self.metadata
            }
        )

        # Validate
        errors = workflow.validate()
        if errors:
            raise ValueError(f"Workflow validation failed: {errors}")

        return workflow

    def reset(self) -> "WorkflowBuilder":
        """
        Reset the builder

        Clears all nodes, edges, and settings.

        Returns:
            Self for chaining
        """
        self.nodes.clear()
        self.edges.clear()
        self.conditions.clear()
        self.entry_point = None
        self.metadata.clear()

        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert builder state to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "entry_point": self.entry_point,
            "metadata": self.metadata
        }


def create_workflow(
    name: str,
    state_schema: Type[BaseModel],
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    entry_point: str
) -> CompiledWorkflow:
    """
    Convenience function to create a workflow from configuration

    Args:
        name: Workflow name
        state_schema: State schema class
        nodes: List of node definitions
            Each node: {"name": str, "action": callable, "metadata": dict}
        edges: List of edge definitions
            Each edge: {"from": str, "to": str, "condition": callable}
        entry_point: Entry point node name

    Returns:
        Compiled workflow
    """
    builder = WorkflowBuilder(name, state_schema)

    # Add nodes
    for node_def in nodes:
        builder.add_node(
            name=node_def["name"],
            action=node_def["action"],
            metadata=node_def.get("metadata")
        )

    # Add edges
    for edge_def in edges:
        builder.add_edge(
            from_node=edge_def["from"],
            to_node=edge_def["to"],
            condition=edge_def.get("condition")
        )

    # Set entry point and build
    builder.set_entry_point(entry_point)
    return builder.build()
