"""简单的 gRPC 测试脚本"""
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
print("Testing gRPC Server Import")
print("=" * 60)

try:
    print("[1/3] Importing proto files...")
    from src.grpc_service import ai_service_pb2, ai_service_pb2_grpc
    print("  ✓ Proto files imported successfully")
except Exception as e:
    print(f"  ✗ Failed to import proto files: {e}")
    sys.exit(1)

try:
    print("[2/3] Importing logger...")
    from src.core.logger import get_logger
    logger = get_logger(__name__)
    print("  ✓ Logger imported successfully")
except Exception as e:
    print(f"  ✗ Failed to import logger: {e}")
    sys.exit(1)

try:
    print("[3/3] Importing servicer...")
    from src.grpc_service.ai_servicer import AIServicer
    print("  ✓ AIServicer imported successfully")
except Exception as e:
    print(f"  ✗ Failed to import AIServicer: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 60)
print("All imports successful!")
print("=" * 60)
