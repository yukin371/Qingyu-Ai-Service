"""
API数据模型
"""
from .chat import (
    Message,
    ChatRequest,
    ChatResponse,
    Usage
)

from .writing import (
    WritingContext,
    ContinueWritingRequest,
    PolishRequest,
    ExpandRequest,
    WritingResponse
)

from .quota import (
    QuotaInfo,
    ConsumeQuotaRequest,
    ConsumeQuotaResponse
)

from .fact_extraction import (
    StateChange,
    RelationChange,
    NewEntityMention,
    EventFact,
    ExtractionResult,
    AnalyzeChapterRequest,
    AnalyzeChapterResponse,
    ExtractFactsRequest,
    ExtractFactsResponse,
    ChangeRequestPayload,
)

__all__ = [
    # Chat
    "Message",
    "ChatRequest",
    "ChatResponse",
    "Usage",

    # Writing
    "WritingContext",
    "ContinueWritingRequest",
    "PolishRequest",
    "ExpandRequest",
    "WritingResponse",

    # Quota
    "QuotaInfo",
    "ConsumeQuotaRequest",
    "ConsumeQuotaResponse",

    # Fact Extraction
    "StateChange",
    "RelationChange",
    "NewEntityMention",
    "EventFact",
    "ExtractionResult",
    "AnalyzeChapterRequest",
    "AnalyzeChapterResponse",
    "ExtractFactsRequest",
    "ExtractFactsResponse",
    "ChangeRequestPayload",
]
