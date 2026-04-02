"""测试 gRPC 服务器基本功能"""
import sys
import io
from pathlib import Path

# 设置 UTF-8 编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("Testing gRPC Server Components")
print("=" * 60)
print()

# 测试导入
print("[1/4] Testing imports...")
try:
    from src.grpc_service import ai_service_pb2, ai_service_pb2_grpc
    print("  OK: Proto files imported")
except Exception as e:
    print(f"  FAIL: {e}")
    sys.exit(1)

try:
    from src.core.logger import get_logger
    logger = get_logger(__name__)
    print("  OK: Logger imported")
except Exception as e:
    print(f"  FAIL: {e}")
    sys.exit(1)

try:
    from src.grpc_service.server import serve
    print("  OK: Server module imported")
except Exception as e:
    print(f"  FAIL: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("[2/4] Testing servicer import (may take time)...")
try:
    from src.grpc_service.ai_servicer import AIServicer
    print("  OK: AIServicer imported")
except Exception as e:
    print(f"  FAIL: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("[3/4] Creating servicer instance...")
try:
    servicer = AIServicer()
    print("  OK: Servicer instance created")
except Exception as e:
    print(f"  FAIL: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("[4/4] All tests passed!")
print()
print("=" * 60)
print("gRPC server components are ready")
print("=" * 60)
