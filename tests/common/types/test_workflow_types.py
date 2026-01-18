"""
Tests for workflow type definitions
"""

import pytest

from src.common.types.workflow_types import (
    WorkflowStatus,
    StepStatus,
    WorkflowStep,
    WorkflowState,
    WorkflowConfig,
    WorkflowExecution,
)


class TestWorkflowStatus:
    """Test WorkflowStatus enum."""

    def test_values(self):
        """Test status values."""
        assert WorkflowStatus.PENDING.value == "pending"
        assert WorkflowStatus.RUNNING.value == "running"
        assert WorkflowStatus.COMPLETED.value == "completed"
        assert WorkflowStatus.FAILED.value == "failed"


class TestStepStatus:
    """Test StepStatus enum."""

    def test_values(self):
        """Test step status values."""
        assert StepStatus.PENDING.value == "pending"
        assert StepStatus.RUNNING.value == "running"
        assert StepStatus.COMPLETED.value == "completed"
        assert StepStatus.FAILED.value == "failed"
        assert StepStatus.SKIPPED.value == "skipped"


class TestWorkflowStep:
    """Test WorkflowStep."""

    def test_create_step(self):
        """Test creating workflow step."""
        step = WorkflowStep(
            step_id="step_1",
            name="First Step",
            step_type="agent"
        )
        assert step.step_id == "step_1"
        assert step.name == "First Step"
        assert step.status == StepStatus.PENDING

    def test_step_with_dependencies(self):
        """Test step with dependencies."""
        step = WorkflowStep(
            step_id="step_2",
            name="Second Step",
            step_type="tool",
            dependencies=["step_1"]
        )
        assert len(step.dependencies) == 1
        assert "step_1" in step.dependencies

    def test_is_ready(self):
        """Test is_ready method."""
        step = WorkflowStep(
            step_id="step_2",
            name="Second Step",
            step_type="tool",
            dependencies=["step_1"]
        )
        assert not step.is_ready([])
        assert step.is_ready(["step_1"])
        assert step.is_ready(["step_1", "step_0"])


class TestWorkflowState:
    """Test WorkflowState."""

    def test_create_state(self):
        """Test creating workflow state."""
        state = WorkflowState(workflow_id="workflow_1")
        assert state.workflow_id == "workflow_1"
        assert state.status == WorkflowStatus.PENDING
        assert len(state.completed_steps) == 0

    def test_variable_operations(self):
        """Test variable operations."""
        state = WorkflowState(workflow_id="workflow_1")
        state.set_variable("key", "value")
        assert state.get_variable("key") == "value"
        assert state.get_variable("missing", "default") == "default"

    def test_step_results(self):
        """Test step results."""
        state = WorkflowState(workflow_id="workflow_1")
        state.step_results["step_1"] = "result_1"
        assert state.get_step_result("step_1") == "result_1"
        assert state.get_step_result("step_2") is None


class TestWorkflowConfig:
    """Test WorkflowConfig."""

    def test_create_config(self):
        """Test creating workflow config."""
        config = WorkflowConfig(
            workflow_id="workflow_1",
            name="Test Workflow"
        )
        assert config.workflow_id == "workflow_1"
        assert config.name == "Test Workflow"
        assert len(config.steps) == 0

    def test_config_with_steps(self):
        """Test config with steps."""
        step1 = WorkflowStep(step_id="step_1", name="Step 1", step_type="agent")
        step2 = WorkflowStep(step_id="step_2", name="Step 2", step_type="tool")
        config = WorkflowConfig(
            workflow_id="workflow_1",
            name="Test Workflow",
            steps=[step1, step2]
        )
        assert len(config.steps) == 2

    def test_get_step_by_id(self):
        """Test get_step_by_id."""
        step1 = WorkflowStep(step_id="step_1", name="Step 1", step_type="agent")
        config = WorkflowConfig(
            workflow_id="workflow_1",
            name="Test Workflow",
            steps=[step1]
        )
        found_step = config.get_step_by_id("step_1")
        assert found_step is not None
        assert found_step.step_id == "step_1"
        assert config.get_step_by_id("missing") is None

    def test_get_initial_steps(self):
        """Test get_initial_steps."""
        step1 = WorkflowStep(step_id="step_1", name="Step 1", step_type="agent")
        step2 = WorkflowStep(
            step_id="step_2",
            name="Step 2",
            step_type="tool",
            dependencies=["step_1"]
        )
        config = WorkflowConfig(
            workflow_id="workflow_1",
            name="Test Workflow",
            steps=[step1, step2]
        )
        initial = config.get_initial_steps()
        assert len(initial) == 1
        assert initial[0].step_id == "step_1"


class TestWorkflowExecution:
    """Test WorkflowExecution."""

    def test_create_execution(self):
        """Test creating workflow execution."""
        state = WorkflowState(workflow_id="workflow_1")
        execution = WorkflowExecution(
            workflow_id="workflow_1",
            state=state
        )
        assert execution.workflow_id == "workflow_1"
        assert execution.state == state
        assert execution.input == {}
