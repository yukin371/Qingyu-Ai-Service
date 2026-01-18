"""Tool基类

定义统一的Tool接口和基础实现
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field

from src.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ToolMetadata:
    """工具元数据"""

    name: str  # 工具名称
    description: str  # 工具描述
    category: str  # 分类：writing, knowledge, analysis
    requires_auth: bool = True  # 是否需要认证
    requires_project: bool = False  # 是否需要项目上下文
    version: str = "1.0.0"  # 版本

    # 高级配置
    timeout_seconds: int = 30  # 超时时间
    max_retries: int = 3  # 最大重试次数
    rate_limit_per_minute: int = 60  # 速率限制


class ToolInputSchema(BaseModel):
    """工具输入Schema基类"""

    class Config:
        extra = "forbid"  # 禁止额外字段


class ToolResult(BaseModel):
    """工具执行结果"""

    success: bool = Field(..., description="是否成功")
    data: Any = Field(default=None, description="返回数据")
    error: Optional[str] = Field(default=None, description="错误信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

    # 性能指标
    duration_ms: int = Field(default=0, description="执行时长（毫秒）")
    retries: int = Field(default=0, description="重试次数")


class BaseTool(ABC):
    """工具基类

    所有Tool必须继承此基类并实现:
    1. input_schema 属性 - 返回Pydantic模型类
    2. _execute_impl 方法 - 实际执行逻辑
    """

    def __init__(
        self,
        metadata: ToolMetadata,
        auth_context: Optional[Dict[str, str]] = None,
    ):
        """初始化

        Args:
            metadata: 工具元数据
            auth_context: 认证上下文（user_id, token等）
        """
        self.metadata = metadata
        self.auth_context = auth_context or {}
        self.logger = get_logger(f"tool.{metadata.name}")

    @property
    @abstractmethod
    def input_schema(self) -> Type[ToolInputSchema]:
        """输入Schema（子类必须实现）

        Returns:
            Pydantic模型类
        """
        pass

    @abstractmethod
    async def _execute_impl(self, validated_input: ToolInputSchema) -> ToolResult:
        """执行实现（子类必须实现）

        Args:
            validated_input: 已验证的输入

        Returns:
            工具执行结果
        """
        pass

    async def execute(
        self,
        params: Dict[str, Any],
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        agent_call_id: Optional[str] = None,
    ) -> ToolResult:
        """执行工具（对外接口）

        Args:
            params: 参数字典
            user_id: 用户ID
            project_id: 项目ID
            agent_call_id: Agent调用ID

        Returns:
            工具执行结果
        """
        loop = asyncio.get_event_loop()
        start_time = loop.time()
        retries = 0

        try:
            # 1. 权限检查
            if self.metadata.requires_auth and not user_id:
                return ToolResult(
                    success=False, error="Missing user_id for authenticated tool"
                )

            if self.metadata.requires_project and not project_id:
                return ToolResult(
                    success=False, error="Missing project_id for project-scoped tool"
                )

            # 2. 参数验证
            try:
                validated_input = self.input_schema(**params)
            except Exception as e:
                self.logger.error(f"Parameter validation failed: {e}")
                return ToolResult(success=False, error=f"Invalid parameters: {str(e)}")

            # 3. 执行（带重试）
            last_error = None
            for attempt in range(self.metadata.max_retries):
                try:
                    # 设置超时
                    result = await asyncio.wait_for(
                        self._execute_impl(validated_input),
                        timeout=self.metadata.timeout_seconds,
                    )

                    # 计算耗时
                    duration_ms = int((loop.time() - start_time) * 1000)
                    result.duration_ms = duration_ms
                    result.retries = retries

                    self.logger.info(
                        "Tool executed successfully",
                        tool=self.metadata.name,
                        duration_ms=duration_ms,
                        retries=retries,
                    )

                    return result

                except asyncio.TimeoutError:
                    last_error = f"Timeout after {self.metadata.timeout_seconds}s"
                    retries += 1
                    self.logger.warning(
                        f"Tool execution timeout (attempt {attempt + 1}/{self.metadata.max_retries})",
                        tool=self.metadata.name,
                    )

                except Exception as e:
                    last_error = str(e)
                    retries += 1
                    self.logger.error(
                        f"Tool execution failed (attempt {attempt + 1}/{self.metadata.max_retries})",
                        tool=self.metadata.name,
                        error=str(e),
                    )

                    # 只在特定错误时重试
                    if not self._is_retryable_error(e):
                        break

                    # 指数退避
                    if attempt < self.metadata.max_retries - 1:
                        await asyncio.sleep(2**attempt)

            # 所有重试失败
            return ToolResult(
                success=False,
                error=f"Tool execution failed after {retries} retries: {last_error}",
                retries=retries,
            )

        except Exception as e:
            self.logger.error(f"Unexpected error in tool execution: {e}", exc_info=True)
            return ToolResult(success=False, error=f"Unexpected error: {str(e)}")

    def _is_retryable_error(self, error: Exception) -> bool:
        """判断错误是否可重试

        Args:
            error: 异常对象

        Returns:
            是否可重试
        """
        # 网络错误、超时错误可重试
        retryable_types = (
            asyncio.TimeoutError,
            ConnectionError,
            TimeoutError,
        )
        return isinstance(error, retryable_types)

    def get_langchain_schema(self) -> Dict[str, Any]:
        """获取LangChain Tool Schema

        Returns:
            符合LangChain格式的Schema
        """
        schema = self.input_schema.schema()

        return {
            "name": self.metadata.name,
            "description": self.metadata.description,
            "parameters": {
                "type": "object",
                "properties": schema.get("properties", {}),
                "required": schema.get("required", []),
            },
        }

