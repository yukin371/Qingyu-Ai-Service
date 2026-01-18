# Phase3 快速开始指南

## 已完成功能

✅ **3个专业Agent**:
- OutlineAgent - 大纲生成
- CharacterAgent - 角色设计  
- PlotAgent - 情节安排

✅ **LangGraph v2.0工作流**:
- 完整的Agent协作流程
- 智能反思循环
- 动态路由和修正

✅ **56个测试用例**:
- 单元测试: 39个
- 集成测试: 17个

---

## 快速测试

### 1. 运行单个Agent测试

```bash
cd python_ai_service

# 测试OutlineAgent
pytest tests/test_outline_agent.py -v

# 测试CharacterAgent  
pytest tests/test_character_agent.py -v

# 测试PlotAgent
pytest tests/test_plot_agent.py -v
```

### 2. 运行集成测试

```bash
# 工作流端到端测试
pytest tests/integration/test_agent_workflow_e2e.py -v

# 反思循环测试
pytest tests/integration/test_reflection_loop_e2e.py -v
```

### 3. 运行所有测试

```bash
pytest tests/test_outline_agent.py tests/test_character_agent.py tests/test_plot_agent.py tests/integration/ -v
```

---

## 使用示例

### 基础使用

```python
from agents.specialized import OutlineAgent, CharacterAgent, PlotAgent
from agents.states.pipeline_state_v2 import create_initial_pipeline_state_v2

# 创建初始状态
state = create_initial_pipeline_state_v2(
    task="创作一个关于修仙少年的玄幻故事",
    user_id="user_001",
    project_id="proj_001"
)

# 执行OutlineAgent
outline_agent = OutlineAgent()
state = await outline_agent.execute(state)

# 执行CharacterAgent
character_agent = CharacterAgent()
state = await character_agent.execute(state)

# 执行PlotAgent
plot_agent = PlotAgent()
state = await plot_agent.execute(state)

# 查看结果
print(f"大纲: {state['agent_outputs']['outline_agent']}")
print(f"角色: {state['agent_outputs']['character_agent']}")
print(f"情节: {state['agent_outputs']['plot_agent']}")
```

### 使用完整工作流

```python
from agents.workflows.agent_workflow_v2 import execute_agent_workflow_v2

# 执行完整工作流（包含反思循环）
final_state = await execute_agent_workflow_v2(
    task="创作一个科幻故事：未来世界的AI革命",
    user_id="user_001",
    project_id="proj_001",
    max_reflections=3,  # 最多3次反思修正
    enable_human_review=True  # 启用人工审核降级
)

# 检查结果
if final_state["review_passed"]:
    print("✅ 创作完成！")
    print(f"迭代次数: {final_state['reflection_count']}")
    print(f"大纲: {final_state['agent_outputs']['outline_agent']['title']}")
    print(f"角色数: {len(final_state['characters'])}")
    print(f"事件数: {len(final_state['timeline_events'])}")
else:
    print("⚠️ 需要人工审核")
    print(f"质量分数: {final_state['review_report']['quality_score']}")
```

---

## 配置说明

### 环境变量

确保以下环境变量已设置：

```bash
# Gemini API Key
GOOGLE_API_KEY=your_api_key_here

# LLM配置（可选）
DEFAULT_LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-2.0-flash-exp
GEMINI_TRANSPORT=rest
```

### Agent参数

每个Agent支持以下参数：

```python
OutlineAgent(
    llm_provider="gemini",  # LLM提供商
    llm_model=None,         # 模型名称（None使用默认）
    temperature=0.7         # 温度参数
)
```

---

## 输出格式

### OutlineAgent输出

```json
{
  "title": "故事标题",
  "genre": "类型",
  "chapters": [
    {
      "chapter_id": 1,
      "title": "章节标题",
      "summary": "概要",
      "key_events": ["事件1", "事件2"],
      "characters_involved": ["角色1"]
    }
  ]
}
```

### CharacterAgent输出

```json
{
  "characters": [
    {
      "name": "角色名",
      "role_type": "protagonist",
      "personality": {
        "traits": ["勇敢"],
        "strengths": ["智慧"],
        "weaknesses": ["冲动"]
      },
      "relationships": [
        {
          "character": "角色B",
          "relation_type": "rival"
        }
      ]
    }
  ]
}
```

### PlotAgent输出

```json
{
  "timeline_events": [
    {
      "event_id": "evt_001",
      "title": "事件标题",
      "description": "详细描述",
      "participants": ["角色A"],
      "impact": {
        "on_plot": "影响主线",
        "on_characters": {"角色A": "成长"}
      }
    }
  ],
  "plot_threads": [
    {
      "thread_id": "main",
      "title": "主线",
      "events": ["evt_001"]
    }
  ]
}
```

---

## 故障排除

### 常见问题

**Q: ImportError: cannot import name 'LLMFactory'**
```bash
# 检查Python路径
export PYTHONPATH=$PYTHONPATH:/path/to/python_ai_service/src
```

**Q: LLM调用失败**
```bash
# 检查API Key
echo $GOOGLE_API_KEY

# 检查网络连接
# 确保可以访问Gemini API
```

**Q: JSON解析失败**
```
# Agent会自动处理JSON解析失败
# 返回默认输出，检查日志获取详情
```

---

## 下一步工作

### 优化建议

1. **Prompt优化**
   - 收集实际生成案例
   - A/B测试不同版本
   - 添加Few-shot示例

2. **性能优化**
   - 并行化Agent执行
   - 缓存LLM响应
   - 减少Token消耗

3. **功能扩展**
   - 添加PlannerAgent
   - 添加WorldviewAgent
   - 添加StyleAgent

### 集成计划

1. **gRPC服务集成**
   - 实现gRPC接口
   - 连接Go后端

2. **前端集成**
   - API接口设计
   - 实时进度反馈

3. **生产部署**
   - Docker镜像
   - 监控和日志
   - 性能调优

---

## 文档索引

- **实现报告**: `doc/implementation/00进度指导/Phase3_专业Agent和工作流实现报告_2025-10-30.md`
- **架构设计**: `doc/design/ai/phase3/05.A2A创作流水线Agent设计_v2.0_智能协作生态.md`
- **测试指南**: `tests/README.md`

---

**更新时间**: 2025-10-30  
**状态**: ✅ 核心功能完成

