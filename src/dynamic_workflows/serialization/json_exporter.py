"""
JSON Workflow Exporter

Export workflows to JSON format for sharing, storage, or analysis.
"""
from typing import Any, Dict, List
from pydantic import BaseModel
import json
import os

from ..builder import CompiledWorkflow


class JsonWorkflowExporter:
    """
    Export workflows to JSON format

    Supports exporting single workflows, multiple workflows, or templates.
    """

    def __init__(self, indent: int = 2):
        """
        Initialize JSON exporter

        Args:
            indent: JSON indentation level
        """
        self.indent = indent

    async def export_to_json(
        self,
        workflow: CompiledWorkflow,
        pretty: bool = True
    ) -> str:
        """
        Export workflow to JSON string

        Args:
            workflow: Workflow to export
            pretty: Whether to pretty-print JSON

        Returns:
            JSON string
        """
        data = await self.export_to_dict(workflow)

        if pretty:
            return json.dumps(data, indent=self.indent, ensure_ascii=False)
        else:
            return json.dumps(data, ensure_ascii=False)

    async def export_to_dict(self, workflow: CompiledWorkflow) -> Dict[str, Any]:
        """
        Export workflow to dictionary

        Args:
            workflow: Workflow to export

        Returns:
            Dictionary representation
        """
        return {
            "name": workflow.name,
            "entry_point": workflow.entry_point,
            "state_schema": workflow.state_schema.__name__,
            "node_count": len(workflow.nodes),
            "edge_count": len(workflow.edges),
            "nodes": [
                {
                    "name": node.name,
                    "metadata": node.metadata
                }
                for node in workflow.nodes.values()
            ],
            "edges": [
                {
                    "from": edge.from_node,
                    "to": edge.to_node,
                    "has_condition": edge.condition is not None,
                    "metadata": edge.metadata
                }
                for edge in workflow.edges
            ],
            "metadata": workflow.metadata,
            "validation_errors": workflow.validate()
        }

    async def save_to_file(
        self,
        workflow: CompiledWorkflow,
        file_path: str,
        pretty: bool = True
    ):
        """
        Save workflow to JSON file

        Args:
            workflow: Workflow to save
            file_path: Path to save file
            pretty: Whether to pretty-print JSON
        """
        json_str = await self.export_to_json(workflow, pretty=pretty)

        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else ".", exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(json_str)

    async def save_template(
        self,
        workflow: CompiledWorkflow,
        template_path: str
    ):
        """
        Save workflow as a reusable template

        Args:
            workflow: Workflow to save as template
            template_path: Path to save template
        """
        # Get workflow data
        data = await self.export_to_dict(workflow)

        # Add template metadata
        data["is_template"] = True
        data["template_version"] = "1.0"

        # Ensure directory exists
        os.makedirs(os.path.dirname(template_path) if os.path.dirname(template_path) else ".", exist_ok=True)

        # Write to file
        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=self.indent, ensure_ascii=False)

    async def export_workflows(
        self,
        workflows: List[CompiledWorkflow],
        pretty: bool = True
    ) -> str:
        """
        Export multiple workflows to JSON array

        Args:
            workflows: List of workflows to export
            pretty: Whether to pretty-print JSON

        Returns:
            JSON string representing array of workflows
        """
        workflow_dicts = []

        for workflow in workflows:
            data = await self.export_to_dict(workflow)
            workflow_dicts.append(data)

        if pretty:
            return json.dumps(workflow_dicts, indent=self.indent, ensure_ascii=False)
        else:
            return json.dumps(workflow_dicts, ensure_ascii=False)

    async def save_workflows_to_file(
        self,
        workflows: List[CompiledWorkflow],
        file_path: str,
        pretty: bool = True
    ):
        """
        Save multiple workflows to JSON file

        Args:
            workflows: List of workflows to save
            file_path: Path to save file
            pretty: Whether to pretty-print JSON
        """
        json_str = await self.export_workflows(workflows, pretty=pretty)

        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else ".", exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(json_str)

    async def export_summary(self, workflow: CompiledWorkflow) -> Dict[str, Any]:
        """
        Export workflow summary (compact version)

        Args:
            workflow: Workflow to summarize

        Returns:
            Summary dictionary
        """
        return {
            "name": workflow.name,
            "entry_point": workflow.entry_point,
            "node_count": len(workflow.nodes),
            "edge_count": len(workflow.edges),
            "is_valid": len(workflow.validate()) == 0,
            "metadata": {
                "description": workflow.metadata.get("description"),
                "version": workflow.metadata.get("version"),
                "author": workflow.metadata.get("author")
            }
        }

    async def export_statistics(
        self,
        workflows: List[CompiledWorkflow]
    ) -> Dict[str, Any]:
        """
        Export statistics for multiple workflows

        Args:
            workflows: List of workflows

        Returns:
            Statistics dictionary
        """
        total_nodes = sum(len(w.nodes) for w in workflows)
        total_edges = sum(len(w.edges) for w in workflows)
        valid_workflows = sum(1 for w in workflows if len(w.validate()) == 0)

        return {
            "total_workflows": len(workflows),
            "valid_workflows": valid_workflows,
            "invalid_workflows": len(workflows) - valid_workflows,
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "average_nodes_per_workflow": total_nodes / len(workflows) if workflows else 0,
            "average_edges_per_workflow": total_edges / len(workflows) if workflows else 0
        }

    async def create_comparison(
        self,
        workflow1: CompiledWorkflow,
        workflow2: CompiledWorkflow
    ) -> Dict[str, Any]:
        """
        Create comparison between two workflows

        Args:
            workflow1: First workflow
            workflow2: Second workflow

        Returns:
            Comparison dictionary
        """
        return {
            "workflow1": {
                "name": workflow1.name,
                "nodes": len(workflow1.nodes),
                "edges": len(workflow1.edges)
            },
            "workflow2": {
                "name": workflow2.name,
                "nodes": len(workflow2.nodes),
                "edges": len(workflow2.edges)
            },
            "differences": {
                "node_difference": len(workflow1.nodes) - len(workflow2.nodes),
                "edge_difference": len(workflow1.edges) - len(workflow2.edges),
                "nodes_only_in_workflow1": list(set(workflow1.nodes.keys()) - set(workflow2.nodes.keys())),
                "nodes_only_in_workflow2": list(set(workflow2.nodes.keys()) - set(workflow1.nodes.keys()))
            }
        }

    def set_indent(self, indent: int):
        """
        Set JSON indentation level

        Args:
            indent: Indentation level
        """
        self.indent = indent
