"""
向量化服务
阶段 2.1 实现
"""
from typing import List, Optional
import torch
from sentence_transformers import SentenceTransformer
import numpy as np

from ..core import get_logger, EmbeddingError, settings

logger = get_logger(__name__)


class EmbeddingService:
    """文本向量化服务"""

    def __init__(self):
        """初始化向量化服务"""
        self.model_name = settings.embedding_model_name
        self.device = settings.embedding_model_device
        self.batch_size = settings.embedding_batch_size
        self.model: Optional[SentenceTransformer] = None

        logger.info(
            "initializing_embedding_service",
            model=self.model_name,
            device=self.device
        )

    def load_model(self) -> None:
        """加载向量化模型"""
        try:
            logger.info("loading_embedding_model", model=self.model_name)

            # 1. 加载模型（SentenceTransformer 会自动下载）
            self.model = SentenceTransformer(self.model_name)

            # 2. 移动到指定设备
            # 自动检测：如果指定cuda但不可用，则回退到cpu
            if self.device == "cuda" and not torch.cuda.is_available():
                logger.warning("cuda_not_available_fallback_to_cpu")
                self.device = "cpu"

            self.model.to(self.device)

            # 3. 设置为评估模式
            self.model.eval()

            # 4. 预热模型（避免首次推理慢）
            logger.info("warming_up_model")
            _ = self.model.encode(["预热模型"], convert_to_numpy=True)

            logger.info(
                "model_loaded_successfully",
                model=self.model_name,
                device=self.device,
                dimension=self.get_dimension()
            )

        except Exception as e:
            logger.error("failed_to_load_model", error=str(e))
            raise EmbeddingError(f"Failed to load embedding model: {str(e)}")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """批量向量化文本

        Args:
            texts: 文本列表

        Returns:
            向量列表
        """
        try:
            if not self.model:
                raise EmbeddingError("Model not loaded. Call load_model() first.")

            logger.info("embedding_texts", count=len(texts))

            # 1. 文本预处理（去除多余空格和换行）
            cleaned_texts = [" ".join(text.split()) for text in texts]

            # 2. 批量编码
            # convert_to_numpy=True 返回 numpy 数组
            # normalize_embeddings=True 进行 L2 归一化
            embeddings = self.model.encode(
                cleaned_texts,
                batch_size=self.batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True,  # L2 归一化（用于内积相似度）
                show_progress_bar=len(texts) > 100  # 大批量时显示进度
            )

            # 3. 转换为 Python list
            embeddings_list = embeddings.tolist()

            logger.info("texts_embedded_successfully", count=len(embeddings_list))

            return embeddings_list

        except Exception as e:
            logger.error("failed_to_embed_texts", error=str(e))
            raise EmbeddingError(f"Failed to embed texts: {str(e)}")

    def embed_query(self, query: str) -> List[float]:
        """向量化查询文本

        Args:
            query: 查询文本

        Returns:
            查询向量
        """
        try:
            # 调用 embed_texts，传入单个查询
            embeddings = self.embed_texts([query])
            return embeddings[0]

        except Exception as e:
            logger.error("failed_to_embed_query", error=str(e))
            raise EmbeddingError(f"Failed to embed query: {str(e)}")

    def get_dimension(self) -> int:
        """获取向量维度

        Returns:
            向量维度
        """
        if self.model:
            # 动态获取模型的输出维度
            return self.model.get_sentence_embedding_dimension()
        else:
            # 默认返回 BGE-large-zh-v1.5 的维度
            return 1024

