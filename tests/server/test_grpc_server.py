"""
简化的gRPC服务器测试 - 独立运行
"""
import asyncio
from concurrent import futures
import grpc
import sys
import os

# 添加路径以导入proto
sys.path.insert(0, os.path.dirname(__file__))

from src.grpc_server import ai_service_pb2, ai_service_pb2_grpc
from src.grpc_server.servicer import AIServicer

async def serve():
    """启动gRPC服务器"""
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))

    # 注册服务
    ai_service_pb2_grpc.add_AIServiceServicer_to_server(AIServicer(), server)

    # 绑定端口
    port = 50052
    server.add_insecure_port(f'[::]:{port}')

    print(f"✅ gRPC服务器启动在端口 {port}")

    await server.start()
    print(f"🎉 gRPC服务器运行中，等待连接...")

    await server.wait_for_termination()

if __name__ == "__main__":
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        print("\n👋 服务器关闭")

