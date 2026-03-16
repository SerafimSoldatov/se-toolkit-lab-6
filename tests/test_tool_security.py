"""Test security requirements from Task 2"""

import pytest
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agent import read_file, list_files

def test_read_file_security():
    """Test that read_file prevents directory traversal"""
    # Test various traversal attempts
    attempts = [
        "../../../etc/passwd",
        "/etc/passwd",
        "..",
        "../",
        "wiki/../../etc/passwd",
        "....//....//etc/passwd",
        "%2e%2e%2fetc/passwd",
    ]
    
    for path in attempts:
        result = read_file(path)
        assert "error" in result.lower() or "invalid" in result.lower() or "outside" in result.lower(), \
            f"Should block path traversal: {path} - got: {result}"

def test_list_files_security():
    """Test that list_files prevents directory traversal"""
    attempts = [
        "../../..",
        "/",
        "../",
        "wiki/../../",
        "/root",
        "....//....//",
    ]
    
    for path in attempts:
        result = list_files(path)
        assert "error" in result.lower() or "invalid" in result.lower() or "outside" in result.lower(), \
            f"Should block path traversal: {path} - got: {result}"
