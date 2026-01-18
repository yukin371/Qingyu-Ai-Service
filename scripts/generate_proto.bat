@echo off
REM 生成 Python Protobuf 代码

echo Generating Python protobuf code...

cd /d "%~dp0\.."

REM 检查 grpc_tools 是否安装
python -c "import grpc_tools" 2>nul
if %errorlevel% neq 0 (
    echo Error: grpc_tools not installed. Run: pip install grpcio-tools
    exit /b 1
)

REM 生成代码
python -m grpc_tools.protoc -I proto --python_out=src/grpc_server --grpc_python_out=src/grpc_server proto/ai_service.proto

echo ✓ Python protobuf code generated in src/grpc_server/

REM 修复导入路径
powershell -Command "(Get-Content src/grpc_server/ai_service_pb2_grpc.py) -replace 'import ai_service_pb2', 'from . import ai_service_pb2' | Set-Content src/grpc_server/ai_service_pb2_grpc.py"

echo ✓ Fixed import paths

