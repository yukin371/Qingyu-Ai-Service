"""
故事写作 Agent - 基于三层上下文进行创作

接收 Go 后端已组装好的 prompt，调用 LLM 生成内容。
"""
import time
from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable

from src.agents.base_agent_v2 import BaseAgentV2, PipelineStateV2
from src.core.config import get_settings
from src.core.logger import get_logger
from src.llm.llm_factory import LLMFactory

logger = get_logger(__name__)


class StoryWriterAgent(BaseAgentV2):
    """
    故事写作 Agent

    基于 Go 后端组装的三层上下文 prompt，调用 LLM 生成符合故事走向的内容。
    支持续写、改写、建议三种模式。
    """

    def __init__(
        self,
        llm_provider: str = "",
        llm_model: str = "",
        temperature: float = 0.8,
        max_tokens: int = 2000,
    ):
        """
        初始化故事写作 Agent

        Args:
            llm_provider: LLM 提供商（空字符串则从配置读取）
            llm_model: LLM 模型（空字符串则从配置读取）
            temperature: 温度参数（越高越有创造性）
            max_tokens: 最大生成 token 数
        """
        super().__init__(name="StoryWriterAgent", description="基于三层上下文的故事写作Agent")
        settings = get_settings()
        self.llm_provider = llm_provider or settings.default_llm_provider
        self.llm_model = llm_model or settings.default_llm_model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def get_runnable(self) -> Runnable[PipelineStateV2, PipelineStateV2]:
        """获取LangChain Runnable（暂未实现）"""
        raise NotImplementedError("StoryWriterAgent暂未实现LangChain Runnable接口")

    async def execute(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行故事写作

        Args:
            prompt: 组装好的三层上下文 prompt
            max_tokens: 最大 token 数（可选）
            temperature: 温度参数（可选）

        Returns:
            Dict 包含:
                - content: 生成的内容
                - model: 使用的模型
                - tokens_used: 消耗的 token 数
        """
        start_time = time.time()

        try:
            # 设置参数
            effective_max_tokens = max_tokens or self.max_tokens
            effective_temperature = temperature or self.temperature

            # 获取 LLM 实例
            llm = LLMFactory.create_llm(
                provider=self.llm_provider,
                model=self.llm_model,
                temperature=effective_temperature,
                max_tokens=effective_max_tokens,
            )

            # 构建消息
            messages = [
                HumanMessage(content=prompt)
            ]

            # 调用 LLM
            logger.info(
                f"StoryWriterAgent 开始生成: provider={self.llm_provider}, "
                f"model={self.llm_model}, max_tokens={effective_max_tokens}, "
                f"temperature={effective_temperature}"
            )

            response = await llm.ainvoke(
                messages,
                max_tokens=effective_max_tokens,
                temperature=effective_temperature,
            )

            # 提取内容
            content = ""
            if hasattr(response, 'content'):
                content = response.content
            elif isinstance(response, str):
                content = response
            else:
                content = str(response)

            elapsed = time.time() - start_time

            # 估算 token 使用量（按字符数估算，中文约 2 字/token）
            tokens_used = len(content) // 2

            logger.info(
                f"StoryWriterAgent 生成完成: {len(content)} 字符, "
                f"约 {tokens_used} tokens, 耗时 {elapsed:.2f}s"
            )

            return {
                "content": content,
                "model": f"{self.llm_provider}/{self.llm_model}",
                "tokens_used": tokens_used,
                "elapsed_seconds": elapsed,
            }

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"StoryWriterAgent 生成失败: {e}, 耗时 {elapsed:.2f}s")
            raise
