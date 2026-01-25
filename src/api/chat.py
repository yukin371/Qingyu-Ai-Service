"""
聊天API路由
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import Optional

from src.api.models.chat import ChatRequest, ChatResponse, Message, Usage
from ..services.agent_service import AgentService
from ..core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

# 依赖注入：获取AgentService实例
async def get_agent_service():
    """获取AgentService实例"""
    # TODO: 实现单例或依赖注入
    return AgentService()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    agent_service: AgentService = Depends(get_agent_service)
):
    """
    AI对话接口

    处理用户对话请求，返回AI回复。

    **请求示例**:
    ```json
    {
      "messages": [
        {"role": "user", "content": "你好"}
      ],
      "model": "gpt-4",
      "temperature": 0.7,
      "max_tokens": 2000
    }
    ```

    **响应示例**:
    ```json
    {
      "message": "你好！有什么可以帮助你的？",
      "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30
      },
      "model": "gpt-4",
      "quota_remaining": 9970
    }
    ```
    """
    try:
        logger.info("chat_request_received", message_count=len(request.messages))

        # TODO: 实现实际的聊天逻辑
        # 1. 验证配额
        # 2. 调用AgentService
        # 3. 扣除配额
        # 4. 返回响应

        # 临时模拟响应
        last_message = request.messages[-1].content if request.messages else ""

        response = ChatResponse(
            message=f"这是对'{last_message}'的模拟回复。实际实现需要集成AgentService。",
            usage=Usage(
                prompt_tokens=50,
                completion_tokens=30,
                total_tokens=80
            ),
            model=request.model,
            quota_remaining=9950
        )

        logger.info("chat_response_sent", total_tokens=response.usage.total_tokens)
        return response

    except Exception as e:
        logger.error("chat_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"聊天处理失败: {str(e)}"
        )
