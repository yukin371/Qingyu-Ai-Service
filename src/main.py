"""
FastAPI 应用入口
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from src.core import settings, get_logger, AIServiceException
from src.api.health import router as health_router
from src.api.chat import router as chat_router
from src.api.writing import router as writing_router
from src.api.quota import router as quota_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """应用生命周期管理"""
    # Startup
    logger.info("starting_application", service=settings.service_name)

    # 启动 gRPC Server（在后台运行）
    try:
        from .grpc_server.server import start_grpc_server
        start_grpc_server()
        logger.info("grpc_server_initialized")
    except Exception as e:
        logger.error("failed_to_start_grpc_server", error=str(e))

    # TODO: 初始化资源
    # - Milvus 连接
    # - Redis 连接
    # - 加载 Embedding 模型

    logger.info("application_started", port=settings.service_port)

    yield

    # Shutdown
    logger.info("shutting_down_application")

    # TODO: 清理资源

    logger.info("application_stopped")


# 创建 FastAPI 应用
app = FastAPI(
    title="Qingyu AI Service",
    description="AI Agent 工作流、RAG 系统、LangGraph 编排 - Phase3 v2.0",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应配置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加 Gzip 压缩
app.add_middleware(GZipMiddleware, minimum_size=1000)


# 全局异常处理
@app.exception_handler(AIServiceException)
async def ai_service_exception_handler(request: Request, exc: AIServiceException):
    """AI 服务异常处理"""
    logger.error(
        "ai_service_exception",
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        path=request.url.path
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理"""
    logger.error(
        "unexpected_exception",
        exception=str(exc),
        exception_type=type(exc).__name__,
        path=request.url.path,
        exc_info=True
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "details": {"exception_type": type(exc).__name__}
        }
    )


# 注册路由
app.include_router(health_router, prefix="/api/v1", tags=["Health"])
app.include_router(chat_router, prefix="/api/v1/ai", tags=["Chat"])
app.include_router(writing_router, prefix="/api/v1/ai", tags=["Writing"])
app.include_router(quota_router, prefix="/api/v1/quota", tags=["Quota"])


@app.get("/", tags=["Root"])
async def root():
    """根路径"""
    return {
        "service": settings.service_name,
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=True,
        log_level=settings.log_level.lower()
    )

