"""
测试WorkspaceContextTool

测试工作区上下文感知工具的各项功能。
"""

import pytest
from src.tools.workspace import (
    WorkspaceContextTool,
    TaskAnalyzer,
    TaskType,
    ContextBuilder
)


class TestTaskAnalyzer:
    """测试任务分析器"""

    def test_continue_writing_detection(self):
        """测试续写任务识别"""
        analyzer = TaskAnalyzer()

        test_cases = [
            ("继续写", TaskType.CONTINUE_WRITING),
            ("续写第三章", TaskType.CONTINUE_WRITING),
            ("接着往下写", TaskType.CONTINUE_WRITING),
            ("continue writing", TaskType.CONTINUE_WRITING),
        ]

        for user_input, expected_type in test_cases:
            result = analyzer.analyze(user_input, {"project_id": "test"})
            assert result.task_type == expected_type, f"Failed for: {user_input}"

    def test_create_chapter_detection(self):
        """测试创建章节识别"""
        analyzer = TaskAnalyzer()

        result = analyzer.analyze(
            "新建章节",
            {"project_id": "test"}
        )
        assert result.task_type == TaskType.CREATE_CHAPTER

    def test_create_outline_detection(self):
        """测试创建大纲识别"""
        analyzer = TaskAnalyzer()

        test_cases = [
            "创建大纲",
            "生成outline",
            "需要一个故事大纲"
        ]

        for user_input in test_cases:
            result = analyzer.analyze(user_input, {"project_id": "test"})
            assert result.task_type == TaskType.CREATE_OUTLINE

    def test_action_override(self):
        """测试明确指定action的情况"""
        analyzer = TaskAnalyzer()

        result = analyzer.analyze(
            "随便什么输入",
            {
                "project_id": "test",
                "action": "create_character"
            }
        )
        assert result.task_type == TaskType.CREATE_CHARACTER

    def test_context_based_inference(self):
        """测试基于上下文的推断"""
        analyzer = TaskAnalyzer()

        # 有chapter_id，默认是续写
        result = analyzer.analyze(
            "写点什么",
            {
                "project_id": "test",
                "chapter_id": "ch_001"
            }
        )
        assert result.task_type == TaskType.CONTINUE_WRITING

        # 有character_id，默认是创建角色
        result = analyzer.analyze(
            "人物",
            {
                "project_id": "test",
                "character_id": "char_001"
            }
        )
        assert result.task_type == TaskType.CREATE_CHARACTER


class TestContextBuilder:
    """测试上下文构建器"""

    @pytest.mark.asyncio
    async def test_build_empty_context(self):
        """测试构建空上下文（无Go API和RAG）"""
        from src.tools.workspace.task_analyzer import TaskContext

        builder = ContextBuilder()
        task_context = TaskContext(
            task_type=TaskType.CONTINUE_WRITING,
            project_id="test_proj"
        )

        context = await builder.build(task_context)

        assert context.task_type == TaskType.CONTINUE_WRITING.value
        assert context.project_info["id"] == "test_proj"
        assert isinstance(context.characters, list)
        assert isinstance(context.outline_nodes, list)

    @pytest.mark.asyncio
    async def test_to_prompt_context(self):
        """测试转换为提示词上下文"""
        from src.tools.workspace.context_builder import StructuredContext

        context = StructuredContext(
            task_type="continue_writing",
            project_info={"title": "测试项目", "genre": "奇幻"},
            characters=[
                {"name": "张三", "role": "主角", "traits": ["勇敢", "善良"]},
                {"name": "李四", "role": "反派", "traits": ["狡猾"]}
            ],
            outline_nodes=[
                {"level": 1, "title": "第一章", "summary": "开端"},
                {"level": 2, "title": "第一节", "summary": "遇见"}
            ]
        )

        prompt = context.to_prompt_context()

        assert "测试项目" in prompt
        assert "张三" in prompt
        assert "第一章" in prompt
        assert "奇幻" in prompt


class TestWorkspaceContextTool:
    """测试工作区上下文工具"""

    @pytest.mark.asyncio
    async def test_get_context_basic(self):
        """测试基本的上下文获取"""
        tool = WorkspaceContextTool()

        context = await tool.get_context(
            user_input="继续写",
            project_id="test_proj",
            chapter_id="ch_001"
        )

        assert context.project_info["id"] == "test_proj"
        assert context.task_type == TaskType.CONTINUE_WRITING.value

    @pytest.mark.asyncio
    async def test_get_context_as_prompt(self):
        """测试转换为提示词"""
        tool = WorkspaceContextTool()

        context = await tool.get_context(
            user_input="创建大纲",
            project_id="test_proj"
        )

        # Markdown格式
        markdown = tool.get_context_as_prompt(context, "markdown")
        assert "## " in markdown

        # JSON格式
        json_str = tool.get_context_as_prompt(context, "json")
        assert "task_type" in json_str

    @pytest.mark.asyncio
    async def test_analyze_task_type_only(self):
        """测试仅分析任务类型"""
        tool = WorkspaceContextTool()

        task_type = await tool.analyze_task_type(
            "续写第三章",
            {"project_id": "test"}
        )

        assert task_type == TaskType.CONTINUE_WRITING

    def test_get_supported_task_types(self):
        """测试获取支持的任务类型"""
        tool = WorkspaceContextTool()

        types = tool.get_supported_task_types()

        assert "continue_writing" in types
        assert "create_chapter" in types
        assert "create_outline" in types
        assert len(types) > 0

    @pytest.mark.asyncio
    async def test_validate_context(self):
        """测试上下文验证"""
        from src.tools.workspace.context_builder import StructuredContext

        tool = WorkspaceContextTool()

        # 完整的上下文
        good_context = StructuredContext(
            task_type="continue_writing",
            project_info={"title": "测试"},
            previous_content="前面的内容...",
            characters=[{"name": "张三"}],
            outline_nodes=[{"title": "第一章"}]
        )

        result = await tool.validate_context(good_context)
        assert result["valid"]
        assert result["completeness_score"] > 0.7

        # 不完整的上下文
        bad_context = StructuredContext(
            task_type="continue_writing",
            project_info={"title": "测试"}
            # 缺少previous_content和characters
        )

        result = await tool.validate_context(bad_context)
        assert len(result["warnings"]) > 0
        assert result["completeness_score"] < 0.7

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """测试错误处理"""
        tool = WorkspaceContextTool()

        # 缺少project_id应该抛出ValueError
        with pytest.raises(ValueError, match="project_id is required"):
            await tool.get_context(
                user_input="测试",
                project_id=""
            )


class TestLangChainIntegration:
    """测试LangChain集成"""

    @pytest.mark.asyncio
    async def test_langchain_wrapper(self):
        """测试LangChain工具包装器"""
        from src.tools.workspace.workspace_context_tool import WorkspaceContextLangChainTool

        workspace_tool = WorkspaceContextTool()
        langchain_tool = WorkspaceContextLangChainTool(workspace_tool)

        assert langchain_tool.name == "workspace_context"
        assert langchain_tool.description

        # 测试异步执行
        result = await langchain_tool._arun(
            user_input="继续写",
            project_id="test_proj"
        )

        assert isinstance(result, str)
        assert len(result) > 0

    def test_langchain_sync_not_supported(self):
        """测试同步执行不支持"""
        from src.tools.workspace.workspace_context_tool import WorkspaceContextLangChainTool

        workspace_tool = WorkspaceContextTool()
        langchain_tool = WorkspaceContextLangChainTool(workspace_tool)

        with pytest.raises(NotImplementedError):
            langchain_tool._run("test", "proj")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

