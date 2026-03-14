import subprocess
import json
import sys
from pathlib import Path

# Project root directory (two levels up from this test file if tests/ is in root)
PROJECT_ROOT = Path(__file__).parent.parent
AGENT_SCRIPT = PROJECT_ROOT / "agent.py"


def test_agent_returns_valid_json():
    """Run agent.py with a simple question and verify the JSON output."""
    # The question to ask
    question = "What is 2+2?"

    # Run the agent as a subprocess
    result = subprocess.run(
        [sys.executable, str(AGENT_SCRIPT), question],
        capture_output=True,
        text=True,
        timeout=30,          # should be well under 60 seconds
        cwd=PROJECT_ROOT,    # so .env.agent.secret is found
    )

    # Check exit code
    assert result.returncode == 0, f"Agent failed with stderr:\n{result.stderr}"

    # Parse stdout as JSON
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        assert False, f"stdout is not valid JSON: {result.stdout}"

    # Verify required fields
    assert "answer" in output, "Missing 'answer' field"
    assert isinstance(output["answer"], str), "'answer' must be a string"

    assert "tool_calls" in output, "Missing 'tool_calls' field"
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be a list"
    assert len(output["tool_calls"]) == 0, "'tool_calls' should be empty for Task 1"

    # Optional: check that the answer is plausible (contains "4")
    assert "4" in output["answer"] or "four" in output["answer"].lower(), \
        f"Answer '{output['answer']}' doesn't mention 4"
