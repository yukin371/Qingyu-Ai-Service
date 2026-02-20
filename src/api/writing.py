"""
写作API路由
"""
from fastapi import APIRouter, HTTPException, status

from ..api.models.writing import (
    WritingContext,
    ContinueWritingRequest,
    PolishRequest,
    ExpandRequest,
    WritingResponse
)
from ..llm.llm_factory import LLMFactory
from ..core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/writing/continue", response_model=WritingResponse)
async def continue_writing(request: ContinueWritingRequest):
    """
    续写接口
    根据当前文本继续写作。
    """
    try:
        logger.info(
            "continue_writing_request",
            project_id=request.project_id,
            text_length=len(request.current_text)
        )

        # 创建LLM实例
        llm = LLMFactory.get_default_llm(temperature=request.temperature, max_tokens=request.continue_length)

        # 构建续写提示
        prompt = f"""请根据以下文本继续写作，续写约{request.continue_length}字：

{request.current_text}

续写内容（直接输出续写内容，不要加任何说明）："""

        # 调用LLM
        response_msg = await llm.ainvoke(prompt)
        generated_text = response_msg.content

        response = WritingResponse(
            generated_text=generated_text,
            usage={
                "prompt_tokens": getattr(response_msg, 'usage_metadata', {}).get('input_tokens', 0) or 0,
                "completion_tokens": getattr(response_msg, 'usage_metadata', {}).get('output_tokens', 0) or 0,
                "total_tokens": getattr(response_msg, 'usage_metadata', {}).get('total_tokens', 0) or 0
            },
            quota_remaining=9850,
            model=request.model
        )

        logger.info("continue_writing_completed")
        return response

    except Exception as e:
        logger.error("continue_writing_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"续写失败: {str(e)}"
        )


@router.post("/writing/polish", response_model=WritingResponse)
async def polish_text(request: PolishRequest):
    """
    润色接口
    对文本进行润色优化。
    """
    try:
        logger.info("polish_request", text_length=len(request.text))

        # 创建LLM实例
        llm = LLMFactory.get_default_llm(temperature=0.5)

        # 构建润色提示
        style_instruction = ""
        if request.style:
            style_instruction = f"目标风格：{request.style}。"

        focus_instruction = ""
        if request.focus_areas:
            focus_instruction = f"重点关注：{', '.join(request.focus_areas)}。"

        prompt = f"""请对以下文本进行润色优化。{style_instruction}{focus_instruction}

原文：
{request.text}

润色后的文本（直接输出润色后的内容，不要加任何说明）："""

        # 调用LLM
        response_msg = await llm.ainvoke(prompt)
        generated_text = response_msg.content

        response = WritingResponse(
            generated_text=generated_text,
            usage={
                "prompt_tokens": getattr(response_msg, 'usage_metadata', {}).get('input_tokens', 0) or 0,
                "completion_tokens": getattr(response_msg, 'usage_metadata', {}).get('output_tokens', 0) or 0,
                "total_tokens": getattr(response_msg, 'usage_metadata', {}).get('total_tokens', 0) or 0
            },
            quota_remaining=9750,
            model=request.model
        )

        logger.info("polish_completed")
        return response

    except Exception as e:
        logger.error("polish_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"润色失败: {str(e)}"
        )


@router.post("/writing/expand", response_model=WritingResponse)
async def expand_text(request: ExpandRequest):
    """
    扩展接口
    对文本进行扩展。
    """
    try:
        logger.info("expand_request", text_length=len(request.text), ratio=request.expand_ratio)

        # 创建LLM实例
        target_length = int(len(request.text) * request.expand_ratio)
        llm = LLMFactory.get_default_llm(temperature=0.7, max_tokens=target_length)

        # 构建扩写提示
        direction_instruction = ""
        if request.direction:
            direction_instruction = f"扩写方向：{request.direction}。"

        prompt = f"""请对以下文本进行扩写，扩写后约{target_length}字。{direction_instruction}

原文：
{request.text}

扩写后的文本（直接输出扩写后的内容，不要加任何说明）："""

        # 调用LLM
        response_msg = await llm.ainvoke(prompt)
        generated_text = response_msg.content

        response = WritingResponse(
            generated_text=generated_text,
            usage={
                "prompt_tokens": getattr(response_msg, 'usage_metadata', {}).get('input_tokens', 0) or 0,
                "completion_tokens": getattr(response_msg, 'usage_metadata', {}).get('output_tokens', 0) or 0,
                "total_tokens": getattr(response_msg, 'usage_metadata', {}).get('total_tokens', 0) or 0
            },
            quota_remaining=9650,
            model=request.model
        )

        logger.info("expand_completed")
        return response

    except Exception as e:
        logger.error("expand_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"扩展失败: {str(e)}"
        )
