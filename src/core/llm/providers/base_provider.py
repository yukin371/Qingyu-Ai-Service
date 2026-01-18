"""
LLM Provider 基类 - 定义统一的 LLM 供应商接口
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator, Optional
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.language_models import BaseChatModel


class BaseLLMProvider(ABC):
    """LLM 供应商基类

    定义统一的接口，支持多种 LLM 供应商
    """

    def __init__(self, api_key: str, model: str, **kwargs):
        self.api_key = api_key
        self.model = model
        self.extra_params = kwargs
        self._llm: Optional[BaseChatModel] = None

    @abstractmethod
    def _initialize_llm(self) -> BaseChatModel:
        """初始化 LLM 实例"""
        pass

    @property
    def llm(self) -> BaseChatModel:
        """获取 LLM 实例（懒加载）"""
        if self._llm is None:
            self._llm = self._initialize_llm()
        return self._llm

    async def generate(
        self, messages: List[BaseMessage], **kwargs
    ) -> AIMessage:
        """生成响应（标准化输出）

        Args:
            messages: 消息列表
            **kwargs: 额外参数（temperature, max_tokens 等）

        Returns:
            AIMessage: 标准化的 AI 响应
        """
        response = await self.llm.ainvoke(messages, **kwargs)
        return self.parse_output(response)

    async def generate_stream(
        self, messages: List[BaseMessage], **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式生成响应

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Yields:
            str: 生成的文本片段
        """
        async for chunk in self.llm.astream(messages, **kwargs):
            if hasattr(chunk, "content") and chunk.content:
                yield chunk.content

    @abstractmethod
    def parse_output(self, raw_output: Any) -> AIMessage:
        """解析原始输出为标准化消息

        不同供应商可能有不同的输出格式，这里统一转换为 AIMessage

        Args:
            raw_output: 原始输出

        Returns:
            AIMessage: 标准化消息
        """
        pass

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """文本向量化

        默认实现，子类可以覆盖

        Args:
            texts: 文本列表

        Returns:
            向量列表
        """
        raise NotImplementedError("Embedding not supported by this provider")

    def get_provider_name(self) -> str:
        """获取供应商名称"""
        return self.__class__.__name__.replace("Provider", "").lower()

    def get_model_name(self) -> str:
        """获取模型名称"""
        return self.model


