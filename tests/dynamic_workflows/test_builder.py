"""
Tests for workflow builder
"""
import pytest
from typing import Dict, Any
from pydantic import BaseModel

from src.dynamic_workflows.builder import (
    WorkflowBuilder,
    CompiledWorkflow,
    WorkflowNode,
    WorkflowEdge,
)


class MockState(BaseModel):
    """Mock state for testing"""
    value: int = 0
    status: str = "pending"
    messages: list = []


class TestWorkflowNode:
    """Test WorkflowNode"""

    def test_create_node(self):
        """Test creating a workflow node"""
        def action(state: MockState) -> Dict[str, Any]:
            return {"value": state.value + 1}

        node = WorkflowNode(
            name="increment",
            action=action
        )

        assert node.name == "increment"
        assert node.action == action
        assert node.metadata == {}

    def test_create_node_with_metadata(self):
        """Test creating a node with metadata"""
        def action(state):
            return {}

        node = WorkflowNode(
            name="process",
            action=action,
            metadata={"description": "Process data", "timeout": 30}
        )

        assert node.metadata == {"description": "Process data", "timeout": 30}

    def test_execute_node(self):
        """Test executing a node"""
        def action(state: MockState) -> Dict[str, Any]:
            return {"value": state.value * 2}

        node = WorkflowNode(name="double", action=action)
        result = node.execute(MockState(value=5))

        assert result == {"value": 10}


class TestWorkflowEdge:
    """Test WorkflowEdge"""

    def test_create_edge(self):
        """Test creating a workflow edge"""
        edge = WorkflowEdge(
            from_node="node_a",
            to_node="node_b"
        )

        assert edge.from_node == "node_a"
        assert edge.to_node == "node_b"
        assert edge.condition is None

    def test_create_conditional_edge(self):
        """Test creating an edge with condition"""
        def condition(state: Dict[str, Any]) -> bool:
            return state.get("value", 0) > 10

        edge = WorkflowEdge(
            from_node="node_a",
            to_node="node_b",
            condition=condition
        )

        assert edge.condition == condition

    def test_edge_condition_evaluation(self):
        """Test evaluating edge condition"""
        def condition(state):
            return state.get("enabled", False)

        edge = WorkflowEdge(
            from_node="start",
            to_node="end",
            condition=condition
        )

        # Condition met
        assert edge.can_traverse({"enabled": True}) is True

        # Condition not met
        assert edge.can_traverse({"enabled": False}) is False

        # No condition (always can traverse)
        unconditional_edge = WorkflowEdge("start", "end")
        assert unconditional_edge.can_traverse({}) is True


class TestWorkflowBuilder:
    """Test WorkflowBuilder"""

    def test_create_builder(self):
        """Test creating a workflow builder"""
        builder = WorkflowBuilder(
            name="test_workflow",
            state_schema=MockState
        )

        assert builder.name == "test_workflow"
        assert builder.state_schema == MockState
        assert len(builder.nodes) == 0
        assert len(builder.edges) == 0
        assert builder.entry_point is None

    def test_add_node(self):
        """Test adding a node"""
        builder = WorkflowBuilder(
            name="node_test",
            state_schema=MockState
        )

        def action(state):
            return {"status": "processed"}

        result = builder.add_node("process", action)

        # Should return self for chaining
        assert result is builder
        assert "process" in builder.nodes
        assert builder.nodes["process"].name == "process"

    def test_add_multiple_nodes(self):
        """Test adding multiple nodes with chaining"""
        builder = WorkflowBuilder(
            name="multi_node",
            state_schema=MockState
        )

        (builder
         .add_node("node_a", lambda s: {"value": 1})
         .add_node("node_b", lambda s: {"value": 2})
         .add_node("node_c", lambda s: {"value": 3}))

        assert len(builder.nodes) == 3
        assert "node_a" in builder.nodes
        assert "node_b" in builder.nodes
        assert "node_c" in builder.nodes

    def test_add_edge(self):
        """Test adding an edge"""
        builder = WorkflowBuilder(
            name="edge_test",
            state_schema=MockState
        )

        builder.add_node("a", lambda s: {})
        builder.add_node("b", lambda s: {})
        builder.add_edge("a", "b")

        assert len(builder.edges) == 1
        assert builder.edges[0].from_node == "a"
        assert builder.edges[0].to_node == "b"

    def test_add_conditional_edge(self):
        """Test adding a conditional edge"""
        builder = WorkflowBuilder(
            name="conditional_edge_test",
            state_schema=MockState
        )

        def condition(state):
            return state.get("value", 0) > 5

        builder.add_node("start", lambda s: {})
        builder.add_node("end", lambda s: {})
        builder.add_edge("start", "end", condition)

        assert len(builder.edges) == 1
        assert builder.edges[0].condition is not None

    def test_set_entry_point(self):
        """Test setting entry point"""
        builder = WorkflowBuilder(
            name="entry_test",
            state_schema=MockState
        )

        builder.add_node("start", lambda s: {})
        builder.set_entry_point("start")

        assert builder.entry_point == "start"

    def test_set_condition(self):
        """Test setting a named condition"""
        builder = WorkflowBuilder(
            name="condition_test",
            state_schema=MockState
        )

        def check_value(state):
            return state.get("value") == 42

        builder.set_condition("check_answer", check_value)

        assert "check_answer" in builder.conditions
        assert builder.conditions["check_answer"] == check_value

    def test_build_simple_workflow(self):
        """Test building a simple workflow"""
        builder = WorkflowBuilder(
            name="simple",
            state_schema=MockState
        )

        # Add nodes
        builder.add_node("start", lambda s: {"status": "started"})
        builder.add_node("process", lambda s: {"status": "processed"})
        builder.add_node("end", lambda s: {"status": "completed"})

        # Add edges
        builder.add_edge("start", "process")
        builder.add_edge("process", "end")

        # Set entry point
        builder.set_entry_point("start")

        # Build
        workflow = builder.build()

        assert isinstance(workflow, CompiledWorkflow)
        assert workflow.name == "simple"
        assert len(workflow.nodes) == 3
        assert len(workflow.edges) == 2
        assert workflow.entry_point == "start"

    def test_build_conditional_workflow(self):
        """Test building a workflow with conditional routing"""
        builder = WorkflowBuilder(
            name="conditional",
            state_schema=MockState
        )

        # Add nodes
        builder.add_node("start", lambda s: {})
        builder.add_node("handle_high", lambda s: {"status": "high"})
        builder.add_node("handle_low", lambda s: {"status": "low"})

        # Add conditional edges
        builder.add_edge(
            "start",
            "handle_high",
            lambda s: s.get("value", 0) > 50
        )
        builder.add_edge(
            "start",
            "handle_low",
            lambda s: s.get("value", 0) <= 50
        )

        builder.set_entry_point("start")
        workflow = builder.build()

        assert len(workflow.edges) == 2
        assert workflow.edges[0].condition is not None

    def test_builder_reset(self):
        """Test resetting the builder"""
        builder = WorkflowBuilder(
            name="reset_test",
            state_schema=MockState
        )

        builder.add_node("node1", lambda s: {})
        builder.add_edge("node1", "node1")
        builder.set_entry_point("node1")

        builder.reset()

        assert len(builder.nodes) == 0
        assert len(builder.edges) == 0
        assert builder.entry_point is None

    def test_duplicate_node_name_raises_error(self):
        """Test that duplicate node names raise an error"""
        builder = WorkflowBuilder(
            name="duplicate_test",
            state_schema=MockState
        )

        builder.add_node("process", lambda s: {})

        with pytest.raises(ValueError, match="already exists"):
            builder.add_node("process", lambda s: {})

    def test_edge_to_nonexistent_node_raises_error(self):
        """Test that edges to nonexistent nodes raise an error"""
        builder = WorkflowBuilder(
            name="edge_error_test",
            state_schema=MockState
        )

        builder.add_node("start", lambda s: {})

        with pytest.raises(ValueError, match="does not exist"):
            builder.add_edge("start", "nonexistent")

    def test_build_without_entry_point_raises_error(self):
        """Test that building without entry point raises an error"""
        builder = WorkflowBuilder(
            name="no_entry_test",
            state_schema=MockState
        )

        builder.add_node("node", lambda s: {})

        with pytest.raises(ValueError, match="entry point"):
            builder.build()


class TestCompiledWorkflow:
    """Test CompiledWorkflow"""

    def test_create_compiled_workflow(self):
        """Test creating a compiled workflow"""
        nodes = {
            "start": WorkflowNode("start", lambda s: {}),
            "end": WorkflowNode("end", lambda s: {})
        }
        edges = [WorkflowEdge("start", "end")]

        workflow = CompiledWorkflow(
            name="test",
            nodes=nodes,
            edges=edges,
            entry_point="start",
            state_schema=MockState
        )

        assert workflow.name == "test"
        assert len(workflow.nodes) == 2
        assert len(workflow.edges) == 1
        assert workflow.entry_point == "start"

    def test_workflow_to_dict(self):
        """Test converting workflow to dictionary"""
        nodes = {
            "a": WorkflowNode("a", lambda s: {"value": 1})
        }
        edges = [WorkflowEdge("a", "a")]

        workflow = CompiledWorkflow(
            name="dict_test",
            nodes=nodes,
            edges=edges,
            entry_point="a",
            state_schema=MockState
        )

        result = workflow.to_dict()

        assert result["name"] == "dict_test"
        assert "nodes" in result
        assert "edges" in result
        assert result["entry_point"] == "a"

    def test_workflow_execution_flow(self):
        """Test executing a simple workflow flow"""
        # Create nodes
        def increment(state: MockState) -> Dict[str, Any]:
            return {"value": state.value + 1}

        def double(state: MockState) -> Dict[str, Any]:
            return {"value": state.value * 2}

        nodes = {
            "start": WorkflowNode("start", increment),
            "middle": WorkflowNode("middle", double),
        }
        edges = [WorkflowEdge("start", "middle")]

        workflow = CompiledWorkflow(
            name="flow_test",
            nodes=nodes,
            edges=edges,
            entry_point="start",
            state_schema=MockState
        )

        # Get next node
        next_nodes = workflow.get_next_nodes("start")
        assert "middle" in next_nodes

        # Execute node
        state = MockState(value=5)
        result = workflow.execute_node("start", state)
        assert result["value"] == 6

    def test_workflow_metadata(self):
        """Test workflow metadata"""
        nodes = {"node": WorkflowNode("node", lambda s: {})}
        edges = []
        metadata = {
            "version": "1.0",
            "description": "Test workflow",
            "author": "Test Author"
        }

        workflow = CompiledWorkflow(
            name="metadata_test",
            nodes=nodes,
            edges=edges,
            entry_point="node",
            state_schema=MockState,
            metadata=metadata
        )

        assert workflow.metadata == metadata
        assert workflow.metadata["version"] == "1.0"
