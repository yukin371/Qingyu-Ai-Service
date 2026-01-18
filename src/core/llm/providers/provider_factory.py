"""
LLM Provider Factory - LLM 供应商工厂
"""

from typing import Dict, Any
from .base_provider import BaseLLMProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from src.core.logger import get_logger
from src.core.config import get_settings

logger = get_logger(__name__)


class LLMProviderFactory:
    """LLM 供应商工厂

    根据配置创建对应的 LLM Provider
    """

    _providers = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
    }

    @classmethod
    def create(
        cls, provider: str = None, model: str = None, **kwargs
    ) -> BaseLLMProvider:
        """创建 LLM Provider

        Args:
            provider: 供应商名称（openai, anthropic）
            model: 模型名称
            **kwargs: 额外参数（api_key, base_url 等）

        Returns:
            BaseLLMProvider: LLM Provider 实例
        """
        settings = get_settings()

        # 如果没有指定 provider，使用配置中的默认值
        if not provider:
            provider = settings.default_llm_provider

        provider = provider.lower()

        # 检查供应商是否支持
        if provider not in cls._providers:
            raise ValueError(
                f"Unsupported LLM provider: {provider}. "
                f"Supported providers: {list(cls._providers.keys())}"
            )

        # 获取 Provider 类
        provider_class = cls._providers[provider]

        # 准备初始化参数
        init_params = cls._prepare_init_params(provider, model, settings, kwargs)

        logger.info(
            f"Creating LLM Provider",
            provider=provider,
            model=init_params.get("model"),
        )

        # 创建 Provider 实例
        return provider_class(**init_params)

    @classmethod
    def _prepare_init_params(
        cls,
        provider: str,
        model: str,
        settings: Any,
        extra_kwargs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """准备初始化参数"""
        params = {}

        # OpenAI 参数
        if provider == "openai":
            params["api_key"] = extra_kwargs.get(
                "api_key", settings.openai_api_key
            )
            params["model"] = model or settings.default_llm_model or "gpt-4-turbo-preview"
            if settings.openai_base_url:
                params["base_url"] = settings.openai_base_url

        # Anthropic 参数
        elif provider == "anthropic":
            params["api_key"] = extra_kwargs.get(
                "api_key", settings.anthropic_api_key
            )
            params["model"] = model or "claude-3-opus-20240229"

        # 通用参数
        if "temperature" in extra_kwargs:
            params["temperature"] = extra_kwargs["temperature"]
        if "max_tokens" in extra_kwargs:
            params["max_tokens"] = extra_kwargs["max_tokens"]

        return params

    @classmethod
    def register_provider(
        cls, name: str, provider_class: type[BaseLLMProvider]
    ) -> None:
        """注册自定义 Provider

        Args:
            name: 供应商名称
            provider_class: Provider 类
        """
        if not issubclass(provider_class, BaseLLMProvider):
            raise TypeError("Provider class must inherit from BaseLLMProvider")

        cls._providers[name.lower()] = provider_class
        logger.info(f"Registered custom LLM provider: {name}")

    @classmethod
    def list_providers(cls) -> list[str]:
        """列出所有支持的供应商"""
        return list(cls._providers.keys())


