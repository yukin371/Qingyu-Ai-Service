#!/bin/bash
# 生成 Python Protobuf 代码

set -e

echo "Generating Python protobuf code..."

cd "$(dirname "$0")/.."

# 检查 grpc_tools 是否安装
python -c "import grpc_tools" 2>/dev/null || {
    echo "Error: grpc_tools not installed. Run: pip install grpcio-tools"
    exit 1
}

# 生成代码
python -m grpc_tools.protoc \
    -I proto \
    --python_out=src/grpc_server \
    --grpc_python_out=src/grpc_server \
    proto/ai_service.proto

echo "✓ Python protobuf code generated in src/grpc_server/"

# 修复导入路径（protobuf 生成的导入路径可能需要调整）
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' 's/import ai_service_pb2/from . import ai_service_pb2/' src/grpc_server/ai_service_pb2_grpc.py
else
    # Linux
    sed -i 's/import ai_service_pb2/from . import ai_service_pb2/' src/grpc_server/ai_service_pb2_grpc.py
fi

echo "✓ Fixed import paths"

