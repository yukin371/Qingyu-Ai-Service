"""
OpenAI Provider - OpenAI LLM 供应商适配器
"""

from typing import Any, List, Optional
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import AIMessage, BaseMessage
from .base_provider import BaseLLMProvider
from src.core.logger import get_logger

logger = get_logger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI 供应商适配器

    支持 GPT-4, GPT-3.5 等系列模型
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4-turbo-preview",
        base_url: Optional[str] = None,
        **kwargs
    ):
        super().__init__(api_key, model, **kwargs)
        self.base_url = base_url
        logger.info(f"OpenAI Provider initialized with model: {model}")

    def _initialize_llm(self) -> ChatOpenAI:
        """初始化 OpenAI LLM"""
        params = {
            "api_key": self.api_key,
            "model": self.model,
            "temperature": self.extra_params.get("temperature", 0.7),
        }

        if self.base_url:
            params["base_url"] = self.base_url

        if "max_tokens" in self.extra_params:
            params["max_tokens"] = self.extra_params["max_tokens"]

        return ChatOpenAI(**params)

    def parse_output(self, raw_output: Any) -> AIMessage:
        """解析 OpenAI 输出

        OpenAI 的输出通常是 AIMessage 格式
        """
        if isinstance(raw_output, AIMessage):
            return raw_output

        if hasattr(raw_output, "content"):
            return AIMessage(
                content=raw_output.content,
                additional_kwargs=getattr(raw_output, "additional_kwargs", {}),
            )

        return AIMessage(content=str(raw_output))

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """OpenAI Embedding

        Args:
            texts: 文本列表

        Returns:
            向量列表
        """
        embeddings = OpenAIEmbeddings(
            api_key=self.api_key,
            model=self.extra_params.get("embedding_model", "text-embedding-3-small"),
        )
        return await embeddings.aembed_documents(texts)
