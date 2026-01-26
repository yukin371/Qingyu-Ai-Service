"""
gRPC服务模块

Note: gRPC generated files (ai_service_pb2, ai_service_pb2_grpc) are
gitignored and need to be generated using scripts/generate_proto.sh

In CI/CD environments, these files may not be available. Tests that
require these files should be marked as integration tests.
"""

# Make these imports optional - create None placeholders if files don't exist
try:
    from . import ai_service_pb2
    from . import ai_service_pb2_grpc
except (ImportError, ModuleNotFoundError):
    # Generated protobuf files not available
    # Create placeholder modules to prevent ImportError
    import sys
    import types

    # Create placeholder modules
    ai_service_pb2 = types.ModuleType("ai_service_pb2_placeholder")
    ai_service_pb2_grpc = types.ModuleType("ai_service_pb2_grpc_placeholder")

    # Add to sys.modules so they can be imported
    sys.modules["grpc_service.ai_service_pb2"] = ai_service_pb2
    sys.modules["grpc_service.ai_service_pb2_grpc"] = ai_service_pb2_grpc

__all__ = ["ai_service_pb2", "ai_service_pb2_grpc"]



