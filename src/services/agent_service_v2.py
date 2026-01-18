"""
Agent Service v2 - 基于 LangChain 1.0

集成所有新特性：
- 统一 Agent 接口
- Middleware 支持
- Checkpointer 持久化
- 多 LLM 供应商
"""

import asyncio
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional
from dataclasses import dataclass

from src.core.agents.base_agent_unified import BaseAgentUnified
from src.core.agents.workflows.a2a_pipeline_v2_unified import create_a2a_pipeline_v2
from src.core.agents.checkpointers import PostgresCheckpointer, BaseCheckpointer
from src.core.agents.middleware import (
    LoggingMiddleware,
    MetricsMiddleware,
    ErrorHandlingMiddleware,
)
from src.core.llm.providers import LLMProviderFactory
from src.core.logger import get_logger
from src.core.config import get_settings

logger = get_logger(__name__)


@dataclass
class AgentExecutionResultV2:
    """Agent 执行结果 v2"""

    execution_id: str
    thread_id: str  # 新增：用于恢复
    output: Any
    status: str
    reasoning: List[str]
    metadata: Dict[str, Any]
    checkpoints: Optional[List[Dict]] = None  # 新增：检查点列表
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "execution_id": self.execution_id,
            "thread_id": self.thread_id,
            "output": self.output,
            "status": self.status,
            "reasoning": self.reasoning,
            "metadata": self.metadata,
            "checkpoints": self.checkpoints,
            "error": self.error,
        }


class AgentServiceV2:
    """Agent 服务 v2.0 - 基于 LangChain 1.0

    主要改进：
    - 集成 Checkpointer 持久化
    - 支持工作流中断恢复
    - Middleware 自动注入
    - 多 LLM 供应商支持
    """

    def __init__(
        self,
        enable_checkpointer: bool = True,
        enable_middleware: bool = True,
    ):
        """初始化服务

        Args:
            enable_checkpointer: 是否启用持久化
            enable_middleware: 是否启用中间件
        """
        self.enable_checkpointer = enable_checkpointer
        self.enable_middleware = enable_middleware

        # Checkpointer
        self.checkpointer: Optional[BaseCheckpointer] = None

        # Middleware 栈
        self.middleware_stack = []

        # 工作流实例
        self.workflows = {}

        # LLM Provider
        self.llm_provider = None

        # 初始化标志
        self._initialized = False

        logger.info(
            "AgentServiceV2 created",
            enable_checkpointer=enable_checkpointer,
            enable_middleware=enable_middleware,
        )

    async def initialize(self) -> None:
        """初始化服务"""
        if self._initialized:
            return

        logger.info("Initializing AgentServiceV2...")

        settings = get_settings()

        # 1. 初始化 Checkpointer
        if self.enable_checkpointer and settings.enable_checkpointer:
            try:
                self.checkpointer = PostgresCheckpointer()
                logger.info("Checkpointer initialized: PostgreSQL")
            except Exception as e:
                logger.warning(
                    f"Failed to initialize checkpointer: {e}. "
                    "Service will run without persistence."
                )

        # 2. 初始化 Middleware
        if self.enable_middleware:
            self.middleware_stack = [
                LoggingMiddleware(),
                MetricsMiddleware(),
                ErrorHandlingMiddleware(enable_fallback=True, max_retries=3),
            ]
            logger.info(f"Middleware initialized: {len(self.middleware_stack)} middlewares")

        # 3. 初始化 LLM Provider
        try:
            self.llm_provider = LLMProviderFactory.create()
            logger.info(
                f"LLM Provider initialized: {self.llm_provider.get_provider_name()}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize LLM provider: {e}")
            raise

        # 4. 创建工作流
        self.workflows = {
            "a2a_pipeline": await create_a2a_pipeline_v2(
                enable_checkpointer=self.enable_checkpointer,
                enable_middleware=self.enable_middleware,
            ),
            # 可以添加更多工作流
        }

        logger.info(f"Workflows initialized: {list(self.workflows.keys())}")

        self._initialized = True
        logger.info("AgentServiceV2 initialized successfully")

    async def execute(
        self,
        workflow_type: str,
        input_data: Dict[str, Any],
        user_id: str,
        project_id: str,
        thread_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> AgentExecutionResultV2:
        """执行 Agent（支持持久化和恢复）

        Args:
            workflow_type: 工作流类型（a2a_pipeline, creative, etc）
            input_data: 输入数据
            user_id: 用户 ID
            project_id: 项目 ID
            thread_id: 线程 ID（可选，用于恢复）
            config: 额外配置

        Returns:
            AgentExecutionResultV2: 执行结果
        """
        if not self._initialized:
            await self.initialize()

        # 生成 execution_id 和 thread_id
        execution_id = str(uuid.uuid4())
        if not thread_id:
            thread_id = f"{user_id}_{project_id}_{int(time.time())}"

        logger.info(
            "Executing agent",
            workflow_type=workflow_type,
            execution_id=execution_id,
            thread_id=thread_id,
        )

        # 获取工作流
        workflow = self.workflows.get(workflow_type)
        if not workflow:
            raise ValueError(f"Unknown workflow type: {workflow_type}")

        # 准备配置
        run_config = {
            "configurable": {
                "thread_id": thread_id,
                "user_id": user_id,
                "project_id": project_id,
                "execution_id": execution_id,
            }
        }

        if config:
            run_config["configurable"].update(config)

        # 执行工作流
        start_time = time.time()

        try:
            result = await workflow.ainvoke(input_data, config=run_config)

            duration = time.time() - start_time

            logger.info(
                "Agent execution completed",
                execution_id=execution_id,
                duration_seconds=duration,
                status=result.get("current_agent", "completed"),
            )

            # 获取检查点列表（如果启用）
            checkpoints = None
            if self.checkpointer:
                try:
                    checkpoints = await self.checkpointer.list_checkpoints(thread_id)
                    checkpoints = [
                        {
                            "checkpoint_id": cp.checkpoint_id,
                            "created_at": cp.created_at.isoformat(),
                        }
                        for cp in checkpoints
                    ]
                except Exception as e:
                    logger.warning(f"Failed to list checkpoints: {e}")

            return AgentExecutionResultV2(
                execution_id=execution_id,
                thread_id=thread_id,
                output=result.get("output", result),
                status="completed",
                reasoning=result.get("reasoning", []),
                metadata={
                    "duration_seconds": duration,
                    "completed_agents": result.get("completed_agents", []),
                    "quality_score": result.get("quality_score", 0),
                },
                checkpoints=checkpoints,
            )

        except Exception as e:
            logger.error(
                "Agent execution failed",
                execution_id=execution_id,
                error=str(e),
                exc_info=True,
            )

            return AgentExecutionResultV2(
                execution_id=execution_id,
                thread_id=thread_id,
                output=None,
                status="failed",
                reasoning=[],
                metadata={},
                error=str(e),
            )

    async def resume(
        self,
        thread_id: str,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> AgentExecutionResultV2:
        """从 Checkpoint 恢复执行

        Args:
            thread_id: 线程 ID
            input_data: 输入数据（可选，None 表示从 checkpoint 恢复）

        Returns:
            AgentExecutionResultV2: 执行结果
        """
        if not self._initialized:
            await self.initialize()

        if not self.checkpointer:
            raise ValueError("Checkpointer is not enabled")

        logger.info(f"Resuming execution from thread_id: {thread_id}")

        # 加载 checkpoint
        checkpoint = await self.checkpointer.load(thread_id)
        if not checkpoint:
            raise ValueError(f"No checkpoint found for thread_id: {thread_id}")

        # 从 metadata 中获取 workflow_type
        workflow_type = checkpoint.metadata.get("workflow_type", "a2a_pipeline")

        workflow = self.workflows.get(workflow_type)
        if not workflow:
            raise ValueError(f"Unknown workflow type: {workflow_type}")

        # 准备配置
        run_config = {
            "configurable": {
                "thread_id": thread_id,
            }
        }

        # 恢复执行
        start_time = time.time()

        try:
            result = await workflow.ainvoke(input_data, config=run_config)

            duration = time.time() - start_time

            logger.info(
                "Agent resumed execution completed",
                thread_id=thread_id,
                duration_seconds=duration,
            )

            return AgentExecutionResultV2(
                execution_id=str(uuid.uuid4()),
                thread_id=thread_id,
                output=result.get("output", result),
                status="completed",
                reasoning=result.get("reasoning", []),
                metadata={
                    "duration_seconds": duration,
                    "resumed_from_checkpoint": True,
                },
            )

        except Exception as e:
            logger.error(
                "Agent resume failed",
                thread_id=thread_id,
                error=str(e),
            )
            raise

    async def stream(
        self,
        workflow_type: str,
        input_data: Dict[str, Any],
        user_id: str,
        project_id: str,
        thread_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式执行 Agent

        Args:
            workflow_type: 工作流类型
            input_data: 输入数据
            user_id: 用户 ID
            project_id: 项目 ID
            thread_id: 线程 ID（可选）

        Yields:
            Dict[str, Any]: 流式输出
        """
        if not self._initialized:
            await self.initialize()

        if not thread_id:
            thread_id = f"{user_id}_{project_id}_{int(time.time())}"

        workflow = self.workflows.get(workflow_type)
        if not workflow:
            raise ValueError(f"Unknown workflow type: {workflow_type}")

        run_config = {
            "configurable": {
                "thread_id": thread_id,
                "user_id": user_id,
                "project_id": project_id,
            }
        }

        logger.info(f"Starting stream execution: {workflow_type}")

        try:
            async for event in workflow.astream(input_data, config=run_config):
                yield event

        except Exception as e:
            logger.error(f"Stream execution failed: {e}")
            raise

    async def list_checkpoints(self, thread_id: str) -> List[Dict]:
        """列出检查点

        Args:
            thread_id: 线程 ID

        Returns:
            检查点列表
        """
        if not self.checkpointer:
            raise ValueError("Checkpointer is not enabled")

        checkpoints = await self.checkpointer.list_checkpoints(thread_id)

        return [
            {
                "checkpoint_id": cp.checkpoint_id,
                "parent_checkpoint_id": cp.parent_checkpoint_id,
                "created_at": cp.created_at.isoformat(),
                "metadata": cp.metadata,
            }
            for cp in checkpoints
        ]

    async def health_check(self) -> Dict[str, Any]:
        """健康检查

        Returns:
            健康状态
        """
        health_status = {
            "healthy": True,
            "initialized": self._initialized,
            "components": {},
        }

        # 检查 Checkpointer
        if self.checkpointer:
            try:
                checkpointer_healthy = await self.checkpointer.health_check()
                health_status["components"]["checkpointer"] = {
                    "healthy": checkpointer_healthy,
                    "type": "PostgreSQL",
                }
            except Exception as e:
                health_status["components"]["checkpointer"] = {
                    "healthy": False,
                    "error": str(e),
                }
                health_status["healthy"] = False

        # 检查 LLM Provider
        if self.llm_provider:
            health_status["components"]["llm_provider"] = {
                "provider": self.llm_provider.get_provider_name(),
                "model": self.llm_provider.get_model_name(),
            }

        # 检查工作流
        health_status["components"]["workflows"] = {
            "count": len(self.workflows),
            "types": list(self.workflows.keys()),
        }

        return health_status

    async def close(self) -> None:
        """关闭服务"""
        logger.info("Closing AgentServiceV2...")

        # 清理资源
        self.workflows.clear()

        logger.info("AgentServiceV2 closed")


