"""
测试MCP工具框架
"""
import os
import sys
from typing import Optional

import pytest
from pydantic import Field

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from core.logger import get_logger
from tools.adapters import LangChainToolAdapter
from tools.base import (
    BaseTool,
    ToolCategory,
    ToolInputSchema,
    ToolMetadata,
    ToolResult,
    ToolStatus,
)
from tools.registry import ToolRegistry, get_global_tool_registry

logger = get_logger(__name__)


# ===== 测试工具示例 =====


class SimpleCalculatorInput(ToolInputSchema):
    """简单计算器输入"""

    operation: str = Field(..., description="运算类型: add, subtract, multiply, divide")
    a: float = Field(..., description="第一个数")
    b: float = Field(..., description="第二个数")


class SimpleCalculatorTool(BaseTool):
    """简单计算器工具（示例）"""

    @property
    def input_schema(self):
        return SimpleCalculatorInput

    async def _execute_impl(self, validated_input: SimpleCalculatorInput) -> ToolResult:
        """执行计算"""
        operation = validated_input.operation
        a = validated_input.a
        b = validated_input.b

        try:
            if operation == "add":
                result = a + b
            elif operation == "subtract":
                result = a - b
            elif operation == "multiply":
                result = a * b
            elif operation == "divide":
                if b == 0:
                    return ToolResult.failed_result(
                        tool_name=self.metadata.name,
                        error="除数不能为零",
                    )
                result = a / b
            else:
                return ToolResult.failed_result(
                    tool_name=self.metadata.name,
                    error=f"未知运算类型: {operation}",
                )

            return ToolResult.success_result(
                tool_name=self.metadata.name,
                data={"result": result},
                message=f"{a} {operation} {b} = {result}",
            )

        except Exception as e:
            return ToolResult.failed_result(
                tool_name=self.metadata.name,
                error=str(e),
            )


# ===== 测试工具元数据 =====


def test_tool_metadata():
    """测试工具元数据"""
    metadata = ToolMetadata(
        name="test_tool",
        description="测试工具",
        category=ToolCategory.SYSTEM,
        version="1.0.0",
        tags=["test", "example"],
        requires_auth=False,
    )

    assert metadata.name == "test_tool"
    assert metadata.category == ToolCategory.SYSTEM
    assert "test" in metadata.tags
    logger.info(f"Tool metadata: {metadata}")


# ===== 测试工具结果 =====


def test_tool_result():
    """测试工具结果"""
    # 成功结果
    success_result = ToolResult.success_result(
        tool_name="test_tool",
        data={"value": 42},
        message="执行成功",
    )

    assert success_result.success is True
    assert success_result.status == ToolStatus.SUCCESS
    assert success_result.data["value"] == 42

    # 失败结果
    failed_result = ToolResult.failed_result(
        tool_name="test_tool",
        error="测试错误",
    )

    assert failed_result.success is False
    assert failed_result.status == ToolStatus.FAILED
    assert "测试错误" in failed_result.error

    logger.info(f"Success result: {success_result}")
    logger.info(f"Failed result: {failed_result}")


# ===== 测试工具基类 =====


@pytest.mark.asyncio
async def test_base_tool_execute():
    """测试工具执行"""
    metadata = ToolMetadata(
        name="calculator",
        description="简单计算器",
        category=ToolCategory.SYSTEM,
    )

    calculator = SimpleCalculatorTool(metadata=metadata)

    # 测试加法
    result = await calculator.execute(
        {"operation": "add", "a": 10, "b": 5}
    )

    assert result.success is True
    assert result.data["result"] == 15

    logger.info(f"Add result: {result}")

    # 测试除法
    result = await calculator.execute(
        {"operation": "divide", "a": 10, "b": 2}
    )

    assert result.success is True
    assert result.data["result"] == 5

    logger.info(f"Divide result: {result}")

    # 测试除零错误
    result = await calculator.execute(
        {"operation": "divide", "a": 10, "b": 0}
    )

    assert result.success is False
    assert "除数不能为零" in result.error

    logger.info(f"Divide by zero result: {result}")


@pytest.mark.asyncio
async def test_tool_input_validation():
    """测试输入验证"""
    metadata = ToolMetadata(
        name="calculator",
        description="简单计算器",
        category=ToolCategory.SYSTEM,
    )

    calculator = SimpleCalculatorTool(metadata=metadata)

    # 缺少必需字段
    result = await calculator.execute({"operation": "add", "a": 10})

    assert result.success is False
    assert result.status == ToolStatus.INVALID_INPUT
    assert "输入验证失败" in result.message

    logger.info(f"Invalid input result: {result}")


# ===== 测试工具注册 =====


def test_tool_registry():
    """测试工具注册机制"""
    registry = ToolRegistry()

    # 注册工具
    metadata = ToolMetadata(
        name="calculator",
        description="简单计算器",
        category=ToolCategory.SYSTEM,
    )

    registry.register(SimpleCalculatorTool, metadata=metadata)

    # 检查注册
    assert registry.is_tool_registered("calculator")
    assert registry.get_tool_count() == 1

    # 获取工具类
    tool_class = registry.get_tool_class("calculator")
    assert tool_class == SimpleCalculatorTool

    # 创建工具实例
    instance = registry.create_tool_instance("calculator")
    assert instance is not None
    assert isinstance(instance, SimpleCalculatorTool)

    # 列出工具
    tools = registry.list_all_tools()
    assert "calculator" in tools

    logger.info(f"Registry: {registry}")
    logger.info(f"Tools: {tools}")


def test_global_tool_registry():
    """测试全局工具注册中心"""
    registry1 = get_global_tool_registry()
    registry2 = get_global_tool_registry()

    # 应该是同一个实例
    assert registry1 is registry2

    logger.info("Global registry is singleton")


# ===== 测试LangChain适配器 =====


@pytest.mark.asyncio
async def test_langchain_adapter():
    """测试LangChain适配器"""
    # 创建MCP工具
    metadata = ToolMetadata(
        name="calculator",
        description="简单计算器",
        category=ToolCategory.SYSTEM,
    )

    mcp_tool = SimpleCalculatorTool(metadata=metadata)

    # 适配为LangChain工具
    langchain_tool = LangChainToolAdapter(mcp_tool=mcp_tool)

    # 验证属性
    assert langchain_tool.name == "calculator"
    assert "简单计算器" in langchain_tool.description
    assert langchain_tool.args_schema == SimpleCalculatorInput

    # 测试异步执行
    result = await langchain_tool._arun(operation="multiply", a=6, b=7)

    assert result["success"] is True
    assert result["data"]["result"] == 42

    logger.info(f"LangChain tool result: {result}")

    # 测试失败情况
    result = await langchain_tool._arun(operation="divide", a=10, b=0)

    assert result["success"] is False
    assert "除数不能为零" in result["error"]

    logger.info(f"LangChain tool error result: {result}")


# ===== 测试工具权限 =====


class AuthRequiredInput(ToolInputSchema):
    """需要认证的工具输入"""

    message: str = Field(..., description="消息")


class AuthRequiredTool(BaseTool):
    """需要认证的工具"""

    @property
    def input_schema(self):
        return AuthRequiredInput

    async def _execute_impl(self, validated_input: AuthRequiredInput) -> ToolResult:
        """执行工具"""
        return ToolResult.success_result(
            tool_name=self.metadata.name,
            data={"message": validated_input.message},
            message="执行成功",
        )


@pytest.mark.asyncio
async def test_tool_auth():
    """测试工具认证"""
    metadata = ToolMetadata(
        name="auth_tool",
        description="需要认证的工具",
        category=ToolCategory.SYSTEM,
        requires_auth=True,
    )

    # 没有认证上下文
    tool_no_auth = AuthRequiredTool(metadata=metadata)
    result = await tool_no_auth.execute({"message": "test"})

    assert result.success is False
    assert result.status == ToolStatus.PERMISSION_DENIED

    logger.info(f"No auth result: {result}")

    # 有认证上下文
    tool_with_auth = AuthRequiredTool(
        metadata=metadata,
        auth_context={"user_id": "test_user"},
    )
    result = await tool_with_auth.execute({"message": "test"})

    assert result.success is True
    assert result.data["message"] == "test"

    logger.info(f"With auth result: {result}")


# ===== 主测试入口 =====


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

