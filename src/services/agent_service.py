"""Agent Service - Agent服务

管理Agent工作流的执行
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional
from collections import defaultdict

from src.agents.workflows.creative import create_creative_workflow, execute_creative_workflow
from src.core.logger import get_logger
from src.services.tool_service import ToolService

logger = get_logger(__name__)


class AgentExecutionResult:
    """Agent执行结果"""

    def __init__(
        self,
        execution_id: str,
        output: str,
        tool_calls: List[Dict[str, Any]],
        status: str,
        reasoning: List[str],
        metadata: Dict[str, Any],
        error: Optional[str] = None,
    ):
        self.execution_id = execution_id
        self.output = output
        self.tool_calls = tool_calls
        self.status = status
        self.reasoning = reasoning
        self.metadata = metadata
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "execution_id": self.execution_id,
            "output": self.output,
            "tool_calls": self.tool_calls,
            "status": self.status,
            "reasoning": self.reasoning,
            "metadata": self.metadata,
            "error": self.error,
        }


class AgentService:
    """Agent服务

    特性：
    - Workflow管理
    - 同步/流式执行
    - 健康检查
    """

    def __init__(self, tool_service: Optional[ToolService] = None):
        """初始化服务

        Args:
            tool_service: 工具服务实例（可选）
        """
        self.tool_service = tool_service or ToolService()
        self.workflows = {}
        self._initialized = False

        # 执行历史记录（内存中，生产环境应该使用数据库）
        self._execution_history: Dict[str, AgentExecutionResult] = {}
        self._max_history_size = 1000

        # 执行统计
        self._execution_stats = defaultdict(lambda: {
            "total": 0,
            "success": 0,
            "failure": 0,
            "total_duration_ms": 0,
        })

        # 正在执行的任务（用于取消）
        self._running_tasks: Dict[str, asyncio.Task] = {}

        logger.info("AgentService created")

    async def initialize(self) -> None:
        """初始化服务"""
        if self._initialized:
            return

        logger.info("Initializing AgentService...")

        # 初始化工具服务
        await self.tool_service.initialize()

        # 创建工作流
        self.workflows["creative"] = create_creative_workflow()

        self._initialized = True
        logger.info(
            "AgentService initialized successfully",
            workflows=list(self.workflows.keys()),
        )

    async def execute(
        self,
        agent_type: str,
        task: str,
        context: Dict[str, Any],
        tools: List[str],
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        execution_id: Optional[str] = None,
    ) -> AgentExecutionResult:
        """执行Agent（同步）

        Args:
            agent_type: Agent类型（creative, outline等）
            task: 任务描述
            context: 上下文信息
            tools: 工具列表
            user_id: 用户ID
            project_id: 项目ID
            execution_id: 执行ID（可选，自动生成）

        Returns:
            执行结果
        """
        if not self._initialized:
            await self.initialize()

        # 生成执行ID
        execution_id = execution_id or str(uuid.uuid4())
        start_time = datetime.utcnow()

        logger.info(
            "Executing agent",
            execution_id=execution_id,
            agent_type=agent_type,
            task_length=len(task),
            tools=tools,
            user_id=user_id,
            project_id=project_id,
        )

        try:
            # 目前只支持creative类型
            if agent_type != "creative":
                raise ValueError(f"Unsupported agent type: {agent_type}")

            # 获取RAG工具
            rag_tool = self.tool_service.get_tool("rag_tool")

            # 创建执行任务
            execution_task = asyncio.create_task(
                execute_creative_workflow(
                    task=task,
                    user_id=user_id or "",
                    project_id=project_id or "",
                    constraints=context.get("constraints", {}),
                    context=context,
                    max_retries=3,
                    rag_tool=rag_tool,
                )
            )

            # 记录正在运行的任务
            self._running_tasks[execution_id] = execution_task

            # 等待执行完成
            final_state = await execution_task

            # 计算耗时
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # 构建结果
            result = AgentExecutionResult(
                execution_id=execution_id,
                output=final_state.get("final_output", ""),
                tool_calls=final_state.get("tool_calls", []),
                status="completed",
                reasoning=final_state.get("reasoning", []),
                metadata={
                    **final_state.get("output_metadata", {}),
                    "duration_ms": duration_ms,
                    "agent_type": agent_type,
                    "user_id": user_id,
                    "project_id": project_id,
                },
            )

            # 保存到历史记录
            self._save_execution_history(result)

            # 更新统计
            self._update_stats(agent_type, True, duration_ms)

            logger.info(
                "Agent execution completed",
                execution_id=execution_id,
                agent_type=agent_type,
                status=result.status,
                output_length=len(result.output),
                duration_ms=duration_ms,
            )

            return result

        except asyncio.CancelledError:
            logger.warning(f"Agent execution cancelled", execution_id=execution_id)

            result = AgentExecutionResult(
                execution_id=execution_id,
                output="",
                tool_calls=[],
                status="cancelled",
                reasoning=[],
                metadata={},
                error="Execution cancelled",
            )

            self._save_execution_history(result)
            raise

        except Exception as e:
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            logger.error(
                f"Agent execution failed",
                execution_id=execution_id,
                error=str(e),
                exc_info=True
            )

            # 创建失败结果
            result = AgentExecutionResult(
                execution_id=execution_id,
                output="",
                tool_calls=[],
                status="failed",
                reasoning=[],
                metadata={"duration_ms": duration_ms},
                error=str(e),
            )

            # 保存到历史记录
            self._save_execution_history(result)

            # 更新统计
            self._update_stats(agent_type, False, duration_ms)

            raise

        finally:
            # 清理正在运行的任务
            if execution_id in self._running_tasks:
                del self._running_tasks[execution_id]

    async def execute_stream(
        self,
        agent_type: str,
        task: str,
        context: Dict[str, Any],
        tools: List[str],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """执行Agent（流式）

        Args:
            agent_type: Agent类型
            task: 任务描述
            context: 上下文信息
            tools: 工具列表

        Yields:
            事件流
        """
        if not self._initialized:
            await self.initialize()

        logger.info(
            "Executing agent stream",
            agent_type=agent_type,
            task_length=len(task),
        )

        # 获取工作流
        workflow = self.workflows.get(agent_type)
        if not workflow:
            raise ValueError(f"Unknown agent type: {agent_type}")

        # 准备初始状态
        from agents.states.creative_state import create_initial_creative_state

        initial_state = create_initial_creative_state(
            task=task,
            user_id=context.get("user_id", ""),
            project_id=context.get("project_id", ""),
            constraints=context.get("constraints", {}),
            context=context,
        )

        # 流式执行
        try:
            async for event in workflow.astream_events(initial_state, version="v1"):
                # 发送事件
                yield {
                    "event": event.get("event"),
                    "name": event.get("name"),
                    "data": event.get("data"),
                }
        except Exception as e:
            logger.error(f"Agent stream execution failed: {e}", exc_info=True)
            raise

    async def cancel_execution(self, execution_id: str) -> bool:
        """取消正在执行的任务

        Args:
            execution_id: 执行ID

        Returns:
            是否成功取消
        """
        if execution_id in self._running_tasks:
            task = self._running_tasks[execution_id]
            task.cancel()
            logger.info(f"Cancelled agent execution", execution_id=execution_id)
            return True
        else:
            logger.warning(f"Execution not found or already completed", execution_id=execution_id)
            return False

    def get_execution_result(self, execution_id: str) -> Optional[AgentExecutionResult]:
        """获取执行结果

        Args:
            execution_id: 执行ID

        Returns:
            执行结果（如果存在）
        """
        return self._execution_history.get(execution_id)

    def list_executions(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[AgentExecutionResult]:
        """列出执行历史

        Args:
            user_id: 用户ID过滤（可选）
            project_id: 项目ID过滤（可选）
            limit: 返回数量限制

        Returns:
            执行结果列表
        """
        results = list(self._execution_history.values())

        # 过滤
        if user_id:
            results = [r for r in results if r.metadata.get("user_id") == user_id]
        if project_id:
            results = [r for r in results if r.metadata.get("project_id") == project_id]

        # 按时间排序（最新在前）
        results.sort(
            key=lambda r: r.metadata.get("created_at", ""),
            reverse=True
        )

        return results[:limit]

    def get_stats(self, agent_type: Optional[str] = None) -> Dict[str, Any]:
        """获取执行统计

        Args:
            agent_type: Agent类型（可选，None表示所有）

        Returns:
            统计信息
        """
        if agent_type:
            return dict(self._execution_stats.get(agent_type, {}))
        else:
            return {
                name: dict(stats)
                for name, stats in self._execution_stats.items()
            }

    def _save_execution_history(self, result: AgentExecutionResult) -> None:
        """保存执行历史

        Args:
            result: 执行结果
        """
        # 限制历史记录大小
        if len(self._execution_history) >= self._max_history_size:
            # 删除最老的记录
            oldest_id = min(
                self._execution_history.keys(),
                key=lambda k: self._execution_history[k].metadata.get("created_at", "")
            )
            del self._execution_history[oldest_id]

        # 添加创建时间
        result.metadata["created_at"] = datetime.utcnow().isoformat()

        # 保存
        self._execution_history[result.execution_id] = result

    def _update_stats(self, agent_type: str, success: bool, duration_ms: int) -> None:
        """更新统计信息

        Args:
            agent_type: Agent类型
            success: 是否成功
            duration_ms: 执行时长（毫秒）
        """
        stats = self._execution_stats[agent_type]
        stats["total"] += 1
        if success:
            stats["success"] += 1
        else:
            stats["failure"] += 1
        stats["total_duration_ms"] += duration_ms

    async def health_check(self) -> Dict[str, Any]:
        """健康检查

        Returns:
            健康状态
        """
        tool_health = await self.tool_service.health_check()

        total_executions = sum(
            stats["total"] for stats in self._execution_stats.values()
        )

        return {
            "healthy": self._initialized and tool_health["healthy"],
            "workflows": list(self.workflows.keys()),
            "tools": tool_health,
            "stats": {
                "total_executions": total_executions,
                "running_tasks": len(self._running_tasks),
                "history_size": len(self._execution_history),
            },
        }

    async def close(self) -> None:
        """关闭服务"""
        # 取消所有正在运行的任务
        for execution_id, task in self._running_tasks.items():
            task.cancel()
            logger.info(f"Cancelled running task on shutdown", execution_id=execution_id)

        await self.tool_service.close()
        logger.info("AgentService closed")

