"""
简单的gRPC测试启动脚本
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
print("Phase3 gRPC Service Test")
print("=" * 60)
print()

# 检查API密钥
if not os.getenv("GOOGLE_API_KEY"):
    print("ERROR: GOOGLE_API_KEY environment variable is not set")
    print()
    print("Please set it first:")
    print("  Windows: set GOOGLE_API_KEY=your_api_key")
    print("  Linux:   export GOOGLE_API_KEY=your_api_key")
    sys.exit(1)

print("API Key: OK")
print()

# 提示检查服务器
print("Before testing, ensure:")
print("  1. gRPC server is running")
print("  2. Server is listening on localhost:50051")
print()
print("If server is not running, start it first:")
print("  python src/grpc_service/server.py")
print()

input("Press Enter to continue...")

# 运行测试
print()
print("Starting tests...")
print()

result = subprocess.run(
    [sys.executable, "tests/test_grpc_phase3.py"],
    cwd=project_root
)

print()
print("=" * 60)
print("Test completed with exit code:", result.returncode)
print("=" * 60)

sys.exit(result.returncode)

