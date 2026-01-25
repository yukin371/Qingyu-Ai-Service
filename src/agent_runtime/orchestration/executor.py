"""
Agent Executor - Agent 执行器

核心执行引擎，集成 Memory、Tools、Workflow 和 Middleware。
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from src.common.types.agent_types import (
    AgentConfig,
    AgentContext,
    AgentResult,
    AgentStatus,
    AgentState,
)
from src.common.interfaces.tool_interface import ITool
from src.agent_runtime.orchestration.middleware.base import (
    AgentMiddleware,
    MiddlewareContext,
    MiddlewarePipeline,
    MiddlewareResult,
)
from src.services.quota_service import QuotaService


logger = logging.getLogger(__name__)


# =============================================================================
# Execution Configuration
# =============================================================================

class ExecutionConfig(BaseModel):
    """
    执行配置

    Attributes:
        timeout: 执行超时时间（秒）
        max_retries: 最大重试次数
        enable_streaming: 是否启用流式输出
        enable_middleware: 是否启用中间件
        retry_on_failure: 失败时是否重试
    """

    timeout: float = Field(default=60, description="Execution timeout in seconds", ge=1)
    max_retries: int = Field(default=3, description="Maximum retry attempts", ge=0)
    enable_streaming: bool = Field(default=False, description="Enable streaming output")
    enable_middleware: bool = Field(default=True, description="Enable middleware pipeline")
    retry_on_failure: bool = Field(default=True, description="Retry on failure")

    model_config = {"use_enum_values": False}


# =============================================================================
# Execution Statistics
# =============================================================================

class ExecutionStats(BaseModel):
    """
    执行统计信息

    Attributes:
        total_tokens: 总 Token 使用量
        prompt_tokens: 提示 Token 使用量
        completion_tokens: 完成 Token 使用量
        execution_time: 执行时间（秒）
        steps_taken: 执行步数
        retry_count: 重试次数
    """

    total_tokens: int = Field(default=0, description="Total tokens used")
    prompt_tokens: int = Field(default=0, description="Prompt tokens used")
    completion_tokens: int = Field(default=0, description="Completion tokens used")
    execution_time: float = Field(default=0, description="Execution time in seconds")
    steps_taken: int = Field(default=0, description="Number of steps taken")
    retry_count: int = Field(default=0, description="Number of retries")

    model_config = {"use_enum_values": False}


# =============================================================================
# Execution Result
# =============================================================================

class ExecutionResult(BaseModel):
    """
    执行结果

    Attributes:
        success: 是否成功
        agent_result: Agent 执行结果
        stats: 执行统计信息
        error: 错误信息
        metadata: 额外的元数据
    """

    success: bool = Field(..., description="Whether execution succeeded")
    agent_result: Optional[AgentResult] = Field(default=None, description="Agent execution result")
    stats: Optional[ExecutionStats] = Field(default=None, description="Execution statistics")
    error: Optional[str] = Field(default=None, description="Error message")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = {"use_enum_values": False}


# =============================================================================
# Agent Executor
# =============================================================================

class AgentExecutor:
    """
    Agent 执行器

    核心执行引擎，负责协调 Memory、Tools、Workflow 和 Middleware 来执行 Agent。

    使用示例:
        ```python
        # 创建执行器
        executor = AgentExecutor(
            agent_id="agent_123",
            config=agent_config,
            memory=memory_backend,
            tools=[search_tool, calculator_tool],
            workflow=compiled_workflow,
            middleware_pipeline=pipeline,
        )

        # 同步执行
        result = await executor.execute(agent_context)

        # 流式执行
        async for token in executor.execute_stream(agent_context):
            print(token, end="")
        ```
    """

    def __init__(
        self,
        agent_id: str,
        config: AgentConfig,
        memory: Optional[Any] = None,
        tools: Optional[List[ITool]] = None,
        workflow: Optional[Any] = None,
        middleware_pipeline: Optional[MiddlewarePipeline] = None,
        db_pool: Optional[Any] = None,
    ):
        """
        初始化执行器

        Args:
            agent_id: Agent ID
            config: Agent 配置
            memory: 可选的 Memory 实例
            tools: 可选的工具列表
            workflow: 可选的 Workflow 实例
            middleware_pipeline: 可选的中间件管道
            db_pool: 可选的数据库连接池（用于配额记录）
        """
        self.agent_id = agent_id
        self.config = config
        self.memory = memory
        self.tools = tools or []
        self.workflow = workflow
        self.middleware_pipeline = middleware_pipeline or MiddlewarePipeline()
        
        # 初始化配额服务
        self.db_pool = db_pool
        self.quota_service = QuotaService(db_pool) if db_pool else None

        # 状态管理
        self._status = AgentStatus.IDLE
        self._current_task: Optional[str] = None
        self._created_at = datetime.utcnow()
        self._started_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None

        logger.info(f"Created AgentExecutor: {agent_id}")

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def status(self) -> AgentStatus:
        """获取当前状态"""
        return self._status

    # -------------------------------------------------------------------------
    # Core Execution Methods
    # -------------------------------------------------------------------------

    async def execute(
        self,
        context: AgentContext,
        config: Optional[ExecutionConfig] = None,
    ) -> ExecutionResult:
        """
        执行 Agent

        Args:
            context: Agent 上下文
            config: 执行配置（可选）

        Returns:
            ExecutionResult 执行结果
        """
        exec_config = config or ExecutionConfig()
        retry_count = 0
        last_error = None

        self._status = AgentStatus.ACTING
        self._current_task = context.current_task
        self._started_at = datetime.utcnow()

        logger.info(f"Starting execution: {self.agent_id}")

        try:
            # 尝试执行（带重试）
            while retry_count <= exec_config.max_retries:
                try:
                    result = await self._execute_once(context, exec_config)
                    if result.success:
                        return result
                    elif not exec_config.retry_on_failure:
                        return result
                    else:
                        last_error = result.error
                        retry_count += 1
                        logger.warning(f"Execution failed, retrying ({retry_count}/{exec_config.max_retries})")

                except asyncio.TimeoutError:
                    last_error = f"Execution timeout after {exec_config.timeout}s"
                    logger.error(last_error)
                    if not exec_config.retry_on_failure or retry_count >= exec_config.max_retries:
                        return ExecutionResult(
                            success=False,
                            error=last_error,
                        )
                    retry_count += 1

            # 所有重试都失败
            return ExecutionResult(
                success=False,
                error=f"Execution failed after {retry_count} retries: {last_error}",
            )

        except Exception as e:
            logger.error(f"Unexpected error during execution: {e}")
            return ExecutionResult(
                success=False,
                error=f"Unexpected error: {str(e)}",
            )

        finally:
            self._status = AgentStatus.COMPLETED if self._status != AgentStatus.ERROR else AgentStatus.ERROR
            self._completed_at = datetime.utcnow()
            logger.info(f"Execution completed: {self.agent_id}")

    async def _execute_once(
        self,
        context: AgentContext,
        config: ExecutionConfig,
    ) -> ExecutionResult:
        """
        执行一次（单次尝试）

        Args:
            context: Agent 上下文
            config: 执行配置

        Returns:
            ExecutionResult 执行结果
        """
        start_time = time.time()

        # 加载 Memory
        if self.memory:
            try:
                memory_vars = await self.memory.load_memory_variables(context)
                context.variables.update(memory_vars)
                logger.debug(f"Loaded memory variables: {list(memory_vars.keys())}")
            except Exception as e:
                logger.error(f"Error loading memory: {e}")

        # 定义处理器
        async def handler(ctx: AgentContext) -> MiddlewareResult:
            # 实际执行 Agent
            try:
                agent_result = await asyncio.wait_for(
                    self._execute_agent(ctx),
                    timeout=config.timeout,
                )

                return MiddlewareResult(
                    success=agent_result.success,
                    agent_result=agent_result,
                    error=agent_result.error,
                )
            except asyncio.TimeoutError:
                raise
            except Exception as e:
                return MiddlewareResult(
                    success=False,
                    error=str(e),
                )

        # 执行中间件管道
        if config.enable_middleware and self.middleware_pipeline.middlewares:
            middleware_result = await self.middleware_pipeline.execute(context, handler)
        else:
            middleware_result = await handler(context)

        # 计算执行时间
        execution_time = time.time() - start_time

        # 保存到 Memory
        if self.memory and middleware_result.agent_result:
            try:
                await self.memory.save_context(context, middleware_result.agent_result)
                logger.debug("Saved context to memory")
            except Exception as e:
                logger.error(f"Error saving to memory: {e}")
        
        # 记录配额消费（不中断主流程）
        if self.quota_service and middleware_result.agent_result:
            try:
                tokens_used = self._calculate_tokens(middleware_result.agent_result, execution_time)
                
                # 从 context 中提取 user_id 和 workflow_type
                user_id = getattr(context, 'user_id', 'unknown')
                workflow_type = getattr(context, 'workflow_type', 'chat')
                
                # 记录配额消费
                await self.quota_service.record_consumption(
                    user_id=user_id,
                    workflow_type=workflow_type,
                    tokens_used=tokens_used,
                    metadata={
                        "agent_id": self.agent_id,
                        "agent_type": getattr(context, 'agent_type', 'unknown'),
                        "model": self.config.model if hasattr(self.config, 'model') else 'unknown',
                        "duration": execution_time,
                        "success": middleware_result.success,
                    }
                )
                logger.info(f"Recorded quota consumption: user={user_id}, tokens={tokens_used}")
            except Exception as e:
                logger.error(f"Error recording quota consumption: {e}")

        # 构建统计信息
        stats = self._build_stats(middleware_result.agent_result, execution_time)

        # 返回结果
        return ExecutionResult(
            success=middleware_result.success,
            agent_result=middleware_result.agent_result,
            stats=stats,
            error=middleware_result.error,
        )

    async def _execute_agent(self, context: AgentContext) -> AgentResult:
        """
        执行 Agent（实际执行逻辑）

        Args:
            context: Agent 上下文

        Returns:
            AgentResult 执行结果

        Raises:
            NotImplementedError: 子类或实际实现需要覆盖此方法
        """
        # 这是基类实现，子类或实际使用时需要覆盖
        # 这里提供一个简单的模拟实现用于测试
        if self.workflow:
            # 使用 LangGraph workflow
            return await self._execute_workflow(context)
        else:
            # 直接使用 LLM
            return await self._execute_llm(context)

    async def _execute_workflow(self, context: AgentContext) -> AgentResult:
        """执行 Workflow（使用 LangGraph）"""
        try:
            # 调用编译后的 workflow
            result = await self.workflow.ainvoke({
                "messages": context.conversation_history,
                "input": context.current_task or "",
            })

            # 提取输出
            if isinstance(result, dict):
                output = result.get("output") or result.get("response") or str(result)
            else:
                output = str(result)

            return AgentResult(
                success=True,
                output=output,
                steps=[{"step": "workflow", "output": output}],
            )
        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
            return AgentResult(
                success=False,
                error=f"Workflow error: {str(e)}",
            )

    async def _execute_llm(self, context: AgentContext) -> AgentResult:
        """直接执行 LLM（用于简单情况）"""
        # 这是一个模拟实现
        # 实际使用时应该集成真正的 LLM 调用
        return AgentResult(
            success=True,
            output=f"LLM response to: {context.current_task}",
            tokens_used={"total": 100, "prompt": 50, "completion": 50},
        )

    def _build_stats(
        self,
        agent_result: Optional[AgentResult],
        execution_time: float,
    ) -> ExecutionStats:
        """构建执行统计信息"""
        stats = ExecutionStats(
            execution_time=execution_time,
            steps_taken=len(agent_result.steps) if agent_result else 0,
        )

        if agent_result and agent_result.tokens_used:
            stats.total_tokens = agent_result.tokens_used.get("total", 0)
            stats.prompt_tokens = agent_result.tokens_used.get("prompt", 0)
            stats.completion_tokens = agent_result.tokens_used.get("completion", 0)

        return stats

    def _calculate_tokens(
        self,
        agent_result: AgentResult,
        execution_time: float
    ) -> int:
        """
        计算使用的 token 数量
        
        Args:
            agent_result: Agent 执行结果
            execution_time: 执行时间（秒）
        
        Returns:
            int: 使用的 token 总数
        """
        # 优先使用 AgentResult 中记录的 token 使用量
        if agent_result.tokens_used:
            if isinstance(agent_result.tokens_used, dict):
                return agent_result.tokens_used.get("total", 0)
            elif isinstance(agent_result.tokens_used, int):
                return agent_result.tokens_used
        
        # 如果没有记录，尝试从 output 中估算
        # 粗略估算：输入 token + 输出 token
        # 假设平均每个 token 约等于 4 个字符（英文）或 1.5 个字符（中文）
        try:
            if agent_result.output:
                # 估算输出 token 数量
                output_tokens = len(str(agent_result.output)) // 3
                
                # 估算输入 token 数量（从 context 中获取，这里使用保守估计）
                input_tokens = 100  # 默认假设输入约 100 tokens
                
                # 总 token 数（输出 token 通常权重更高，因为需要更多计算）
                total_tokens = input_tokens + int(output_tokens * 1.5)
                
                logger.debug(f"Calculated tokens: input={input_tokens}, output={output_tokens}, total={total_tokens}")
                return total_tokens
        except Exception as e:
            logger.warning(f"Error calculating tokens from output: {e}")
        
        # 如果所有方法都失败，返回默认值
        logger.warning("Unable to calculate tokens, using default estimate")
        return 100

    # -------------------------------------------------------------------------
    # Streaming Execution
    # -------------------------------------------------------------------------

    async def execute_stream(
        self,
        context: AgentContext,
        config: Optional[ExecutionConfig] = None,
    ) -> AsyncIterator[str]:
        """
        流式执行 Agent

        Args:
            context: Agent 上下文
            config: 执行配置（可选）

        Yields:
            str: Token 流
        """
        exec_config = config or ExecutionConfig()
        exec_config.enable_streaming = True

        self._status = AgentStatus.ACTING
        self._current_task = context.current_task
        self._started_at = datetime.utcnow()

        logger.info(f"Starting streaming execution: {self.agent_id}")

        try:
            async for token in self._execute_agent_stream(context):
                yield token

        except Exception as e:
            logger.error(f"Error during streaming execution: {e}")
            yield f"\n[Error: {str(e)}]"

        finally:
            self._status = AgentStatus.COMPLETED
            self._completed_at = datetime.utcnow()

    async def _execute_agent_stream(
        self,
        context: AgentContext,
    ) -> AsyncIterator[str]:
        """
        流式执行 Agent（实际实现）

        Args:
            context: Agent 上下文

        Yields:
            str: Token 流
        """
        # 基类实现，提供模拟流式输出
        # 实际使用时应该集成真正的流式 LLM 调用
        response = f"Streaming response to: {context.current_task}"
        for word in response.split():
            yield word + " "
            await asyncio.sleep(0.01)  # 模拟网络延迟

    # -------------------------------------------------------------------------
    # State Management
    # -------------------------------------------------------------------------

    def get_state(self) -> AgentState:
        """
        获取执行器状态

        Returns:
            AgentState 当前状态
        """
        return AgentState(
            agent_id=self.agent_id,
            status=self._status,
            current_task=self._current_task,
            created_at=self._created_at,
            started_at=self._started_at,
            completed_at=self._completed_at,
        )

    def reset(self) -> None:
        """重置执行器状态"""
        self._status = AgentStatus.IDLE
        self._current_task = None
        self._started_at = None
        self._completed_at = None
        logger.info(f"Reset AgentExecutor: {self.agent_id}")

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"AgentExecutor(id={self.agent_id}, "
            f"status={self._status.value}, "
            f"tools={len(self.tools)}, "
            f"has_workflow={self.workflow is not None}, "
            f"has_memory={self.memory is not None})"
        )
