"""快速测试gRPC - 显示所有错误"""
import asyncio
import sys
import os
from concurrent import futures

# 设置路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'grpc_server'))

print("=" * 60)
print("Starting gRPC Server Test")
print("=" * 60)

try:
    import grpc
    print("✅ grpc imported")

    import ai_service_pb2
    print("✅ ai_service_pb2 imported")

    import ai_service_pb2_grpc
    print("✅ ai_service_pb2_grpc imported")

    class TestServicer(ai_service_pb2_grpc.AIServiceServicer):
        async def HealthCheck(self, request, context):
            print("❤️  Health check received!")
            return ai_service_pb2.HealthCheckResponse(
                status="healthy",
                checks={"server": "ok"}
            )

        async def GenerateContent(self, request, context):
            print(f"📝 GenerateContent called: project_id={request.project_id}, prompt={request.prompt[:50]}...")
            return ai_service_pb2.GenerateContentResponse(
                content=f"[测试响应] 收到您的请求: {request.prompt}",
                tokens_used=100,
                model=request.options.model if request.options else "test-model",
                generated_at=0
            )

    async def serve():
        server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
        ai_service_pb2_grpc.add_AIServiceServicer_to_server(TestServicer(), server)

        port = 50052
        server.add_insecure_port(f'[::]:{port}')

        print(f"\n🚀 Starting server on port {port}...")
        await server.start()
        print(f"✅ Server is RUNNING on port {port}")
        print(f"🔗 Test with: go run test_grpc_connection.go\n")

        await server.wait_for_termination()

    if __name__ == "__main__":
        asyncio.run(serve())

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

