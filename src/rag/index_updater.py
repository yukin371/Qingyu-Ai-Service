"""
向量索引更新器

监听文档事件并自动更新Milvus向量索引

Author: Qingyu AI Team
Date: 2025-10-28
"""

from typing import Optional
import asyncio

from src.events.document_events import (
    DocumentEvent,
    DocumentCreatedEvent,
    DocumentUpdatedEvent,
    DocumentDeletedEvent,
    EventType
)
from src.events.handlers import EventHandler
from src.rag.embedding_manager import EmbeddingManager
from src.rag.milvus_client import MilvusClient
from src.rag.text_splitter import RecursiveCharacterTextSplitter
from src.core.logger import logger
from src.core.config import settings
from src.core.exceptions import IndexUpdateError


class VectorIndexUpdater(EventHandler):
    """
    向量索引更新器

    负责处理文档事件，自动更新Milvus向量索引
    """

    def __init__(
        self,
        embedding_manager: EmbeddingManager,
        milvus_client: MilvusClient,
        text_splitter: Optional[RecursiveCharacterTextSplitter] = None
    ):
        """
        初始化索引更新器

        Args:
            embedding_manager: 向量化管理器
            milvus_client: Milvus客户端
            text_splitter: 文本分块器（可选）
        """
        super().__init__("VectorIndexUpdater")

        self.embedding_manager = embedding_manager
        self.milvus_client = milvus_client
        self.text_splitter = text_splitter or RecursiveCharacterTextSplitter(
            chunk_size=settings.text_chunk_size,
            chunk_overlap=settings.text_chunk_overlap
        )

        # 统计信息
        self.stats = {
            'created': 0,
            'updated': 0,
            'deleted': 0,
            'errors': 0
        }

        logger.info("vector_index_updater_initialized")

    def can_handle(self, event: DocumentEvent) -> bool:
        """判断是否能处理此事件"""
        return event.event_type in [
            EventType.DOCUMENT_CREATED,
            EventType.DOCUMENT_UPDATED,
            EventType.DOCUMENT_DELETED
        ]

    async def handle(self, event: DocumentEvent) -> None:
        """
        处理事件

        Args:
            event: 文档事件
        """
        try:
            if event.event_type == EventType.DOCUMENT_CREATED:
                await self.handle_document_created(event)
            elif event.event_type == EventType.DOCUMENT_UPDATED:
                await self.handle_document_updated(event)
            elif event.event_type == EventType.DOCUMENT_DELETED:
                await self.handle_document_deleted(event)
            else:
                logger.warning(
                    "unknown_event_type",
                    event_type=event.event_type,
                    event_id=event.event_id
                )

            await self.on_success(event)

        except Exception as e:
            self.stats['errors'] += 1
            await self.on_error(event, e)
            raise IndexUpdateError(
                f"Failed to handle event: {str(e)}",
                details={
                    'event_id': event.event_id,
                    'event_type': event.event_type,
                    'document_id': event.document_id
                }
            ) from e

    async def handle_document_created(
        self,
        event: DocumentCreatedEvent
    ) -> None:
        """
        处理文档创建事件

        Args:
            event: 文档创建事件
        """
        logger.info(
            "handling_document_created",
            event_id=event.event_id,
            document_id=event.document_id
        )

        # 1. 文本分块
        chunks = self.text_splitter.create_chunks(
            text=event.content,
            metadata={
                'source': event.source,
                'title': event.title,
                'tags': event.tags,
                'created_by': event.user_id,
                'created_at': event.timestamp.isoformat()
            }
        )

        if not chunks:
            logger.warning(
                "no_chunks_created",
                document_id=event.document_id
            )
            return

        # 2. 向量化
        texts = [chunk.text for chunk in chunks]
        vectors = await self.embedding_manager.embed_texts(texts)

        # 3. 构建插入数据
        chunk_dicts = [
            {
                'text': chunk.text,
                'chunk_id': chunk.chunk_id,
                'metadata': chunk.metadata
            }
            for chunk in chunks
        ]

        # 4. 插入Milvus
        ids = self.milvus_client.insert_document(
            document_id=event.document_id,
            chunks=chunk_dicts,
            vectors=vectors
        )

        self.stats['created'] += 1

        logger.info(
            "document_indexed",
            event_id=event.event_id,
            document_id=event.document_id,
            chunk_count=len(chunks),
            vector_count=len(ids)
        )

    async def handle_document_updated(
        self,
        event: DocumentUpdatedEvent
    ) -> None:
        """
        处理文档更新事件

        Args:
            event: 文档更新事件
        """
        logger.info(
            "handling_document_updated",
            event_id=event.event_id,
            document_id=event.document_id
        )

        # 1. 删除旧向量
        try:
            self.milvus_client.delete_document(event.document_id)
            logger.debug(
                "old_vectors_deleted",
                document_id=event.document_id
            )
        except Exception as e:
            logger.warning(
                "failed_to_delete_old_vectors",
                document_id=event.document_id,
                error=str(e)
            )

        # 2. 重新分块和向量化（复用创建逻辑）
        # 将更新事件转换为创建事件
        create_event = DocumentCreatedEvent(
            event_id=event.event_id,
            event_type=EventType.DOCUMENT_CREATED,
            document_id=event.document_id,
            timestamp=event.timestamp,
            user_id=event.user_id,
            metadata=event.metadata,
            content=event.content,
            source=event.source,
            title=event.title,
            tags=event.tags
        )

        await self.handle_document_created(create_event)

        self.stats['updated'] += 1

        logger.info(
            "document_reindexed",
            event_id=event.event_id,
            document_id=event.document_id
        )

    async def handle_document_deleted(
        self,
        event: DocumentDeletedEvent
    ) -> None:
        """
        处理文档删除事件

        Args:
            event: 文档删除事件
        """
        logger.info(
            "handling_document_deleted",
            event_id=event.event_id,
            document_id=event.document_id
        )

        # 删除所有相关向量
        self.milvus_client.delete_document(event.document_id)

        self.stats['deleted'] += 1

        logger.info(
            "document_vectors_deleted",
            event_id=event.event_id,
            document_id=event.document_id
        )

    def get_stats(self) -> dict:
        """获取统计信息"""
        return self.stats.copy()

    def reset_stats(self) -> None:
        """重置统计信息"""
        self.stats = {
            'created': 0,
            'updated': 0,
            'deleted': 0,
            'errors': 0
        }

