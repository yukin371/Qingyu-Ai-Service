"""
工具执行结果定义
"""
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ToolStatus(str, Enum):
    """工具执行状态"""

    SUCCESS = "success"  # 成功
    FAILED = "failed"  # 失败
    PARTIAL = "partial"  # 部分成功
    TIMEOUT = "timeout"  # 超时
    PERMISSION_DENIED = "permission_denied"  # 权限拒绝
    INVALID_INPUT = "invalid_input"  # 输入无效


class ToolResult(BaseModel):
    """工具执行结果

    MCP工具范式的统一返回格式
    """

    # 执行状态
    status: ToolStatus = Field(..., description="执行状态")
    success: bool = Field(..., description="是否成功")

    # 结果数据
    data: Optional[Any] = Field(None, description="结果数据")
    message: Optional[str] = Field(None, description="结果消息")
    error: Optional[str] = Field(None, description="错误信息")

    # 元数据
    tool_name: str = Field(..., description="工具名称")
    execution_time: Optional[float] = Field(None, description="执行时间（秒）")
    tokens_used: Optional[int] = Field(None, description="Token消耗")
    metadata: Dict = Field(default_factory=dict, description="额外元数据")

    # 调试信息
    debug_info: Optional[Dict] = Field(None, description="调试信息")

    @classmethod
    def success_result(
        cls,
        tool_name: str,
        data: Any,
        message: Optional[str] = None,
        execution_time: Optional[float] = None,
        tokens_used: Optional[int] = None,
        **kwargs,
    ) -> "ToolResult":
        """创建成功结果"""
        return cls(
            status=ToolStatus.SUCCESS,
            success=True,
            tool_name=tool_name,
            data=data,
            message=message or "执行成功",
            execution_time=execution_time,
            tokens_used=tokens_used,
            **kwargs,
        )

    @classmethod
    def failed_result(
        cls,
        tool_name: str,
        error: str,
        status: ToolStatus = ToolStatus.FAILED,
        execution_time: Optional[float] = None,
        **kwargs,
    ) -> "ToolResult":
        """创建失败结果"""
        return cls(
            status=status,
            success=False,
            tool_name=tool_name,
            error=error,
            message=f"执行失败: {error}",
            execution_time=execution_time,
            **kwargs,
        )

    @classmethod
    def invalid_input_result(
        cls, tool_name: str, error: str, **kwargs
    ) -> "ToolResult":
        """创建输入无效结果"""
        return cls.failed_result(
            tool_name=tool_name,
            error=error,
            status=ToolStatus.INVALID_INPUT,
            **kwargs,
        )

    @classmethod
    def permission_denied_result(
        cls, tool_name: str, error: str = "权限不足", **kwargs
    ) -> "ToolResult":
        """创建权限拒绝结果"""
        return cls.failed_result(
            tool_name=tool_name,
            error=error,
            status=ToolStatus.PERMISSION_DENIED,
            **kwargs,
        )

    def to_dict(self) -> Dict:
        """转换为字典"""
        return self.model_dump()

    def __str__(self) -> str:
        if self.success:
            return f"ToolResult<{self.tool_name}: {self.status}>"
        else:
            return f"ToolResult<{self.tool_name}: {self.status} - {self.error}>"

    def __repr__(self) -> str:
        return self.__str__()

