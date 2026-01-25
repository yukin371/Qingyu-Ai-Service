# Qingyu AI Service - HTTP API 测试指南

本文档提供HTTP REST API的测试指南。

## 快速开始

### 1. 启动服务

```bash
cd Qingyu-Ai-Service
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8001
```

服务将在 http://localhost:8001 启动。

### 2. 查看API文档

- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

## API端点测试

### 健康检查

```bash
curl http://localhost:8001/api/v1/health
```

**预期响应**:
```json
{
  "status": "healthy",
  "service": "Qingyu AI Service",
  "version": "0.1.0"
}
```

---

### 聊天API

#### 1. 发送聊天消息

```bash
curl -X POST http://localhost:8001/api/v1/ai/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "你好，请介绍一下自己"}
    ],
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 2000
  }'
```

**预期响应**:
```json
{
  "message": "这是对'你好，请介绍一下自己'的模拟回复...",
  "usage": {
    "prompt_tokens": 50,
    "completion_tokens": 30,
    "total_tokens": 80
  },
  "model": "gpt-4",
  "quota_remaining": 9950
}
```

---

### 写作API

#### 1. 续写文本

```bash
curl -X POST http://localhost:8001/api/v1/ai/writing/continue \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj123",
    "current_text": "这是一个故事的开头，主人公名叫李明，他住在一个小镇上。",
    "continue_length": 200,
    "context": {
      "genre": "都市",
      "characters": ["李明", "王芳"]
    },
    "model": "gpt-4",
    "temperature": 0.7
  }'
```

**预期响应**:
```json
{
  "generated_text": "这是续写的内容...",
  "usage": {
    "prompt_tokens": 100,
    "completion_tokens": 200,
    "total_tokens": 300
  },
  "quota_remaining": 9750,
  "model": "gpt-4"
}
```

#### 2. 润色文本

```bash
curl -X POST http://localhost:8001/api/v1/ai/writing/polish \
  -H "Content-Type: application/json" \
  -d '{
    "text": "这个故事很好看，我很喜欢。",
    "style": "文学",
    "focus_areas": ["grammar", "vocabulary"],
    "model": "gpt-4"
  }'
```

**预期响应**:
```json
{
  "generated_text": "这是润色后的文本...",
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 40,
    "total_tokens": 60
  },
  "quota_remaining": 9690,
  "model": "gpt-4"
}
```

#### 3. 扩展文本

```bash
curl -X POST http://localhost:8001/api/v1/ai/writing/expand \
  -H "Content-Type: application/json" \
  -d '{
    "text": "春天来了，花儿开了。",
    "expand_ratio": 2.0,
    "direction": "详细描述",
    "model": "gpt-4"
  }'
```

**预期响应**:
```json
{
  "generated_text": "这是扩展后的文本...",
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 30,
    "total_tokens": 45
  },
  "quota_remaining": 9645,
  "model": "gpt-4"
}
```

---

### 配额API

#### 1. 查询配额

```bash
curl http://localhost:8001/api/v1/quota/user123
```

**预期响应**:
```json
{
  "user_id": "user123",
  "quota_type": "free",
  "total_quota": 10000,
  "used_quota": 0,
  "remaining_quota": 10000,
  "reset_at": "2024-02-18T12:00:00.000000"
}
```

#### 2. 消费配额

```bash
curl -X POST http://localhost:8001/api/v1/quota/user123/consume \
  -H "Content-Type: application/json" \
  -d '{
    "tokens": 100,
    "operation": "chat"
  }'
```

**预期响应**:
```json
{
  "success": true,
  "remaining_quota": 9900,
  "message": "配额扣除成功：消费 100 tokens"
}
```

#### 3. 配额统计

```bash
curl http://localhost:8001/api/v1/quota/statistics/user123
```

**预期响应**:
```json
{
  "user_id": "user123",
  "total_usage": 100,
  "remaining_quota": 9900,
  "usage_percentage": 1.0,
  "operations": {
    "chat": 50,
    "writing": 50
  }
}
```

---

## 使用Postman测试

### 导入集合

创建Postman集合并添加以下请求：

1. **健康检查**
   - Method: GET
   - URL: `{{baseUrl}}/api/v1/health`

2. **聊天**
   - Method: POST
   - URL: `{{baseUrl}}/api/v1/ai/chat`
   - Body: raw JSON

3. **续写**
   - Method: POST
   - URL: `{{baseUrl}}/api/v1/ai/writing/continue`
   - Body: raw JSON

4. **润色**
   - Method: POST
   - URL: `{{baseUrl}}/api/v1/ai/writing/polish`
   - Body: raw JSON

5. **扩展**
   - Method: POST
   - URL: `{{baseUrl}}/api/v1/ai/writing/expand`
   - Body: raw JSON

6. **查询配额**
   - Method: GET
   - URL: `{{baseUrl}}/api/v1/quota/{{userId}}`

7. **消费配额**
   - Method: POST
   - URL: `{{baseUrl}}/api/v1/quota/{{userId}}/consume`
   - Body: raw JSON

### 环境变量

在Postman中设置以下环境变量：

- `baseUrl`: `http://localhost:8001`
- `userId`: `test-user-123`

---

## 使用Python测试

创建测试文件 `test_api.py`:

```python
import requests
import json

BASE_URL = "http://localhost:8001"

def test_health():
    """测试健康检查"""
    response = requests.get(f"{BASE_URL}/api/v1/health")
    print(f"Health Check: {response.json()}")

def test_chat():
    """测试聊天"""
    payload = {
        "messages": [
            {"role": "user", "content": "你好"}
        ],
        "model": "gpt-4"
    }
    response = requests.post(f"{BASE_URL}/api/v1/ai/chat", json=payload)
    print(f"Chat: {response.json()}")

def test_continue_writing():
    """测试续写"""
    payload = {
        "project_id": "test-project",
        "current_text": "这是一个测试。",
        "continue_length": 100
    }
    response = requests.post(f"{BASE_URL}/api/v1/ai/writing/continue", json=payload)
    print(f"Continue Writing: {response.json()}")

def test_quota():
    """测试配额"""
    user_id = "test-user"
    response = requests.get(f"{BASE_URL}/api/v1/quota/{user_id}")
    print(f"Get Quota: {response.json()}")

if __name__ == "__main__":
    print("=== 测试API ===\n")
    test_health()
    test_chat()
    test_continue_writing()
    test_quota()
```

运行测试：

```bash
python test_api.py
```

---

## 当前限制

这些API端点目前使用模拟数据，实际实现需要：

1. **集成AgentService**: 将AI调用连接到实际的Agent服务
2. **配额持久化**: 使用数据库存储配额数据（目前是内存存储）
3. **JWT认证**: 添加用户认证中间件
4. **错误处理**: 完善错误处理和日志记录
5. **性能优化**: 添加缓存、连接池等优化
6. **流式输出**: 实现流式响应支持

---

## 下一步

1. ✅ HTTP API基础框架完成
2. ⏳ 集成实际的AgentService
3. ⏳ 添加JWT认证
4. ⏳ 实现配额持久化
5. ⏳ 编写完整的单元测试
6. ⏳ 性能测试和优化
7. ⏳ 准备生产部署配置

---

## 故障排查

### 服务无法启动

```bash
# 检查端口是否被占用
netstat -ano | findstr :8001  # Windows
lsof -i :8001                  # Linux/Mac

# 更换端口
python -m uvicorn src.main:app --port 8002
```

### 导入错误

```bash
# 确保在项目根目录
cd qingyu-ai-service

# 安装依赖
pip install -r requirements.txt
```

### API返回500错误

查看服务日志，检查：
- AgentService是否正确初始化
- 数据库连接是否正常
- 配额服务是否可用

---

## 相关文档

- [移除计划](../../docs/architecture/ai-service-removal-plan.md)
- [检查清单](../../docs/architecture/ai-service-removal-checklist.md)
- [后端HTTP客户端指南](../../scripts/ai-service/03-backend-http-client-guide.md)
