"""
Regression tests for Task 2: The Documentation Agent
Exactly 2 tool-calling regression tests as required by the task
"""

import pytest
import subprocess
import json
import re

@pytest.fixture
def run_agent():
    """Helper to run the agent and return parsed output"""
    def _run_agent(question):
        result = subprocess.run(
            ["python", "agent.py", question],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0, f"Agent failed: {result.stderr}"
        return json.loads(result.stdout)
    return _run_agent

# ============================================================
# TEST 1: read_file tool test
# ============================================================
def test_merge_conflict_question(run_agent):
    """
    Test that agent uses read_file to answer about merge conflicts
    Expected: read_file in tool_calls, source points to git.md
    """
    result = run_agent("How do you resolve a merge conflict?")
    
    # 1. Check required fields exist
    assert "answer" in result, "Missing 'answer' field"
    assert "source" in result, "Missing 'source' field"
    assert "tool_calls" in result, "Missing 'tool_calls' field"
    
    # 2. Check that tool_calls is populated
    assert len(result["tool_calls"]) > 0, "tool_calls should not be empty"
    
    # 3. Check that read_file was used
    read_file_calls = [
        call for call in result["tool_calls"] 
        if call["tool"] == "read_file"
    ]
    assert len(read_file_calls) > 0, "Agent should use read_file tool"
    
    # 4. Check that it read a git-related file
    git_reads = [
        call for call in read_file_calls
        if "git" in call["args"].get("path", "").lower()
    ]
    assert len(git_reads) > 0, "Agent should read git documentation"
    
    # 5. Check source format
    assert "wiki/" in result["source"], f"Source should contain wiki/, got: {result['source']}"
    assert ".md" in result["source"], f"Source should be a .md file, got: {result['source']}"
    
    # 6. Check that answer mentions merge conflicts
    answer_lower = result["answer"].lower()
    conflict_terms = ["conflict", "merge", "<<<<<<<", "=======", ">>>>>>>", "marker"]
    assert any(term in answer_lower for term in conflict_terms), \
        f"Answer doesn't mention merge conflicts: {result['answer'][:100]}"

# ============================================================
# TEST 2: list_files tool test (FIXED VERSION)
# ============================================================
def test_list_wiki_files(run_agent):
    """
    Test that agent uses list_files to explore wiki
    Expected: list_files in tool_calls
    """
    result = run_agent("What files are in the wiki?")
    
    # 1. Check required fields exist
    assert "answer" in result, "Missing 'answer' field"
    assert "source" in result, "Missing 'source' field"
    assert "tool_calls" in result, "Missing 'tool_calls' field"
    
    # 2. Check that tool_calls is populated
    assert len(result["tool_calls"]) > 0, "tool_calls should not be empty"
    
    # 3. Check that list_files was used
    list_files_calls = [
        call for call in result["tool_calls"] 
        if call["tool"] == "list_files"
    ]
    assert len(list_files_calls) > 0, "Agent should use list_files tool"
    
    # 4. Check that it listed the wiki directory (FIXED)
    wiki_lists = [
        call for call in list_files_calls
        if "wiki" in call["args"].get("path", "").lower()
    ]
    assert len(wiki_lists) > 0, "Agent should list wiki directory"
    
    # 5. Check that answer mentions files
    answer_lower = result["answer"].lower()
    file_terms = ["file", "wiki", ".md", "documentation", "found"]
    assert any(term in answer_lower for term in file_terms), \
        f"Answer doesn't mention wiki files: {result['answer'][:100]}"
    
    # 6. Check that tool results contain file listings
    for call in list_files_calls:
        if "wiki" in call["args"].get("path", ""):
            assert call["result"] and len(call["result"]) > 0, \
                "list_files result should contain file names"
            break

# ============================================================
# Optional: Helper to run both tests
# ============================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
