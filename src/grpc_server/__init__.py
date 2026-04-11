"""
gRPC 服务端：与 Go 后端通信
pb2 文件由 CI (grpc_tools.protoc) 生成到此目录。
"""
from . import ai_service_pb2, ai_service_pb2_grpc

__all__ = ["ai_service_pb2", "ai_service_pb2_grpc"]

