"""
Milvus 客户端封装
阶段 1.3 实现
"""
from typing import List, Dict, Any, Optional
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

from ..core import get_logger, MilvusConnectionError, settings

logger = get_logger(__name__)


class MilvusClient:
    """Milvus 向量数据库客户端"""

    def __init__(self):
        """初始化 Milvus 客户端"""
        self.host = settings.milvus_host
        self.port = settings.milvus_port
        self.collection_name = settings.milvus_collection_name
        self.collection: Optional[Collection] = None

        logger.info(
            "initializing_milvus_client",
            host=self.host,
            port=self.port
        )

    def connect(self) -> None:
        """连接到 Milvus 服务器"""
        try:
            logger.info("connecting_to_milvus", host=self.host, port=self.port)

            connections.connect(
                alias="default",
                host=self.host,
                port=str(self.port)
            )

            logger.info("connected_to_milvus")

        except Exception as e:
            logger.error("failed_to_connect_to_milvus", error=str(e))
            raise MilvusConnectionError(f"Failed to connect to Milvus: {str(e)}")

    def disconnect(self) -> None:
        """断开 Milvus 连接"""
        try:
            connections.disconnect(alias="default")
            logger.info("disconnected_from_milvus")
        except Exception as e:
            logger.error("failed_to_disconnect_from_milvus", error=str(e))

    def create_collection(self, dimension: int = 1024) -> None:
        """创建 Collection

        Args:
            dimension: 向量维度，默认 1024（BGE-large-zh-v1.5）
        """
        try:
            logger.info("creating_collection", name=self.collection_name, dimension=dimension)

            # 1. 定义 Schema
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=200),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dimension),
                FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=200),  # 文档ID
                FieldSchema(name="chunk_id", dtype=DataType.INT64),  # 文档内chunk序号
                FieldSchema(name="metadata", dtype=DataType.JSON),
            ]
            schema = CollectionSchema(fields=fields, description="Qingyu Knowledge Base")

            # 2. 创建 Collection
            self.collection = Collection(name=self.collection_name, schema=schema)
            logger.info("collection_created", name=self.collection_name)

            # 3. 创建索引
            index_params = {
                "metric_type": "IP",  # 内积相似度（归一化后等价余弦）
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128}
            }
            self.collection.create_index(field_name="vector", index_params=index_params)
            logger.info("index_created", index_type="IVF_FLAT")

            # 4. 加载 Collection 到内存
            self.collection.load()
            logger.info("collection_loaded", name=self.collection_name)

        except Exception as e:
            logger.error("failed_to_create_collection", error=str(e))
            raise MilvusConnectionError(f"Failed to create collection: {str(e)}")

    def insert(
        self,
        texts: List[str],
        vectors: List[List[float]],
        metadata: List[Dict[str, Any]],
        document_ids: Optional[List[str]] = None,
        chunk_ids: Optional[List[int]] = None
    ) -> List[str]:
        """插入向量数据

        Args:
            texts: 文本列表
            vectors: 向量列表
            metadata: 元数据列表
            document_ids: 文档ID列表（可选，默认生成UUID）
            chunk_ids: chunk序号列表（可选，默认为0）

        Returns:
            插入的文档 ID 列表
        """
        try:
            if not self.collection:
                raise MilvusConnectionError("Collection not loaded. Call create_collection() first.")

            # 生成唯一 ID
            import uuid
            ids = [str(uuid.uuid4()) for _ in range(len(texts))]

            # 提取 source 字段（如果存在）
            sources = [meta.get("source", "unknown") for meta in metadata]

            # 处理document_id和chunk_id
            if document_ids is None:
                document_ids = ids  # 默认使用主键ID
            if chunk_ids is None:
                chunk_ids = [0] * len(texts)  # 默认chunk_id为0

            # 构建批量插入数据
            entities = [
                ids,
                texts,
                vectors,
                sources,
                document_ids,
                chunk_ids,
                metadata
            ]

            logger.info("inserting_vectors", count=len(texts), unique_documents=len(set(document_ids)))

            # 执行插入
            insert_result = self.collection.insert(entities)
            self.collection.flush()

            logger.info("vectors_inserted", count=len(ids), ids_sample=ids[:3])

            return ids

        except Exception as e:
            logger.error("failed_to_insert_vectors", error=str(e))
            raise MilvusConnectionError(f"Failed to insert vectors: {str(e)}")

    def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """检索相似向量

        Args:
            query_vector: 查询向量
            top_k: 返回结果数量
            filters: 元数据过滤条件

        Returns:
            检索结果列表
        """
        try:
            if not self.collection:
                raise MilvusConnectionError("Collection not loaded. Call create_collection() first.")

            # 构建搜索参数
            search_params = {
                "metric_type": "IP",
                "params": {"nprobe": 10}
            }

            # 构建过滤表达式（如果有）
            expr = None
            if filters:
                # 简单的过滤表达式构建
                # 例如：filters = {"source": "project"} -> expr = 'source == "project"'
                filter_clauses = []
                for key, value in filters.items():
                    if isinstance(value, str):
                        filter_clauses.append(f'{key} == "{value}"')
                    else:
                        filter_clauses.append(f'{key} == {value}')
                expr = " and ".join(filter_clauses) if filter_clauses else None

            logger.info("searching_vectors", top_k=top_k, has_filters=filters is not None)

            # 执行搜索
            results = self.collection.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                expr=expr,
                output_fields=["id", "text", "source", "metadata"]
            )

            # 解析结果
            search_results = []
            for hits in results:
                for hit in hits:
                    search_results.append({
                        "id": hit.entity.get("id"),
                        "text": hit.entity.get("text"),
                        "source": hit.entity.get("source"),
                        "metadata": hit.entity.get("metadata"),
                        "score": hit.score
                    })

            logger.info("search_completed", results_count=len(search_results))

            return search_results

        except Exception as e:
            logger.error("failed_to_search_vectors", error=str(e))
            raise MilvusConnectionError(f"Failed to search vectors: {str(e)}")

    def delete(self, ids: List[str]) -> None:
        """删除向量数据

        Args:
            ids: 要删除的文档 ID 列表
        """
        try:
            if not self.collection:
                raise MilvusConnectionError("Collection not loaded. Call create_collection() first.")

            # 构建删除表达式
            # 使用 IN 操作符批量删除
            ids_str = ", ".join([f'"{id}"' for id in ids])
            expr = f"id in [{ids_str}]"

            logger.info("deleting_vectors", count=len(ids))

            # 执行删除
            self.collection.delete(expr)
            self.collection.flush()

            logger.info("vectors_deleted", count=len(ids))

        except Exception as e:
            logger.error("failed_to_delete_vectors", error=str(e))
            raise MilvusConnectionError(f"Failed to delete vectors: {str(e)}")

    def insert_document(
        self,
        document_id: str,
        chunks: List[Dict[str, Any]],
        vectors: List[List[float]]
    ) -> List[str]:
        """插入文档（自动分块）

        Args:
            document_id: 文档ID
            chunks: chunk列表，每个chunk包含 {'text': str, 'chunk_id': int, 'metadata': dict}
            vectors: 向量列表

        Returns:
            插入的ID列表
        """
        try:
            # 提取数据
            texts = [chunk['text'] for chunk in chunks]
            chunk_ids = [chunk.get('chunk_id', i) for i, chunk in enumerate(chunks)]
            metadatas = [chunk.get('metadata', {}) for chunk in chunks]
            document_ids = [document_id] * len(chunks)

            # 批量插入
            ids = self.insert(
                texts=texts,
                vectors=vectors,
                metadata=metadatas,
                document_ids=document_ids,
                chunk_ids=chunk_ids
            )

            logger.info(
                "document_inserted",
                document_id=document_id,
                chunk_count=len(chunks)
            )

            return ids

        except Exception as e:
            logger.error(
                "failed_to_insert_document",
                document_id=document_id,
                error=str(e)
            )
            raise MilvusConnectionError(f"Failed to insert document: {str(e)}")

    def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """获取文档的所有chunk

        Args:
            document_id: 文档ID

        Returns:
            chunk列表
        """
        try:
            if not self.collection:
                raise MilvusConnectionError("Collection not loaded.")

            # 构建查询表达式
            expr = f'document_id == "{document_id}"'

            logger.info("querying_document_chunks", document_id=document_id)

            # 查询所有chunk
            results = self.collection.query(
                expr=expr,
                output_fields=["id", "text", "source", "document_id", "chunk_id", "metadata"]
            )

            # 按chunk_id排序
            sorted_results = sorted(results, key=lambda x: x.get('chunk_id', 0))

            logger.info(
                "document_chunks_retrieved",
                document_id=document_id,
                chunk_count=len(sorted_results)
            )

            return sorted_results

        except Exception as e:
            logger.error(
                "failed_to_get_document_chunks",
                document_id=document_id,
                error=str(e)
            )
            raise MilvusConnectionError(f"Failed to get document chunks: {str(e)}")

    def delete_document(self, document_id: str) -> None:
        """删除文档的所有chunk

        Args:
            document_id: 文档ID
        """
        try:
            if not self.collection:
                raise MilvusConnectionError("Collection not loaded.")

            # 构建删除表达式
            expr = f'document_id == "{document_id}"'

            logger.info("deleting_document", document_id=document_id)

            # 执行删除
            self.collection.delete(expr)
            self.collection.flush()

            logger.info("document_deleted", document_id=document_id)

        except Exception as e:
            logger.error(
                "failed_to_delete_document",
                document_id=document_id,
                error=str(e)
            )
            raise MilvusConnectionError(f"Failed to delete document: {str(e)}")

    def health_check(self) -> bool:
        """健康检查

        Returns:
            是否健康
        """
        try:
            # 简单检查连接状态
            connections.list_connections()
            return True
        except Exception as e:
            logger.error("milvus_health_check_failed", error=str(e))
            return False

