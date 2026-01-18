"""
健康检查 API
"""
from typing import Dict, Any
from fastapi import APIRouter, status
from datetime import datetime

from ..core import settings, get_logger

router = APIRouter(tags=["Health"])
logger = get_logger(__name__)


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="健康检查",
    description="检查服务是否正常运行"
)
async def health_check() -> Dict[str, Any]:
    """健康检查端点"""
    logger.info("health_check_called")

    return {
        "status": "healthy",
        "service": settings.service_name,
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0"
    }


@router.get(
    "/health/ready",
    status_code=status.HTTP_200_OK,
    summary="就绪检查",
    description="检查服务是否就绪（所有依赖服务连接正常）"
)
async def readiness_check() -> Dict[str, Any]:
    """就绪检查端点

    注意：此端点需要在 FastAPI 应用启动时注入 MilvusClient 实例。
    示例实现：

    @app.on_event("startup")
    async def startup():
        app.state.milvus_client = MilvusClient()
        app.state.milvus_client.connect()
        app.state.embedding_service = EmbeddingService()
        app.state.embedding_service.load_model()

    然后在此函数中：
        milvus_status = request.app.state.milvus_client.health_check()
        checks["milvus"] = "ok" if milvus_status else "error"
    """
    logger.info("readiness_check_called")

    # TODO: 检查 Milvus、gRPC、Redis 连接状态
    # 当前返回基本状态，实际应用需要注入依赖服务实例
    checks = {
        "milvus": "not_checked",  # 需要注入 MilvusClient
        "grpc": "not_checked",    # 需要检查 Go gRPC 连接
        "redis": "not_checked"    # 需要检查 Redis 连接
    }

    # 判断是否所有检查都通过
    all_ready = all(status == "ok" for status in checks.values())

    return {
        "status": "ready" if all_ready else "partial",
        "service": settings.service_name,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
        "message": "Full dependency checks not yet implemented. See function docstring for implementation guide."
    }


@router.get(
    "/health/live",
    status_code=status.HTTP_200_OK,
    summary="存活检查",
    description="检查服务进程是否存活"
)
async def liveness_check() -> Dict[str, Any]:
    """存活检查端点"""
    return {
        "status": "alive",
        "service": settings.service_name,
        "timestamp": datetime.utcnow().isoformat()
    }

