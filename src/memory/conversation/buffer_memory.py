"""
Buffer Memory Implementation

This module provides a simple buffer-based conversation memory that stores
recent messages up to a configurable limit. Compatible with LangChain 1.2.x.
"""

import threading
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage

from src.common.types.memory_types import MemoryType, MemoryScope
from src.common.types.agent_types import Message, MessageRole
from src.common.exceptions import MemoryValidationError, MemoryOperationError


class BufferMemory:
    """
    Buffer-based conversation memory.

    Stores recent messages in memory with a configurable limit.
    When the limit is exceeded, oldest messages are removed first (FIFO).

    Attributes:
        max_messages: Maximum number of messages to store
        memory_type: Type of memory (EPISODIC, WORKING, etc.)
        scope: Memory scope (SESSION, USER, AGENT, GLOBAL)
        session_id: Session identifier
        user_id: User identifier
        return_messages: Whether to return Message objects (LangChain compatibility)

    Example:
        >>> memory = BufferMemory(max_messages=10, session_id="session123")
        >>> memory.add_message(Message(role=MessageRole.HUMAN, content="Hello"))
        >>> messages = memory.get_messages()
        >>> memory.clear()
    """

    def __init__(
        self,
        max_messages: int = 10,
        memory_type: MemoryType = MemoryType.WORKING,
        scope: MemoryScope = MemoryScope.SESSION,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        return_messages: bool = True,
    ):
        """
        Initialize BufferMemory.

        Args:
            max_messages: Maximum number of messages to store
            memory_type: Type of memory
            scope: Memory scope
            session_id: Session identifier (for SESSION scope)
            user_id: User identifier (for USER scope)
            return_messages: Whether to return Message objects

        Raises:
            MemoryValidationError: If max_messages is invalid
        """
        if max_messages <= 0:
            raise MemoryValidationError(
                f"max_messages must be positive, got {max_messages}"
            )

        self.max_messages = max_messages
        self.memory_type = memory_type
        self.scope = scope
        self.session_id = session_id or str(uuid4())
        self.user_id = user_id
        self.return_messages = return_messages

        self._messages: List[Message] = []
        self._lock = threading.Lock()

    @property
    def messages(self) -> List[Message]:
        """Get all stored messages."""
        return self._messages.copy()

    @property
    def message_count(self) -> int:
        """Get the number of stored messages."""
        return len(self._messages)

    def add_message(self, message: Union[Message, BaseMessage, str]) -> None:
        """
        Add a message to memory.

        Args:
            message: Message to add (Message, BaseMessage, or string)

        Raises:
            MemoryValidationError: If message is invalid
            MemoryOperationError: If operation fails
        """
        try:
            with self._lock:
                # Convert LangChain messages to our Message type
                if isinstance(message, BaseMessage):
                    converted = self._convert_langchain_message(message)
                elif isinstance(message, str):
                    converted = Message(
                        role=MessageRole.USER,
                        content=message
                    )
                elif isinstance(message, Message):
                    converted = message
                else:
                    raise MemoryValidationError(
                        f"Invalid message type: {type(message)}"
                    )

                # Add message
                self._messages.append(converted)

                # Trim if necessary
                if len(self._messages) > self.max_messages:
                    # Remove oldest messages
                    self._messages = self._messages[-self.max_messages:]

        except MemoryValidationError:
            raise
        except Exception as e:
            raise MemoryOperationError(
                f"Failed to add message: {str(e)}"
            )

    def _convert_langchain_message(self, message: BaseMessage) -> Message:
        """
        Convert LangChain BaseMessage to our Message type.

        Args:
            message: LangChain message

        Returns:
            Converted Message
        """
        # Map LangChain message types to our roles
        if isinstance(message, HumanMessage):
            role = MessageRole.USER
        elif isinstance(message, AIMessage):
            role = MessageRole.ASSISTANT
        elif isinstance(message, SystemMessage):
            role = MessageRole.SYSTEM
        else:
            # Default to USER for unknown types
            role = MessageRole.USER

        return Message(
            role=role,
            content=message.content,
            metadata=message.kwargs if hasattr(message, 'kwargs') else {}
        )

    def get_messages(self, limit: Optional[int] = None) -> List[Message]:
        """
        Get stored messages.

        Args:
            limit: Maximum number of messages to return (most recent first)

        Returns:
            List of messages
        """
        with self._lock:
            if limit is None:
                return self._messages.copy()
            else:
                return self._messages[-limit:].copy()

    def get_last_message(self) -> Optional[Message]:
        """
        Get the most recent message.

        Returns:
            Last message or None if empty
        """
        with self._lock:
            if self._messages:
                return self._messages[-1]
            return None

    def clear(self) -> None:
        """Clear all messages from memory."""
        with self._lock:
            self._messages.clear()

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """
        Save context from conversation (LangChain compatibility).

        Args:
            inputs: Input dictionary (typically {"input": "user message"})
            outputs: Output dictionary (typically {"output": "ai response"})
        """
        # Extract messages
        if "input" in inputs:
            self.add_message(
                Message(role=MessageRole.USER, content=str(inputs["input"]))
            )

        if "output" in outputs:
            self.add_message(
                Message(role=MessageRole.ASSISTANT, content=str(outputs["output"]))
            )

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load memory variables (LangChain compatibility).

        Args:
            inputs: Input variables

        Returns:
            Dictionary with conversation history
        """
        messages = self.get_messages()
        return {
            "history": messages,
            "messages": [msg.model_dump() for msg in messages],
        }

    def trim_messages(self, max_messages: Optional[int] = None) -> None:
        """
        Manually trim messages to a limit.

        Args:
            max_messages: Maximum messages to keep (uses self.max_messages if None)
        """
        with self._lock:
            limit = max_messages or self.max_messages
            if len(self._messages) > limit:
                self._messages = self._messages[-limit:]

    def get_conversation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the conversation.

        Returns:
            Dictionary with conversation statistics
        """
        with self._lock:
            user_count = sum(1 for msg in self._messages if msg.role == MessageRole.USER)
            assistant_count = sum(1 for msg in self._messages if msg.role == MessageRole.ASSISTANT)

            return {
                "messages": len(self._messages),
                "user_messages": user_count,
                "assistant_messages": assistant_count,
                "summary": f"Conversation with {len(self._messages)} messages "
                          f"({user_count} user, {assistant_count} assistant)",
            }

    def filter_by_role(self, role: MessageRole) -> List[Message]:
        """
        Filter messages by role.

        Args:
            role: Role to filter by

        Returns:
            Filtered list of messages
        """
        with self._lock:
            return [msg for msg in self._messages if msg.role == role]

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"BufferMemory("
            f"messages={len(self._messages)}, "
            f"max={self.max_messages}, "
            f"type={self.memory_type.value}, "
            f"scope={self.scope.value})"
        )


__all__ = ["BufferMemory"]
