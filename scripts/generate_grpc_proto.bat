@echo off
REM Generate gRPC Python Code

echo ========================================
echo Generate gRPC Protobuf Code
echo ========================================

cd /d %~dp0..

echo.
echo [1/3] Checking dependencies...
python -c "import grpc_tools.protoc" 2>NUL
if errorlevel 1 (
    echo grpcio-tools not installed, installing...
    pip install grpcio-tools
)

echo.
echo [2/3] Generating Python protobuf code...
python -m grpc_tools.protoc ^
    -I proto ^
    --python_out=src\grpc_service ^
    --grpc_python_out=src\grpc_service ^
    proto\ai_service.proto

if errorlevel 1 (
    echo Code generation failed
    pause
    exit /b 1
)

echo.
echo [3/3] Fixing import paths...
REM Fix import paths in generated code
python -c "pb_file='src/grpc_service/ai_service_pb2_grpc.py'; content=open(pb_file).read(); content=content.replace('import ai_service_pb2', 'from . import ai_service_pb2'); open(pb_file, 'w').write(content)" 2>NUL

echo.
echo Code generation completed!
echo Generated files:
echo   - src\grpc_service\ai_service_pb2.py
echo   - src\grpc_service\ai_service_pb2_grpc.py
echo.
pause

