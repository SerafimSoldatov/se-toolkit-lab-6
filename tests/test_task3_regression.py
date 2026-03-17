"""
Regression tests for Task 3: The System Agent
2 tool-calling regression tests as required
"""

import pytest
import sys
from pathlib import Path

# Add project root to path (in case conftest.py isn't loaded properly)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# The run_agent fixture should be automatically available from conftest.py

def test_backend_framework_question(run_agent):
    """
    Test that agent reads source code to identify framework
    Expected: read_file in tool_calls
    """
    result = run_agent("What Python web framework does this project's backend use? Read the source code to find out.")
    
    # Check required fields
    assert "answer" in result
    assert "tool_calls" in result
    
    # Check that read_file was used
    read_file_calls = [call for call in result["tool_calls"] if call["tool"] == "read_file"]
    assert len(read_file_calls) > 0, "Agent should use read_file tool"
    
    # Check that it read Python files
    py_reads = [call for call in read_file_calls if ".py" in call["args"].get("path", "")]
    assert len(py_reads) > 0, "Agent should read Python source files"
    
    # Answer should mention FastAPI
    answer_lower = result["answer"].lower()
    assert "fastapi" in answer_lower, f"Answer should mention FastAPI, got: {result['answer'][:100]}"

def test_items_count_question(run_agent):
    """
    Test that agent queries API for database item count
    Expected: query_api in tool_calls
    """
    result = run_agent("How many items are currently stored in the database? Query the running API to find out.")
    
    # Check required fields
    assert "answer" in result
    assert "tool_calls" in result
    
    # Check that query_api was used
    api_calls = [call for call in result["tool_calls"] if call["tool"] == "query_api"]
    assert len(api_calls) > 0, "Agent should use query_api tool"
    
    # Check that it called the items endpoint
    items_calls = [
        call for call in api_calls 
        if "items" in call["args"].get("path", "").lower()
    ]
    assert len(items_calls) > 0, "Agent should query /items/ endpoint"
    
    # Answer should contain a number
    answer = result["answer"]
    assert any(c.isdigit() for c in answer), f"Answer should contain a number, got: {answer[:100]}"
