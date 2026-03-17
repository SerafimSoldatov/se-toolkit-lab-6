"""
Complete benchmark tests for all 10 questions from Task 3
Tests that agent uses correct tools and returns expected keywords
"""

import pytest
import json
import re

class TestBenchmarkQuestions:
    """Test all 10 benchmark questions from the task"""

    def test_q0_branch_protection(self, run_agent):
        """
        Question 0: According to the project wiki, what steps are needed to protect a branch on GitHub?
        Expected: read_file tool, keywords: branch, protect
        """
        result = run_agent("According to the project wiki, what steps are needed to protect a branch on GitHub?")
        
        # Check tool usage
        tools = [call["tool"] for call in result["tool_calls"]]
        assert "read_file" in tools, "Should use read_file tool"
        
        # Check answer contains keywords
        answer = result["answer"].lower()
        assert "branch" in answer, f"Answer missing 'branch': {answer[:100]}"
        assert "protect" in answer or "protection" in answer, f"Answer missing 'protect': {answer[:100]}"
        
        # Source should point to wiki
        assert "wiki/" in result["source"], f"Source should be from wiki: {result['source']}"

    def test_q1_ssh_connection(self, run_agent):
        """
        Question 1: What does the project wiki say about connecting to your VM via SSH?
        Expected: read_file tool, keywords: ssh, key, connect
        """
        result = run_agent("What does the project wiki say about connecting to your VM via SSH? Summarize the key steps.")
        
        # Check tool usage
        tools = [call["tool"] for call in result["tool_calls"]]
        assert "read_file" in tools, "Should use read_file tool"
        
        # Check answer contains keywords
        answer = result["answer"].lower()
        keywords = ["ssh", "key", "connect", "vm"]
        assert any(k in answer for k in keywords), f"Answer missing SSH keywords: {answer[:100]}"
        
        # Source should point to wiki
        assert "wiki/" in result["source"], f"Source should be from wiki: {result['source']}"

    def test_q2_fastapi_framework(self, run_agent):
        """
        Question 2: What Python web framework does this project's backend use?
        Expected: read_file tool, keyword: FastAPI
        """
        result = run_agent("What Python web framework does this project's backend use? Read the source code to find out.")
        
        # Check tool usage
        tools = [call["tool"] for call in result["tool_calls"]]
        assert "read_file" in tools, "Should use read_file tool"
        
        # Check it read Python files
        py_reads = [call for call in result["tool_calls"] 
                   if call["tool"] == "read_file" and ".py" in call["args"].get("path", "")]
        assert len(py_reads) > 0, "Should read Python source files"
        
        # Answer should mention FastAPI
        answer = result["answer"].lower()
        assert "fastapi" in answer, f"Answer should mention FastAPI: {answer[:100]}"

    def test_q3_api_router_modules(self, run_agent):
        """
        Question 3: List all API router modules in the backend. What domain does each one handle?
        Expected: list_files tool, keywords: items, interactions, analytics, pipeline
        """
        result = run_agent("List all API router modules in the backend. What domain does each one handle?")
        
        # Check tool usage
        tools = [call["tool"] for call in result["tool_calls"]]
        assert "list_files" in tools, "Should use list_files tool"
        
        # Check answer contains expected domains
        answer = result["answer"].lower()
        expected = ["items", "interactions", "analytics", "pipeline"]
        found = [e for e in expected if e in answer]
        assert len(found) >= 3, f"Expected at least 3 of {expected}, found: {found}"

    def test_q4_items_count(self, run_agent):
        """
        Question 4: How many items are currently stored in the database?
        Expected: query_api tool, answer contains a number
        """
        result = run_agent("How many items are currently stored in the database? Query the running API to find out.")
        
        # Check tool usage
        tools = [call["tool"] for call in result["tool_calls"]]
        assert "query_api" in tools, "Should use query_api tool"
        
        # Check it queried the items endpoint
        api_calls = [call for call in result["tool_calls"] 
                    if call["tool"] == "query_api" and "items" in call["args"].get("path", "")]
        assert len(api_calls) > 0, "Should query /items/ endpoint"
        
        # Answer should contain a number
        answer = result["answer"]
        assert any(c.isdigit() for c in answer), f"Answer should contain a number: {answer[:100]}"

    def test_q5_status_code_no_auth(self, run_agent):
        """
        Question 5: What HTTP status code does the API return when you request /items/ without auth?
        Expected: query_api tool, keywords: 401 or 403
        """
        result = run_agent("What HTTP status code does the API return when you request /items/ without an authentication header?")
        
        # Check tool usage
        tools = [call["tool"] for call in result["tool_calls"]]
        assert "query_api" in tools, "Should use query_api tool"
        
        # Answer should contain 401 or 403
        answer = result["answer"]
        assert "401" in answer or "403" in answer, f"Answer should contain 401 or 403: {answer[:100]}"

    def test_q6_zero_division_bug(self, run_agent):
        """
        Question 6: Query /analytics/completion-rate for lab-99. What error and what's the bug?
        Expected: query_api + read_file tools, keywords: ZeroDivisionError, division by zero
        """
        result = run_agent("Query /analytics/completion-rate for a lab with no data (e.g., lab-99). What error do you get, and what is the bug in the source code?")
        
        # Check both tools were used
        tools = [call["tool"] for call in result["tool_calls"]]
        assert "query_api" in tools, "Should use query_api tool"
        assert "read_file" in tools, "Should use read_file tool to find bug"
        
        # Check order: query_api should come before read_file
        tool_sequence = [call["tool"] for call in result["tool_calls"]]
        query_index = tool_sequence.index("query_api") if "query_api" in tool_sequence else -1
        read_index = tool_sequence.index("read_file") if "read_file" in tool_sequence else -1
        assert query_index < read_index, "Should query API first, THEN read code"
        
        # Answer should mention division by zero
        answer = result["answer"].lower()
        keywords = ["zerodivision", "division by zero", "divide by zero", "zero"]
        assert any(k in answer for k in keywords), f"Answer should mention division by zero: {answer[:200]}"

    def test_q7_top_learners_crash(self, run_agent):
        """
        Question 7: /analytics/top-learners crashes. Find error and explain.
        Expected: query_api + read_file tools, keywords: TypeError, None, NoneType, sorted
        """
        result = run_agent("The /analytics/top-learners endpoint crashes for some labs. Query it, find the error, and read the source code to explain what went wrong.")
        
        # Check both tools were used
        tools = [call["tool"] for call in result["tool_calls"]]
        assert "query_api" in tools, "Should use query_api tool"
        assert "read_file" in tools, "Should use read_file tool to find bug"
        
        # Answer should mention TypeError or None
        answer = result["answer"].lower()
        keywords = ["typeerror", "none", "nonetype", "sorted", "none type"]
        assert any(k in answer for k in keywords), f"Answer should mention TypeError/None: {answer[:200]}"

    def test_q8_request_journey(self, run_agent):
        """
        Question 8: Explain full journey of HTTP request from browser to database and back.
        Expected: read_file tool, must trace ≥4 hops: Caddy → FastAPI → auth → router → ORM → PostgreSQL
        """
        result = run_agent("Read docker-compose.yml and the backend Dockerfile. Explain the full journey of an HTTP request from the browser to the database and back.")
        
        # Check tool usage
        tools = [call["tool"] for call in result["tool_calls"]]
        assert "read_file" in tools, "Should use read_file tool"
        
        # Check it read the required files
        read_files = [call["args"].get("path", "") for call in result["tool_calls"] if call["tool"] == "read_file"]
        files_str = " ".join(read_files)
        assert "docker-compose.yml" in files_str or "docker" in files_str, "Should read docker-compose.yml"
        assert "Dockerfile" in files_str, "Should read Dockerfile"
        
        # Answer should mention key components (at least 4 hops)
        answer = result["answer"].lower()
        components = ["caddy", "fastapi", "auth", "router", "orm", "postgres", "postgresql", "database"]
        found = [c for c in components if c in answer]
        assert len(found) >= 4, f"Should mention at least 4 components from the journey. Found: {found}"

    def test_q9_etl_idempotency(self, run_agent):
        """
        Question 9: Explain how ETL pipeline ensures idempotency.
        Expected: read_file tool, must identify external_id check and explain duplicate skipping
        """
        result = run_agent("Read the ETL pipeline code. Explain how it ensures idempotency — what happens if the same data is loaded twice?")
        
        # Check tool usage
        tools = [call["tool"] for call in result["tool_calls"]]
        assert "read_file" in tools, "Should use read_file tool"
        
        # Check it read ETL-related files
        read_files = [call["args"].get("path", "") for call in result["tool_calls"] if call["tool"] == "read_file"]
        files_str = " ".join(read_files)
        assert "etl" in files_str or "pipeline" in files_str, "Should read ETL pipeline code"
        
        # Answer should mention external_id and duplicate handling
        answer = result["answer"].lower()
        keywords = ["external_id", "external id", "duplicate", "skip", "unique", "already exists"]
        found = [k for k in keywords if k in answer]
        assert len(found) >= 2, f"Should explain idempotency mechanism. Found keywords: {found}"


class TestToolUsage:
    """Additional tests to verify correct tool usage patterns"""

    def test_tool_selection_accuracy(self, run_agent):
        """Test that agent selects correct tool for different question types"""
        
        # Wiki question should use read_file on wiki
        wiki_result = run_agent("What does the wiki say about Git?")
        wiki_tools = [call["tool"] for call in wiki_result["tool_calls"]]
        assert "read_file" in wiki_tools
        wiki_reads = [call for call in wiki_result["tool_calls"] 
                     if call["tool"] == "read_file" and "wiki/" in call["args"].get("path", "")]
        assert len(wiki_reads) > 0, "Wiki question should read from wiki/"
        
        # Code question should read Python files
        code_result = run_agent("What's in the main.py file?")
        code_tools = [call["tool"] for call in code_result["tool_calls"]]
        assert "read_file" in code_tools
        code_reads = [call for call in code_result["tool_calls"] 
                     if call["tool"] == "read_file" and ".py" in call["args"].get("path", "")]
        assert len(code_reads) > 0, "Code question should read .py files"
        
        # API question should use query_api
        api_result = run_agent("Check if the API is healthy")
        api_tools = [call["tool"] for call in api_result["tool_calls"]]
        assert "query_api" in api_tools, "API question should use query_api"

    def test_max_tool_calls_respected(self, run_agent):
        """Test that agent never exceeds 10 tool calls"""
        result = run_agent("Tell me everything about the project architecture, including wiki docs, source code, and API endpoints.")
        assert len(result["tool_calls"]) <= 10, f"Exceeded max tool calls: {len(result['tool_calls'])}"

    def test_source_optional_for_api(self, run_agent):
        """Test that source can be empty for API-only questions"""
        result = run_agent("What's the current API status?")
        # Source is optional, so no assertion about its content
        assert "answer" in result
        assert "tool_calls" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
