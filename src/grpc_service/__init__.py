"""
gRPC服务模块

pb2 文件从主仓库 proto 目录生成，使用 qingyu.ai.v1 包结构。
"""
from .qingyu.ai.v1 import ai_service_pb2, ai_service_pb2_grpc

__all__ = ["ai_service_pb2", "ai_service_pb2_grpc"]

