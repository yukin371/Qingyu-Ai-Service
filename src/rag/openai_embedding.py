"""
OpenAI Embedding API集成

提供OpenAI text-embedding-3系列模型的向量化服务

支持的模型:
- text-embedding-3-small (1536维)
- text-embedding-3-large (3072维)

Author: Qingyu AI Team
Date: 2025-10-28
"""

from typing import List, Optional
import asyncio
import hashlib
from openai import AsyncOpenAI, OpenAIError, RateLimitError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from src.core.config import settings
from src.core.logger import logger
from src.core.exceptions import EmbeddingError


class OpenAIEmbedding:
    """
    OpenAI Embedding服务

    使用OpenAI API进行文本向量化，支持:
    - 异步批量处理
    - 自动重试
    - 速率限制处理
    - Token计数优化
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        batch_size: int = None,
        max_retries: int = None
    ):
        """
        初始化OpenAI Embedding服务

        Args:
            model_name: 模型名称 (默认从配置读取)
            api_key: API密钥 (默认从配置读取)
            batch_size: 批量大小 (默认从配置读取)
            max_retries: 最大重试次数 (默认从配置读取)
        """
        self.model_name = model_name or settings.openai_embedding_model
        self.api_key = api_key or settings.openai_api_key
        self.batch_size = batch_size or settings.openai_embedding_batch_size
        self.max_retries = max_retries or settings.openai_embedding_max_retries

        # 异步客户端
        self.client: Optional[AsyncOpenAI] = None

        # 模型维度映射
        self.model_dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536
        }

        logger.info(
            "openai_embedding_initialized",
            model=self.model_name,
            batch_size=self.batch_size,
            max_retries=self.max_retries
        )

    async def initialize(self):
        """初始化异步客户端"""
        if self.client is None:
            if not self.api_key:
                raise EmbeddingError(
                    "OpenAI API key is not configured",
                    details={"config_key": "OPENAI_API_KEY"}
                )

            self.client = AsyncOpenAI(api_key=self.api_key)
            logger.info("openai_client_initialized", model=self.model_name)

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _create_embedding(
        self,
        texts: List[str]
    ) -> List[List[float]]:
        """
        调用OpenAI API创建向量（带重试）

        Args:
            texts: 文本列表

        Returns:
            向量列表
        """
        try:
            response = await self.client.embeddings.create(
                model=self.model_name,
                input=texts,
                encoding_format="float"
            )

            # 提取向量并按原始顺序排序
            embeddings = [None] * len(texts)
            for item in response.data:
                embeddings[item.index] = item.embedding

            # 记录token使用情况
            logger.debug(
                "openai_embedding_created",
                model=self.model_name,
                text_count=len(texts),
                total_tokens=response.usage.total_tokens
            )

            return embeddings

        except RateLimitError as e:
            logger.warning(
                "openai_rate_limit_hit",
                model=self.model_name,
                error=str(e)
            )
            raise  # 让tenacity重试

        except OpenAIError as e:
            logger.error(
                "openai_api_error",
                model=self.model_name,
                error_type=type(e).__name__,
                error=str(e)
            )
            raise EmbeddingError(
                f"OpenAI API error: {str(e)}",
                details={
                    "model": self.model_name,
                    "text_count": len(texts)
                }
            ) from e

    async def embed_texts(
        self,
        texts: List[str],
        show_progress: bool = False
    ) -> List[List[float]]:
        """
        批量文本向量化

        自动分批处理，避免超过API限制

        Args:
            texts: 文本列表
            show_progress: 是否显示进度

        Returns:
            向量列表
        """
        await self.initialize()

        if not texts:
            return []

        # 预处理：去除空文本
        processed_texts = [text.strip() if text else "" for text in texts]

        # 分批处理
        all_embeddings = []
        total_batches = (len(processed_texts) + self.batch_size - 1) // self.batch_size

        logger.info(
            "openai_embedding_batch_start",
            model=self.model_name,
            total_texts=len(processed_texts),
            batch_size=self.batch_size,
            total_batches=total_batches
        )

        for i in range(0, len(processed_texts), self.batch_size):
            batch = processed_texts[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1

            if show_progress:
                logger.info(
                    "processing_batch",
                    batch_num=batch_num,
                    total_batches=total_batches
                )

            try:
                batch_embeddings = await self._create_embedding(batch)
                all_embeddings.extend(batch_embeddings)

            except Exception as e:
                logger.error(
                    "batch_embedding_failed",
                    batch_num=batch_num,
                    batch_size=len(batch),
                    error=str(e)
                )
                raise

        logger.info(
            "openai_embedding_batch_complete",
            model=self.model_name,
            total_embeddings=len(all_embeddings)
        )

        return all_embeddings

    async def embed_query(self, query: str) -> List[float]:
        """
        单文本向量化（优化的查询接口）

        Args:
            query: 查询文本

        Returns:
            向量
        """
        await self.initialize()

        if not query or not query.strip():
            raise EmbeddingError(
                "Query text cannot be empty",
                details={"query": query}
            )

        embeddings = await self.embed_texts([query.strip()])
        return embeddings[0]

    def get_dimension(self) -> int:
        """
        获取模型的向量维度

        Returns:
            向量维度
        """
        return self.model_dimensions.get(self.model_name, 1536)

    async def health_check(self) -> bool:
        """
        健康检查

        Returns:
            是否健康
        """
        try:
            await self.initialize()
            # 简单的向量化测试
            await self.embed_query("health check")
            return True
        except Exception as e:
            logger.error(
                "openai_embedding_health_check_failed",
                model=self.model_name,
                error=str(e)
            )
            return False

