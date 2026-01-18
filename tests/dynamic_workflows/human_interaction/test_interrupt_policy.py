"""
Tests for interrupt policy
"""
import pytest
import asyncio
from typing import Dict, Any
from pydantic import BaseModel

from src.dynamic_workflows.human_interaction.interrupt_policy import (
    InterruptPolicy,
    InterruptTrigger,
    InterruptCondition,
    ApprovalRequest,
)


class MockState(BaseModel):
    """Mock state for testing"""
    value: int = 0
    status: str = "pending"
    requires_approval: bool = False
    user_role: str = "user"


class TestInterruptTrigger:
    """Test InterruptTrigger"""

    def test_create_trigger(self):
        """Test creating an interrupt trigger"""
        trigger = InterruptTrigger(
            node_name="approval_node",
            trigger_type="manual"
        )

        assert trigger.node_name == "approval_node"
        assert trigger.trigger_type == "manual"
        assert trigger.metadata == {}

    def test_create_trigger_with_metadata(self):
        """Test creating trigger with metadata"""
        trigger = InterruptTrigger(
            node_name="review",
            trigger_type="automatic",
            metadata={"reason": "high_value", "threshold": 1000}
        )

        assert trigger.metadata["threshold"] == 1000


class TestInterruptCondition:
    """Test InterruptCondition"""

    def test_always_condition(self):
        """Test always interrupt condition"""
        condition = InterruptCondition.always()

        assert condition.check(MockState()) is True

    def test_never_condition(self):
        """Test never interrupt condition"""
        condition = InterruptCondition.never()

        assert condition.check(MockState()) is False

    def test_field_equals_condition(self):
        """Test field equals condition"""
        condition = InterruptCondition.field_equals(
            "status", "needs_review"
        )

        # Matching state
        assert condition.check(MockState(status="needs_review")) is True

        # Non-matching state
        assert condition.check(MockState(status="approved")) is False

    def test_field_greater_than_condition(self):
        """Test field greater than condition"""
        condition = InterruptCondition.field_greater_than("value", 100)

        # Greater than
        assert condition.check(MockState(value=150)) is True

        # Not greater than
        assert condition.check(MockState(value=50)) is False

    def test_custom_condition(self):
        """Test custom condition function"""
        def custom_check(state: MockState) -> bool:
            return state.requires_approval and state.value > 50

        condition = InterruptCondition(custom_check)

        # Should interrupt
        assert condition.check(MockState(
            requires_approval=True,
            value=100
        )) is True

        # Should not interrupt (value too low)
        assert condition.check(MockState(
            requires_approval=True,
            value=30
        )) is False

        # Should not interrupt (not required)
        assert condition.check(MockState(
            requires_approval=False,
            value=100
        )) is False

    def test_and_condition(self):
        """Test AND condition composition"""
        cond1 = InterruptCondition.field_equals("status", "pending")
        cond2 = InterruptCondition.field_greater_than("value", 50)

        combined = cond1 & cond2

        # Both conditions met
        assert combined.check(MockState(status="pending", value=100)) is True

        # Only first condition met
        assert combined.check(MockState(status="pending", value=30)) is False

        # Only second condition met
        assert combined.check(MockState(status="approved", value=100)) is False

    def test_or_condition(self):
        """Test OR condition composition"""
        cond1 = InterruptCondition.field_equals("user_role", "admin")
        cond2 = InterruptCondition.field_greater_than("value", 1000)

        combined = cond1 | cond2

        # First condition met
        assert combined.check(MockState(user_role="admin", value=10)) is True

        # Second condition met
        assert combined.check(MockState(user_role="user", value=1500)) is True

        # Neither condition met
        assert combined.check(MockState(user_role="user", value=100)) is False

    def test_not_condition(self):
        """Test NOT condition"""
        condition = InterruptCondition.field_equals("status", "approved")
        inverted = ~condition

        # Original condition would be true
        assert condition.check(MockState(status="approved")) is True
        assert inverted.check(MockState(status="approved")) is False

        # Original condition would be false
        assert condition.check(MockState(status="pending")) is False
        assert inverted.check(MockState(status="pending")) is True


class TestApprovalRequest:
    """Test ApprovalRequest"""

    def test_create_approval_request(self):
        """Test creating an approval request"""
        request = ApprovalRequest(
            state_id="test_state_123",
            node_name="review_node",
            reason="High value transaction requires approval",
            timeout=3600
        )

        assert request.state_id == "test_state_123"
        assert request.node_name == "review_node"
        assert request.reason == "High value transaction requires approval"
        assert request.timeout == 3600
        assert request.status == "pending"

    def test_request_approval(self):
        """Test approving a request"""
        request = ApprovalRequest(
            state_id="state_1",
            node_name="node_1",
            reason="Test"
        )

        request.approve(approver="admin", comment="Approved")

        assert request.status == "approved"
        assert request.approver == "admin"
        assert request.comment == "Approved"

    def test_request_rejection(self):
        """Test rejecting a request"""
        request = ApprovalRequest(
            state_id="state_1",
            node_name="node_1",
            reason="Test"
        )

        request.reject(rejecter="admin", comment="Insufficient information")

        assert request.status == "rejected"
        assert request.rejecter == "admin"
        assert request.comment == "Insufficient information"

    def test_request_timeout(self):
        """Test request timeout"""
        request = ApprovalRequest(
            state_id="state_1",
            node_name="node_1",
            reason="Test"
        )

        request.timeout_request()

        assert request.status == "timeout"

    def test_is_pending(self):
        """Test is_pending check"""
        request = ApprovalRequest(
            state_id="state_1",
            node_name="node_1",
            reason="Test"
        )

        assert request.is_pending() is True

        request.approve("admin")
        assert request.is_pending() is False


class TestInterruptPolicy:
    """Test InterruptPolicy"""

    def test_create_policy(self):
        """Test creating an interrupt policy"""
        policy = InterruptPolicy(name="test_policy")

        assert policy.name == "test_policy"
        assert len(policy.conditions) == 0

    def test_add_condition(self):
        """Test adding interrupt condition"""
        policy = InterruptPolicy(name="conditional_policy")
        condition = InterruptCondition.field_greater_than("value", 100)

        policy.add_condition("high_value_check", condition)

        assert "high_value_check" in policy.conditions
        assert policy.conditions["high_value_check"] == condition

    def test_should_interrupt_with_condition(self):
        """Test should_interrupt with matching condition"""
        policy = InterruptPolicy(name="value_check")
        policy.add_condition(
            "check_value",
            InterruptCondition.field_greater_than("value", 100)
        )

        # Should interrupt (value > 100)
        result = asyncio.run(policy.should_interrupt(
            MockState(value=150),
            "process_node"
        ))
        assert result is True

        # Should not interrupt (value <= 100)
        result = asyncio.run(policy.should_interrupt(
            MockState(value=50),
            "process_node"
        ))
        assert result is False

    def test_should_interrupt_for_specific_node(self):
        """Test interrupt only for specific nodes"""
        policy = InterruptPolicy(name="node_specific")
        policy.add_interrupt_node("approval_required")

        # Should interrupt for specified node
        result = asyncio.run(policy.should_interrupt(
            MockState(),
            "approval_required"
        ))
        assert result is True

        # Should not interrupt for other nodes
        result = asyncio.run(policy.should_interrupt(
            MockState(),
            "normal_processing"
        ))
        assert result is False

    def test_multiple_conditions(self):
        """Test policy with multiple conditions"""
        policy = InterruptPolicy(name="multi_condition")
        policy.add_condition(
            "admin_check",
            InterruptCondition.field_equals("user_role", "admin")
        )
        policy.add_condition(
            "high_value_check",
            InterruptCondition.field_greater_than("value", 1000)
        )

        # Interrupt if user is admin
        result = asyncio.run(policy.should_interrupt(
            MockState(user_role="admin", value=10),
            "process"
        ))
        assert result is True

        # Interrupt if value is high
        result = asyncio.run(policy.should_interrupt(
            MockState(user_role="user", value=1500),
            "process"
        ))
        assert result is True

        # Don't interrupt if neither condition met
        result = asyncio.run(policy.should_interrupt(
            MockState(user_role="user", value=100),
            "process"
        ))
        assert result is False

    def test_create_approval_request(self):
        """Test creating approval request"""
        policy = InterruptPolicy(name="approval_policy")

        request = policy.create_request(
            state_id="state_123",
            node_name="review",
            reason="Manual review required"
        )

        assert isinstance(request, ApprovalRequest)
        assert request.state_id == "state_123"
        assert request.node_name == "review"

    def test_wait_for_approval_timeout(self):
        """Test waiting for approval with timeout"""
        policy = InterruptPolicy(name="timeout_policy")

        request = ApprovalRequest(
            state_id="test_state",
            node_name="test_node",
            reason="Test",
            timeout=1  # 1 second timeout
        )

        # Manually trigger timeout
        request.timeout_request()

        # Check request status is timeout
        assert request.is_pending() is False
        assert request.status == "timeout"

    def test_wait_for_approval_immediate(self):
        """Test immediate approval"""
        policy = InterruptPolicy(name="immediate_policy")

        request = ApprovalRequest(
            state_id="test_state",
            node_name="test_node",
            reason="Test"
        )

        # Approve immediately
        request.approve("admin")

        # Check status changed
        assert request.is_pending() is False
        assert request.is_approved() is True
        assert request.approver == "admin"
