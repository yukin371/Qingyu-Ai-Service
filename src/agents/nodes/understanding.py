"""Understanding Node - 理解任务节点

分析用户任务，提取关键要素，制定执行计划
"""

import json
from typing import Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.agents.states.creative_state import CreativeAgentState
from src.core.config import get_settings
from src.core.logger import get_logger

logger = get_logger(__name__)


async def understand_task_node(state: CreativeAgentState) -> Dict:
    """理解任务节点

    职责：
    1. 分析用户任务
    2. 提取关键要素
    3. 制定执行计划

    Args:
        state: 当前状态

    Returns:
        更新后的状态
    """
    logger.info("Understanding task...", task=state.get("task", "")[:100])

    settings = get_settings()

    # 初始化LLM
    llm = ChatOpenAI(
        model=settings.default_llm_model,
        temperature=0,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )

    # 构建Prompt
    system_message = SystemMessage(
        content="""你是一个专业的写作助手。你的任务是理解用户的创作需求，并制定详细的执行计划。

请分析用户的任务，提取以下信息：
1. 任务类型（续写、创作、改写等）
2. 关键要素（角色、情节、场景等）
3. 创作约束（字数、风格、类型等）
4. 所需工具（角色卡、大纲、RAG检索等）

输出格式：JSON
{
  "task_type": "任务类型",
  "key_elements": ["要素1", "要素2"],
  "constraints": {"字数": 1000, "风格": "悬疑"},
  "required_tools": ["rag_tool", "character_tool"],
  "plan": [
    {"step": "检索相关设定", "tool": "rag_tool"},
    {"step": "查询角色信息", "tool": "character_tool"},
    {"step": "生成内容", "tool": "llm"}
  ]
}"""
    )

    user_message = HumanMessage(
        content=f"""任务：{state['task']}

项目ID：{state['project_id']}
用户ID：{state['user_id']}

请分析这个任务并制定执行计划。"""
    )

    try:
        # 调用LLM
        response = await llm.ainvoke([system_message, user_message])

        # 解析响应
        try:
            analysis = json.loads(response.content)
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response as JSON, using default plan")
            analysis = {
                "task_type": "general",
                "key_elements": [],
                "constraints": {},
                "required_tools": ["rag_tool"],
                "plan": [
                    {"step": "检索相关信息", "tool": "rag_tool"},
                    {"step": "生成内容", "tool": "llm"},
                ],
            }

        logger.info(
            "Task analysis completed",
            task_type=analysis.get("task_type"),
            tools=analysis.get("required_tools"),
            plan_steps=len(analysis.get("plan", [])),
        )

        # 更新状态
        return {
            "messages": [system_message, user_message, response],
            "plan": analysis.get("plan", []),
            "current_plan_index": 0,
            "constraints": {**state.get("constraints", {}), **analysis.get("constraints", {})},
            "tools_to_use": analysis.get("required_tools", []),
            "reasoning": [
                f"任务分析完成：{analysis.get('task_type')}",
                f"关键要素：{', '.join(analysis.get('key_elements', []))}",
                f"执行计划：{len(analysis.get('plan', []))} 个步骤",
            ],
            "current_step": "rag_retrieval",
        }

    except Exception as e:
        logger.error(f"Understanding node failed: {e}", exc_info=True)
        return {
            "errors": [f"Understanding failed: {str(e)}"],
            "current_step": "error",
        }

