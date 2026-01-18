"""
向量化模型管理器

提供统一的向量化接口，支持多种Embedding模型：
- local: 本地模型（BGE等）
- openai: OpenAI Embedding API
- custom: 自定义模型

Author: Qingyu AI Team
Date: 2025-10-28
"""

from typing import List, Dict, Optional, Literal
from enum import Enum
import asyncio

from src.core.config import settings
from src.core.logger import get_logger
from src.core.exceptions import EmbeddingError

logger = get_logger(__name__)


class ModelType(str, Enum):
    """支持的模型类型"""
    LOCAL = "local"
    OPENAI = "openai"
    CUSTOM = "custom"


class EmbeddingManager:
    """
    向量化模型管理器

    提供统一的接口管理不同类型的Embedding模型，
    自动路由到相应的实现。
    """

    def __init__(
        self,
        model_type: str = None,
        model_config: Optional[Dict] = None
    ):
        """
        初始化模型管理器

        Args:
            model_type: 模型类型 (local/openai/custom)
            model_config: 模型配置字典
        """
        self.model_type = model_type or settings.embedding_provider
        self.config = model_config or {}

        # 延迟加载实际模型
        self._model_instance = None
        self._dimension = None

        logger.info(
            "embedding_manager_initialized",
            model_type=self.model_type,
            config_keys=list(self.config.keys())
        )

    async def _ensure_model_loaded(self):
        """确保模型已加载（懒加载）"""
        if self._model_instance is not None:
            return

        try:
            if self.model_type == ModelType.LOCAL:
                from src.rag.embedding_service import EmbeddingService
                self._model_instance = EmbeddingService()
                self._model_instance.load_model()
                self._dimension = self._model_instance.get_dimension()

            elif self.model_type == ModelType.OPENAI:
                from src.rag.openai_embedding import OpenAIEmbedding
                self._model_instance = OpenAIEmbedding()
                await self._model_instance.initialize()
                self._dimension = self._model_instance.get_dimension()

            else:
                raise EmbeddingError(
                    f"Unsupported model type: {self.model_type}",
                    details={"supported_types": [e.value for e in ModelType]}
                )

            logger.info(
                "embedding_model_loaded",
                model_type=self.model_type,
                dimension=self._dimension
            )

        except Exception as e:
            logger.error(
                "embedding_model_load_failed",
                model_type=self.model_type,
                error=str(e)
            )
            raise EmbeddingError(
                f"Failed to load {self.model_type} model: {str(e)}",
                details={"model_type": self.model_type}
            ) from e

    async def embed_texts(
        self,
        texts: List[str],
        show_progress: bool = False
    ) -> List[List[float]]:
        """
        批量文本向量化

        Args:
            texts: 文本列表
            show_progress: 是否显示进度（大批量时有用）

        Returns:
            向量列表，每个向量是List[float]

        Raises:
            EmbeddingError: 向量化失败
        """
        await self._ensure_model_loaded()

        if not texts:
            logger.warning("embed_texts_empty_input")
            return []

        try:
            logger.info(
                "embedding_texts_start",
                model_type=self.model_type,
                text_count=len(texts)
            )

            # 根据模型类型调用不同的实现
            if self.model_type == ModelType.LOCAL:
                # 本地模型是同步的，在executor中运行
                loop = asyncio.get_event_loop()
                embeddings = await loop.run_in_executor(
                    None,
                    self._model_instance.embed_texts,
                    texts
                )
            else:
                # OpenAI模型是异步的
                embeddings = await self._model_instance.embed_texts(texts)

            logger.info(
                "embedding_texts_success",
                model_type=self.model_type,
                text_count=len(texts),
                embedding_count=len(embeddings)
            )

            return embeddings

        except Exception as e:
            logger.error(
                "embedding_texts_failed",
                model_type=self.model_type,
                text_count=len(texts),
                error=str(e)
            )
            raise EmbeddingError(
                f"Failed to embed texts: {str(e)}",
                details={
                    "model_type": self.model_type,
                    "text_count": len(texts)
                }
            ) from e

    async def embed_query(self, query: str) -> List[float]:
        """
        单文本向量化（优化的查询接口）

        Args:
            query: 查询文本

        Returns:
            向量（List[float]）

        Raises:
            EmbeddingError: 向量化失败
        """
        await self._ensure_model_loaded()

        if not query or not query.strip():
            raise EmbeddingError(
                "Query text cannot be empty",
                details={"query": query}
            )

        try:
            logger.debug(
                "embedding_query_start",
                model_type=self.model_type,
                query_length=len(query)
            )

            # 根据模型类型调用不同的实现
            if self.model_type == ModelType.LOCAL:
                loop = asyncio.get_event_loop()
                embedding = await loop.run_in_executor(
                    None,
                    self._model_instance.embed_query,
                    query
                )
            else:
                embedding = await self._model_instance.embed_query(query)

            logger.debug(
                "embedding_query_success",
                model_type=self.model_type,
                embedding_dimension=len(embedding)
            )

            return embedding

        except Exception as e:
            logger.error(
                "embedding_query_failed",
                model_type=self.model_type,
                query_length=len(query),
                error=str(e)
            )
            raise EmbeddingError(
                f"Failed to embed query: {str(e)}",
                details={
                    "model_type": self.model_type,
                    "query_length": len(query)
                }
            ) from e

    def get_dimension(self) -> int:
        """
        获取向量维度

        Returns:
            向量维度
        """
        if self._dimension is None:
            # 如果还没加载，返回配置的默认值
            if self.model_type == ModelType.LOCAL:
                return 1024  # BGE-large-zh-v1.5
            elif self.model_type == ModelType.OPENAI:
                return 1536  # text-embedding-3-small
            else:
                return 1024  # 默认

        return self._dimension

    async def health_check(self) -> Dict[str, any]:
        """
        健康检查

        Returns:
            健康状态字典
        """
        try:
            await self._ensure_model_loaded()

            # 简单的向量化测试
            test_text = "健康检查测试"
            embedding = await self.embed_query(test_text)

            return {
                "status": "healthy",
                "model_type": self.model_type,
                "dimension": len(embedding),
                "model_loaded": self._model_instance is not None
            }

        except Exception as e:
            logger.error(
                "embedding_health_check_failed",
                model_type=self.model_type,
                error=str(e)
            )
            return {
                "status": "unhealthy",
                "model_type": self.model_type,
                "error": str(e)
            }


# 全局单例（可选，推荐在API层使用依赖注入）
_embedding_manager_instance: Optional[EmbeddingManager] = None


def get_embedding_manager() -> EmbeddingManager:
    """
    获取全局EmbeddingManager实例（单例模式）

    Returns:
        EmbeddingManager实例
    """
    global _embedding_manager_instance

    if _embedding_manager_instance is None:
        _embedding_manager_instance = EmbeddingManager()

    return _embedding_manager_instance

