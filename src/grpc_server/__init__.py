"""
gRPC 服务端：与 Go 后端通信

此目录存放由 protobuf 编译生成的 Python 代码。
运行 proto/generate.sh 来生成这些文件。
"""

# 导入生成的 protobuf 模块
# 这些文件由 proto/generate.sh 脚本生成
try:
    from . import ai_service_pb2
    from . import ai_service_pb2_grpc

    __all__ = ["ai_service_pb2", "ai_service_pb2_grpc"]
except ImportError:
    # 如果生成的文件不存在（例如在 CI 中首次运行）
    # 允许导入失败，稍后会生成这些文件
    __all__ = []

