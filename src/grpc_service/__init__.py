"""
gRPC服务模块
"""
try:
    from . import ai_service_pb2, ai_service_pb2_grpc
    __all__ = ["ai_service_pb2", "ai_service_pb2_grpc"]
except ImportError:
    # gRPC generated files not available - this is expected in environments
    # where proto files haven't been compiled yet
    __all__ = []


