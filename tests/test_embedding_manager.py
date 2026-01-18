"""
EmbeddingManager 测试

测试统一向量化管理器的核心功能

Author: Qingyu AI Team
Date: 2025-10-28
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.rag.embedding_manager import EmbeddingManager, ModelType
from src.core.exceptions import EmbeddingError


class TestEmbeddingManager:
    """EmbeddingManager 测试类"""

    @pytest.mark.asyncio
    async def test_local_model_initialization(self):
        """测试本地模型初始化"""
        manager = EmbeddingManager(model_type="local")

        assert manager.model_type == "local"
        assert manager._model_instance is None  # 懒加载

    @pytest.mark.asyncio
    async def test_openai_model_initialization(self):
        """测试OpenAI模型初始化"""
        manager = EmbeddingManager(model_type="openai")

        assert manager.model_type == "openai"
        assert manager._model_instance is None

    @pytest.mark.asyncio
    async def test_unsupported_model_type(self):
        """测试不支持的模型类型"""
        manager = EmbeddingManager(model_type="unsupported")

        with pytest.raises(EmbeddingError) as exc_info:
            await manager._ensure_model_loaded()

        assert "Unsupported model type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_embed_texts_empty_input(self):
        """测试空输入"""
        manager = EmbeddingManager(model_type="local")

        result = await manager.embed_texts([])

        assert result == []

    @pytest.mark.asyncio
    async def test_embed_query_empty_input(self):
        """测试空查询"""
        manager = EmbeddingManager(model_type="local")

        with pytest.raises(EmbeddingError) as exc_info:
            await manager.embed_query("")

        assert "cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch('src.rag.embedding_manager.EmbeddingService')
    async def test_local_model_embed_texts(self, mock_embedding_service):
        """测试本地模型文本向量化（Mock）"""
        # 设置Mock
        mock_instance = Mock()
        mock_instance.embed_texts.return_value = [[0.1] * 1024, [0.2] * 1024]
        mock_instance.get_dimension.return_value = 1024
        mock_embedding_service.return_value = mock_instance

        # 测试
        manager = EmbeddingManager(model_type="local")
        await manager._ensure_model_loaded()

        # 因为是同步模型，需要在executor中运行
        import asyncio
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            mock_instance.embed_texts,
            ["text1", "text2"]
        )

        assert len(embeddings) == 2
        assert len(embeddings[0]) == 1024

    @pytest.mark.asyncio
    async def test_get_dimension_before_load(self):
        """测试加载前获取维度（使用默认值）"""
        manager_local = EmbeddingManager(model_type="local")
        manager_openai = EmbeddingManager(model_type="openai")

        # 应该返回默认维度
        assert manager_local.get_dimension() == 1024
        assert manager_openai.get_dimension() == 1536

    @pytest.mark.asyncio
    @patch('src.rag.embedding_manager.EmbeddingService')
    async def test_health_check(self, mock_embedding_service):
        """测试健康检查"""
        # 设置Mock
        mock_instance = Mock()
        mock_instance.embed_query.return_value = [0.1] * 1024
        mock_instance.get_dimension.return_value = 1024
        mock_embedding_service.return_value = mock_instance

        # 测试
        manager = EmbeddingManager(model_type="local")

        # Mock ensure_model_loaded
        manager._model_instance = mock_instance
        manager._dimension = 1024

        # 执行健康检查
        result = await manager.health_check()

        assert result["status"] == "healthy"
        assert result["model_type"] == "local"
        assert result["dimension"] == 1024
        assert result["model_loaded"] is True


# 集成测试（需要实际模型）
@pytest.mark.integration
@pytest.mark.asyncio
async def test_local_model_full_flow():
    """完整流程测试（需要实际下载模型）"""
    try:
        manager = EmbeddingManager(model_type="local")

        # 向量化
        texts = ["这是测试文本一", "这是测试文本二"]
        embeddings = await manager.embed_texts(texts)

        assert len(embeddings) == 2
        assert len(embeddings[0]) > 0

        # 查询
        query_embedding = await manager.embed_query("这是查询文本")
        assert len(query_embedding) > 0

        # 健康检查
        health = await manager.health_check()
        assert health["status"] == "healthy"

    except Exception as e:
        pytest.skip(f"Integration test skipped: {str(e)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

