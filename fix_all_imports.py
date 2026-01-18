#!/usr/bin/env python3
"""Fix all import statements in the codebase"""
import os
import re
from pathlib import Path

def fix_imports_in_file(file_path: Path):
    """Fix import statements in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Fix all module imports to use src. prefix
        replacements = [
            (r'^from agents\.', 'from src.agents.'),
            (r'^from tools\.', 'from src.tools.'),
            (r'^from config\.', 'from src.config.'),
            (r'^from core\.', 'from src.core.'),
            (r'^from rag\.', 'from src.rag.'),
            (r'^from grpc_service\b', 'from src.grpc_service'),
            (r'^from grpc_server\b', 'from src.grpc_server'),
            (r'^from services\b', 'from src.services'),
            (r'^from llm\b', 'from src.llm'),
            (r'^from infrastructure\b', 'from src.infrastructure'),
        ]

        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        # Only write if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function"""
    src_dir = Path("D:/Github/青羽/Qingyu_backend/python_ai_service/src")

    # Find all Python files
    py_files = list(src_dir.rglob("*.py"))

    fixed_count = 0
    for file_path in py_files:
        if fix_imports_in_file(file_path):
            fixed_count += 1

    print(f"\nTotal files fixed: {fixed_count}")

if __name__ == "__main__":
    main()
