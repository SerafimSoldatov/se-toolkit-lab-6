"""Shared fixtures for all tests"""

import pytest
import subprocess
import json

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
