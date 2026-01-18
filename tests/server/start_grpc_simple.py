"""
最简化的gRPC服务器 - 用于测试
"""
import asyncio
from concurrent import futures
import grpc
import sys
import os

# 添加proto生成的代码到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'grpc_server'))

try:
    import ai_service_pb2
    import ai_service_pb2_grpc
    print("✅ Proto文件导入成功")
except ImportError as e:
    print(f"❌ Proto导入失败: {e}")
    print("请运行: python -m grpc_tools.protoc -I./proto --python_out=./src/grpc_server --grpc_python_out=./src/grpc_server ./proto/ai_service.proto")
    sys.exit(1)

class SimpleAIServicer(ai_service_pb2_grpc.AIServiceServicer):
    """简化的AI服务实现"""

    async def HealthCheck(self, request, context):
        print("📞 收到健康检查请求")
        return ai_service_pb2.HealthCheckResponse(
            status="healthy",
            checks={"test": "ok"}
        )

    async def GenerateContent(self, request, context):
        print(f"📞 收到生成内容请求: project_id={request.project_id}, prompt={request.prompt[:50]}...")
        return ai_service_pb2.GenerateContentResponse(
            content=f"[测试响应] 收到您的请求: {request.prompt}",
            tokens_used=100,
            model=request.options.model if request.options else "test-model",
            generated_at=0
        )

async def serve():
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    ai_service_pb2_grpc.add_AIServiceServicer_to_server(SimpleAIServicer(), server)

    port = 50052
    server.add_insecure_port(f'[::]:{port}')

    print(f"🚀 gRPC服务器启动中...")
    await server.start()
    print(f"✅ gRPC服务器已启动，监听端口: {port}")
    print(f"💡 测试命令: go run test_grpc_connection.go")

    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        print("\n👋 正在关闭服务器...")
        await server.stop(5)
        print("✅ 服务器已关闭")

if __name__ == "__main__":
    print("=" * 60)
    print("Qingyu Python AI Service - gRPC Server")
    print("=" * 60)
    asyncio.run(serve())

