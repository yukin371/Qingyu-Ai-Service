"""
TextSplitter 测试

测试文本分块器的核心功能

Author: Qingyu AI Team
Date: 2025-10-28
"""

import pytest
from src.rag.text_splitter import RecursiveCharacterTextSplitter, TextChunk


class TestRecursiveCharacterTextSplitter:
    """递归字符分块器测试"""

    def test_basic_split(self):
        """测试基础分块"""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=20,
            chunk_overlap=5
        )

        text = "这是第一段。这是第二段。这是第三段。"
        chunks = splitter.split_text(text)

        assert len(chunks) > 0
        assert all(len(chunk) <= 30 for chunk in chunks)  # 考虑overlap

    def test_chinese_text_split(self):
        """测试中文文本分块"""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=100,
            chunk_overlap=20
        )

        text = "这是一个很长的中文段落。" * 10
        chunks = splitter.split_text(text)

        assert len(chunks) > 1
        # 验证有重叠
        if len(chunks) >= 2:
            # 第二个chunk应该包含第一个chunk的结尾部分
            assert chunks[1] != chunks[0]

    def test_paragraph_split(self):
        """测试段落分割"""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=50,
            chunk_overlap=10
        )

        text = "第一段内容。\n\n第二段内容。\n\n第三段内容。"
        chunks = splitter.split_text(text)

        assert len(chunks) >= 2

    def test_empty_text(self):
        """测试空文本"""
        splitter = RecursiveCharacterTextSplitter()

        chunks = splitter.split_text("")
        assert chunks == []

        chunks = splitter.split_text("   ")
        assert chunks == []

    def test_create_chunks_with_metadata(self):
        """测试创建带元数据的chunk"""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=30,
            chunk_overlap=5
        )

        text = "这是第一段。这是第二段。这是第三段。"
        metadata = {"source": "test", "author": "tester"}

        chunks = splitter.create_chunks(text, metadata)

        assert len(chunks) > 0
        assert all(isinstance(chunk, TextChunk) for chunk in chunks)
        assert all(chunk.metadata == metadata for chunk in chunks)
        assert all(chunk.chunk_id >= 0 for chunk in chunks)

    def test_split_documents(self):
        """测试批量文档分割"""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=50,
            chunk_overlap=10
        )

        documents = [
            {
                'id': 'doc1',
                'text': '这是第一个文档的内容。' * 5,
                'metadata': {'source': 'file1'}
            },
            {
                'id': 'doc2',
                'content': '这是第二个文档的内容。' * 5,
                'metadata': {'source': 'file2'}
            }
        ]

        chunks = splitter.split_documents(documents)

        assert len(chunks) > 0
        # 验证元数据保留
        assert all('metadata' in chunk for chunk in chunks)
        assert all('document_id' in chunk['metadata'] for chunk in chunks)
        # 验证chunk_id
        assert all('chunk_id' in chunk for chunk in chunks)

    def test_long_text_split(self):
        """测试长文本分割"""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=100,
            chunk_overlap=20
        )

        # 创建一个很长的文本
        long_text = "这是一个句子。" * 100
        chunks = splitter.split_text(long_text)

        assert len(chunks) > 5
        # 验证每个chunk大小
        for chunk in chunks:
            assert len(chunk) <= 120  # chunk_size + 考虑分隔符

    def test_custom_separators(self):
        """测试自定义分隔符"""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=50,
            chunk_overlap=10,
            separators=["\n\n", "|", " "]
        )

        text = "段落一内容|段落二内容|段落三内容"
        chunks = splitter.split_text(text)

        assert len(chunks) >= 1


# 性能测试
@pytest.mark.performance
def test_large_document_performance():
    """测试大文档分块性能"""
    import time

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    # 创建大文档
    large_text = "这是一个很长的段落。" * 1000

    start_time = time.time()
    chunks = splitter.split_text(large_text)
    duration = time.time() - start_time

    assert len(chunks) > 0
    assert duration < 5.0  # 应该在5秒内完成

    print(f"\n性能测试：{len(large_text)}字符 → {len(chunks)}个chunk，耗时{duration:.2f}秒")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

