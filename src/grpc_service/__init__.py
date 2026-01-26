"""
gRPC服务模块

此模块包含 gRPC 服务的实现代码。
生成的 protobuf 代码位于 grpc_server/ 目录中。
"""
# 从 grpc_server 导入生成的 protobuf 代码
from .grpc_server import ai_service_pb2, ai_service_pb2_grpc

__all__ = ["ai_service_pb2", "ai_service_pb2_grpc"]
