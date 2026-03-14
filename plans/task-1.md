# Task 1: Call an LLM from Code - Implementation Plan

## LLM Provider and Model
- **Provider**: Qwen Code API hosted on the student VM.
- **API Base**: `http://10.93.25.123//:42005/v1` (note: double slash before port – this may need correction; verify the actual endpoint format)
- **Model**: `qwen3-coder-plus`

## Environment Configuration
- Use `.env.agent.secret` to store the following variables:
  ```
  LLM_API_KEY=my-new-secret-qwen-key
  LLM_API_BASE=http://10.93.25.123//:42005/v1
  LLM_MODEL=qwen3-coder-plus
  ```
- Load these in `agent.py` using `python-dotenv` (or `os.getenv` with a fallback to manual dotenv loading).

## Agent Structure
1. Read the question from the first command-line argument (`sys.argv[1]`). If missing, print error to stderr and exit with code 1.
2. Load environment variables from `.env.agent.secret` using `dotenv.load_dotenv()`.
3. Check that `LLM_API_KEY`, `LLM_API_BASE`, and `LLM_MODEL` are set; if any are missing, print a descriptive error to stderr and exit.
4. Create an OpenAI-compatible client with:
   - `api_key` from environment
   - `base_url` from environment
   - `timeout` set to 30 seconds (to stay within the 60-second overall limit)
5. Call the chat completions endpoint with:
   - Model: the value from `LLM_MODEL`
   - Messages: a simple system prompt (`"You are a helpful assistant."`) and the user question.
   - `temperature=0.0` for deterministic answers.
6. Extract the answer from `response.choices[0].message.content`.
7. Construct a JSON object:
   ```json
   {
     "answer": "<the LLM answer>",
     "tool_calls": []
   }
   ```
8. Print the JSON to stdout (only that line; no other output).
9. If any exception occurs during the API call, print the error to stderr and exit with code 1.

## Error Handling
- **Missing question**: print usage to stderr, exit 1.
- **Missing environment variables**: list missing ones, exit 1.
- **API connection/timeout errors**: catch exception, print error, exit 1.
- All debug/progress information goes to stderr only.

## Testing Strategy
- Write a regression test (e.g., `tests/test_agent.py`) that runs:
  ```bash
  uv run agent.py "What is 2+2?"
  ```
- Verify:
  - Exit code 0.
  - stdout is valid JSON.
  - JSON contains `"answer"` (string) and `"tool_calls"` (list).
  - `"tool_calls"` is an empty list.
- The test should use `subprocess` to run the agent and assert the output.
- The test will depend on the `.env.agent.secret` file being present with valid credentials. For local development, this is acceptable; for CI, we may need to mock the API or provide a test environment.

## Potential Issues and Mitigations
- **API base format**: The provided URL `http://10.93.25.123//:42005/v1` has an extra slash before the port – this might cause connection errors. Verify the correct endpoint (e.g., `http://10.93.25.123:42005/v1` or `http://10.93.25.123/v1` with port implied) and adjust the environment variable accordingly.
- **API key validity**: Ensure the key `my-new-secret-qwen-key` is correct and active.
- **Network reachability**: The VM IP must be accessible from where the agent runs.
- **Timeout**: If the API is slow, the 30-second client timeout might be too short; we can increase it or implement retries later. For now, 30 seconds should be sufficient for a simple call.
