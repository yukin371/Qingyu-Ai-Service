"""
聊天API路由
"""
from fastapi import APIRouter, HTTPException, status
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.api.models.chat import ChatRequest, ChatResponse, Usage
from src.llm.llm_factory import LLMFactory
from ..core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

def _build_langchain_messages(messages):
    """将 API 消息转换为 LangChain 消息。"""
    converted = []
    for message in messages:
        role = (message.role or "").lower()
        content = message.content or ""

        if role == "system":
            converted.append(SystemMessage(content=content))
        elif role == "assistant":
            converted.append(AIMessage(content=content))
        else:
            converted.append(HumanMessage(content=content))

    return converted


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
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

        llm = LLMFactory.get_default_llm(
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        response_msg = await llm.ainvoke(_build_langchain_messages(request.messages))

        response = ChatResponse(
            message=response_msg.content if isinstance(response_msg.content, str) else str(response_msg.content),
            usage=Usage(
                prompt_tokens=getattr(response_msg, "usage_metadata", {}).get("input_tokens", 0) or 0,
                completion_tokens=getattr(response_msg, "usage_metadata", {}).get("output_tokens", 0) or 0,
                total_tokens=getattr(response_msg, "usage_metadata", {}).get("total_tokens", 0) or 0,
            ),
            model=request.model,
            quota_remaining=9950,
        )

        logger.info("chat_response_sent", total_tokens=response.usage.total_tokens)
        return response

    except Exception as e:
        logger.error("chat_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"聊天处理失败: {str(e)}"
        )
