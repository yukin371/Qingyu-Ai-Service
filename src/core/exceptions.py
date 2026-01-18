"""
自定义异常类
"""
from typing import Any, Optional


class AIServiceException(Exception):
    """AI 服务基础异常"""

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ConfigurationError(AIServiceException):
    """配置错误"""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, "CONFIGURATION_ERROR", details)


class MilvusConnectionError(AIServiceException):
    """Milvus 连接错误"""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, "MILVUS_CONNECTION_ERROR", details)


class EmbeddingError(AIServiceException):
    """向量化错误"""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, "EMBEDDING_ERROR", details)


class GRPCConnectionError(AIServiceException):
    """gRPC 连接错误"""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, "GRPC_CONNECTION_ERROR", details)


class ExternalServiceError(AIServiceException):
    """外部服务错误"""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, "EXTERNAL_SERVICE_ERROR", details)


class AgentExecutionError(AIServiceException):
    """Agent 执行错误"""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, "AGENT_EXECUTION_ERROR", details)


class RAGQueryError(AIServiceException):
    """RAG 查询错误"""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, "RAG_QUERY_ERROR", details)


class ValidationError(AIServiceException):
    """参数验证错误"""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, "VALIDATION_ERROR", details)


class MemoryOperationError(AIServiceException):
    """Memory 操作错误"""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, "MEMORY_OPERATION_ERROR", details)


class MemoryValidationError(AIServiceException):
    """Memory 验证错误"""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, "MEMORY_VALIDATION_ERROR", details)


class RAGError(AIServiceException):
    """RAG 错误"""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, "RAG_ERROR", details)

