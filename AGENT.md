Here's a comprehensive `AGENT.md` that documents your agent according to the task requirements:

```markdown
# Documentation Agent

## Overview

This agent is a CLI tool that answers questions about the lab by reading the documentation in the `wiki/` directory. It implements an **agentic loop** with tool-calling capabilities to explore files and find answers.

## Agentic Loop

The agent follows this exact loop as specified in Task 2:

```
Question ──▶ LLM ──▶ tool call? ──yes──▶ execute tool ──▶ back to LLM
                         │
### Implementation

```python
MAX_TOOL_CALLS = 10
messages = [system_prompt, user_question]
tool_calls_history = []

while tool_call_count < MAX_TOOL_CALLS:
    response = call_llm(messages, tools)
    
    if response.has_tool_calls():
        for tool_call in response.tool_calls:
            result = execute_tool(tool_call)
            tool_calls_history.append({"tool": name, "args": args, "result": result})
            messages.append(assistant_message)
            messages.append(tool_response)
    else:
        # Final answer
        return {
            "answer": response.content,
            "source": extract_source(response.content),
            "tool_calls": tool_calls_history
        }
```

## Tools

The agent implements two tools as function-calling schemas:

### 1. `read_file`

Reads a file from the project repository.

- **Parameters:** `path` (string) — relative path from project root
- **Returns:** file contents as a string, or an error message if the file doesn't exist
- **Security:** Prevents directory traversal (no `../` access outside project)

**Tool Schema:**
```json
{
  "type": "function",
  "function": {
    "name": "read_file",
    "description": "Read a file from the project repository",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {
          "type": "string",
          "description": "Relative path from project root"
        }
      },
      "required": ["path"]
    }
  }
}
```

### 2. `list_files`

Lists files and directories at a given path.

- **Parameters:** `path` (string) — relative directory path from project root
- **Returns:** newline-separated listing of entries
- **Security:** Prevents directory traversal

**Tool Schema:**
```json
{
  "type": "function",
  "function": {
    "name": "list_files",
    "description": "List files and directories at a given path",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {
          "type": "string",
          "description": "Relative directory path from project root"
        }
      },
      "required": ["path"]
    }
  }
}
```

## System Prompt Strategy

The system prompt instructs the LLM to:

1. **Explore first**: Use `list_files('wiki')` to discover available documentation
2. **Read relevant files**: Use `read_file()` on files that might contain the answer
3. **Find answers**: Extract information from file contents
4. **Cite sources**: Include the source reference in the format `wiki/filename.md#section`

```python
SYSTEM_PROMPT = """You are a documentation agent. You have access to two tools:
- list_files(path): List files in a directory
- read_file(path): Read a file's contents

The wiki is in the 'wiki/' directory. Always:
1. First use list_files('wiki') to see what files exist
2. Then use read_file on relevant files to find answers
3. When you answer, include the source as 'wiki/filename.md#section'"""
```

## CLI Interface

The agent accepts a single question as a command-line argument:

```bash
python agent.py "How do you resolve a merge conflict?"
```

### Output Format

The agent returns a JSON object with three required fields:

```json
{
  "answer": "Edit the conflicting file, choose which changes to keep, then stage and commit.",
  "source": "wiki/git.md#merge-conflict",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git.md\nworkflow.md\n..."
    },
    {
      "tool": "read_file",
      "args": {"path": "wiki/git.md"},
      "result": "# Git documentation..."
    }
  ]
}
```

- **`answer`** (string): The final answer to the user's question
- **`source`** (string): The wiki section that contains the answer (format: `wiki/filename.md#section`)
- **`tool_calls`** (array): All tool calls made during the agentic loop, each with `tool`, `args`, and `result`

## Configuration

Create a `.env.agent.secret` file:

```env
LLM_API_KEY=your-api-key-here
LLM_API_BASE=http://your-vm-ip:port/v1
LLM_MODEL=qwen3-coder-plus
```

Supported models:
- `qwen3-coder-plus` (Qwen 3 Coder Plus)
- `qwen3-coder-flash` (faster variant)
- `coder-model` (Qwen 3.5 Plus)
- Any OpenRouter model (e.g., `openai/gpt-3.5-turbo`)

The agent automatically loads this file at startup.

## Security Features

### Path Traversal Prevention

Both tools implement strict path validation:

```python
def is_safe_path(path: str) -> bool:
    """Prevent directory traversal attacks"""
    try:
        full_path = (PROJECT_ROOT / path).resolve()
        return str(full_path).startswith(str(PROJECT_ROOT))
    except:
        return False
```

This ensures:
- No access to files outside the project directory
- No `../` traversal
- No absolute paths (e.g., `/etc/passwd`)
- Safe file reading and listing

## Error Handling

The agent handles various error cases gracefully:

| Error Case | Handling |
|------------|----------|
| Missing API key | Exits with clear error message |
| Network errors | Returns error in answer field |
| Invalid paths | Returns error in tool result |
| File not found | Returns error message in tool result |
| Max tool calls (10) | Returns partial answer with explanation |

## Testing

### Regression Tests (Required)

The agent includes exactly 2 tool-calling regression tests as required:

1. **`test_merge_conflict_question`** - Verifies `read_file` tool usage
2. **`test_list_wiki_files`** - Verifies `list_files` tool usage

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run only the required regression tests
pytest tests/test_task2_regression.py -v

# Run with coverage
pytest tests/ --cov=agent.py --cov-report=term-missing
```

### Test Structure

```python
def test_merge_conflict_question(run_agent):
    """Test that agent uses read_file to answer about merge conflicts"""
    result = run_agent("How do you resolve a merge conflict?")
    
    # Verify tool usage
    assert any(call["tool"] == "read_file" for call in result["tool_calls"])
    
    # Verify source format
    assert "wiki/" in result["source"]
    assert ".md" in result["source"]
    
    # Verify answer relevance
    assert any(term in result["answer"].lower() for term in ["conflict", "merge"])
```

## Project Structure

```
se-toolkit-lab-6/
├── agent.py                 # Main agent implementation
├── .env.agent.secret       # API configuration (not in git)
├── wiki/                    # Documentation files
│   ├── git.md
│   ├── workflow.md
│   └── ...
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── conftest.py          # Shared pytest fixtures
│   ├── test_task2_regression.py  # Required regression tests
│   ├── test_agent_loop.py   # Agentic loop tests
│   ├── test_tool_security.py # Security tests
│   └── test_integration.py  # Integration tests
├── plans/                    # Implementation plans
│   └── task-2.md            # Task 2 implementation plan
└── AGENT.md                 # This documentation
```

## Implementation Plan

The implementation followed the plan in `plans/task-2.md`:

1. **Tool Schemas**: Defined `read_file` and `list_files` with OpenAI function-calling format
2. **Agentic Loop**: Implemented the loop with max 10 tool calls
3. **Security**: Added path traversal prevention
4. **Source Extraction**: Added logic to extract wiki section references
5. **Testing**: Created regression tests for both tools

## Dependencies

- `requests`: HTTP calls to LLM API
- `pytest`: Testing framework
- `pytest-cov`: Test coverage (optional)

Install with:
```bash
pip install requests pytest pytest-cov
```

## Git Workflow

The agent was developed following the required Git workflow:

1. Issue created: `[Task] The Documentation Agent`
2. Branch created: `task-2-documentation-agent`
3. Commits made with clear messages
4. Pull request opened with `Closes #...`
5. Partner approval obtained
6. Merged to main

---
