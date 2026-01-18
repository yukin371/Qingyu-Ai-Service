"""
Workflow Type Definitions

This module defines all types related to workflow management, including
workflow states, configurations, and execution tracking.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Enums
# =============================================================================

class WorkflowStatus(str, Enum):
    """Status of a workflow."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Status of a workflow step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# =============================================================================
# Workflow Step
# =============================================================================

class WorkflowStep(BaseModel):
    """
    A single step in a workflow.

    Attributes:
        step_id: Unique identifier for the step
        name: Human-readable name
        description: Step description
        step_type: Type of step (agent, tool, conditional, etc.)
        config: Step configuration
        dependencies: IDs of steps this step depends on
        status: Current status
        result: Step result (if completed)
        error: Error message (if failed)
        started_at: Step start time
        completed_at: Step completion time
    """

    step_id: str
    name: str
    description: Optional[str] = None
    step_type: str
    config: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(use_enum_values=False)

    def is_ready(self, completed_steps: List[str]) -> bool:
        """Check if step is ready to execute."""
        return all(dep in completed_steps for dep in self.dependencies)


# =============================================================================
# Workflow State
# =============================================================================

class WorkflowState(BaseModel):
    """
    Current state of a workflow execution.

    Attributes:
        workflow_id: Unique workflow identifier
        execution_id: Unique execution identifier
        status: Current status
        current_step: ID of the current step
        completed_steps: IDs of completed steps
        variables: Workflow variables
        step_results: Results from each step
        error: Error message (if failed)
        started_at: Execution start time
        completed_at: Execution completion time
    """

    workflow_id: str
    execution_id: UUID = Field(default_factory=uuid4)
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_step: Optional[str] = None
    completed_steps: List[str] = Field(default_factory=list)
    variables: Dict[str, Any] = Field(default_factory=dict)
    step_results: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(use_enum_values=False)

    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a workflow variable."""
        return self.variables.get(key, default)

    def set_variable(self, key: str, value: Any) -> None:
        """Set a workflow variable."""
        self.variables[key] = value

    def get_step_result(self, step_id: str) -> Optional[Any]:
        """Get result from a completed step."""
        return self.step_results.get(step_id)


# =============================================================================
# Workflow Configuration
# =============================================================================

class WorkflowConfig(BaseModel):
    """
    Configuration for a workflow.

    Attributes:
        workflow_id: Unique workflow identifier
        name: Human-readable name
        description: Workflow description
        steps: List of workflow steps
        variables: Initial variable values
        max_execution_time: Maximum execution time in seconds
        retry_policy: Retry policy for failed steps
        parallel_execution: Whether to run independent steps in parallel
    """

    workflow_id: str
    name: str
    description: Optional[str] = None
    steps: List[WorkflowStep] = Field(default_factory=list)
    variables: Dict[str, Any] = Field(default_factory=dict)
    max_execution_time: Optional[int] = Field(default=None, ge=1)
    retry_policy: Dict[str, Any] = Field(default_factory=dict)
    parallel_execution: bool = False

    def get_step_by_id(self, step_id: str) -> Optional[WorkflowStep]:
        """Get a step by its ID."""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None

    def get_initial_steps(self) -> List[WorkflowStep]:
        """Get steps with no dependencies."""
        return [step for step in self.steps if not step.dependencies]


# =============================================================================
# Workflow Execution
# =============================================================================

class WorkflowExecution(BaseModel):
    """
    Record of a workflow execution.

    Attributes:
        execution_id: Unique execution identifier
        workflow_id: Workflow being executed
        state: Current workflow state
        input: Input data
        output: Output data (if completed)
        metadata: Additional metadata
        created_at: Creation timestamp
        started_at: Execution start time
        completed_at: Execution completion time
    """

    execution_id: UUID = Field(default_factory=uuid4)
    workflow_id: str
    state: WorkflowState
    input: Dict[str, Any] = Field(default_factory=dict)
    output: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# =============================================================================
# Export all types
# =============================================================================

__all__ = [
    # Enums
    "WorkflowStatus",
    "StepStatus",
    # Step
    "WorkflowStep",
    # State
    "WorkflowState",
    # Config
    "WorkflowConfig",
    # Execution
    "WorkflowExecution",
]
