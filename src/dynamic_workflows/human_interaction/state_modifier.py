"""
State Modifier for Human-in-the-Loop Workflows

Provides capabilities for modifying workflow state during execution,
including pausing, resuming, and updating state.
"""
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel
from enum import Enum
import asyncio
from datetime import datetime


class ModificationType(str, Enum):
    """Types of state modifications"""
    UPDATE = "update"
    DELETE = "delete"
    APPEND = "append"


class StateModification:
    """
    Represents a single state modification
    """

    def __init__(
        self,
        type: ModificationType,
        field: str,
        value: Any = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize state modification

        Args:
            type: Modification type
            field: Field to modify
            value: New value (for update/append)
            metadata: Additional metadata
        """
        self.type = type
        self.field = field
        self.value = value
        self.metadata = metadata or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "type": self.type.value,
            "field": self.field,
            "value": self.value,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class WorkflowStateStore:
    """
    In-memory store for workflow states

    In production, this would be replaced with a persistent store.
    """

    def __init__(self):
        """Initialize state store"""
        self.states: Dict[str, BaseModel] = {}
        self.history: Dict[str, List[StateModification]] = {}

    def save(self, thread_id: str, state: BaseModel):
        """
        Save workflow state

        Args:
            thread_id: Thread identifier
            state: State to save
        """
        self.states[thread_id] = state

        # Initialize history if needed
        if thread_id not in self.history:
            self.history[thread_id] = []

    def load(self, thread_id: str) -> BaseModel:
        """
        Load workflow state

        Args:
            thread_id: Thread identifier

        Returns:
            Saved state

        Raises:
            KeyError: If thread not found
        """
        if thread_id not in self.states:
            raise KeyError(f"Thread '{thread_id}' not found")

        return self.states[thread_id]

    def delete(self, thread_id: str):
        """
        Delete workflow state

        Args:
            thread_id: Thread identifier
        """
        if thread_id in self.states:
            del self.states[thread_id]

        if thread_id in self.history:
            del self.history[thread_id]

    def list_threads(self) -> List[str]:
        """
        List all thread IDs

        Returns:
            List of thread IDs
        """
        return list(self.states.keys())

    def add_modification(
        self,
        thread_id: str,
        modification: StateModification
    ):
        """
        Add modification to history

        Args:
            thread_id: Thread identifier
            modification: Modification to record
        """
        if thread_id not in self.history:
            self.history[thread_id] = []

        self.history[thread_id].append(modification)

    def get_history(self, thread_id: str) -> List[StateModification]:
        """
        Get modification history

        Args:
            thread_id: Thread identifier

        Returns:
            List of modifications
        """
        return self.history.get(thread_id, [])


class StateModifier:
    """
    Modifier for workflow state

    Provides operations to pause, resume, and modify workflow state.
    """

    def __init__(self, store: Optional[WorkflowStateStore] = None):
        """
        Initialize state modifier

        Args:
            store: State store (creates new if None)
        """
        self.store = store or WorkflowStateStore()

    async def pause_workflow(self, thread_id: str):
        """
        Pause workflow execution

        Args:
            thread_id: Thread identifier

        Raises:
            KeyError: If thread not found
        """
        state = self.store.load(thread_id)

        # Update status if supported
        if hasattr(state, "status"):
            state.status = "paused"

            # Record modification
            modification = StateModification(
                type=ModificationType.UPDATE,
                field="status",
                value="paused",
                metadata={"action": "pause_workflow"}
            )
            self.store.add_modification(thread_id, modification)

        # Save updated state
        self.store.save(thread_id, state)

    async def resume_workflow(self, thread_id: str):
        """
        Resume workflow execution

        Args:
            thread_id: Thread identifier

        Raises:
            KeyError: If thread not found
        """
        state = self.store.load(thread_id)

        # Update status if supported
        if hasattr(state, "status"):
            state.status = "running"

            # Record modification
            modification = StateModification(
                type=ModificationType.UPDATE,
                field="status",
                value="running",
                metadata={"action": "resume_workflow"}
            )
            self.store.add_modification(thread_id, modification)

        # Save updated state
        self.store.save(thread_id, state)

    async def modify_state(
        self,
        thread_id: str,
        updates: Dict[str, Any]
    ):
        """
        Modify workflow state

        Args:
            thread_id: Thread identifier
            updates: Dictionary of field updates

        Raises:
            KeyError: If thread not found
        """
        state = self.store.load(thread_id)

        # Apply updates
        for field, value in updates.items():
            if hasattr(state, field):
                # Record modification
                modification = StateModification(
                    type=ModificationType.UPDATE,
                    field=field,
                    value=value
                )
                self.store.add_modification(thread_id, modification)

                # Update field
                setattr(state, field, value)

        # Save updated state
        self.store.save(thread_id, state)

    async def append_to_field(
        self,
        thread_id: str,
        field: str,
        value: Any
    ):
        """
        Append value to a list field

        Args:
            thread_id: Thread identifier
            field: Field name (must be a list)
            value: Value to append

        Raises:
            KeyError: If thread not found
            AttributeError: If field is not a list
        """
        state = self.store.load(thread_id)

        if hasattr(state, field):
            current_value = getattr(state, field)

            if not isinstance(current_value, list):
                raise AttributeError(f"Field '{field}' is not a list")

            # Append value
            current_value.append(value)

            # Record modification
            modification = StateModification(
                type=ModificationType.APPEND,
                field=field,
                value=value
            )
            self.store.add_modification(thread_id, modification)

            # Save updated state
            self.store.save(thread_id, state)

    async def delete_field(
        self,
        thread_id: str,
        field: str
    ):
        """
        Delete a field from state

        Args:
            thread_id: Thread identifier
            field: Field to delete

        Raises:
            KeyError: If thread not found
        """
        state = self.store.load(thread_id)

        if hasattr(state, field):
            # Record modification
            old_value = getattr(state, field)
            modification = StateModification(
                type=ModificationType.DELETE,
                field=field,
                value=old_value
            )
            self.store.add_modification(thread_id, modification)

            # Delete field (set to None or default)
            setattr(state, field, None)

            # Save updated state
            self.store.save(thread_id, state)

    async def get_modification_history(
        self,
        thread_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get modification history for thread

        Args:
            thread_id: Thread identifier

        Returns:
            List of modification dictionaries
        """
        if thread_id not in self.store.states:
            raise KeyError(f"Thread '{thread_id}' not found")

        history = self.store.get_history(thread_id)
        return [mod.to_dict() for mod in history]

    async def get_state_snapshot(self, thread_id: str) -> Dict[str, Any]:
        """
        Get current state snapshot

        Args:
            thread_id: Thread identifier

        Returns:
            Dictionary representation of state

        Raises:
            KeyError: If thread not found
        """
        state = self.store.load(thread_id)

        snapshot = state.model_dump() if hasattr(state, "model_dump") else state.__dict__
        snapshot["thread_id"] = thread_id
        snapshot["timestamp"] = datetime.now().isoformat()

        return snapshot

    async def create_checkpoint(self, thread_id: str, name: str):
        """
        Create a named checkpoint of current state

        Args:
            thread_id: Thread identifier
            name: Checkpoint name

        Raises:
            KeyError: If thread not found
        """
        state = self.store.load(thread_id)

        # Store checkpoint
        checkpoint_key = f"{thread_id}:checkpoint:{name}"
        self.store.save(checkpoint_key, state)

    async def restore_checkpoint(self, thread_id: str, name: str):
        """
        Restore state from checkpoint

        Args:
            thread_id: Thread identifier
            name: Checkpoint name

        Raises:
            KeyError: If checkpoint not found
        """
        checkpoint_key = f"{thread_id}:checkpoint:{name}"
        checkpoint_state = self.store.load(checkpoint_key)

        # Restore to thread
        self.store.save(thread_id, checkpoint_state)

        # Record modification
        modification = StateModification(
            type=ModificationType.UPDATE,
            field="_restore",
            value=name,
            metadata={"action": "restore_checkpoint"}
        )
        self.store.add_modification(thread_id, modification)

    def list_checkpoints(self, thread_id: str) -> List[str]:
        """
        List all checkpoints for a thread

        Args:
            thread_id: Thread identifier

        Returns:
            List of checkpoint names
        """
        checkpoints = []

        for key in self.store.list_threads():
            if key.startswith(f"{thread_id}:checkpoint:"):
                # Extract checkpoint name
                name = key.split(":")[-1]
                checkpoints.append(name)

        return checkpoints

    async def batch_modify(
        self,
        thread_id: str,
        modifications: List[Dict[str, Any]]
    ):
        """
        Apply multiple modifications atomically

        Args:
            thread_id: Thread identifier
            modifications: List of modification dicts
                Each dict: {"field": str, "value": any, "type": str}

        Raises:
            KeyError: If thread not found
        """
        state = self.store.load(thread_id)

        for mod in modifications:
            field = mod["field"]
            value = mod.get("value")
            mod_type = mod.get("type", "update")

            if mod_type == "delete":
                if hasattr(state, field):
                    old_value = getattr(state, field)
                    modification = StateModification(
                        type=ModificationType.DELETE,
                        field=field,
                        value=old_value
                    )
                    self.store.add_modification(thread_id, modification)
                    setattr(state, field, None)

            elif mod_type == "append":
                if hasattr(state, field):
                    current = getattr(state, field)
                    if isinstance(current, list):
                        current.append(value)
                        modification = StateModification(
                            type=ModificationType.APPEND,
                            field=field,
                            value=value
                        )
                        self.store.add_modification(thread_id, modification)

            else:  # update
                if hasattr(state, field):
                    modification = StateModification(
                        type=ModificationType.UPDATE,
                        field=field,
                        value=value
                    )
                    self.store.add_modification(thread_id, modification)
                    setattr(state, field, value)

        # Save updated state
        self.store.save(thread_id, state)

    def to_dict(self) -> Dict[str, Any]:
        """Convert modifier to dictionary"""
        return {
            "thread_count": len(self.store.list_threads()),
            "threads": self.store.list_threads()
        }
