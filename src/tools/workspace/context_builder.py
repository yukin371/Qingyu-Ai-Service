"""
上下文构建器

根据任务类型，智能构建结构化的工作区上下文。
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import structlog

from .task_analyzer import TaskType, TaskContext

logger = structlog.get_logger(__name__)


@dataclass
class StructuredContext:
    """结构化上下文数据"""

    task_type: str
    project_info: Dict[str, Any]

    # 文档上下文
    previous_content: Optional[str] = None  # 前序内容
    current_chapter: Optional[Dict[str, Any]] = None  # 当前章节
    outline_nodes: List[Dict[str, Any]] = None  # 相关大纲节点

    # 角色上下文
    characters: List[Dict[str, Any]] = None  # 相关角色卡
    character_relations: List[Dict[str, Any]] = None  # 角色关系

    # 世界观上下文
    world_settings: List[Dict[str, Any]] = None  # 世界观设定
    timeline_events: List[Dict[str, Any]] = None  # 时间线事件

    # RAG检索结果
    retrieved_docs: List[Dict[str, Any]] = None  # 检索到的相关文档

    # 元数据
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.outline_nodes is None:
            self.outline_nodes = []
        if self.characters is None:
            self.characters = []
        if self.character_relations is None:
            self.character_relations = []
        if self.world_settings is None:
            self.world_settings = []
        if self.timeline_events is None:
            self.timeline_events = []
        if self.retrieved_docs is None:
            self.retrieved_docs = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)

    def to_prompt_context(self) -> str:
        """
        转换为适合LLM的提示词上下文

        Returns:
            格式化的上下文字符串
        """
        sections = []

        # 1. 项目信息
        if self.project_info:
            sections.append("## 项目信息")
            sections.append(f"项目名称: {self.project_info.get('title', 'N/A')}")
            if genre := self.project_info.get('genre'):
                sections.append(f"类型: {genre}")
            sections.append("")

        # 2. 当前任务
        sections.append("## 当前任务")
        sections.append(f"任务类型: {self.task_type}")
        sections.append("")

        # 3. 大纲结构
        if self.outline_nodes:
            sections.append("## 大纲结构")
            for node in self.outline_nodes:
                level = node.get('level', 1)
                indent = "  " * (level - 1)
                title = node.get('title', 'N/A')
                summary = node.get('summary', '')
                sections.append(f"{indent}- {title}")
                if summary and len(summary) < 100:
                    sections.append(f"{indent}  {summary}")
            sections.append("")

        # 4. 相关角色
        if self.characters:
            sections.append("## 相关角色")
            for char in self.characters:
                name = char.get('name', 'N/A')
                role = char.get('role', 'N/A')
                traits = char.get('traits', [])
                sections.append(f"- **{name}** ({role})")
                if traits:
                    sections.append(f"  特征: {', '.join(traits[:3])}")
            sections.append("")

        # 5. 前序内容
        if self.previous_content:
            sections.append("## 前序内容")
            # 截取最后500字符
            preview = self.previous_content[-500:] if len(self.previous_content) > 500 else self.previous_content
            if len(self.previous_content) > 500:
                sections.append("...")
            sections.append(preview)
            sections.append("")

        # 6. 世界观设定
        if self.world_settings:
            sections.append("## 世界观设定")
            for setting in self.world_settings[:3]:  # 最多3条
                category = setting.get('category', 'N/A')
                content = setting.get('content', 'N/A')
                sections.append(f"- [{category}] {content[:100]}")
            sections.append("")

        # 7. RAG检索结果
        if self.retrieved_docs:
            sections.append("## 相关参考资料")
            for i, doc in enumerate(self.retrieved_docs[:3], 1):  # 最多3条
                text = doc.get('text', 'N/A')
                score = doc.get('score', 0)
                sections.append(f"{i}. (相似度: {score:.2f}) {text[:150]}")
            sections.append("")

        return "\n".join(sections)


class ContextBuilder:
    """
    上下文构建器

    根据任务类型和项目状态，智能构建结构化的工作区上下文。
    """

    def __init__(
        self,
        go_api_client=None,
        rag_pipeline=None
    ):
        """
        初始化上下文构建器

        Args:
            go_api_client: Go后端API客户端（用于获取项目数据）
            rag_pipeline: RAG检索流水线（用于语义检索）
        """
        self.go_api_client = go_api_client
        self.rag_pipeline = rag_pipeline
        self.logger = logger.bind(component="context_builder")

    async def build(
        self,
        task_context: TaskContext
    ) -> StructuredContext:
        """
        构建结构化上下文

        Args:
            task_context: 任务上下文信息

        Returns:
            StructuredContext: 结构化的上下文数据
        """
        self.logger.info(
            "Building structured context",
            task_type=task_context.task_type.value,
            project_id=task_context.project_id
        )

        # 1. 获取项目基本信息
        project_info = await self._fetch_project_info(task_context.project_id)

        # 2. 根据任务类型构建不同的上下文
        context = StructuredContext(
            task_type=task_context.task_type.value,
            project_info=project_info,
            metadata=task_context.metadata
        )

        # 3. 根据任务类型加载不同的上下文数据
        if task_context.task_type == TaskType.CONTINUE_WRITING:
            await self._build_writing_context(context, task_context)
        elif task_context.task_type == TaskType.CREATE_CHAPTER:
            await self._build_chapter_creation_context(context, task_context)
        elif task_context.task_type == TaskType.CREATE_OUTLINE:
            await self._build_outline_context(context, task_context)
        elif task_context.task_type == TaskType.CREATE_CHARACTER:
            await self._build_character_context(context, task_context)
        elif task_context.task_type == TaskType.REVIEW_CONTENT:
            await self._build_review_context(context, task_context)

        self.logger.info(
            "Context built successfully",
            has_characters=len(context.characters),
            has_outline=len(context.outline_nodes),
            has_retrieved=len(context.retrieved_docs)
        )

        return context

    async def _fetch_project_info(self, project_id: str) -> Dict[str, Any]:
        """获取项目基本信息"""
        if not self.go_api_client:
            return {"id": project_id, "title": "Unknown"}

        try:
            # TODO: 调用Go API获取项目信息
            # project = await self.go_api_client.get_project(project_id)
            # return project
            return {
                "id": project_id,
                "title": "示例项目",
                "genre": "奇幻",
                "status": "writing"
            }
        except Exception as e:
            self.logger.error("Failed to fetch project info", error=str(e))
            return {"id": project_id, "title": "Unknown"}

    async def _build_writing_context(
        self,
        context: StructuredContext,
        task_context: TaskContext
    ):
        """构建续写任务的上下文"""
        project_id = task_context.project_id
        chapter_id = task_context.target_id

        # 1. 加载前序内容
        if chapter_id:
            context.previous_content = await self._fetch_previous_content(
                project_id, chapter_id
            )

        # 2. 加载相关角色
        context.characters = await self._fetch_relevant_characters(
            project_id, chapter_id
        )

        # 3. 加载大纲节点
        context.outline_nodes = await self._fetch_outline_nodes(
            project_id, chapter_id
        )

        # 4. RAG检索相关内容
        if self.rag_pipeline and context.previous_content:
            # 使用最后200字作为查询
            query = context.previous_content[-200:]
            context.retrieved_docs = await self._rag_search(query, project_id)

    async def _build_chapter_creation_context(
        self,
        context: StructuredContext,
        task_context: TaskContext
    ):
        """构建新建章节任务的上下文"""
        project_id = task_context.project_id

        # 1. 加载完整大纲
        context.outline_nodes = await self._fetch_outline_nodes(project_id)

        # 2. 加载所有角色
        context.characters = await self._fetch_relevant_characters(project_id)

        # 3. 加载世界观设定
        context.world_settings = await self._fetch_world_settings(project_id)

    async def _build_outline_context(
        self,
        context: StructuredContext,
        task_context: TaskContext
    ):
        """构建大纲创建任务的上下文"""
        project_id = task_context.project_id

        # 1. 加载已有大纲（如果存在）
        context.outline_nodes = await self._fetch_outline_nodes(project_id)

        # 2. 加载角色信息
        context.characters = await self._fetch_relevant_characters(project_id)

    async def _build_character_context(
        self,
        context: StructuredContext,
        task_context: TaskContext
    ):
        """构建角色创建任务的上下文"""
        project_id = task_context.project_id

        # 1. 加载已有角色
        context.characters = await self._fetch_relevant_characters(project_id)

        # 2. 加载角色关系
        context.character_relations = await self._fetch_character_relations(project_id)

    async def _build_review_context(
        self,
        context: StructuredContext,
        task_context: TaskContext
    ):
        """构建审核任务的上下文"""
        project_id = task_context.project_id
        target_id = task_context.target_id

        # 加载需要审核的内容及其相关上下文
        context.outline_nodes = await self._fetch_outline_nodes(project_id)
        context.characters = await self._fetch_relevant_characters(project_id)

        if target_id:
            context.current_chapter = await self._fetch_chapter(project_id, target_id)

    # ===== 数据获取辅助方法 =====

    async def _fetch_previous_content(
        self,
        project_id: str,
        chapter_id: str
    ) -> Optional[str]:
        """获取前序内容"""
        # TODO: 实现实际的API调用
        return None

    async def _fetch_relevant_characters(
        self,
        project_id: str,
        context_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取相关角色"""
        # TODO: 实现实际的API调用
        return []

    async def _fetch_outline_nodes(
        self,
        project_id: str,
        chapter_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取大纲节点"""
        # TODO: 实现实际的API调用
        return []

    async def _fetch_world_settings(
        self,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """获取世界观设定"""
        # TODO: 实现实际的API调用
        return []

    async def _fetch_character_relations(
        self,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """获取角色关系"""
        # TODO: 实现实际的API调用
        return []

    async def _fetch_chapter(
        self,
        project_id: str,
        chapter_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取章节信息"""
        # TODO: 实现实际的API调用
        return None

    async def _rag_search(
        self,
        query: str,
        project_id: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """RAG检索"""
        if not self.rag_pipeline:
            return []

        try:
            # TODO: 实现实际的RAG检索
            # results = await self.rag_pipeline.retrieve(
            #     query=query,
            #     top_k=top_k,
            #     filters={"project_id": project_id}
            # )
            # return results
            return []
        except Exception as e:
            self.logger.error("RAG search failed", error=str(e))
            return []

