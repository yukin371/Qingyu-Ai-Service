"""Generation Node - 生成节点

调用LLM生成创作内容
"""

from typing import Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.agents.states.creative_state import CreativeAgentState
from src.core.config import get_settings
from src.core.logger import get_logger

logger = get_logger(__name__)


async def generation_node(state: CreativeAgentState) -> Dict:
    """生成节点

    职责：
    1. 构建增强Prompt
    2. 调用LLM生成内容
    3. 保存生成结果

    Args:
        state: 当前状态

    Returns:
        更新后的状态
    """
    logger.info("Generating content...")

    settings = get_settings()

    # 初始化LLM
    llm = ChatOpenAI(
        model=settings.default_llm_model,
        temperature=0.7,
        max_tokens=2000,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )

    # 构建系统提示
    system_prompt = """你是一位专业的网络小说作家，擅长创作引人入胜的故事。
请根据用户需求和参考资料，创作高质量的内容。

创作要求：
1. 内容要符合用户的具体要求
2. 保持角色性格一致
3. 情节合理连贯
4. 文笔流畅自然"""

    # 构建用户提示
    user_prompt_parts = [f"创作任务：{state['task']}"]

    # 添加RAG检索的上下文
    if state.get("retrieved_context"):
        user_prompt_parts.append(f"\n【参考资料】\n{state['retrieved_context']}")

    # 添加约束条件
    if state.get("constraints"):
        constraints_str = "\n".join(
            [f"- {k}: {v}" for k, v in state["constraints"].items()]
        )
        user_prompt_parts.append(f"\n【创作约束】\n{constraints_str}")

    # 如果是重试，添加之前的审核反馈
    if state.get("review_result") and not state.get("review_passed"):
        review = state["review_result"]
        feedback_parts = []
        if review.get("issues"):
            feedback_parts.append(f"问题：{', '.join(review['issues'])}")
        if review.get("suggestions"):
            feedback_parts.append(f"建议：{', '.join(review['suggestions'])}")

        if feedback_parts:
            user_prompt_parts.append(
                f"\n【上次审核反馈】\n{chr(10).join(feedback_parts)}\n\n请根据反馈改进内容。"
            )

    user_prompt = "\n".join(user_prompt_parts)

    try:
        # 调用LLM
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = await llm.ainvoke(messages)
        generated_content = response.content

        # 统计Token使用（粗略估计）
        tokens_used = len(response.content) // 4

        logger.info(
            "Content generation completed",
            content_length=len(generated_content),
            tokens_used=tokens_used,
        )

        return {
            "messages": messages + [response],
            "generated_content": generated_content,
            "content_draft": generated_content,
            "tokens_used": tokens_used,
            "current_step": "review",
            "reasoning": [f"内容生成完成，字数约 {len(generated_content)}"],
        }

    except Exception as e:
        logger.error(f"Generation node failed: {e}", exc_info=True)
        return {
            "errors": [f"Generation failed: {str(e)}"],
            "current_step": "error",
        }

