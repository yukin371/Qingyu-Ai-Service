"""
写作API路由
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict

from src.api.models.writing import (
    WritingContext,
    ContinueWritingRequest,
    PolishRequest,
    ExpandRequest,
    WritingResponse
)
from ..services.agent_service import AgentService
from ..core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

# 依赖注入：获取AgentService实例
async def get_agent_service():
    """获取AgentService实例"""
    # TODO: 实现单例或依赖注入
    return AgentService()


@router.post("/writing/continue", response_model=WritingResponse)
async def continue_writing(
    request: ContinueWritingRequest,
    agent_service: AgentService = Depends(get_agent_service)
):
    """
    续写接口

    根据当前文本继续写作。

    **请求示例**:
    ```json
    {
      "project_id": "proj123",
      "current_text": "这是开头...",
      "continue_length": 100,
      "context": {
        "genre": "玄幻",
        "characters": ["张三", "李四"]
      }
    }
    ```
    """
    try:
        logger.info(
            "continue_writing_request",
            project_id=request.project_id,
            text_length=len(request.current_text)
        )

        # TODO: 实现实际的续写逻辑
        # 1. 获取项目上下文
        # 2. 调用AgentService执行续写
        # 3. 扣除配额
        # 4. 返回响应

        response = WritingResponse(
            generated_text=f"这是对'{request.current_text[:50]}...'的续写内容。",
            usage={
                "prompt_tokens": 100,
                "completion_tokens": request.continue_length,
                "total_tokens": 100 + request.continue_length
            },
            quota_remaining=9850,
            model=request.model
        )

        logger.info("continue_writing_completed", tokens_generated=response.usage["completion_tokens"])
        return response

    except Exception as e:
        logger.error("continue_writing_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"续写失败: {str(e)}"
        )


@router.post("/writing/polish", response_model=WritingResponse)
async def polish_text(
    request: PolishRequest,
    agent_service: AgentService = Depends(get_agent_service)
):
    """
    润色接口

    对文本进行润色优化。

    **请求示例**:
    ```json
    {
      "text": "待润色的文本",
      "style": "文学",
      "focus_areas": ["grammar", "vocabulary"]
    }
    ```
    """
    try:
        logger.info("polish_request", text_length=len(request.text))

        # TODO: 实现实际的润色逻辑
        response = WritingResponse(
            generated_text=f"这是对'{request.text[:50]}...'的润色结果。",
            usage={
                "prompt_tokens": len(request.text),
                "completion_tokens": len(request.text),
                "total_tokens": len(request.text) * 2
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
async def expand_text(
    request: ExpandRequest,
    agent_service: AgentService = Depends(get_agent_service)
):
    """
    扩展接口

    对文本进行扩展。

    **请求示例**:
    ```json
    {
      "text": "待扩展的文本",
      "expand_ratio": 1.5,
      "direction": "详细描述"
    }
    ```
    """
    try:
        logger.info("expand_request", text_length=len(request.text), ratio=request.expand_ratio)

        # TODO: 实现实际的扩展逻辑
        expanded_length = int(len(request.text) * request.expand_ratio)

        response = WritingResponse(
            generated_text=f"这是对'{request.text[:50]}...'的扩展内容，目标长度{expanded_length}字符。",
            usage={
                "prompt_tokens": len(request.text),
                "completion_tokens": expanded_length,
                "total_tokens": len(request.text) + expanded_length
            },
            quota_remaining=9650,
            model=request.model
        )

        logger.info("expand_completed", expanded_length=expanded_length)
        return response

    except Exception as e:
        logger.error("expand_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"扩展失败: {str(e)}"
        )
