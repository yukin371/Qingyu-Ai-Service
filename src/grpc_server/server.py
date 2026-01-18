"""
gRPC Server 启动模块
"""
import asyncio
from concurrent import futures

import grpc
from grpc_reflection.v1alpha import reflection

from ..core import settings, get_logger
from . import ai_service_pb2, ai_service_pb2_grpc
from .servicer import AIServicer

logger = get_logger(__name__)


async def serve():
    """启动 gRPC 服务器"""
    # 创建异步 gRPC 服务器
    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ('grpc.max_send_message_length', 100 * 1024 * 1024),  # 100MB
            ('grpc.max_receive_message_length', 100 * 1024 * 1024),  # 100MB
            ('grpc.keepalive_time_ms', 10000),  # 10s
            ('grpc.keepalive_timeout_ms', 5000),  # 5s
            ('grpc.keepalive_permit_without_calls', True),
            ('grpc.http2.max_pings_without_data', 0),
            ('grpc.http2.min_time_between_pings_ms', 10000),
            ('grpc.http2.min_ping_interval_without_data_ms', 5000),
        ]
    )

    # 注册服务
    ai_service_pb2_grpc.add_AIServiceServicer_to_server(
        AIServicer(),
        server
    )

    # 启用 gRPC 反射（用于调试）
    SERVICE_NAMES = (
        ai_service_pb2.DESCRIPTOR.services_by_name['AIService'].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)

    # 绑定端口
    grpc_port = settings.go_grpc_port + 1  # Python gRPC 端口 = Go gRPC 端口 + 1
    server.add_insecure_port(f'[::]:{grpc_port}')

    logger.info("starting_grpc_server", port=grpc_port)

    # 启动服务器
    await server.start()

    logger.info("grpc_server_started", port=grpc_port)

    # 保持运行
    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("shutting_down_grpc_server")
        await server.stop(grace=5)
        logger.info("grpc_server_stopped")


def start_grpc_server():
    """同步启动入口（用于在 FastAPI 中启动）"""
    import threading

    # 在后台线程启动异步gRPC服务器
    def run_server():
        asyncio.run(serve())

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    logger.info("grpc_server_thread_started", port=settings.go_grpc_port + 1)


if __name__ == "__main__":
    # 独立运行 gRPC Server
    asyncio.run(serve())

