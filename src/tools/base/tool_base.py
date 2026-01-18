"""
工具基类定义
"""
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type

from pydantic import ValidationError

from src.core.logger import get_logger
from src.tools.base.tool_metadata import ToolMetadata
from src.tools.base.tool_result import ToolResult, ToolStatus
from src.tools.base.tool_schema import ToolInputSchema

logger = get_logger(__name__)


class BaseTool(ABC):
    """工具基类

    MCP（Modular, Composable, Portable）工具范式的基础实现

    所有工具都应继承此类并实现:
    1. input_schema - 输入模式（Pydantic Model）
    2. _execute_impl - 具体执行逻辑
    """

    def __init__(
        self,
        metadata: ToolMetadata,
        auth_context: Optional[Dict] = None,
        **kwargs,
    ):
        """初始化工具

        Args:
            metadata: 工具元数据
            auth_context: 认证上下文（用户ID、项目ID等）
            **kwargs: 额外参数
        """
        self.metadata = metadata
        self.auth_context = auth_context or {}
        self.config = kwargs
        self._retry_count = 0

        logger.info(
            f"Tool initialized: {self.metadata.name} (v{self.metadata.version})"
        )

    # ===== 核心接口 =====

    @property
    @abstractmethod
    def input_schema(self) -> Type[ToolInputSchema]:
        """输入模式（Pydantic Model）"""
        pass

    @abstractmethod
    async def _execute_impl(self, validated_input: ToolInputSchema) -> ToolResult:
        """执行工具的具体逻辑（子类实现）

        Args:
            validated_input: 已验证的输入

        Returns:
            ToolResult: 执行结果
        """
        pass

    # ===== 公共接口 =====

    async def execute(self, input_data: Dict[str, Any]) -> ToolResult:
        """执行工具（带验证和错误处理）

        Args:
            input_data: 输入数据（字典格式）

        Returns:
            ToolResult: 执行结果
        """
        start_time = time.time()

        try:
            # Step 1: 验证权限
            if self.metadata.requires_auth:
                if not self._check_auth():
                    return ToolResult.permission_denied_result(
                        tool_name=self.metadata.name,
                        error="需要身份认证"
                    )

            if self.metadata.requires_project:
                if not self._check_project_context():
                    return ToolResult.invalid_input_result(
                        tool_name=self.metadata.name,
                        error="需要项目上下文"
                    )

            # Step 2: 验证输入
            try:
                validated_input = self.input_schema(**input_data)
            except ValidationError as e:
                error_msg = str(e)
                logger.warning(f"Tool input validation failed: {error_msg}")
                return ToolResult.invalid_input_result(
                    tool_name=self.metadata.name,
                    error=f"输入验证失败: {error_msg}",
                    execution_time=time.time() - start_time,
                )

            # Step 3: 执行工具
            logger.info(f"Executing tool: {self.metadata.name}")
            result = await self._execute_impl(validated_input)

            # Step 4: 添加元数据
            if result.execution_time is None:
                result.execution_time = time.time() - start_time

            logger.info(
                f"Tool executed successfully: {self.metadata.name} "
                f"in {result.execution_time:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(
                f"Tool execution failed: {self.metadata.name}",
                exc_info=True
            )
            return ToolResult.failed_result(
                tool_name=self.metadata.name,
                error=str(e),
                execution_time=time.time() - start_time,
                debug_info={"exception": str(e)},
            )

    async def execute_with_retry(
        self, input_data: Dict[str, Any], max_retries: Optional[int] = None
    ) -> ToolResult:
        """执行工具（带重试）

        Args:
            input_data: 输入数据
            max_retries: 最大重试次数（默认使用metadata配置）

        Returns:
            ToolResult: 执行结果
        """
        max_retries = max_retries or self.metadata.max_retries
        self._retry_count = 0

        while self._retry_count <= max_retries:
            result = await self.execute(input_data)

            if result.success:
                return result

            self._retry_count += 1
            if self._retry_count <= max_retries:
                logger.warning(
                    f"Tool execution failed, retrying... "
                    f"({self._retry_count}/{max_retries})"
                )
            else:
                logger.error(
                    f"Tool execution failed after {max_retries} retries"
                )

        return result

    # ===== 辅助方法 =====

    def _check_auth(self) -> bool:
        """检查身份认证"""
        return "user_id" in self.auth_context

    def _check_project_context(self) -> bool:
        """检查项目上下文"""
        return "project_id" in self.auth_context

    def get_name(self) -> str:
        """获取工具名称"""
        return self.metadata.name

    def get_description(self) -> str:
        """获取工具描述"""
        return self.metadata.description

    def get_category(self) -> str:
        """获取工具类别"""
        return self.metadata.category

    def get_metadata(self) -> ToolMetadata:
        """获取工具元数据"""
        return self.metadata

    def __str__(self) -> str:
        return f"<{self.metadata.name}Tool v{self.metadata.version}>"

    def __repr__(self) -> str:
        return self.__str__()

