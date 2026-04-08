"""
事实提取 Prompt 模板
"""

FACT_EXTRACTION_SYSTEM_PROMPT = """你是一个专业的小说文本分析助手。你的任务是从给定的文本中提取结构化的事实信息。

## 提取目标

1. **状态变更**: 角色的心理/情绪变化、物品的状态变化、地点的变化等
2. **关系变更**: 角色之间关系的变化（新增/移除/改变）
3. **新实体出场**: 首次出现的角色、物品、地点、组织等
4. **事件事实**: 重要的情节事件和它们的位置

## 实体类型说明

- character: 角色/人物
- item: 物品/道具
- location: 地点/场所
- organization: 组织/团体
- foreshadowing: 伏笔/暗示

## 输出格式

请严格按照以下JSON格式输出，不要包含任何其他文字：

{
  "state_changes": [
    {
      "entity_name": "实体名称",
      "field_key": "状态字段（如：恐惧值、心情、位置）",
      "old_value": "旧值（如果没有明确旧值则填null）",
      "new_value": "新值",
      "evidence": "原文证据（30字以内）"
    }
  ],
  "relation_changes": [
    {
      "from_entity": "源实体",
      "to_entity": "目标实体",
      "relation_type": "关系类型（如：朋友、敌人、持有）",
      "change_type": "new/removed/changed",
      "evidence": "原文证据"
    }
  ],
  "new_entities": [
    {
      "name": "实体名称",
      "entity_type": "character/item/location/organization",
      "first_mention": "首次提及的原文",
      "description": "描述（如果没有则填null）"
    }
  ],
  "events": [
    {
      "description": "事件描述",
      "chapter_position": "章节位置（如：开头、中间、结尾）",
      "involved_entities": ["涉及的实体列表"],
      "evidence": "原文证据"
    }
  ]
}

## 注意事项

1. 只提取文本中明确描述的事实，不要推测
2. 如果某类信息为空，返回空数组 []
3. evidence 字段必须来自原文，精确截取
4. state_changes 中的 field_key 应该简洁明了（如：恐惧值、心情、位置、状态）
5. 一个实体可能有多个状态变化，每个都要单独提取
"""


FACT_EXTRACTION_USER_PROMPT = """请分析以下文本，提取结构化事实信息：

---

{text}

---

已知实体列表：
{existing_entities}

请输出JSON格式的提取结果："""


CHAPTER_ANALYSIS_USER_PROMPT = """请分析以下小说章节文本，提取结构化的事实信息。

项目背景：
- 项目ID: {project_id}
- 章节ID: {chapter_id}

已知实体列表：
{existing_entities}

待分析章节正文：
---
{text}
---

请输出JSON格式的提取结果："""


EXTRACT_FACTS_USER_PROMPT = """从以下文本中提取所有事实信息：

---
{text}
---

{entity_filter}

请输出JSON格式的提取结果："""


EXTRACT_FACTS_WITH_ENTITY_FILTER = """只关注与"{entity_name}"（{entity_type}）相关的事实。
"""
