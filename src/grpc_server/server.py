"""
gRPC Server 启动模块

DEPRECATED: 此模块已弃用，请使用 src/grpc_service/server.py 代替。

此文件仅保留用于向后兼容，新代码应直接使用 grpc_service.server。
"""
import asyncio
import warnings

warnings.warn(
    "grpc_server.server is deprecated, use grpc_service.server instead",
    DeprecationWarning,
    stacklevel=2
)

# 转发到新的 server 模块
from src.grpc_service.server import serve, start_grpc_server

__all__ = ['serve', 'start_grpc_server']


def _deprecated_serve():
    """弃用的 serve 函数"""
    warnings.warn(
        "grpc_server.server.serve is deprecated, use grpc_service.server.serve instead",
        DeprecationWarning,
        stacklevel=2
    )
    return serve()


def _deprecated_start_grpc_server():
    """弃用的 start_grpc_server 函数"""
    warnings.warn(
        "grpc_server.server.start_grpc_server is deprecated, use grpc_service.server.start_grpc_server instead",
        DeprecationWarning,
        stacklevel=2
    )
    return start_grpc_server()
