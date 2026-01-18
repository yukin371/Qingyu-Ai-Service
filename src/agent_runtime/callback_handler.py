"""
Agent Callback Handler - 回调处理

处理 Agent 执行过程中的各种事件，包括：
- LLM 调用（start, new_token, end, error）
- Tool 调用（start, end, error）
- Chain 执行（start, end, error）
- 自定义事件

集成 LangSmith 进行日志记录，支持流式输出到客户端。
"""
import logging
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field

from pydantic import BaseModel, Field
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)


# =============================================================================
# Callback Event
# =============================================================================

@dataclass
class CallbackEvent:
    """
    回调事件

    记录 Agent 执行过程中的单个事件。
    """

    event_type: str  # Event type (e.g., 'llm_start', 'tool_end')
    session_id: str  # Session ID
    user_id: str  # User ID
    data: Dict[str, Any] = field(default_factory=dict)  # Event data
    timestamp: datetime = field(default_factory=datetime.utcnow)  # Event timestamp
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "event_type": self.event_type,
            "data": self.data,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


# =============================================================================
# Agent Callback Handler
# =============================================================================

class AgentCallbackHandler(BaseCallbackHandler):
    """
    Agent 回调处理器

    处理 LangChain 执行过程中的所有回调事件。

    功能：
    - 记录所有事件到内存
    - 流式传输 token 到客户端
    - 发送事件到 LangSmith（可选）
    - 生成执行摘要

    使用示例:
        ```python
        handler = AgentCallbackHandler(
            session_id="session_123",
            user_id="user_abc",
            enable_langsmith=True,
            enable_streaming=True,
        )

        # 流式回调
        def stream_callback(token: str):
            print(f"Token: {token}")

        handler.streaming_callback = stream_callback

        # 使用 handler
        result = agent.invoke(
            input="Hello!",
            config={"callbacks": [handler]}
        )

        # 获取摘要
        summary = handler.get_summary()
        ```
    """

    def __init__(
        self,
        session_id: str,
        user_id: str,
        enable_langsmith: bool = True,
        enable_streaming: bool = False,
        max_events: int = 1000,
    ):
        """
        初始化回调处理器

        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            enable_langsmith: 是否启用 LangSmith 日志
            enable_streaming: 是否启用流式输出
            max_events: 最大事件数量
        """
        super().__init__()

        self.session_id = session_id
        self.user_id = user_id
        self.enable_langsmith = enable_langsmith
        self.enable_streaming = enable_streaming
        self.max_events = max_events

        # 事件存储
        self._events: List[CallbackEvent] = []

        # 流式回调
        self.streaming_callback: Optional[Callable[[str], None]] = None

        # 统计
        self._stats = {
            "llm_calls": 0,
            "tool_calls": 0,
            "chain_calls": 0,
            "errors": 0,
        }

        logger.info(
            f"CallbackHandler initialized: session={session_id}, user={user_id}, "
            f"langsmith={enable_langsmith}, streaming={enable_streaming}"
        )

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def events(self) -> List[CallbackEvent]:
        """获取所有事件"""
        return self._events.copy()

    # -------------------------------------------------------------------------
    # LLM Events
    # -------------------------------------------------------------------------

    def on_llm_start(
        self,
        prompts: List[str],
        invocation_params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """当 LLM 开始调用时触发"""
        self._add_event(
            event_type="llm_start",
            data={
                "prompts": prompts,
                "invocation_params": invocation_params or {},
            },
        )
        self._stats["llm_calls"] += 1

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """当 LLM 生成新 token 时触发"""
        self._add_event(
            event_type="llm_new_token",
            data={"token": token},
        )

        # 流式输出
        if self.enable_streaming and self.streaming_callback:
            try:
                self.streaming_callback(token)
            except Exception as e:
                logger.error(f"Error in streaming callback: {e}")

    def on_llm_end(self, result: LLMResult, **kwargs: Any) -> None:
        """当 LLM 调用结束时触发"""
        self._add_event(
            event_type="llm_end",
            data={
                "output": result.generations,
                "llm_output": result.llm_output or {},
            },
        )

    def on_llm_error(
        self,
        error: Exception,
        **kwargs: Any,
    ) -> None:
        """当 LLM 调用出错时触发"""
        self._add_event(
            event_type="llm_error",
            data={
                "error": str(error),
                "error_type": type(error).__name__,
            },
        )
        self._stats["errors"] += 1
        logger.error(f"LLM error: {error}")

    # -------------------------------------------------------------------------
    # Chain Events
    # -------------------------------------------------------------------------

    def on_chain_start(
        self,
        inputs: Dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """当 Chain 开始执行时触发"""
        self._add_event(
            event_type="chain_start",
            data={"inputs": inputs},
        )
        self._stats["chain_calls"] += 1

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """当 Chain 执行结束时触发"""
        self._add_event(
            event_type="chain_end",
            data={"outputs": outputs},
        )

    def on_chain_error(
        self,
        error: Exception,
        **kwargs: Any,
    ) -> None:
        """当 Chain 执行出错时触发"""
        self._add_event(
            event_type="chain_error",
            data={
                "error": str(error),
                "error_type": type(error).__name__,
            },
        )
        self._stats["errors"] += 1
        logger.error(f"Chain error: {error}")

    # -------------------------------------------------------------------------
    # Tool Events
    # -------------------------------------------------------------------------

    def on_tool_start(
        self,
        tool_name: str,
        input_str: str | Dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """当 Tool 开始执行时触发"""
        self._add_event(
            event_type="tool_start",
            data={
                "tool_name": tool_name,
                "input": input_str,
            },
        )
        self._stats["tool_calls"] += 1

    def on_tool_end(
        self,
        output: str,
        **kwargs: Any,
    ) -> None:
        """当 Tool 执行结束时触发"""
        self._add_event(
            event_type="tool_end",
            data={"output": output},
        )

    def on_tool_error(
        self,
        error: Exception,
        **kwargs: Any,
    ) -> None:
        """当 Tool 执行出错时触发"""
        self._add_event(
            event_type="tool_error",
            data={
                "error": str(error),
                "error_type": type(error).__name__,
            },
        )
        self._stats["errors"] += 1
        logger.error(f"Tool error: {error}")

    # -------------------------------------------------------------------------
    # Event Management
    # -------------------------------------------------------------------------

    def _add_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        添加事件

        Args:
            event_type: 事件类型
            data: 事件数据
        """
        event = CallbackEvent(
            event_type=event_type,
            data=data,
            session_id=self.session_id,
            user_id=self.user_id,
        )

        self._events.append(event)

        # 限制事件数量
        if len(self._events) > self.max_events:
            self._events = self._events[-self.max_events:]

        # 发送到 LangSmith（如果启用）
        if self.enable_langsmith:
            try:
                self._send_to_langsmith(event)
            except Exception as e:
                logger.error(f"Error sending to LangSmith: {e}")

    def get_events_by_type(self, prefix: str = "") -> List[CallbackEvent]:
        """
        按类型筛选事件

        Args:
            prefix: 事件类型前缀

        Returns:
            List of events matching the prefix
        """
        if prefix:
            return [e for e in self._events if e.event_type.startswith(prefix)]
        return self._events.copy()

    def get_events_since(self, timestamp: datetime) -> List[CallbackEvent]:
        """
        获取指定时间之后的事件

        Args:
            timestamp: 时间戳

        Returns:
            List of events after the timestamp
        """
        return [e for e in self._events if e.timestamp > timestamp]

    def clear_events(self) -> None:
        """清除所有事件"""
        self._events.clear()
        self._stats = {
            "llm_calls": 0,
            "tool_calls": 0,
            "chain_calls": 0,
            "errors": 0,
        }
        logger.info("Events cleared")

    def get_summary(self) -> Dict[str, Any]:
        """
        获取执行摘要

        Returns:
            Dictionary with execution summary
        """
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "total_events": len(self._events),
            "llm_calls": self._stats["llm_calls"],
            "tool_calls": self._stats["tool_calls"],
            "chain_calls": self._stats["chain_calls"],
            "errors": self._stats["errors"],
            "event_types": self._count_event_types(),
        }

    def _count_event_types(self) -> Dict[str, int]:
        """统计各类型事件数量"""
        counts: Dict[str, int] = {}
        for event in self._events:
            event_type = event.event_type
            counts[event_type] = counts.get(event_type, 0) + 1
        return counts

    # -------------------------------------------------------------------------
    # LangSmith Integration
    # -------------------------------------------------------------------------

    def _send_to_langsmith(self, event: CallbackEvent) -> None:
        """
        发送事件到 LangSmith

        Args:
            event: 要发送的事件
        """
        # LangSmith 集成由 LangChain 自动处理
        # 这里我们只记录日志
        logger.debug(f"Event logged to LangSmith: {event.event_type}")

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Convert handler to dictionary"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "enable_langsmith": self.enable_langsmith,
            "enable_streaming": self.enable_streaming,
            "events": [e.to_dict() for e in self._events],
            "stats": self._stats,
        }


# =============================================================================
# Convenience Functions
# =============================================================================

def create_callback_handler(
    session_id: str,
    user_id: str,
    **kwargs
) -> AgentCallbackHandler:
    """
    创建回调处理器

    Args:
        session_id: 会话 ID
        user_id: 用户 ID
        **kwargs: 其他配置参数

    Returns:
        AgentCallbackHandler instance
    """
    return AgentCallbackHandler(
        session_id=session_id,
        user_id=user_id,
        **kwargs
    )
