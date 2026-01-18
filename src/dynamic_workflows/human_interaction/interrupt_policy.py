"""
Interrupt Policy for Human-in-the-Loop Workflows

Provides mechanisms for interrupting workflow execution for human review,
approval, and intervention.
"""
from typing import Any, Callable, Dict, List, Optional, Type
from pydantic import BaseModel
from enum import Enum
import asyncio


class InterruptTrigger:
    """
    Represents an interrupt trigger

    Defines when and why a workflow should be interrupted.
    """

    def __init__(
        self,
        node_name: str,
        trigger_type: str = "manual",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize interrupt trigger

        Args:
            node_name: Node that triggers the interrupt
            trigger_type: Type of trigger (manual, automatic, conditional)
            metadata: Additional metadata
        """
        self.node_name = node_name
        self.trigger_type = trigger_type
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "node_name": self.node_name,
            "trigger_type": self.trigger_type,
            "metadata": self.metadata
        }


class InterruptCondition:
    """
    Condition for interrupting workflow execution

    Supports various condition types and composition.
    """

    def __init__(self, check_func: Callable[[BaseModel], bool]):
        """
        Initialize interrupt condition

        Args:
            check_func: Function that evaluates condition against state
        """
        self.check_func = check_func

    def check(self, state: BaseModel) -> bool:
        """
        Check if condition is met

        Args:
            state: Current workflow state

        Returns:
            True if condition is met
        """
        try:
            return self.check_func(state)
        except Exception:
            return False

    def __and__(self, other: "InterruptCondition") -> "InterruptCondition":
        """AND composition"""
        def combined_check(state: BaseModel) -> bool:
            return self.check(state) and other.check(state)

        return InterruptCondition(combined_check)

    def __or__(self, other: "InterruptCondition") -> "InterruptCondition":
        """OR composition"""
        def combined_check(state: BaseModel) -> bool:
            return self.check(state) or other.check(state)

        return InterruptCondition(combined_check)

    def __invert__(self) -> "InterruptCondition":
        """NOT composition"""
        def inverted_check(state: BaseModel) -> bool:
            return not self.check(state)

        return InterruptCondition(inverted_check)

    @staticmethod
    def always() -> "InterruptCondition":
        """Create condition that always triggers"""
        return InterruptCondition(lambda state: True)

    @staticmethod
    def never() -> "InterruptCondition":
        """Create condition that never triggers"""
        return InterruptCondition(lambda state: False)

    @staticmethod
    def field_equals(field_name: str, value: Any) -> "InterruptCondition":
        """Create field equals condition"""
        def check(state: BaseModel) -> bool:
            return getattr(state, field_name, None) == value

        return InterruptCondition(check)

    @staticmethod
    def field_greater_than(field_name: str, threshold: float) -> "InterruptCondition":
        """Create field greater than condition"""
        def check(state: BaseModel) -> bool:
            field_value = getattr(state, field_name, 0)
            return field_value > threshold

        return InterruptCondition(check)

    @staticmethod
    def field_less_than(field_name: str, threshold: float) -> "InterruptCondition":
        """Create field less than condition"""
        def check(state: BaseModel) -> bool:
            field_value = getattr(state, field_name, 0)
            return field_value < threshold

        return InterruptCondition(check)


class ApprovalStatus(str, Enum):
    """Approval status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


class ApprovalRequest:
    """
    Represents a request for human approval

    Tracks the approval workflow state.
    """

    def __init__(
        self,
        state_id: str,
        node_name: str,
        reason: str,
        timeout: int = 3600,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize approval request

        Args:
            state_id: Unique state identifier
            node_name: Node requesting approval
            reason: Reason for approval request
            timeout: Timeout in seconds
            metadata: Additional metadata
        """
        self.state_id = state_id
        self.node_name = node_name
        self.reason = reason
        self.timeout = timeout
        self.metadata = metadata or {}

        self.status = ApprovalStatus.PENDING
        self.approver: Optional[str] = None
        self.rejecter: Optional[str] = None
        self.comment: Optional[str] = None
        self.created_at = None  # Would be datetime in real implementation

    def approve(self, approver: str, comment: Optional[str] = None):
        """
        Approve the request

        Args:
            approver: Approver identifier
            comment: Optional approval comment
        """
        self.status = ApprovalStatus.APPROVED
        self.approver = approver
        self.comment = comment

    def reject(self, rejecter: str, comment: Optional[str] = None):
        """
        Reject the request

        Args:
            rejecter: Rejecter identifier
            comment: Optional rejection comment
        """
        self.status = ApprovalStatus.REJECTED
        self.rejecter = rejecter
        self.comment = comment

    def timeout_request(self):
        """Mark request as timed out"""
        self.status = ApprovalStatus.TIMEOUT

    def is_pending(self) -> bool:
        """Check if request is still pending"""
        return self.status == ApprovalStatus.PENDING

    def is_approved(self) -> bool:
        """Check if request was approved"""
        return self.status == ApprovalStatus.APPROVED

    def is_rejected(self) -> bool:
        """Check if request was rejected"""
        return self.status == ApprovalStatus.REJECTED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "state_id": self.state_id,
            "node_name": self.node_name,
            "reason": self.reason,
            "status": self.status.value,
            "timeout": self.timeout,
            "approver": self.approver,
            "rejecter": self.rejecter,
            "comment": self.comment,
            "metadata": self.metadata
        }


class InterruptPolicy:
    """
    Policy for managing workflow interrupts

    Defines conditions and rules for interrupting workflows.
    """

    def __init__(
        self,
        name: str,
        default_timeout: int = 3600
    ):
        """
        Initialize interrupt policy

        Args:
            name: Policy name
            default_timeout: Default timeout for approvals (seconds)
        """
        self.name = name
        self.default_timeout = default_timeout

        self.conditions: Dict[str, InterruptCondition] = {}
        self.interrupt_nodes: List[str] = []
        self.pending_requests: Dict[str, ApprovalRequest] = {}

    def add_condition(
        self,
        name: str,
        condition: InterruptCondition
    ) -> "InterruptPolicy":
        """
        Add interrupt condition

        Args:
            name: Condition name
            condition: Interrupt condition

        Returns:
            Self for chaining
        """
        self.conditions[name] = condition
        return self

    def add_interrupt_node(self, node_name: str) -> "InterruptPolicy":
        """
        Add node that always triggers interrupt

        Args:
            node_name: Node name

        Returns:
            Self for chaining
        """
        if node_name not in self.interrupt_nodes:
            self.interrupt_nodes.append(node_name)
        return self

    async def should_interrupt(
        self,
        state: BaseModel,
        node_name: str
    ) -> bool:
        """
        Check if workflow should interrupt

        Args:
            state: Current workflow state
            node_name: Current node name

        Returns:
            True if should interrupt
        """
        # Check if node is in interrupt list
        if node_name in self.interrupt_nodes:
            return True

        # Check conditions
        for condition in self.conditions.values():
            if condition.check(state):
                return True

        return False

    def create_request(
        self,
        state_id: str,
        node_name: str,
        reason: str,
        timeout: Optional[int] = None
    ) -> ApprovalRequest:
        """
        Create approval request

        Args:
            state_id: State identifier
            node_name: Node name
            reason: Reason for request
            timeout: Optional timeout override

        Returns:
            ApprovalRequest instance
        """
        request = ApprovalRequest(
            state_id=state_id,
            node_name=node_name,
            reason=reason,
            timeout=timeout or self.default_timeout
        )

        self.pending_requests[state_id] = request
        return request

    async def wait_for_approval(
        self,
        request: ApprovalRequest,
        timeout: Optional[int] = None
    ) -> ApprovalRequest:
        """
        Wait for approval request to be resolved

        Args:
            request: Approval request
            timeout: Timeout in seconds

        Returns:
            Resolved approval request

        Raises:
            asyncio.TimeoutError: If timeout expires
        """
        timeout = timeout or request.timeout

        try:
            # Wait for status change
            while request.is_pending():
                await asyncio.sleep(0.1)

            return request

        except asyncio.TimeoutError:
            request.timeout_request()
            raise

    def get_request(self, state_id: str) -> Optional[ApprovalRequest]:
        """
        Get approval request by state ID

        Args:
            state_id: State identifier

        Returns:
            ApprovalRequest if exists, None otherwise
        """
        return self.pending_requests.get(state_id)

    def cancel_request(self, state_id: str):
        """
        Cancel pending approval request

        Args:
            state_id: State identifier
        """
        if state_id in self.pending_requests:
            del self.pending_requests[state_id]

    def to_dict(self) -> Dict[str, Any]:
        """Convert policy to dictionary"""
        return {
            "name": self.name,
            "default_timeout": self.default_timeout,
            "condition_count": len(self.conditions),
            "interrupt_nodes": self.interrupt_nodes,
            "pending_requests": len(self.pending_requests)
        }
