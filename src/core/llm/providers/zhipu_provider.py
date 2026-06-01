"""
Zhipu Provider - 智谱AI (GLM) LLM 供应商适配器

智谱AI使用兼容OpenAI的API格式
"""

from typing import Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from .openai_provider import OpenAIProvider
from src.core.logger import get_logger

logger = get_logger(__name__)


class ZhipuProvider(OpenAIProvider):
    """智谱AI 供应商适配器

    智谱AI (BigModel/GLM) 使用兼容 OpenAI 的 API 格式
    支持 GLM-4, GLM-3-Turbo 等模型
    """

    DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"

    def __init__(
        self,
        api_key: str,
        model: str = "glm-4",
        base_url: Optional[str] = None,
        **kwargs
    ):
        # 使用智谱的默认base_url
        base_url = base_url or self.DEFAULT_BASE_URL
        super().__init__(api_key, model, base_url, **kwargs)
        logger.info(f"Zhipu Provider initialized with model: {model}")
