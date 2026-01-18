"""
任务类型分析器

识别当前写作任务的类型，以便提供针对性的上下文。
"""

from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


class TaskType(str, Enum):
    """任务类型枚举"""

    CONTINUE_WRITING = "continue_writing"  # 续写任务
    CREATE_CHAPTER = "create_chapter"      # 新建章节
    CREATE_OUTLINE = "create_outline"      # 创建大纲
    CREATE_CHARACTER = "create_character"  # 创建角色
    REVIEW_CONTENT = "review_content"      # 审核内容
    EDIT_CONTENT = "edit_content"          # 编辑内容
    GENERATE_PLOT = "generate_plot"        # 生成情节
    UNKNOWN = "unknown"                    # 未知类型


@dataclass
class TaskContext:
    """任务上下文信息"""

    task_type: TaskType
    project_id: str
    target_id: Optional[str] = None  # 目标ID（章节ID、角色ID等）
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TaskAnalyzer:
    """
    任务类型分析器

    根据用户输入和上下文信息，智能识别当前任务类型。
    """

    def __init__(self):
        """初始化分析器"""
        self.logger = logger.bind(component="task_analyzer")

    def analyze(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> TaskContext:
        """
        分析任务类型

        Args:
            user_input: 用户输入的指令或内容
            context: 额外的上下文信息（可选）
                - project_id: 项目ID
                - chapter_id: 章节ID
                - character_id: 角色ID
                - action: 明确指定的动作类型

        Returns:
            TaskContext: 识别的任务上下文
        """
        context = context or {}

        # 1. 如果明确指定了action，直接使用
        if "action" in context:
            task_type = self._map_action_to_task_type(context["action"])
            return TaskContext(
                task_type=task_type,
                project_id=context.get("project_id", ""),
                target_id=context.get("target_id"),
                metadata=context
            )

        # 2. 基于关键词和上下文推断
        task_type = self._infer_task_type(user_input, context)

        self.logger.info(
            "Task type analyzed",
            task_type=task_type.value,
            has_target=bool(context.get("target_id"))
        )

        return TaskContext(
            task_type=task_type,
            project_id=context.get("project_id", ""),
            target_id=context.get("target_id"),
            metadata=context
        )

    def _map_action_to_task_type(self, action: str) -> TaskType:
        """映射动作字符串到任务类型"""
        action_mapping = {
            "continue": TaskType.CONTINUE_WRITING,
            "create_chapter": TaskType.CREATE_CHAPTER,
            "create_outline": TaskType.CREATE_OUTLINE,
            "create_character": TaskType.CREATE_CHARACTER,
            "review": TaskType.REVIEW_CONTENT,
            "edit": TaskType.EDIT_CONTENT,
            "generate_plot": TaskType.GENERATE_PLOT,
        }
        return action_mapping.get(action, TaskType.UNKNOWN)

    def _infer_task_type(
        self,
        user_input: str,
        context: Dict[str, Any]
    ) -> TaskType:
        """基于输入和上下文推断任务类型"""
        user_input_lower = user_input.lower()

        # 关键词匹配
        keywords_mapping = {
            TaskType.CONTINUE_WRITING: ["继续", "续写", "接着写", "往下写", "continue"],
            TaskType.CREATE_CHAPTER: ["新建章节", "创建章节", "新章节", "create chapter"],
            TaskType.CREATE_OUTLINE: ["大纲", "outline", "创建大纲", "生成大纲"],
            TaskType.CREATE_CHARACTER: ["角色", "人物", "character", "创建角色"],
            TaskType.REVIEW_CONTENT: ["审核", "review", "检查", "评估"],
            TaskType.EDIT_CONTENT: ["修改", "编辑", "改写", "edit"],
            TaskType.GENERATE_PLOT: ["情节", "剧情", "plot", "生成情节"],
        }

        for task_type, keywords in keywords_mapping.items():
            if any(keyword in user_input_lower for keyword in keywords):
                return task_type

        # 基于上下文推断
        if context.get("chapter_id"):
            # 有章节ID，可能是续写或编辑
            if any(word in user_input_lower for word in ["修改", "edit", "改"]):
                return TaskType.EDIT_CONTENT
            return TaskType.CONTINUE_WRITING

        if context.get("character_id"):
            return TaskType.CREATE_CHARACTER

        # 默认返回未知
        return TaskType.UNKNOWN

