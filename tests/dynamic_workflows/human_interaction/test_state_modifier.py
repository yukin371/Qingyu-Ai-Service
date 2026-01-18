"""
Tests for state modifier
"""
import pytest
import asyncio
from typing import Dict, Any
from pydantic import BaseModel
from unittest.mock import Mock, AsyncMock

from src.dynamic_workflows.human_interaction.state_modifier import (
    StateModifier,
    WorkflowStateStore,
    StateModification,
    ModificationType,
)


class MockState(BaseModel):
    """Mock state for testing"""
    value: int = 0
    status: str = "pending"
    messages: list = []
    metadata: Dict[str, Any] = {}


class TestWorkflowStateStore:
    """Test WorkflowStateStore"""

    def test_create_store(self):
        """Test creating a state store"""
        store = WorkflowStateStore()

        assert len(store.states) == 0

    def test_save_state(self):
        """Test saving state"""
        store = WorkflowStateStore()
        state = MockState(value=42, status="active")

        store.save("thread_123", state)

        assert "thread_123" in store.states
        assert store.states["thread_123"].value == 42

    def test_load_state(self):
        """Test loading state"""
        store = WorkflowStateStore()
        state = MockState(value=100)

        store.save("thread_456", state)

        loaded = store.load("thread_456")

        assert loaded.value == 100
        assert loaded.status == "pending"

    def test_load_nonexistent_state(self):
        """Test loading nonexistent state"""
        store = WorkflowStateStore()

        with pytest.raises(KeyError):
            store.load("nonexistent_thread")

    def test_delete_state(self):
        """Test deleting state"""
        store = WorkflowStateStore()
        state = MockState()

        store.save("thread_789", state)
        assert "thread_789" in store.states

        store.delete("thread_789")
        assert "thread_789" not in store.states

    def test_list_threads(self):
        """Test listing all threads"""
        store = WorkflowStateStore()

        store.save("thread_1", MockState())
        store.save("thread_2", MockState())
        store.save("thread_3", MockState())

        threads = store.list_threads()

        assert len(threads) == 3
        assert "thread_1" in threads
        assert "thread_2" in threads
        assert "thread_3" in threads


class TestStateModification:
    """Test StateModification"""

    def test_create_modification(self):
        """Test creating a state modification"""
        modification = StateModification(
            type=ModificationType.UPDATE,
            field="value",
            value=42
        )

        assert modification.type == ModificationType.UPDATE
        assert modification.field == "value"
        assert modification.value == 42

    def test_modification_to_dict(self):
        """Test converting modification to dict"""
        modification = StateModification(
            type=ModificationType.UPDATE,
            field="status",
            value="approved",
            metadata={"user": "admin"}
        )

        result = modification.to_dict()

        assert result["type"] == "update"
        assert result["field"] == "status"
        assert result["value"] == "approved"
        assert result["metadata"]["user"] == "admin"


class TestStateModifier:
    """Test StateModifier"""

    def test_create_modifier(self):
        """Test creating a state modifier"""
        store = WorkflowStateStore()
        modifier = StateModifier(store)

        assert modifier.store == store

    @pytest.mark.asyncio
    async def test_pause_workflow(self):
        """Test pausing a workflow"""
        store = WorkflowStateStore()
        modifier = StateModifier(store)

        # Save initial state
        state = MockState(value=10, status="running")
        store.save("thread_pause", state)

        # Pause workflow
        await modifier.pause_workflow("thread_pause")

        # Check status is paused
        loaded_state = store.load("thread_pause")
        assert loaded_state.status == "paused"

    @pytest.mark.asyncio
    async def test_resume_workflow(self):
        """Test resuming a workflow"""
        store = WorkflowStateStore()
        modifier = StateModifier(store)

        # Save paused state
        state = MockState(value=20, status="paused")
        store.save("thread_resume", state)

        # Resume workflow
        await modifier.resume_workflow("thread_resume")

        # Check status is running
        loaded_state = store.load("thread_resume")
        assert loaded_state.status == "running"

    @pytest.mark.asyncio
    async def test_modify_state_single_field(self):
        """Test modifying a single field"""
        store = WorkflowStateStore()
        modifier = StateModifier(store)

        # Save initial state
        state = MockState(value=5, status="pending")
        store.save("thread_modify", state)

        # Modify state
        await modifier.modify_state(
            "thread_modify",
            {"status": "approved"}
        )

        # Check modification
        loaded_state = store.load("thread_modify")
        assert loaded_state.status == "approved"
        assert loaded_state.value == 5  # Unchanged

    @pytest.mark.asyncio
    async def test_modify_state_multiple_fields(self):
        """Test modifying multiple fields"""
        store = WorkflowStateStore()
        modifier = StateModifier(store)

        # Save initial state
        state = MockState(value=1, status="pending")
        store.save("thread_multi", state)

        # Modify multiple fields
        await modifier.modify_state(
            "thread_multi",
            {
                "value": 99,
                "status": "completed",
                "messages": ["Done"]
            }
        )

        # Check modifications
        loaded_state = store.load("thread_multi")
        assert loaded_state.value == 99
        assert loaded_state.status == "completed"
        assert loaded_state.messages == ["Done"]

    @pytest.mark.asyncio
    async def test_modify_state_with_nested_dict(self):
        """Test modifying nested metadata dict"""
        store = WorkflowStateStore()
        modifier = StateModifier(store)

        # Save initial state
        state = MockState(
            value=10,
            metadata={"key1": "value1"}
        )
        store.save("thread_nested", state)

        # Modify metadata
        await modifier.modify_state(
            "thread_nested",
            {"metadata": {"key2": "value2"}}
        )

        # Check modification
        loaded_state = store.load("thread_nested")
        assert loaded_state.metadata == {"key2": "value2"}

    @pytest.mark.asyncio
    async def test_get_modification_history(self):
        """Test getting modification history"""
        store = WorkflowStateStore()
        modifier = StateModifier(store)

        # Save state
        state = MockState(value=0)
        store.save("thread_history", state)

        # Make modifications
        await modifier.modify_state("thread_history", {"value": 10})
        await modifier.modify_state("thread_history", {"status": "active"})
        await modifier.modify_state("thread_history", {"value": 20})

        # Get history
        history = await modifier.get_modification_history("thread_history")

        assert len(history) == 3
        assert history[0]["field"] == "value" or history[0]["field"] == "status"

    @pytest.mark.asyncio
    async def test_pause_and_resume_sequence(self):
        """Test pause-modify-resume sequence"""
        store = WorkflowStateStore()
        modifier = StateModifier(store)

        # Initial state
        state = MockState(value=5, status="running")
        store.save("thread_sequence", state)

        # Pause
        await modifier.pause_workflow("thread_sequence")
        assert store.load("thread_sequence").status == "paused"

        # Modify
        await modifier.modify_state("thread_sequence", {"value": 10})
        assert store.load("thread_sequence").value == 10

        # Resume
        await modifier.resume_workflow("thread_sequence")
        assert store.load("thread_sequence").status == "running"
        assert store.load("thread_sequence").value == 10

    @pytest.mark.asyncio
    async def test_modify_nonexistent_thread_raises_error(self):
        """Test that modifying nonexistent thread raises error"""
        store = WorkflowStateStore()
        modifier = StateModifier(store)

        with pytest.raises(KeyError):
            await modifier.modify_state(
                "nonexistent_thread",
                {"value": 1}
            )

    @pytest.mark.asyncio
    async def test_pause_nonexistent_thread_raises_error(self):
        """Test that pausing nonexistent thread raises error"""
        store = WorkflowStateStore()
        modifier = StateModifier(store)

        with pytest.raises(KeyError):
            await modifier.pause_workflow("nonexistent_thread")

    @pytest.mark.asyncio
    async def test_get_state_snapshot(self):
        """Test getting state snapshot"""
        store = WorkflowStateStore()
        modifier = StateModifier(store)

        # Save state
        state = MockState(value=42, status="active")
        store.save("thread_snapshot", state)

        # Get snapshot
        snapshot = await modifier.get_state_snapshot("thread_snapshot")

        assert snapshot["value"] == 42
        assert snapshot["status"] == "active"
        assert "timestamp" in snapshot

    def test_modification_type_enum(self):
        """Test ModificationType enum"""
        assert ModificationType.UPDATE.value == "update"
        assert ModificationType.DELETE.value == "delete"
        assert ModificationType.APPEND.value == "append"

    @pytest.mark.asyncio
    async def test_batch_modifications(self):
        """Test batch modifications"""
        store = WorkflowStateStore()
        modifier = StateModifier(store)

        # Save state
        state = MockState(value=0, status="pending", messages=[])
        store.save("thread_batch", state)

        # Batch modify
        modifications = [
            {"value": 10},
            {"status": "processing"},
            {"messages": ["Step 1"]}
        ]

        for mod in modifications:
            await modifier.modify_state("thread_batch", mod)

        # Verify all modifications
        loaded = store.load("thread_batch")
        assert loaded.value == 10
        assert loaded.status == "processing"
        assert loaded.messages == ["Step 1"]
