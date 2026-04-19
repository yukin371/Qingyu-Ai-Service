"""
gRPC服务器启动脚本 - Phase3 AI服务
"""
import asyncio
import threading
from concurrent import futures
import sys
from pathlib import Path

import grpc

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core import settings
from src.core.logger import get_logger
from src.grpc_service.ai_servicer import AIServicer
from src.grpc_service import ai_service_pb2_grpc

logger = get_logger(__name__)


async def serve(host: str = "0.0.0.0", port: int = 50051):
    """
    启动gRPC服务器

    Args:
        host: 监听地址
        port: 监听端口
    """
    # 创建服务器
    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ("grpc.max_send_message_length", 50 * 1024 * 1024),  # 50MB
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),  # 50MB
        ],
    )

    # 创建servicer
    servicer = AIServicer()

    # 注册服务到server
    ai_service_pb2_grpc.add_AIServiceServicer_to_server(servicer, server)

    # 绑定端口
    server_address = f"{host}:{port}"
    server.add_insecure_port(server_address)

    logger.info(f"🚀 gRPC服务器启动 - 监听地址: {server_address}")
    logger.info("📋 可用服务:")
    logger.info("  - ExecuteCreativeWorkflow: 完整创作工作流")
    logger.info("  - GenerateOutline: 大纲生成")
    logger.info("  - GenerateCharacters: 角色生成")
    logger.info("  - GeneratePlot: 情节生成")
    logger.info("  - HealthCheck: 健康检查")

    # 启动服务器
    await server.start()

    logger.info("✅ gRPC服务器就绪，等待请求...")

    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("⏹️  收到停止信号，关闭服务器...")
        await server.stop(grace=5)
        logger.info("👋 服务器已关闭")


def start_grpc_server(host: str = "0.0.0.0", port: int | None = None):
    """在后台线程同步拉起 gRPC 服务，供 FastAPI lifespan 调用。"""
    target_port = port or settings.grpc_port

    def run_server():
        asyncio.run(serve(host=host, port=target_port))

    thread = threading.Thread(
        target=run_server,
        name="qingyu-ai-grpc-server",
        daemon=True,
    )
    thread.start()
    logger.info("grpc_server_thread_started", host=host, port=target_port)
    return thread


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Phase3 AI gRPC服务器")
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="监听地址（默认: 0.0.0.0）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=50051,
        help="监听端口（默认: 50051）",
    )

    args = parser.parse_args()

    # 运行服务器
    asyncio.run(serve(host=args.host, port=args.port))


if __name__ == "__main__":
    main()

