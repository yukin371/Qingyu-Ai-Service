"""
Milvus 集成测试
阶段 1.3 测试

注意：这些测试需要 Milvus 服务运行在 localhost:19530
"""
import pytest
from typing import List

from src.rag.milvus_client import MilvusClient
from src.rag.embedding_service import EmbeddingService


# 测试数据
TEST_TEXTS = [
    "青羽写作平台是一个 AI 辅助写作应用",
    "支持用户管理、文档存储、AI 文本生成等功能",
    "采用现代化分层架构和设计模式"
]


@pytest.fixture
def milvus_client():
    """Milvus 客户端 fixture"""
    client = MilvusClient()
    try:
        client.connect()
        yield client
    finally:
        client.disconnect()


@pytest.fixture
def embedding_service():
    """向量化服务 fixture"""
    service = EmbeddingService()
    service.load_model()
    return service


@pytest.mark.integration
class TestMilvusIntegration:
    """Milvus 集成测试"""

    def test_milvus_connection(self, milvus_client):
        """测试 Milvus 连接"""
        # 健康检查应该返回 True
        assert milvus_client.health_check() is True

    def test_create_collection(self, milvus_client):
        """测试 Collection 创建"""
        # 创建 collection（维度 1024）
        milvus_client.create_collection(dimension=1024)

        # Collection 应该已加载
        assert milvus_client.collection is not None

    def test_insert_vectors(self, milvus_client, embedding_service):
        """测试向量插入"""
        # 准备数据
        texts = TEST_TEXTS
        vectors = embedding_service.embed_texts(texts)
        metadata = [
            {"source": "test", "index": i}
            for i in range(len(texts))
        ]

        # 创建 collection
        milvus_client.create_collection(dimension=len(vectors[0]))

        # 插入向量
        ids = milvus_client.insert(texts, vectors, metadata)

        # 验证返回的 ID 数量
        assert len(ids) == len(texts)

    def test_search_vectors(self, milvus_client, embedding_service):
        """测试向量检索"""
        # 准备数据并插入
        texts = TEST_TEXTS
        vectors = embedding_service.embed_texts(texts)
        metadata = [
            {"source": "test", "index": i}
            for i in range(len(texts))
        ]

        milvus_client.create_collection(dimension=len(vectors[0]))
        milvus_client.insert(texts, vectors, metadata)

        # 使用第一个文本作为查询
        query_vector = vectors[0]

        # 执行搜索
        results = milvus_client.search(query_vector, top_k=3)

        # 验证结果
        assert len(results) > 0
        # Top-1 应该是原文本（相似度最高）
        assert results[0]["text"] == texts[0]
        assert results[0]["score"] > 0.99  # 归一化后内积应该接近 1

    def test_delete_vectors(self, milvus_client, embedding_service):
        """测试向量删除"""
        # 准备数据并插入
        texts = TEST_TEXTS
        vectors = embedding_service.embed_texts(texts)
        metadata = [{"source": "test", "index": i} for i in range(len(texts))]

        milvus_client.create_collection(dimension=len(vectors[0]))
        ids = milvus_client.insert(texts, vectors, metadata)

        # 删除第一个向量
        milvus_client.delete([ids[0]])

        # 搜索应该返回少于原始数量的结果
        query_vector = vectors[1]
        results = milvus_client.search(query_vector, top_k=10)
        assert len(results) == len(texts) - 1

    def test_embedding_service(self, embedding_service):
        """测试向量化服务"""
        # 测试批量向量化
        texts = TEST_TEXTS
        vectors = embedding_service.embed_texts(texts)

        # 验证结果
        assert len(vectors) == len(texts)
        assert len(vectors[0]) == 1024  # BGE-large-zh-v1.5 维度

        # 测试单个查询向量化
        query = "AI 写作平台"
        query_vector = embedding_service.embed_query(query)
        assert len(query_vector) == 1024

    @pytest.mark.slow
    def test_end_to_end_rag(self, milvus_client, embedding_service):
        """端到端 RAG 流程测试"""
        # 1. 创建 collection
        dimension = embedding_service.get_dimension()
        milvus_client.create_collection(dimension=dimension)

        # 2. 准备知识库文本
        texts = TEST_TEXTS
        vectors = embedding_service.embed_texts(texts)
        metadata = [
            {"source": "knowledge_base", "category": "platform"},
        ] * len(texts)

        # 3. 插入向量
        ids = milvus_client.insert(texts, vectors, metadata)
        assert len(ids) == len(texts)

        # 4. 查询
        query = "什么是青羽写作平台？"
        query_vector = embedding_service.embed_query(query)

        # 5. 检索
        results = milvus_client.search(query_vector, top_k=2)

        # 6. 验证
        assert len(results) > 0
        # 第一个结果应该包含相关内容
        assert "青羽" in results[0]["text"] or "写作" in results[0]["text"]


# 运行测试的说明
"""
运行测试前，确保：
1. Milvus 服务运行在 localhost:19530
2. 已安装所有依赖：poetry install
3. 模型会自动下载（首次运行需要时间）

运行命令：
    pytest tests/test_milvus_integration.py -v -m integration

跳过慢速测试：
    pytest tests/test_milvus_integration.py -v -m "integration and not slow"
"""

