"""
快速测试脚本 - 内置API密钥
"""
import os
import sys

# 直接设置API密钥（仅用于测试）
os.environ["GOOGLE_API_KEY"] = "AIzaSyD-q07WgZPd8mw4f1hVKVw44yXNUWrAuOk"

# 运行测试
if __name__ == "__main__":
    from pathlib import Path
    import subprocess

    project_root = Path(__file__).parent

    print("=" * 60)
    print("Phase3 gRPC Quick Test")
    print("=" * 60)
    print()
    print("API Key: Set (built-in)")
    print()
    print("Before testing, ensure gRPC server is running:")
    print("  python run_grpc_server.py")
    print()

    input("Press Enter to start test...")

    print()
    print("Running tests...")
    print()

    # 运行测试
    result = subprocess.run(
        [sys.executable, "tests/test_grpc_phase3.py"],
        cwd=project_root,
        env=os.environ.copy()
    )

    print()
    print("=" * 60)
    print("Test completed with exit code:", result.returncode)
    print("=" * 60)

    sys.exit(result.returncode)

