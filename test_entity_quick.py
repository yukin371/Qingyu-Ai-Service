#!/usr/bin/env python
"""Quick test script for Entity Memory"""

import sys
import pytest

def main():
    """Run entity memory tests"""
    result = pytest.main([
        "tests/memory/conversation/test_entity_memory.py",
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure
        "-k", "not concurrent"  # Skip slow concurrent tests
    ])
    return result

if __name__ == "__main__":
    sys.exit(main())
