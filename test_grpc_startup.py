"""测试 gRPC 服务器启动"""
import sys
import subprocess
import time
from pathlib import Path

# 启动服务器
proc = subprocess.Popen(
    [sys.executable, "src/grpc_service/server.py", "--host", "0.0.0.0", "--port", "50051"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    cwd=Path(__file__).parent
)

# 等待服务器启动
time.sleep(5)

# 终止服务器
proc.terminate()

# 读取输出
output = []
while True:
    line = proc.stdout.readline()
    if not line:
        break
    output.append(line)
    print(line.strip())

proc.wait()
print("\n服务器已停止")
