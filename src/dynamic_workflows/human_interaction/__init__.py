"""
Human-in-the-Loop Interaction

Provides capabilities for interrupting workflows and modifying state during execution.
"""

from .interrupt_policy import (
    InterruptPolicy,
    InterruptCondition,
    InterruptTrigger,
    ApprovalRequest,
    ApprovalStatus,
)

from .state_modifier import (
    StateModifier,
    WorkflowStateStore,
    StateModification,
    ModificationType,
)

__all__ = [
    # Interrupt Policy
    "InterruptPolicy",
    "InterruptCondition",
    "InterruptTrigger",
    "ApprovalRequest",
    "ApprovalStatus",

    # State Modifier
    "StateModifier",
    "WorkflowStateStore",
    "StateModification",
    "ModificationType",
]
