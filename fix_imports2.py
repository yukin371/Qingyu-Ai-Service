#!/usr/bin/env python3
"""Fix import statements in the codebase"""
import os
import re
from pathlib import Path

def fix_imports_in_file(file_path: Path):
    """Fix import statements in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Fix 'from tools.' to 'from src.tools.'
        content = re.sub(r'^from tools\.', 'from src.tools.', content, flags=re.MULTILINE)

        # Fix 'import tools.' to 'import src.tools.' (less common)
        content = re.sub(r'^import tools\.', 'import src.tools.', content, flags=re.MULTILINE)

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
