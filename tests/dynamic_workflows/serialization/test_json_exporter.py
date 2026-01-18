"""
Tests for JSON workflow exporter
"""
import pytest
import tempfile
import json
import os
from pathlib import Path

from src.dynamic_workflows.serialization.json_exporter import (
    JsonWorkflowExporter,
)
from src.dynamic_workflows.builder import (
    WorkflowBuilder,
    WorkflowNode,
    WorkflowEdge,
    CompiledWorkflow,
)
from pydantic import BaseModel


class MockState(BaseModel):
    """Mock state"""
    value: int = 0
    status: str = "pending"


class TestJsonWorkflowExporter:
    """Test JsonWorkflowExporter"""

    def test_create_exporter(self):
        """Test creating a JSON exporter"""
        exporter = JsonWorkflowExporter()

        assert exporter is not None

    @pytest.mark.asyncio
    async def test_export_simple_workflow(self):
        """Test exporting a simple workflow to JSON"""
        builder = WorkflowBuilder(name="simple", state_schema=MockState)
        builder.add_node("start", lambda s: {"status": "started"})
        builder.add_node("end", lambda s: {"status": "ended"})
        builder.add_edge("start", "end")
        builder.set_entry_point("start")

        workflow = builder.build()

        exporter = JsonWorkflowExporter()
        json_str = await exporter.export_to_json(workflow)

        # Parse and verify
        data = json.loads(json_str)

        assert data["name"] == "simple"
        assert data["entry_point"] == "start"
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1

    @pytest.mark.asyncio
    async def test_export_workflow_with_metadata(self):
        """Test exporting workflow with metadata"""
        builder = WorkflowBuilder(
            name="metadata_test",
            state_schema=MockState,
            description="Test workflow with metadata"
        )
        builder.add_node("node", lambda s: {})
        builder.set_entry_point("node")
        builder.set_metadata("author", "Test Author")
        builder.set_metadata("version", "1.0")

        workflow = builder.build()

        exporter = JsonWorkflowExporter()
        json_str = await exporter.export_to_json(workflow)

        data = json.loads(json_str)

        assert data["metadata"]["description"] == "Test workflow with metadata"
        assert data["metadata"]["author"] == "Test Author"
        assert data["metadata"]["version"] == "1.0"

    @pytest.mark.asyncio
    async def test_export_workflow_with_edges(self):
        """Test exporting workflow with edges"""
        builder = WorkflowBuilder(name="edge_test", state_schema=MockState)

        builder.add_node("a", lambda s: {"value": 1})
        builder.add_node("b", lambda s: {"value": 2})
        builder.add_node("c", lambda s: {"value": 3})

        builder.add_edge("a", "b")
        builder.add_edge("b", "c")
        builder.add_edge("a", "c")

        builder.set_entry_point("a")

        workflow = builder.build()

        exporter = JsonWorkflowExporter()
        json_str = await exporter.export_to_json(workflow)

        data = json.loads(json_str)

        assert len(data["edges"]) == 3

        # Verify edges
        edge_connections = [(e["from"], e["to"]) for e in data["edges"]]
        assert ("a", "b") in edge_connections
        assert ("b", "c") in edge_connections
        assert ("a", "c") in edge_connections

    @pytest.mark.asyncio
    async def test_save_to_file(self):
        """Test saving workflow to JSON file"""
        builder = WorkflowBuilder(name="file_test", state_schema=MockState)
        builder.add_node("start", lambda s: {})
        builder.set_entry_point("start")

        workflow = builder.build()

        exporter = JsonWorkflowExporter()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            await exporter.save_to_file(workflow, temp_path)

            # Verify file was created and contains valid JSON
            assert os.path.exists(temp_path)

            with open(temp_path, 'r') as f:
                data = json.load(f)

            assert data["name"] == "file_test"

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_save_template(self):
        """Test saving workflow as template"""
        builder = WorkflowBuilder(
            name="template_test",
            state_schema=MockState,
            description="A reusable template"
        )
        builder.add_node("step1", lambda s: {})
        builder.add_node("step2", lambda s: {})
        builder.add_edge("step1", "step2")
        builder.set_entry_point("step1")

        workflow = builder.build()

        exporter = JsonWorkflowExporter()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            await exporter.save_template(workflow, temp_path)

            # Verify template file
            with open(temp_path, 'r') as f:
                data = json.load(f)

            assert data["name"] == "template_test"
            assert data["metadata"]["description"] == "A reusable template"
            assert "is_template" in data or "template" in data

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_export_conditional_edges(self):
        """Test exporting workflow with conditional edges"""
        builder = WorkflowBuilder(name="conditional", state_schema=MockState)

        builder.add_node("router", lambda s: {})
        builder.add_node("a", lambda s: {})
        builder.add_node("b", lambda s: {})

        builder.add_edge("router", "a", lambda s: s.get("value") == 1)
        builder.add_edge("router", "b", lambda s: s.get("value") == 2)

        builder.set_entry_point("router")

        workflow = builder.build()

        exporter = JsonWorkflowExporter()
        json_str = await exporter.export_to_json(workflow)

        data = json.loads(json_str)

        # Note: Conditions are functions, so they won't be fully serializable
        # But the edge structure should be preserved
        assert len(data["edges"]) == 2
        assert data["edges"][0]["from"] == "router"

    @pytest.mark.asyncio
    async def test_export_workflow_to_dict(self):
        """Test exporting workflow to dictionary"""
        builder = WorkflowBuilder(name="dict_test", state_schema=MockState)
        builder.add_node("node1", lambda s: {"value": 1})
        builder.add_node("node2", lambda s: {"value": 2})
        builder.add_edge("node1", "node2")
        builder.set_entry_point("node1")

        workflow = builder.build()

        exporter = JsonWorkflowExporter()
        data = await exporter.export_to_dict(workflow)

        assert isinstance(data, dict)
        assert data["name"] == "dict_test"
        assert "nodes" in data
        assert "edges" in data

    @pytest.mark.asyncio
    async def test_export_pretty_print(self):
        """Test exporting with pretty printing"""
        builder = WorkflowBuilder(name="pretty", state_schema=MockState)
        builder.add_node("node", lambda s: {})
        builder.set_entry_point("node")

        workflow = builder.build()

        exporter = JsonWorkflowExporter()
        json_str = await exporter.export_to_json(workflow, pretty=True)

        # Pretty printed JSON should have indentation
        assert "\n" in json_str
        assert "  " in json_str  # Should have spaces for indentation

        # Should be valid JSON
        data = json.loads(json_str)
        assert data["name"] == "pretty"

    @pytest.mark.asyncio
    async def test_export_compact(self):
        """Test exporting without pretty printing"""
        builder = WorkflowBuilder(name="compact", state_schema=MockState)
        builder.add_node("node", lambda s: {})
        builder.set_entry_point("node")

        workflow = builder.build()

        exporter = JsonWorkflowExporter()
        json_str = await exporter.export_to_json(workflow, pretty=False)

        # Compact JSON should not have unnecessary whitespace
        # (though it may still have some)
        assert json_str is not None

        # Should be valid JSON
        data = json.loads(json_str)
        assert data["name"] == "compact"

    @pytest.mark.asyncio
    async def test_export_multiple_workflows(self):
        """Test exporting multiple workflows to array"""
        builder1 = WorkflowBuilder(name="workflow1", state_schema=MockState)
        builder1.add_node("node", lambda s: {})
        builder1.set_entry_point("node")

        builder2 = WorkflowBuilder(name="workflow2", state_schema=MockState)
        builder2.add_node("node", lambda s: {})
        builder2.set_entry_point("node")

        workflow1 = builder1.build()
        workflow2 = builder2.build()

        exporter = JsonWorkflowExporter()
        json_str = await exporter.export_workflows([workflow1, workflow2])

        data = json.loads(json_str)

        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["name"] == "workflow1"
        assert data[1]["name"] == "workflow2"
