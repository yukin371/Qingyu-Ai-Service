"""
LLM模块

推荐使用 src.core.llm.providers.LLMProviderFactory（新版本）
此模块的 LLMFactory 保留用于向后兼容
"""
from src.llm.llm_factory import LLMFactory

# 兼容性：同时导出 core 版本
from src.core.llm.providers import (
    LLMProviderFactory,
    BaseLLMProvider,
    OpenAIProvider,
    AnthropicProvider,
    GeminiProvider,
    ZhipuProvider,
)

__all__ = [
    # 旧版本（向后兼容）
    "LLMFactory",
    # 新版本（推荐）
    "LLMProviderFactory",
    "BaseLLMProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "GeminiProvider",
    "ZhipuProvider",
]

