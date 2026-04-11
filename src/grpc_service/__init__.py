"""
gRPC服务模块

pb2 文件统一由 grpc_server 包持有（CI 生成到此目录），
本包通过 re-export 保持对下游调用方透明。
"""
from ..grpc_server import ai_service_pb2, ai_service_pb2_grpc

__all__ = ["ai_service_pb2", "ai_service_pb2_grpc"]

