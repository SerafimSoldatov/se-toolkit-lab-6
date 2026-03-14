# Task 2: The Documentation Agent - Implementation Plan

## 1. Tool Schemas Definition
- Define `read_file` tool with `path` parameter
- Define `list_files` tool with `path` parameter
- Format tools according to OpenAI function-calling schema

## 2. Agentic Loop Implementation

MAX_TOOL_CALLS = 10
tool_call_count = 0
messages = [system_prompt, user_message]

while tool_call_count < MAX_TOOL_CALLS:
response = call_llm(messages, tools)

if response.has_tool_calls():
for tool_call in response.tool_calls:
tool_call_count++
result = execute_tool(tool_call)
messages.append(tool_response_message)
track tool_call in tool_calls_history
else 


## 3. Tool Implementations
- `read_file(path)`: Read file content, validate path safety
- `list_files(path)`: List directory contents, validate path safety
- Path security: Prevent directory traversal attacks

## 4. System Prompt Strategy
Tell the LLM to:
1. Use `list_files` to discover wiki structure
2. Use `read_file` to read relevant wiki files
3. Find answers in wiki files
4. Return source as `wiki/filename.md#section`
5. Stop when answer found

## 5. Output Format
JSON with:
- `answer`: The final answer text
- `source`: Wiki section reference
- `tool_calls`: Array of all tool calls made
