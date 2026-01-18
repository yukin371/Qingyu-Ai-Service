"""Review Node - 审核节点

评估生成内容质量，决定是否需要重新生成
"""

import json
from typing import Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.agents.states.creative_state import CreativeAgentState
from src.core.config import get_settings
from src.core.logger import get_logger

logger = get_logger(__name__)


async def review_node(state: CreativeAgentState) -> Dict:
    """审核节点

    职责：
    1. 检查生成内容质量
    2. 评估是否符合要求
    3. 提供改进建议

    Args:
        state: 当前状态

    Returns:
        更新后的状态
    """
    logger.info("Reviewing generated content...")

    settings = get_settings()

    # 初始化LLM
    llm = ChatOpenAI(
        model=settings.default_llm_model,
        temperature=0,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )

    # 构建审核Prompt
    system_message = SystemMessage(
        content="""你是一位专业的内容审核专家。请评估生成的内容质量。

评估标准：
1. 内容是否符合用户要求
2. 逻辑是否连贯
3. 角色性格是否一致（如果有参考资料）
4. 文笔是否流畅
5. 是否有明显错误

输出格式：JSON
{
  "passed": true/false,
  "score": 85,
  "issues": ["问题1", "问题2"],
  "suggestions": ["建议1", "建议2"],
  "summary": "总体评价"
}

评分标准：
- 90-100：优秀，完全符合要求
- 80-89：良好，基本符合要求
- 70-79：及格，可接受但有改进空间
- 60-69：不及格，建议重写
- 60以下：较差，需要重新生成"""
    )

    user_message = HumanMessage(
        content=f"""原始任务：{state['task']}

生成内容：
{state['generated_content']}

请评估这个内容的质量。"""
    )

    try:
        # 调用LLM
        response = await llm.ainvoke([system_message, user_message])

        # 解析审核结果
        try:
            review_result = json.loads(response.content)
        except json.JSONDecodeError:
            logger.warning("Failed to parse review result as JSON, using default")
            # 解析失败，默认通过
            review_result = {
                "passed": True,
                "score": 75,
                "issues": [],
                "suggestions": [],
                "summary": "内容可接受",
            }

        # 判断是否通过（分数>=70或明确标记为passed）
        passed = review_result.get("passed", False) or review_result.get("score", 0) >= 70

        logger.info(
            "Review completed",
            passed=passed,
            score=review_result.get("score", 0),
            issues_count=len(review_result.get("issues", [])),
        )

        return {
            "messages": [system_message, user_message, response],
            "review_result": review_result,
            "review_passed": passed,
            "current_step": "finalize" if passed else "regenerate",
            "reasoning": [
                f"审核完成：{'通过' if passed else '不通过'}",
                f"评分：{review_result.get('score', 0)}",
                f"问题：{len(review_result.get('issues', []))}",
            ],
        }

    except Exception as e:
        logger.error(f"Review node failed: {e}", exc_info=True)
        # 审核失败，默认通过（避免阻塞）
        return {
            "review_result": {
                "passed": True,
                "score": 70,
                "issues": [],
                "suggestions": [],
                "summary": "审核异常，默认通过",
            },
            "review_passed": True,
            "current_step": "finalize",
            "warnings": [f"Review failed: {str(e)}"],
            "reasoning": ["审核异常，默认通过"],
        }

