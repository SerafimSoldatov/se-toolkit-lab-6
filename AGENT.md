# AGENT.md

## Overview

`agent.py` is a command-line tool that sends a question to an LLM and returns a structured JSON response. It is the foundation for an agent that will later support tool calling (Tasks 2–3). For Task 1, the agent simply calls the LLM, returns the answer, and provides an empty `tool_calls` list.

## LLM Provider

**Provider:** Qwen Code API hosted on the student VM.  
**API Base:** `http://10.93.25.123:42005/v1` (after correcting the malformed URL)  
**Model:** `qwen3-coder-plus`

This provider was chosen because it offers:
- Free 1000 requests per day
- Good support for tool calling (needed in later tasks)
- Low latency within the VM network
- No credit card required

## Configuration

The agent reads its configuration from a `.env.agent.secret` file in the project root. This file contains:

```
LLM_API_KEY=my-new-secret-qwen-key
LLM_API_BASE=http://10.93.25.123:42005/v1
LLM_MODEL=qwen3-coder-plus
```

**Note:** The API key and base URL should match the actual Qwen Code API setup on the VM. The port `42005` is the exposed port from the Qwen Code API container.

## How It Works

1. **Read Input:** The agent takes the question as the first command-line argument.
2. **Load Environment:** It uses `python-dotenv` to load variables from `.env.agent.secret`.
3. **Validate:** Checks that all required environment variables are present; if any are missing, it prints an error to stderr and exits with code 1.
4. **Initialize Client:** Creates an OpenAI-compatible client with the given base URL and API key, setting a timeout of 30 seconds.
5. **Call LLM:** Sends a chat completion request with a minimal system prompt (`"You are a helpful assistant."`) and the user's question. Temperature is set to 0 for deterministic output.
6. **Handle Errors:** Catches any exceptions during the API call (connection errors, authentication failures, etc.), prints the error to stderr, and exits with code 1.
7. **Format Output:** Constructs a JSON object:
   ```json
   {
     "answer": "<LLM response>",
     "tool_calls": []
   }
   ```
   and prints it to stdout. Only this JSON line goes to stdout; all other output goes to stderr.
8. **Exit:** Exits with code 0 on success.

## Dependencies

- Python 3.10+
- `openai` – for the OpenAI-compatible client
- `python-dotenv` – to load environment variables from a `.env` file

Install with:
```bash
uv add openai python-dotenv
```

## Usage

Run the agent with a question:
```bash
uv run agent.py "What does REST stand for?"
```

Expected output (example):
```json
{"answer": "REST stands for Representational State Transfer.", "tool_calls": []}
```

## Error Handling Examples

- **Missing question:**
  ```
  $ uv run agent.py
  Error: No question provided.
  Usage: uv run agent.py "Your question"
  ```
  Exit code 1.

- **Missing environment variables:**
  ```
  Error: Missing environment variables: LLM_API_KEY, LLM_API_BASE
  Please ensure they are set in .env.agent.secret
  ```
  Exit code 1.

- **Connection error (e.g., VM unreachable):**
  ```
  Error calling LLM: Connection error.
  ```
  Exit code 1.

All error messages go to stderr, preserving the JSON-only stdout.

## Testing

A regression test is provided in `tests/test_agent.py`. It runs the agent with a simple question, checks that the exit code is 0, parses the stdout as JSON, and verifies the presence of `answer` (string) and `tool_calls` (empty list).

Run tests with:
```bash
uv run pytest tests/
```

## Architecture Diagram

```
User question → agent.py → OpenAI-compatible client → Qwen Code API (VM) → LLM response → JSON stdout
```

All debug/info output → stderr.

## Future Extensions

In Tasks 2–3, the agent will be extended to support tool calling. The `tool_calls` list in the output will be populated with tool invocations, and the agent will handle multi-step interactions. The current implementation provides the necessary plumbing for those extensions.

---

