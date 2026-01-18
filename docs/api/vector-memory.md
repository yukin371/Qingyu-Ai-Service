# Vector Memory (向量记忆)

## 概述

VectorMemory 是基于 Milvus 向量数据库的语义记忆系统，支持向量检索和相似度搜索。它能够存储和检索语义化的记忆，使 AI 助手能够根据语义相似性找到相关的历史信息。

## 核心功能

### 1. 添加记忆 (Add Memory)

```python
from src.memory.semantic.vector_memory import VectorMemory

# 创建 VectorMemory 实例
memory = VectorMemory(
    milvus_client=milvus_client,
    embedding_manager=embedding_manager
)

# 添加记忆（自动生成 embedding）
memory_id = await memory.add_memory(
    content="用户喜欢阅读科幻小说",
    metadata={"category": "preference", "user_id": "user123"}
)

# 添加记忆（使用预计算的 embedding）
memory_id = await memory.add_memory(
    content="用户正在学习 Python 编程",
    embedding=[0.1, 0.2, ...],  # 1024 维向量
    metadata={"category": "activity", "user_id": "user123"}
)
```

### 2. 相似度搜索 (Similarity Search)

```python
# 使用文本查询
results = await memory.search(
    query_text="用户有哪些兴趣爱好？",
    top_k=5
)

# 使用向量查询
results = await memory.search(
    query_embedding=embedding_vector,
    top_k=10
)

# 带元数据过滤的搜索
results = await memory.search(
    query_text="用户喜欢什么？",
    top_k=5,
    filters={"category": "preference"},
    min_score=0.7  # 最低相似度分数
)

# 处理搜索结果
for result in results:
    print(f"ID: {result.id}")
    print(f"内容: {result.content}")
    print(f"相似度: {result.score:.3f}")
    print(f"元数据: {result.metadata}")
```

### 3. 更新记忆 (Update Memory)

```python
# 更新记忆内容
await memory.update_memory(
    memory_id="mem123",
    content="用户喜欢阅读科幻小说和历史书籍"
)

# 仅更新元数据
await memory.update_memory(
    memory_id="mem123",
    metadata={"category": "preference", "updated": "2025-01-16"}
)
```

### 4. 删除记忆 (Delete Memory)

```python
await memory.delete_memory(memory_id="mem123")
```

### 5. 批量操作 (Batch Operations)

```python
# 批量添加记忆
memories = [
    {"content": "用户有一只叫 Luna 的猫", "metadata": {"category": "personal"}},
    {"content": "用户住在北京", "metadata": {"category": "location"}},
    {"content": "用户是一名软件工程师", "metadata": {"category": "work"}},
]
memory_ids = await memory.add_batch_memories(memories)
```

### 6. 健康检查和统计

```python
# 健康检查
health = await memory.health_check()
print(f"状态: {health['status']}")
print(f"Milvus: {health['milvus']}")
print(f"Embedding: {health['embedding']}")

# 获取统计信息
stats = await memory.get_memory_stats()
print(f"集合名称: {stats['collection_name']}")
print(f"向量维度: {stats['dimension']}")
```

## API 参考

### VectorMemory 类

#### 初始化

```python
VectorMemory(
    milvus_client: MilvusClient,
    embedding_manager: EmbeddingManager,
    collection_name: str = "semantic_memory",
    dimension: Optional[int] = None
)
```

#### 方法

##### add_memory

添加单个记忆。

```python
async def add_memory(
    self,
    content: str,
    embedding: Optional[List[float]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str
```

**参数:**
- `content`: 记忆内容文本
- `embedding`: 预计算的嵌入向量（可选，自动生成）
- `metadata`: 元数据字典（可选）

**返回:** 记忆 ID

**异常:**
- `MemoryValidationError`: 内容为空
- `MemoryOperationError`: 操作失败

##### search

相似度搜索。

```python
async def search(
    self,
    query_embedding: Optional[List[float]] = None,
    query_text: Optional[str] = None,
    top_k: int = 10,
    filters: Optional[Dict[str, Any]] = None,
    min_score: float = 0.0
) -> List[MemorySearchResult]
```

**参数:**
- `query_embedding`: 查询向量（可选）
- `query_text`: 查询文本（可选，自动嵌入）
- `top_k`: 返回的最大结果数
- `filters`: 元数据过滤条件
- `min_score`: 最低相似度分数阈值

**返回:** MemorySearchResult 列表

##### delete_memory

删除记忆。

```python
async def delete_memory(self, memory_id: str) -> None
```

##### update_memory

更新记忆。

```python
async def update_memory(
    self,
    memory_id: str,
    content: Optional[str] = None,
    embedding: Optional[List[float]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None
```

##### add_batch_memories

批量添加记忆。

```python
async def add_batch_memories(
    self,
    memories: List[Dict[str, Any]]
) -> List[str]
```

##### health_check

健康检查。

```python
async def health_check(self) -> Dict[str, Any]
```

##### get_memory_stats

获取统计信息。

```python
async def get_memory_stats(self) -> Dict[str, Any]
```

### MemorySearchResult 数据类

搜索结果数据结构。

```python
@dataclass
class MemorySearchResult:
    id: str                              # 唯一标识
    content: str                          # 记忆内容
    score: float                          # 相似度分数 (0-1)
    metadata: Dict[str, Any]              # 元数据
    created_at: Optional[datetime]        # 创建时间

    def to_dict(self) -> Dict[str, Any]   # 转换为字典
```

## 使用场景

### 1. 用户偏好记忆

```python
# 记住用户偏好
await memory.add_memory(
    content="用户喜欢简洁的回复，不喜欢冗长的解释",
    metadata={"type": "preference", "user_id": "user123"}
)

# 检索相关偏好
results = await memory.search(
    query_text="如何回复用户？",
    filters={"user_id": "user123", "type": "preference"}
)
```

### 2. 对话历史语义检索

```python
# 存储重要对话内容
await memory.add_memory(
    content="用户询问了关于 Python 装饰器的问题",
    metadata={"type": "conversation", "topic": "python"}
)

# 后续对话中检索相关信息
results = await memory.search(
    query_text="用户之前问过什么问题？",
    filters={"topic": "python"}
)
```

### 3. 知识积累

```python
# 积累领域知识
await memory.add_memory(
    content="Python 装饰器是一种用于修改函数行为的语法糖",
    metadata={"type": "knowledge", "domain": "programming"}
)

# 检索相关知识
results = await memory.search(
    query_text="什么是装饰器？",
    filters={"domain": "programming"}
)
```

## 测试

运行测试：

```bash
# 运行所有测试
uv run pytest tests/memory/semantic/test_vector_memory.py -v

# 运行特定测试
uv run pytest tests/memory/semantic/test_vector_memory.py::TestVectorMemory::test_add_memory -v

# 运行集成测试（需要实际 Milvus 实例）
uv run pytest tests/memory/semantic/test_vector_memory.py -m integration
```

## 注意事项

1. **Milvus 连接**: 确保 Milvus 服务正在运行并可访问
2. **向量维度**: 确保嵌入向量维度与配置一致（默认 1024）
3. **元数据过滤**: 过滤条件支持的字段取决于 Milvus collection schema
4. **更新操作**: Milvus 不支持直接更新，当前实现是删除后重新插入
5. **性能**: 批量操作比单个操作更高效

## 示例

完整示例请参考 `examples/vector_memory_demo.py`。

## 相关文档

- [RAG Pipeline Documentation](../rag/README.md)
- [Milvus Client Documentation](../rag/milvus_client.md)
- [Embedding Manager Documentation](../rag/embedding_manager.md)
