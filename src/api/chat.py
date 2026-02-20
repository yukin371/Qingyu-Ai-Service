"""
聊天API路由
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import Optional

from ..api.models.chat import ChatRequest, ChatResponse, Message, Usage
from ..llm.llm_factory import LLMFactory
from ..core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    AI对话接口

    处理用户对话请求，返回AI回复。
    """
    try:
        logger.info("chat_request_received", message_count=len(request.messages))

        if not request.messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="消息不能为空"
            )

        # 使用LLM工厂创建LLM实例（默认使用配置的质谱GLM-4.7）
        llm = LLMFactory.get_default_llm(
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens or 2000
        )

        # 转换消息格式为LangChain格式
        langchain_messages = []
        for msg in request.messages:
            langchain_messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # 调用LLM
        response_msg = await llm.ainvoke(langchain_messages)

        # 获取响应内容
        ai_message = response_msg.content

        # 构建响应
        response = ChatResponse(
            message=ai_message,
            usage=Usage(
                prompt_tokens=getattr(response_msg, 'usage_metadata', {}).get('input_tokens', 0) or 0,
                completion_tokens=getattr(response_msg, 'usage_metadata', {}).get('output_tokens', 0) or 0,
                total_tokens=getattr(response_msg, 'usage_metadata', {}).get('total_tokens', 0) or 0
            ),
            model=request.model or "glm-4",
            quota_remaining=9900
        )

        logger.info("chat_response_sent", total_tokens=response.usage.total_tokens)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("chat_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"聊天处理失败: {str(e)}"
        )
