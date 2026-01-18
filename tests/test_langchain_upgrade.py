"""
测试 LangChain 1.2.x 升级后的核心功能

这个测试文件验证 LangChain 升级后的基本功能是否正常。
"""
import pytest
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


class TestLangChainCore:
    """测试 LangChain 核心功能"""

    def test_message_creation(self):
        """测试消息创建"""
        human_msg = HumanMessage(content="Hello")
        ai_msg = AIMessage(content="Hi there!")
        system_msg = SystemMessage(content="You are a helpful assistant")

        assert human_msg.content == "Hello"
        assert ai_msg.content == "Hi there!"
        assert system_msg.content == "You are a helpful assistant"

    def test_prompt_template(self):
        """测试提示词模板"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant."),
            ("user", "{input}")
        ])

        messages = prompt.format_messages(input="Hello")
        assert len(messages) == 2
        assert messages[0].content == "You are a helpful assistant."
        assert messages[1].content == "Hello"

    def test_output_parser(self):
        """测试输出解析器"""
        parser = StrOutputParser()
        result = parser.parse("Test output")

        assert result == "Test output"


class TestLangChainImports:
    """测试关键模块导入"""

    def test_import_langchain(self):
        """测试导入 langchain"""
        import langchain
        assert langchain.__version__ >= "1.2.0"

    def test_import_langchain_core(self):
        """测试导入 langchain_core"""
        import langchain_core
        assert langchain_core.__version__ >= "1.2.0"

    def test_import_langchain_openai(self):
        """测试导入 langchain_openai"""
        from langchain_openai import ChatOpenAI
        assert ChatOpenAI is not None

    def test_import_langchain_anthropic(self):
        """测试导入 langchain_anthropic"""
        from langchain_anthropic import ChatAnthropic
        assert ChatAnthropic is not None

    def test_import_langchain_community(self):
        """测试导入 langchain_community"""
        import langchain_community
        assert langchain_community is not None


class TestLangGraphImports:
    """测试 LangGraph 导入"""

    def test_import_langgraph(self):
        """测试导入 langgraph"""
        from langgraph.graph import StateGraph
        assert StateGraph is not None

    def test_import_langgraph_checkpoint(self):
        """测试导入 langgraph_checkpoint"""
        from langgraph.checkpoint.memory import MemorySaver
        assert MemorySaver is not None


class TestLangSmithImports:
    """测试 LangSmith 导入"""

    def test_import_langsmith(self):
        """测试导入 langsmith"""
        import langsmith
        assert langsmith is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
