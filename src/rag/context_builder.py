"""
上下文构建器

智能构建RAG上下文，包括：
- Token计数
- 智能截断
- 引用标注
- 模板化

Author: Qingyu AI Team
Date: 2025-10-28
"""

from typing import List, Optional
import re

from src.rag.schemas import RetrievalResult
from src.core.logger import logger


class ContextBuilder:
    """
    上下文构建器

    负责将检索结果组装成适合LLM的上下文
    """

    def __init__(self, model: str = "gpt-3.5-turbo"):
        """
        初始化上下文构建器

        Args:
            model: LLM模型名称（用于token计数）
        """
        self.model = model

        # 尝试导入tiktoken（可选）
        try:
            import tiktoken
            self.encoding = tiktoken.encoding_for_model(model)
            self.use_tiktoken = True
            logger.info("context_builder_initialized", model=model, encoding="tiktoken")
        except Exception as e:
            self.encoding = None
            self.use_tiktoken = False
            logger.warning(
                "tiktoken_not_available",
                model=model,
                error=str(e),
                fallback="character_estimation"
            )

    def count_tokens(self, text: str) -> int:
        """
        计算token数量

        Args:
            text: 文本

        Returns:
            token数量
        """
        if self.use_tiktoken and self.encoding:
            return len(self.encoding.encode(text))
        else:
            # 简单估算：中文约1.5字符/token，英文约4字符/token
            # 这里采用保守估算：1字符=1token
            return len(text)

    def build_context(
        self,
        query: str,
        results: List[RetrievalResult],
        max_tokens: int = 2000,
        template: Optional[str] = None
    ) -> str:
        """
        构建上下文

        Args:
            query: 查询文本
            results: 检索结果列表
            max_tokens: 最大token数
            template: 自定义模板

        Returns:
            构建的上下文文本
        """
        if not results:
            return f"没有找到与「{query}」相关的资料。"

        # 使用自定义模板或默认模板
        if template:
            return self._build_with_template(query, results, max_tokens, template)
        else:
            return self._build_default(query, results, max_tokens)

    def _build_default(
        self,
        query: str,
        results: List[RetrievalResult],
        max_tokens: int
    ) -> str:
        """
        使用默认模板构建上下文

        Args:
            query: 查询文本
            results: 检索结果列表
            max_tokens: 最大token数

        Returns:
            上下文文本
        """
        # 固定部分
        header = "基于以下参考资料回答问题：\n\n"
        footer = f"\n问题：{query}\n\n请基于上述资料回答，并在回答中标注引用来源（如[1]、[2]）。"

        # 计算固定部分token
        fixed_tokens = self.count_tokens(header + footer)
        available_tokens = max_tokens - fixed_tokens

        if available_tokens <= 0:
            logger.warning(
                "insufficient_token_budget",
                max_tokens=max_tokens,
                fixed_tokens=fixed_tokens
            )
            return header + footer

        # 逐个添加资料，确保不超过token限制
        context_parts = [header]
        used_tokens = 0
        included_count = 0

        for i, result in enumerate(results, 1):
            # 格式化资料
            source_text = self._format_source(i, result)
            source_tokens = self.count_tokens(source_text)

            # 检查是否超过限制
            if used_tokens + source_tokens > available_tokens:
                # 尝试截断最后一个资料
                if included_count == 0:
                    # 至少包含一个资料的截断版本
                    truncated = self._truncate_source(
                        i, result, available_tokens - used_tokens
                    )
                    context_parts.append(truncated)
                    included_count += 1
                break

            context_parts.append(source_text)
            used_tokens += source_tokens
            included_count += 1

        context_parts.append(footer)

        logger.info(
            "context_built",
            query=query[:50],
            included_sources=included_count,
            total_sources=len(results),
            estimated_tokens=fixed_tokens + used_tokens
        )

        return "".join(context_parts)

    def _build_with_template(
        self,
        query: str,
        results: List[RetrievalResult],
        max_tokens: int,
        template: str
    ) -> str:
        """
        使用自定义模板构建上下文

        模板支持的占位符：
        - {query}: 查询文本
        - {sources}: 资料列表
        - {source_count}: 资料数量

        Args:
            query: 查询文本
            results: 检索结果列表
            max_tokens: 最大token数
            template: 模板字符串

        Returns:
            上下文文本
        """
        # 构建资料列表
        sources_text = []
        for i, result in enumerate(results, 1):
            source = self._format_source(i, result)
            sources_text.append(source)

        # 填充模板
        context = template.format(
            query=query,
            sources="\n".join(sources_text),
            source_count=len(results)
        )

        # 检查token限制
        context_tokens = self.count_tokens(context)
        if context_tokens > max_tokens:
            # 截断资料
            logger.warning(
                "template_context_too_long",
                estimated_tokens=context_tokens,
                max_tokens=max_tokens
            )
            # 简单截断策略：逐个移除资料直到满足限制
            while sources_text and self.count_tokens(context) > max_tokens:
                sources_text.pop()
                context = template.format(
                    query=query,
                    sources="\n".join(sources_text),
                    source_count=len(sources_text)
                )

        return context

    def _format_source(self, index: int, result: RetrievalResult) -> str:
        """
        格式化单个资料

        Args:
            index: 资料序号
            result: 检索结果

        Returns:
            格式化的资料文本
        """
        return (
            f"[资料{index}] 来源：{result.source} "
            f"(相关度：{result.score:.2f})\n"
            f"{result.text}\n"
        )

    def _truncate_source(
        self,
        index: int,
        result: RetrievalResult,
        max_tokens: int
    ) -> str:
        """
        截断资料以适应token限制

        Args:
            index: 资料序号
            result: 检索结果
            max_tokens: 最大token数

        Returns:
            截断后的资料文本
        """
        # 资料头部
        header = f"[资料{index}] 来源：{result.source}\n"
        header_tokens = self.count_tokens(header)

        # 可用于文本的token
        available_tokens = max_tokens - header_tokens - 10  # 留10个token给省略号

        if available_tokens <= 0:
            return header + "...\n"

        # 截断文本
        text = result.text
        while self.count_tokens(text) > available_tokens and len(text) > 0:
            # 按句子截断（尝试在句号处截断）
            sentences = re.split(r'([。！？.!?])', text)
            if len(sentences) > 1:
                text = "".join(sentences[:-2])  # 移除最后一个句子
            else:
                # 按字符截断
                text = text[:int(len(text) * 0.8)]

        return header + text + "...\n"

    def add_citations(
        self,
        context: str,
        results: List[RetrievalResult]
    ) -> str:
        """
        添加引用标注

        在上下文末尾添加引用列表

        Args:
            context: 上下文文本
            results: 检索结果列表

        Returns:
            添加引用后的上下文
        """
        if not results:
            return context

        citations = ["\n\n---\n参考资料：\n"]

        for i, result in enumerate(results, 1):
            citation = (
                f"[{i}] {result.source} - "
                f"{result.get_citation_text(max_length=100)}\n"
            )
            citations.append(citation)

        return context + "".join(citations)

