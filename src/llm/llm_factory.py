"""
LLM 工厂类
支持多种LLM提供商（OpenAI、Anthropic、Gemini）
"""
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger(__name__)


class LLMFactory:
    """LLM工厂类，用于创建不同提供商的LLM实例"""

    @staticmethod
    def create_llm(
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> BaseChatModel:
        """创建LLM实例

        Args:
            provider: LLM提供商 (openai, anthropic, gemini)
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数

        Returns:
            BaseChatModel: LLM实例
        """
        provider = provider or settings.default_llm_provider
        model = model or settings.default_llm_model

        logger.info(f"Creating LLM instance: provider={provider}, model={model}")

        if provider == "openai":
            return LLMFactory._create_openai_llm(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
        elif provider == "anthropic":
            return LLMFactory._create_anthropic_llm(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
        elif provider == "gemini":
            return LLMFactory._create_gemini_llm(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
        else:
            raise ValueError(
                f"Unsupported LLM provider: {provider}. "
                f"Supported: openai, anthropic, gemini"
            )

    @staticmethod
    def _create_openai_llm(
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        **kwargs,
    ) -> ChatOpenAI:
        """创建OpenAI LLM实例"""
        return ChatOpenAI(
            model=model or settings.openai_model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    @staticmethod
    def _create_anthropic_llm(
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        **kwargs,
    ) -> ChatAnthropic:
        """创建Anthropic LLM实例"""
        return ChatAnthropic(
            model=model or settings.anthropic_model,
            api_key=settings.anthropic_api_key,
            temperature=temperature,
            max_tokens=max_tokens or 4096,
            **kwargs,
        )

    @staticmethod
    def _create_gemini_llm(
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        **kwargs,
    ) -> ChatGoogleGenerativeAI:
        """创建Gemini LLM实例

        使用 transport='rest' 避免 gRPC 被防火墙阻断
        """
        # 确保使用REST传输协议
        transport = kwargs.pop("transport", settings.gemini_transport)

        return ChatGoogleGenerativeAI(
            model=model or settings.gemini_model,
            google_api_key=settings.google_api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            transport=transport,  # 使用REST避免gRPC被防火墙阻断
            **kwargs,
        )

    @staticmethod
    def get_default_llm(
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> BaseChatModel:
        """获取默认LLM实例"""
        return LLMFactory.create_llm(
            provider=settings.default_llm_provider,
            model=settings.default_llm_model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

