"""
文本分块器

提供多种文本分块策略，适用于RAG系统的文档处理：
- 递归字符分块（推荐）
- 语义分块（未来）

支持中文文本的智能分割和元数据保留。

Author: Qingyu AI Team
Date: 2025-10-28
"""

from typing import List, Dict, Callable, Optional
import re
from dataclasses import dataclass

from src.core.config import settings
from src.core.logger import logger


@dataclass
class TextChunk:
    """文本块数据结构"""
    text: str
    chunk_id: int
    start_index: int
    end_index: int
    metadata: Optional[Dict] = None


class RecursiveCharacterTextSplitter:
    """
    递归字符文本分块器

    按照分隔符优先级递归分割文本，确保：
    - 块大小尽量接近chunk_size
    - 保持语义完整性（优先在段落、句子边界分割）
    - 支持重叠（overlap）以保留上下文

    适用于：小说、文章、文档等长文本
    """

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        separators: Optional[List[str]] = None,
        length_function: Callable[[str], int] = len,
        keep_separator: bool = True
    ):
        """
        初始化分块器

        Args:
            chunk_size: 块大小（字符数）
            chunk_overlap: 重叠大小（字符数）
            separators: 分隔符优先级列表（从高到低）
            length_function: 长度计算函数
            keep_separator: 是否保留分隔符
        """
        self.chunk_size = chunk_size or settings.text_chunk_size
        self.chunk_overlap = chunk_overlap or settings.text_chunk_overlap
        self.length_function = length_function
        self.keep_separator = keep_separator

        # 默认分隔符（中文优化）
        if separators is None:
            self.separators = [
                "\n\n",    # 段落
                "\n",      # 换行
                "。",      # 中文句号
                "！",      # 中文感叹号
                "？",      # 中文问号
                "；",      # 中文分号
                "，",      # 中文逗号
                ".",       # 英文句号
                "!",       # 英文感叹号
                "?",       # 英文问号
                ";",       # 英文分号
                ",",       # 英文逗号
                " ",       # 空格
                ""         # 字符级别（最后保底）
            ]
        else:
            self.separators = separators

        logger.info(
            "text_splitter_initialized",
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators_count=len(self.separators)
        )

    def _split_text_with_regex(
        self,
        text: str,
        separator: str
    ) -> List[str]:
        """
        使用正则表达式分割文本

        Args:
            text: 待分割文本
            separator: 分隔符

        Returns:
            分割后的文本列表
        """
        if separator:
            if self.keep_separator:
                # 保留分隔符
                splits = re.split(f"({re.escape(separator)})", text)
                # 合并分隔符和文本
                merged = []
                for i in range(1, len(splits), 2):
                    merged.append(splits[i - 1] + splits[i])
                if len(splits) % 2 == 1:
                    merged.append(splits[-1])
                return [s for s in merged if s]
            else:
                return [s for s in text.split(separator) if s]
        else:
            # 空分隔符：字符级别分割
            return list(text)

    def _merge_splits(
        self,
        splits: List[str],
        separator: str
    ) -> List[str]:
        """
        合并分割后的文本块，确保大小合适

        Args:
            splits: 分割后的文本列表
            separator: 分隔符（用于重新连接）

        Returns:
            合并后的文本块列表
        """
        separator_len = self.length_function(separator)

        docs = []
        current_doc = []
        current_length = 0

        for split in splits:
            split_len = self.length_function(split)

            # 单个split就超过chunk_size，直接添加
            if split_len > self.chunk_size:
                if current_doc:
                    docs.append(separator.join(current_doc))
                    current_doc = []
                    current_length = 0
                docs.append(split)
                continue

            # 添加会超过chunk_size，先保存当前doc
            if current_length + split_len + (separator_len if current_doc else 0) > self.chunk_size:
                if current_doc:
                    docs.append(separator.join(current_doc))
                    # 保留overlap的内容
                    while current_doc and current_length > self.chunk_overlap:
                        removed = current_doc.pop(0)
                        current_length -= self.length_function(removed) + separator_len

            current_doc.append(split)
            current_length += split_len + (separator_len if current_doc else 0)

        # 添加最后一个doc
        if current_doc:
            docs.append(separator.join(current_doc))

        return docs

    def _split_text_recursive(
        self,
        text: str,
        separators: List[str]
    ) -> List[str]:
        """
        递归分割文本

        Args:
            text: 待分割文本
            separators: 分隔符列表

        Returns:
            分割后的文本块列表
        """
        final_chunks = []
        separator = separators[-1]
        new_separators = []

        # 选择合适的分隔符
        for i, sep in enumerate(separators):
            if sep == "":
                separator = sep
                break
            if re.search(re.escape(sep), text):
                separator = sep
                new_separators = separators[i + 1:]
                break

        # 使用当前分隔符分割
        splits = self._split_text_with_regex(text, separator)

        # 合并分割后的文本
        good_splits = []
        for split in splits:
            if self.length_function(split) < self.chunk_size:
                good_splits.append(split)
            else:
                # 太大，需要进一步分割
                if good_splits:
                    merged = self._merge_splits(good_splits, separator)
                    final_chunks.extend(merged)
                    good_splits = []

                if not new_separators:
                    # 没有更多分隔符了，直接添加
                    final_chunks.append(split)
                else:
                    # 递归分割
                    recursive_chunks = self._split_text_recursive(split, new_separators)
                    final_chunks.extend(recursive_chunks)

        # 处理剩余的good_splits
        if good_splits:
            merged = self._merge_splits(good_splits, separator)
            final_chunks.extend(merged)

        return final_chunks

    def split_text(self, text: str) -> List[str]:
        """
        分割文本

        Args:
            text: 待分割的长文本

        Returns:
            分割后的文本块列表
        """
        if not text or not text.strip():
            logger.warning("split_text_empty_input")
            return []

        chunks = self._split_text_recursive(text, self.separators)

        logger.info(
            "text_split_complete",
            original_length=len(text),
            chunk_count=len(chunks),
            avg_chunk_size=sum(len(c) for c in chunks) // len(chunks) if chunks else 0
        )

        return chunks

    def create_chunks(
        self,
        text: str,
        metadata: Optional[Dict] = None
    ) -> List[TextChunk]:
        """
        创建带元数据的文本块对象

        Args:
            text: 待分割文本
            metadata: 元数据（会复制到每个chunk）

        Returns:
            TextChunk对象列表
        """
        split_texts = self.split_text(text)

        chunks = []
        current_index = 0

        for i, chunk_text in enumerate(split_texts):
            # 查找chunk在原文中的位置
            start_index = text.find(chunk_text, current_index)
            if start_index == -1:
                start_index = current_index
            end_index = start_index + len(chunk_text)

            chunk = TextChunk(
                text=chunk_text,
                chunk_id=i,
                start_index=start_index,
                end_index=end_index,
                metadata=metadata.copy() if metadata else {}
            )
            chunks.append(chunk)
            current_index = end_index

        return chunks

    def split_documents(
        self,
        documents: List[Dict]
    ) -> List[Dict]:
        """
        分割文档列表（保留元数据）

        Args:
            documents: 文档列表，每个文档是一个字典
                      必须包含 'content' 或 'text' 字段
                      可选包含 'metadata' 字段

        Returns:
            分割后的文档列表
        """
        all_chunks = []

        for doc_id, doc in enumerate(documents):
            # 提取文本内容
            text = doc.get('content') or doc.get('text') or ""
            metadata = doc.get('metadata', {})

            # 添加文档ID到元数据
            metadata['document_id'] = doc.get('id') or doc_id
            metadata['original_document_id'] = doc.get('id') or doc_id

            # 分块
            chunks = self.create_chunks(text, metadata)

            # 转换为字典
            for chunk in chunks:
                chunk_dict = {
                    'text': chunk.text,
                    'chunk_id': chunk.chunk_id,
                    'start_index': chunk.start_index,
                    'end_index': chunk.end_index,
                    'metadata': chunk.metadata
                }
                all_chunks.append(chunk_dict)

        logger.info(
            "documents_split_complete",
            document_count=len(documents),
            total_chunks=len(all_chunks),
            avg_chunks_per_doc=len(all_chunks) / len(documents) if documents else 0
        )

        return all_chunks


class SemanticTextSplitter:
    """
    语义文本分块器（占位，未来实现）

    基于embedding相似度进行智能分块，
    确保每个chunk的语义完整性。

    实现思路：
    1. 按句子分割
    2. 计算相邻句子的embedding
    3. 计算相似度
    4. 在相似度低的地方分割
    5. 确保chunk大小合适
    """

    def __init__(self, chunk_size: int = 500, embedding_model=None):
        """初始化语义分块器"""
        self.chunk_size = chunk_size
        self.embedding_model = embedding_model

        logger.warning(
            "semantic_splitter_not_implemented",
            message="SemanticTextSplitter is a placeholder for future implementation"
        )

    def split_text(self, text: str) -> List[str]:
        """分割文本（占位）"""
        raise NotImplementedError(
            "SemanticTextSplitter will be implemented in Stage 2.2"
        )

