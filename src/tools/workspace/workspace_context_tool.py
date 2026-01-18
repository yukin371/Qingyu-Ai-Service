"""
工作区上下文感知工具

借鉴Cursor AI的设计理念，提供主动的、智能的上下文获取能力。

这是Agent系统的核心基础工具，让Agent能够：
1. 自动理解当前任务类型
2. 智能加载相关上下文（角色、大纲、前序内容等）
3. 结合RAG检索提供更丰富的背景信息
4. 以结构化方式返回，易于LLM理解和使用
"""

from typing import Dict, Any, Optional
import structlog

from .task_analyzer import TaskAnalyzer, TaskType, TaskContext
from .context_builder import ContextBuilder, StructuredContext

logger = structlog.get_logger(__name__)


class WorkspaceContextTool:
    """
    工作区上下文工具

    这是一个智能工具，能够：
    - 分析用户意图，识别任务类型
    - 主动加载相关上下文信息
    - 结合RAG检索提供丰富的背景知识
    - 返回结构化的上下文数据，供Agent使用

    Examples:
        >>> tool = WorkspaceContextTool(go_api_client, rag_pipeline)
        >>>
        >>> # 场景1: 续写任务
        >>> context = await tool.get_context(
        ...     user_input="继续写第三章",
        ...     project_id="proj_123",
        ...     chapter_id="ch_003"
        ... )
        >>>
        >>> # 场景2: 创建角色
        >>> context = await tool.get_context(
        ...     user_input="创建一个新角色",
        ...     project_id="proj_123",
        ...     action="create_character"
        ... )
    """

    def __init__(
        self,
        go_api_client=None,
        rag_pipeline=None
    ):
        """
        初始化工作区上下文工具

        Args:
            go_api_client: Go后端API客户端
            rag_pipeline: RAG检索流水线
        """
        self.task_analyzer = TaskAnalyzer()
        self.context_builder = ContextBuilder(
            go_api_client=go_api_client,
            rag_pipeline=rag_pipeline
        )
        self.logger = logger.bind(component="workspace_context_tool")

    async def get_context(
        self,
        user_input: str,
        project_id: str,
        **kwargs
    ) -> StructuredContext:
        """
        获取工作区上下文

        这是主要的入口方法，智能分析任务并返回相应的上下文。

        Args:
            user_input: 用户输入（任务描述或指令）
            project_id: 项目ID
            **kwargs: 额外参数
                - chapter_id: 章节ID
                - character_id: 角色ID
                - target_id: 通用目标ID
                - action: 明确指定的动作（可选）
                - include_rag: 是否包含RAG检索（默认True）

        Returns:
            StructuredContext: 结构化的工作区上下文

        Raises:
            ValueError: 如果project_id为空
            Exception: 其他错误
        """
        if not project_id:
            raise ValueError("project_id is required")

        self.logger.info(
            "Getting workspace context",
            project_id=project_id,
            user_input=user_input[:50] if user_input else None
        )

        # 1. 分析任务类型
        context_dict = {
            "project_id": project_id,
            **kwargs
        }
        task_context = self.task_analyzer.analyze(user_input, context_dict)

        # 2. 构建结构化上下文
        structured_context = await self.context_builder.build(task_context)

        self.logger.info(
            "Context retrieved successfully",
            task_type=task_context.task_type.value,
            context_size=len(str(structured_context.to_dict()))
        )

        return structured_context

    def get_context_as_prompt(
        self,
        context: StructuredContext,
        format_type: str = "markdown"
    ) -> str:
        """
        将上下文转换为适合LLM的提示词格式

        Args:
            context: 结构化上下文
            format_type: 格式类型（markdown, plain, json）

        Returns:
            格式化的上下文字符串
        """
        if format_type == "json":
            import json
            return json.dumps(context.to_dict(), ensure_ascii=False, indent=2)
        elif format_type == "plain":
            return str(context.to_dict())
        else:  # markdown (default)
            return context.to_prompt_context()

    async def analyze_task_type(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> TaskType:
        """
        仅分析任务类型（轻量级方法）

        当你只需要知道任务类型而不需要完整上下文时使用。

        Args:
            user_input: 用户输入
            context: 额外上下文

        Returns:
            TaskType: 识别的任务类型
        """
        task_context = self.task_analyzer.analyze(user_input, context)
        return task_context.task_type

    def get_supported_task_types(self) -> list:
        """
        获取支持的任务类型列表

        Returns:
            任务类型列表
        """
        return [task_type.value for task_type in TaskType]

    async def validate_context(
        self,
        context: StructuredContext
    ) -> Dict[str, Any]:
        """
        验证上下文的完整性和质量

        Args:
            context: 待验证的上下文

        Returns:
            验证结果字典 {
                "valid": bool,
                "warnings": list,
                "suggestions": list
            }
        """
        warnings = []
        suggestions = []

        # 检查基础信息
        if not context.project_info:
            warnings.append("缺少项目信息")

        # 根据任务类型检查必需的上下文
        if context.task_type == TaskType.CONTINUE_WRITING.value:
            if not context.previous_content:
                warnings.append("续写任务缺少前序内容")
                suggestions.append("尝试加载章节的前序段落")
            if not context.characters:
                suggestions.append("建议加载相关角色信息以提高生成质量")

        elif context.task_type == TaskType.CREATE_CHAPTER.value:
            if not context.outline_nodes:
                warnings.append("创建章节时建议提供大纲信息")

        elif context.task_type == TaskType.CREATE_CHARACTER.value:
            if context.characters:
                suggestions.append(f"已有{len(context.characters)}个角色，注意保持角色一致性")

        valid = len(warnings) == 0

        return {
            "valid": valid,
            "warnings": warnings,
            "suggestions": suggestions,
            "completeness_score": self._calculate_completeness_score(context)
        }

    def _calculate_completeness_score(
        self,
        context: StructuredContext
    ) -> float:
        """计算上下文完整性评分（0-1）"""
        score = 0.0
        max_score = 0.0

        # 基础信息（必须）
        max_score += 1.0
        if context.project_info:
            score += 1.0

        # 任务相关上下文（根据任务类型）
        task_type = context.task_type

        if task_type in [TaskType.CONTINUE_WRITING.value, TaskType.EDIT_CONTENT.value]:
            max_score += 2.0
            if context.previous_content:
                score += 1.0
            if context.characters:
                score += 0.5
            if context.outline_nodes:
                score += 0.5

        elif task_type == TaskType.CREATE_CHAPTER.value:
            max_score += 2.0
            if context.outline_nodes:
                score += 1.0
            if context.characters:
                score += 0.5
            if context.world_settings:
                score += 0.5

        elif task_type in [TaskType.CREATE_OUTLINE.value, TaskType.CREATE_CHARACTER.value]:
            max_score += 1.0
            if context.characters or context.outline_nodes:
                score += 1.0

        # RAG增强
        max_score += 0.5
        if context.retrieved_docs:
            score += 0.5

        return score / max_score if max_score > 0 else 0.0


# ===== LangChain Tool Wrapper =====

class WorkspaceContextLangChainTool:
    """
    LangChain工具包装器

    将WorkspaceContextTool包装成LangChain Tool格式，
    以便在LangChain Agent中使用。
    """

    def __init__(self, workspace_tool: WorkspaceContextTool):
        """
        初始化LangChain工具包装器

        Args:
            workspace_tool: WorkspaceContextTool实例
        """
        self.workspace_tool = workspace_tool
        self.name = "workspace_context"
        self.description = (
            "获取当前工作区的智能上下文信息。"
            "输入: 用户任务描述和项目ID。"
            "输出: 结构化的上下文信息，包括相关角色、大纲、前序内容等。"
        )

    async def _arun(
        self,
        user_input: str,
        project_id: str,
        **kwargs
    ) -> str:
        """异步执行工具"""
        context = await self.workspace_tool.get_context(
            user_input=user_input,
            project_id=project_id,
            **kwargs
        )
        return self.workspace_tool.get_context_as_prompt(context)

    def _run(self, *args, **kwargs):
        """同步执行（不支持）"""
        raise NotImplementedError(
            "WorkspaceContextTool只支持异步执行，请使用_arun"
        )

