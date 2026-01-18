"""
简单的gRPC服务器启动脚本
避免批处理文件编码问题
"""
import subprocess
import sys
import os
from pathlib import Path

# 设置当前目录为项目根目录
project_root = Path(__file__).parent
os.chdir(project_root)

print("=" * 60)
print("Phase3 gRPC Server Startup")
print("=" * 60)
print()

# 检查API密钥
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("ERROR: GOOGLE_API_KEY environment variable is not set")
    print()
    print("Please set it first:")
    print("  Windows: set GOOGLE_API_KEY=your_api_key")
    print("  Linux:   export GOOGLE_API_KEY=your_api_key")
    print()
    input("Press Enter to exit...")
    sys.exit(1)

print(f"API Key: {api_key[:20]}...")
print()

# 检查依赖
print("[1/2] Checking dependencies...")
try:
    import grpc
    import google.generativeai
    print("Dependencies: OK")
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Installing requirements...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

print()
print("[2/2] Starting gRPC server...")
print()
print("=" * 60)
print("Server will listen on 0.0.0.0:50051")
print("Press Ctrl+C to stop")
print("=" * 60)
print()

# 启动服务器
try:
    subprocess.run([
        sys.executable,
        "src/grpc_service/server.py",
        "--host", "0.0.0.0",
        "--port", "50051"
    ])
except KeyboardInterrupt:
    print()
    print("Server stopped")
    sys.exit(0)

