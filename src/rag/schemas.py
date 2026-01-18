"""
RAG系统数据结构定义

定义RAG系统中使用的核心数据结构

Author: Qingyu AI Team
Date: 2025-10-28
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class RetrievalResult:
    """
    检索结果

    表示单个检索到的文档片段
    """
    id: str                              # 唯一标识
    text: str                            # 文本内容
    score: float                         # 相关性分数
    source: str                          # 来源（project/chapter/document等）
    document_id: str                     # 文档ID
    chunk_id: int                        # chunk序号
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据

    def __post_init__(self):
        """验证数据"""
        if self.score < 0 or self.score > 1:
            # 归一化分数到0-1
            if self.score > 1:
                self.score = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'text': self.text,
            'score': self.score,
            'source': self.source,
            'document_id': self.document_id,
            'chunk_id': self.chunk_id,
            'metadata': self.metadata
        }

    def get_citation_text(self, max_length: int = 100) -> str:
        """获取引用文本片段"""
        if len(self.text) <= max_length:
            return self.text
        return self.text[:max_length] + "..."


@dataclass
class RAGContext:
    """
    RAG上下文

    包含完整的RAG流程结果，用于生成回复
    """
    query: str                           # 用户查询
    context: str                         # 构建的上下文文本
    sources: List[RetrievalResult]       # 参考资料列表
    total_tokens: int                    # 总token数
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据

    # 可选字段
    retrieved_count: int = 0             # 检索到的文档数
    reranked: bool = False               # 是否经过重排序
    hybrid_search: bool = False          # 是否使用混合检索
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'query': self.query,
            'context': self.context,
            'sources': [s.to_dict() for s in self.sources],
            'total_tokens': self.total_tokens,
            'retrieved_count': self.retrieved_count,
            'reranked': self.reranked,
            'hybrid_search': self.hybrid_search,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat()
        }

    def get_source_ids(self) -> List[str]:
        """获取所有来源ID"""
        return [source.document_id for source in self.sources]

    def get_citations(self) -> str:
        """获取引用列表文本"""
        citations = []
        for i, source in enumerate(self.sources, 1):
            citation = f"[{i}] {source.source} - {source.get_citation_text()}"
            citations.append(citation)
        return "\n".join(citations)


@dataclass
class Citation:
    """
    引用信息

    表示回复中引用的具体来源
    """
    index: int                           # 引用序号 [1], [2]...
    source: str                          # 来源描述
    document_id: str                     # 文档ID
    chunk_id: int                        # chunk序号
    text_snippet: str                    # 文本片段
    score: float = 0.0                   # 相关性分数

    def format(self) -> str:
        """格式化引用"""
        return f"[{self.index}] {self.source}: {self.text_snippet}"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'index': self.index,
            'source': self.source,
            'document_id': self.document_id,
            'chunk_id': self.chunk_id,
            'text_snippet': self.text_snippet,
            'score': self.score
        }


@dataclass
class RerankerResult:
    """
    重排序结果

    包含重排序后的文档及其新分数
    """
    result: RetrievalResult              # 检索结果
    rerank_score: float                  # 重排序分数
    original_rank: int                   # 原始排名
    new_rank: int                        # 新排名

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'result': self.result.to_dict(),
            'rerank_score': self.rerank_score,
            'original_rank': self.original_rank,
            'new_rank': self.new_rank
        }


@dataclass
class HybridSearchResult:
    """
    混合检索结果

    包含向量检索和BM25检索的融合结果
    """
    result: RetrievalResult              # 检索结果
    vector_score: float                  # 向量检索分数
    bm25_score: float                    # BM25分数
    final_score: float                   # 融合后分数
    fusion_method: str                   # 融合方法（rrf/weighted）

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'result': self.result.to_dict(),
            'vector_score': self.vector_score,
            'bm25_score': self.bm25_score,
            'final_score': self.final_score,
            'fusion_method': self.fusion_method
        }


# 类型别名
ResultList = List[RetrievalResult]
CitationList = List[Citation]

