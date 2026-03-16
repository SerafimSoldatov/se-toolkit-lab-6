"""Test agentic loop behavior"""

import pytest
import subprocess
import json

def test_max_tool_calls_limit(run_agent):
    """Test that agent respects 10 tool call limit"""
    # Ask a complex question that might need many tool calls
    result = run_agent("Tell me everything about git")
    
    assert len(result["tool_calls"]) <= 10, \
        f"Agent made {len(result['tool_calls'])} tool calls, exceeding limit of 10"

def test_tool_calls_structure(run_agent):
    """Test that tool_calls entries have correct structure"""
    result = run_agent("What files are in the wiki?")
    
    for call in result["tool_calls"]:
        assert "tool" in call, f"Missing 'tool' in {call}"
        assert "args" in call, f"Missing 'args' in {call}"
        assert "result" in call, f"Missing 'result' in {call}"
        assert isinstance(call["args"], dict), f"args should be dict, got {type(call['args'])}"
        assert isinstance(call["result"], str), f"result should be str, got {type(call['result'])}"

def test_source_format(run_agent):
    """Test that source field follows required format"""
    result = run_agent("How do you configure git?")
    
    source = result["source"]
    assert "wiki/" in source, f"Source should contain wiki/, got: {source}"
    assert ".md" in source, f"Source should be a .md file, got: {source}"
