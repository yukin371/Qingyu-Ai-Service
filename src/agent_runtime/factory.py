"""
Agent Factory - Agent 工厂

负责组装 Memory + Tools + Workflow 创建完整的 Agent 执行器。

设计原则:
- 依赖注入：支持自定义 Memory、Tools、Workflow
- 模板系统：预定义 Agent 模板，快速创建
- 验证：确保配置正确
- 可扩展：支持动态注册新组件
"""
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime
import uuid

from pydantic import BaseModel, Field

from src.common.types.agent_types import (
    AgentConfig,
    AgentContext,
    AgentResult,
    AgentCapability,
)
from src.common.interfaces.tool_interface import ITool

if TYPE_CHECKING:
    from src.agent_runtime.orchestration.executor import AgentExecutor


logger = logging.getLogger(__name__)


# =============================================================================
# Agent Template
# =============================================================================

class AgentTemplate(BaseModel):
    """
    Agent 模板定义

    预定义的 Agent 配置模板，用于快速创建特定类型的 Agent。
    """

    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    config: AgentConfig = Field(..., description="Agent configuration")
    required_capabilities: List[AgentCapability] = Field(
        default_factory=list,
        description="Required agent capabilities"
    )
    default_tools: List[str] = Field(
        default_factory=list,
        description="Default tools to include"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )

    def validate(self) -> bool:
        """
        验证模板配置

        Returns:
            bool: True if valid

        Raises:
            ValueError: If template is invalid
        """
        if not self.name:
            raise ValueError("Template name cannot be empty")

        if not self.config.model:
            raise ValueError("Template must specify a model")

        return True


# =============================================================================
# Agent Factory
# =============================================================================

class AgentFactory:
    """
    Agent 工厂

    负责创建和配置 Agent 执行器，组装 Memory、Tools、Workflow 等组件。

    使用示例:
        ```python
        factory = AgentFactory()

        # 创建基本 Agent
        executor = await factory.create_agent(
            name="my_agent",
            config=AgentConfig(
                name="my_agent",
                description="My agent",
                model="gpt-4",
            )
        )

        # 创建带工具的 Agent
        executor = await factory.create_agent(
            name="tool_agent",
            config=config,
            tools=[search_tool, calculator_tool],
        )

        # 从模板创建
        executor = await factory.create_from_template(
            template_name="writer",
            config={"max_tokens": 2000},
        )
        ```
    """

    def __init__(self):
        """初始化工厂"""
        self._templates: Dict[str, AgentTemplate] = {}
        self._tool_registry: Optional[Any] = None
        self._memory_backend: Optional[Any] = None
        self._workflow_builder: Optional[Any] = None

        # 注册默认模板
        self._register_default_templates()

    # -------------------------------------------------------------------------
    # Template Management
    # -------------------------------------------------------------------------

    def register_template(self, template: AgentTemplate) -> None:
        """
        注册 Agent 模板

        Args:
            template: 模板定义
        """
        template.validate()
        self._templates[template.name] = template
        logger.info(f"Registered agent template: {template.name}")

    def unregister_template(self, template_name: str) -> None:
        """
        注销模板

        Args:
            template_name: 模板名称
        """
        if template_name in self._templates:
            del self._templates[template_name]
            logger.info(f"Unregistered agent template: {template_name}")

    def get_template(self, template_name: str) -> Optional[AgentTemplate]:
        """
        获取模板

        Args:
            template_name: 模板名称

        Returns:
            AgentTemplate or None
        """
        return self._templates.get(template_name)

    def list_templates(self) -> Dict[str, AgentTemplate]:
        """
        列出所有模板

        Returns:
            Dict of template name -> template
        """
        return self._templates.copy()

    # -------------------------------------------------------------------------
    # Component Registration
    # -------------------------------------------------------------------------

    def set_tool_registry(self, registry: Any) -> None:
        """
        设置工具注册表

        Args:
            registry: ToolRegistryV2 instance
        """
        self._tool_registry = registry
        logger.info("Tool registry configured")

    def set_memory_backend(self, backend: Any) -> None:
        """
        设置内存后端

        Args:
            backend: Memory backend instance
        """
        self._memory_backend = backend
        logger.info("Memory backend configured")

    def set_workflow_builder(self, builder: Any) -> None:
        """
        设置工作流构建器

        Args:
            builder: WorkflowBuilder instance
        """
        self._workflow_builder = builder
        logger.info("Workflow builder configured")

    # -------------------------------------------------------------------------
    # Agent Creation
    # -------------------------------------------------------------------------

    async def create_agent(
        self,
        name: str,
        config: AgentConfig,
        memory: Optional[Any] = None,
        tools: Optional[List[ITool]] = None,
        workflow: Optional[Any] = None,
    ) -> "AgentExecutor":
        """
        创建 Agent 执行器

        Args:
            name: Agent 名称
            config: Agent 配置
            memory: 可选的 Memory 实例
            tools: 可选的工具列表
            workflow: 可选的 Workflow 实例

        Returns:
            AgentExecutor: Agent 执行器实例

        Raises:
            ValueError: 如果配置无效
        """
        logger.info(f"Creating agent: {name}")

        # 验证配置
        if not config.model:
            raise ValueError("Agent config must specify a model")

        # 导入 AgentExecutor（延迟导入避免循环依赖）
        from src.agent_runtime.orchestration.executor import AgentExecutor

        # 生成唯一 ID
        agent_id = f"{name}_{uuid.uuid4().hex[:8]}"

        # 创建执行器
        executor = AgentExecutor(
            agent_id=agent_id,
            config=config,
            memory=memory or self._memory_backend,
            tools=tools or [],
            workflow=workflow,
        )

        logger.info(f"Agent created successfully: {agent_id}")
        return executor

    async def create_from_template(
        self,
        template_name: str,
        config: Optional[Dict[str, Any]] = None,
        tools: Optional[List[ITool]] = None,
    ) -> "AgentExecutor":
        """
        从模板创建 Agent

        Args:
            template_name: 模板名称
            config: 配置覆盖
            tools: 额外的工具

        Returns:
            AgentExecutor: Agent 执行器实例

        Raises:
            ValueError: 如果模板不存在
        """
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")

        logger.info(f"Creating agent from template: {template_name}")

        # 合并配置
        agent_config = template.config.model_copy()
        if config:
            for key, value in config.items():
                if hasattr(agent_config, key):
                    setattr(agent_config, key, value)

        # 获取默认工具
        tool_list = tools or []
        if template.default_tools and self._tool_registry:
            for tool_name in template.default_tools:
                tool = await self._tool_registry.get_tool(tool_name)
                if tool:
                    tool_list.append(tool)

        # 创建 Agent
        executor = await self.create_agent(
            name=template_name,
            config=agent_config,
            tools=tool_list,
        )

        logger.info(f"Agent created from template: {template_name}")
        return executor

    async def create_batch(
        self,
        configs: List[Dict[str, Any]],
    ) -> List["AgentExecutor"]:
        """
        批量创建 Agents

        Args:
            configs: 配置列表，每个包含 name, config, tools 等

        Returns:
            List of AgentExecutor instances
        """
        executors = []

        for conf in configs:
            executor = await self.create_agent(
                name=conf["name"],
                config=conf["config"],
                tools=conf.get("tools"),
                memory=conf.get("memory"),
                workflow=conf.get("workflow"),
            )
            executors.append(executor)

        logger.info(f"Created {len(executors)} agents in batch")
        return executors

    # -------------------------------------------------------------------------
    # Private Methods
    # -------------------------------------------------------------------------

    def _register_default_templates(self) -> None:
        """注册默认模板"""
        # 写手助手
        writer_template = AgentTemplate(
            name="writer",
            description="Creative writing assistant",
            config=AgentConfig(
                name="writer",
                description="Creative writing assistant",
                model="gpt-4",
                temperature=0.8,
                max_tokens=2000,
                system_prompt="You are a creative writing assistant. Help users with writing tasks.",
                capabilities=[AgentCapability.TEXT_GENERATION],
            ),
            required_capabilities=[AgentCapability.TEXT_GENERATION],
        )

        # 数据分析师
        analyst_template = AgentTemplate(
            name="analyst",
            description="Data analysis assistant",
            config=AgentConfig(
                name="analyst",
                description="Data analysis assistant",
                model="gpt-4",
                temperature=0.3,
                max_tokens=1500,
                system_prompt="You are a data analyst. Help users analyze data and provide insights.",
                capabilities=[
                    AgentCapability.CODE_EXECUTION,
                    AgentCapability.REASONING,
                ],
            ),
            required_capabilities=[
                AgentCapability.CODE_EXECUTION,
                AgentCapability.REASONING,
            ],
        )

        # 搜索助手
        searcher_template = AgentTemplate(
            name="searcher",
            description="Web search assistant",
            config=AgentConfig(
                name="searcher",
                description="Web search assistant",
                model="gpt-4",
                temperature=0.5,
                max_tokens=1500,
                system_prompt="You are a search assistant. Help users find information online.",
                capabilities=[
                    AgentCapability.WEB_SEARCH,
                    AgentCapability.TOOL_USE,
                ],
            ),
            required_capabilities=[
                AgentCapability.WEB_SEARCH,
                AgentCapability.TOOL_USE,
            ],
        )

        self.register_template(writer_template)
        self.register_template(analyst_template)
        self.register_template(searcher_template)

        logger.info(f"Registered {len(self._templates)} default templates")


# =============================================================================
# Convenience Functions
# =============================================================================

async def create_agent(
    name: str,
    model: str,
    **kwargs
) -> "AgentExecutor":
    """
    快捷创建 Agent

    Args:
        name: Agent 名称
        model: 模型名称
        **kwargs: 其他配置参数

    Returns:
        AgentExecutor instance
    """
    factory = AgentFactory()

    config = AgentConfig(
        name=name,
        description=f"Agent {name}",
        model=model,
        **kwargs
    )

    return await factory.create_agent(name=name, config=config)
