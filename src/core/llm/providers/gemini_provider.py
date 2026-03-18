"""
Gemini Provider - Google Gemini LLM 供应商适配器
"""

from typing import Any, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage
from .base_provider import BaseLLMProvider
from src.core.logger import get_logger

logger = get_logger(__name__)


class GeminiProvider(BaseLLMProvider):
    """Google Gemini 供应商适配器

    支持 Gemini Pro, Gemini Flash 等模型
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash-exp",
        transport: str = "rest",
        **kwargs
    ):
        super().__init__(api_key, model, **kwargs)
        self.transport = transport
        logger.info(f"Gemini Provider initialized with model: {model}")

    def _initialize_llm(self) -> ChatGoogleGenerativeAI:
        """初始化 Gemini LLM"""
        params = {
            "google_api_key": self.api_key,
            "model": self.model,
            "transport": self.transport,  # 使用REST避免gRPC被防火墙阻断
        }

        if "temperature" in self.extra_params:
            params["temperature"] = self.extra_params["temperature"]
        if "max_tokens" in self.extra_params:
            params["max_tokens"] = self.extra_params["max_tokens"]

        return ChatGoogleGenerativeAI(**params)

    def parse_output(self, raw_output: Any) -> AIMessage:
        """解析 Gemini 输出"""
        if isinstance(raw_output, AIMessage):
            return raw_output

        if hasattr(raw_output, "content"):
            return AIMessage(
                content=raw_output.content,
                additional_kwargs=getattr(raw_output, "additional_kwargs", {}),
            )

        return AIMessage(content=str(raw_output))
