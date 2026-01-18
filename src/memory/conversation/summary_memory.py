"""
Summary Memory Implementation

This module provides conversation memory with automatic summarization using LLM.
When the buffer exceeds a limit, old messages are summarized.
"""

import threading
from typing import Any, Dict, List, Optional, Union

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.language_models import BaseChatModel

from src.memory.conversation.buffer_memory import BufferMemory
from src.common.types.memory_types import MemoryType, MemoryScope
from src.common.types.agent_types import Message, MessageRole
from src.common.exceptions import MemoryValidationError, MemoryOperationError


class SummaryMemory(BufferMemory):
    """
    Conversation memory with automatic summarization.

    Summarizes old messages when buffer exceeds limit using an LLM.
    Inherits from BufferMemory and adds summarization capabilities.

    Attributes:
        llm: Language model for generating summaries
        max_messages: Maximum messages before summarization
        summary_prompt: Custom prompt for summarization (optional)
        current_summary: Current conversation summary

    Example:
        >>> llm = ChatOpenAI(model="gpt-4")
        >>> memory = SummaryMemory(llm=llm, max_messages=10)
        >>> memory.add_message(Message(role=MessageRole.USER, content="Hello"))
        >>> # Automatically summarizes when limit exceeded
    """

    def __init__(
        self,
        llm: BaseChatModel,
        max_messages: int = 10,
        memory_type: MemoryType = MemoryType.EPISODIC,
        scope: MemoryScope = MemoryScope.SESSION,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        summary_prompt: Optional[str] = None,
        return_messages: bool = True,
    ):
        """
        Initialize SummaryMemory.

        Args:
            llm: Language model for summarization
            max_messages: Maximum messages before triggering summarization
            memory_type: Type of memory
            scope: Memory scope
            session_id: Session identifier
            user_id: User identifier
            summary_prompt: Custom prompt for summarization
            return_messages: Whether to return Message objects
        """
        super().__init__(
            max_messages=max_messages,
            memory_type=memory_type,
            scope=scope,
            session_id=session_id,
            user_id=user_id,
            return_messages=return_messages,
        )

        self.llm = llm
        self.summary_prompt = summary_prompt or self._default_summary_prompt()
        self.current_summary: Optional[str] = None
        self._lock = threading.Lock()

    def _default_summary_prompt(self) -> str:
        """Get default summarization prompt."""
        return """Summarize the following conversation concisely:

{chat_history}

Focus on key information, decisions, and outcomes."""

    def add_message(self, message: Union[Message, BaseMessage, str]) -> None:
        """
        Add a message and trigger summarization if needed.

        Args:
            message: Message to add

        Raises:
            MemoryValidationError: If message is invalid
            MemoryOperationError: If operation fails
        """
        try:
            with self._lock:
                # Add message normally
                super().add_message(message)

                # Check if we need to summarize
                if len(self._messages) > self.max_messages:
                    self._summarize_older_messages()

        except (MemoryValidationError, MemoryOperationError):
            raise
        except Exception as e:
            raise MemoryOperationError(
                f"Failed to add message to summary memory: {str(e)}"
            )

    def _summarize_older_messages(self) -> None:
        """
        Summarize older messages and keep recent ones.

        Keeps the most recent max_messages//2 messages and summarizes the rest.
        """
        try:
            # Get messages to summarize (older half)
            messages_to_summarize = self._messages[:self.max_messages // 2]
            recent_messages = self._messages[self.max_messages // 2:]

            if messages_to_summarize:
                # Generate summary
                summary = self._generate_summary(messages_to_summarize)

                # Update current summary
                if self.current_summary:
                    self.current_summary = f"{self.current_summary}\n\n{summary}"
                else:
                    self.current_summary = summary

                # Keep only recent messages
                self._messages = recent_messages

        except Exception as e:
            raise MemoryOperationError(
                f"Failed to summarize messages: {str(e)}"
            )

    def _generate_summary(self, messages: List[Message]) -> str:
        """
        Generate a summary of the given messages using LLM.

        Args:
            messages: Messages to summarize

        Returns:
            Generated summary text
        """
        try:
            # Convert messages to LangChain format
            lc_messages = self._convert_to_langchain_messages(messages)

            # Create prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a helpful assistant that summarizes conversations."),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "Please provide a concise summary of the above conversation."),
            ])

            # Invoke LLM
            chain = prompt | self.llm
            response = chain.invoke({"chat_history": lc_messages})

            return response.content

        except Exception as e:
            raise MemoryOperationError(
                f"Failed to generate summary: {str(e)}"
            )

    def _convert_to_langchain_messages(
        self,
        messages: List[Message]
    ) -> List[BaseMessage]:
        """
        Convert our Message types to LangChain BaseMessage.

        Args:
            messages: Our Message objects

        Returns:
            List of LangChain messages
        """
        lc_messages = []
        for msg in messages:
            if msg.role == MessageRole.USER:
                lc_messages.append(HumanMessage(content=msg.content))
            elif msg.role == MessageRole.ASSISTANT:
                lc_messages.append(AIMessage(content=msg.content))
            elif msg.role == MessageRole.SYSTEM:
                lc_messages.append(SystemMessage(content=msg.content))
            else:
                # Default to human
                lc_messages.append(HumanMessage(content=msg.content))

        return lc_messages

    def get_summary(self) -> Optional[str]:
        """
        Get the current conversation summary.

        Returns:
            Current summary or None if no summary exists
        """
        return self.current_summary

    def get_messages_with_summary(self) -> Dict[str, Any]:
        """
        Get both the summary and recent messages.

        Returns:
            Dictionary with 'summary' and 'messages' keys
        """
        with self._lock:
            return {
                "summary": self.current_summary,
                "messages": self._messages.copy(),
            }

    def clear(self) -> None:
        """Clear all messages and summary."""
        with self._lock:
            super().clear()
            self.current_summary = None

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load memory variables with summary included.

        Args:
            inputs: Input variables

        Returns:
            Dictionary with history including summary
        """
        with self._lock:
            messages = self.get_messages()
            return {
                "history": messages,
                "summary": self.current_summary,
                "messages": [msg.model_dump() for msg in messages],
            }

    def get_conversation_summary(self) -> Dict[str, Any]:
        """
        Get enhanced conversation summary with statistics.

        Returns:
            Dictionary with conversation statistics
        """
        base_summary = super().get_conversation_summary()

        with self._lock:
            base_summary["has_summary"] = self.current_summary is not None
            base_summary["summary_length"] = len(self.current_summary) if self.current_summary else 0

            return base_summary

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"SummaryMemory("
            f"messages={len(self._messages)}, "
            f"max={self.max_messages}, "
            f"has_summary={self.current_summary is not None}, "
            f"type={self.memory_type.value}, "
            f"scope={self.scope.value})"
        )


__all__ = ["SummaryMemory"]
