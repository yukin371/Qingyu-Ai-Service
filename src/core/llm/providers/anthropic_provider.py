"""
Anthropic Provider - Anthropic Claude LLM 供应商适配器
"""

from typing import Any, List
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage
from .base_provider import BaseLLMProvider
from src.core.logger import get_logger

logger = get_logger(__name__)


class AnthropicProvider(BaseLLMProvider):
    """Anthropic 供应商适配器

    支持 Claude 3 系列模型
    """

    def __init__(
        self, api_key: str, model: str = "claude-3-opus-20240229", **kwargs
    ):
        super().__init__(api_key, model, **kwargs)
        logger.info(f"Anthropic Provider initialized with model: {model}")

    def _initialize_llm(self) -> ChatAnthropic:
        """初始化 Anthropic LLM"""
        return ChatAnthropic(
            api_key=self.api_key,
            model=self.model,
            temperature=self.extra_params.get("temperature", 0.7),
            max_tokens=self.extra_params.get("max_tokens", 4096),
        )

    def parse_output(self, raw_output: Any) -> AIMessage:
        """解析 Anthropic 输出

        Claude 的输出格式与 OpenAI 略有不同，需要转换
        """
        if isinstance(raw_output, AIMessage):
            return raw_output

        # Claude 的响应也是 AIMessage，但可能包含不同的元数据
        if hasattr(raw_output, "content"):
            content = raw_output.content

            # Claude 可能返回多个内容块
            if isinstance(content, list):
                # 提取文本内容
                text_content = ""
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_content += block.get("text", "")
                    elif hasattr(block, "text"):
                        text_content += block.text
                content = text_content

            return AIMessage(
                content=content,
                additional_kwargs=getattr(raw_output, "additional_kwargs", {}),
            )

        # 降级处理
        return AIMessage(content=str(raw_output))

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Anthropic Embedding

        注意：Anthropic 目前不提供 Embedding API
        可以考虑使用 OpenAI 或其他 Embedding 服务
        """
        raise NotImplementedError(
            "Anthropic does not provide embedding API. "
            "Please use OpenAI or other embedding providers."
        )


