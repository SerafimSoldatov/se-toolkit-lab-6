# Lab plan — Build Your Own Agent

**Topic:** Agent loop, LLM tool calling, CLI development, course review
**Date:** 2026-03-11

## Main goals

- Demystify the agent loop by building one from scratch.
- Reinforce understanding of all course material (labs 1-6) through an evaluation benchmark.
- Teach LLM API integration and tool calling as a transferable skill.

## Design principles

| Principle | Implication |
|-----------|-------------|
| Learn by debugging, not by one-shotting | Students iterate against a hidden benchmark. They see what fails, diagnose why, fix, re-run. |
| Specify interfaces, not implementations | We define CLI input/output format, tool schemas, eval criteria. How they build the agent is their choice. |
| Evaluate the agent, evaluate the student | The question bank tests both agent correctness AND student understanding of course material. |
| Build on what exists | The agent operates on their deployed lab 5 system (backend, DB, frontend). No new infrastructure. |
| Progressive difficulty | Basic questions need just an LLM. Tool questions need real implementations. Edge cases need iteration. |

## Learning outcomes

By the end of this lab, students should be able to:

- [Understand] Explain how an agentic loop works: user input → LLM → tool call → execute → feed result → repeat until final answer.
- [Apply] Integrate with an LLM API using the OpenAI-compatible chat completions format with tool/function calling.
- [Apply] Implement tools that read files, list directories, and query HTTP APIs, then register them as function-calling schemas.
- [Apply] Build a CLI that accepts structured input and produces structured output (JSON).
- [Analyze] Debug agent behavior by examining tool call traces, identifying prompt issues, and fixing tool implementations.
- [Evaluate] Assess agent quality against a benchmark, iterating on prompts and tools to improve pass rate.

## Lab story

You have a running Learning Management Service from the previous lab — a backend, a database full of analytics data, and a frontend dashboard. The course is coming to a close and you need to review everything you've learned. Instead of manually reviewing, you'll build a CLI agent that can answer questions about the course and about your own system. The agent uses an LLM with tools to read your codebase and query your API.

An evaluation benchmark tests your agent with ~30 questions. You can't see the questions upfront — you discover them by running the checker. Each failed question tells you what went wrong, and you fix it. By the time your agent passes, you've reviewed the course material and understood how agents work.

## Architecture

```
Student's VM:
  agent.py (CLI) ←→ OpenRouter API (free LLM)
       │
       ├── read_file(path)   → local filesystem
       ├── list_files(dir)   → local filesystem
       └── query_api(path)   → localhost:42002 (their deployed backend)

Autochecker:
  SSH → python agent.py '{"question":"..."}' → stdout JSON
  Compare answer against expected → PASS/FAIL
```

## LLM access

**Provider:** OpenRouter (free tier, zero cost)
- Students create an account at openrouter.ai, get an API key (no credit card)
- API is OpenAI-compatible: `POST https://openrouter.ai/api/v1/chat/completions`
- Default model: `meta-llama/llama-3.3-70b-instruct:free` (128k ctx, tool calling)
- 18+ free models support tool calling; students may switch

**Alternatives considered and rejected:**
- Shared API key: risk of leaks, hard to rate-limit per student
- Student-provided keys: unequal access, cost barrier
- Local models (Ollama): VM resources too limited, tool calling unreliable

## Tool interface

**Decision:** OpenAI-style function calling (industry standard).

Students define tools as JSON schemas in the `tools` parameter of the API request. The LLM returns structured `tool_calls`. Students execute the tool, send the result back as a `tool` role message, and loop until the LLM gives a final text answer.

**Alternatives considered and rejected:**
- Provided SDK/wrapper: hides how agents actually work, defeats the pedagogical goal
- Free-form text parsing (regex): fragile, non-standard, wastes time on parsing bugs

## CLI interface (all tasks)

**Input:** JSON argument with question field
```bash
python agent.py '{"question": "What does REST stand for?"}'
```

**Output:** Single JSON line to stdout
```json
{"answer": "Representational State Transfer.", "tool_calls": []}
```

With tools:
```json
{
  "answer": "The backend uses FastAPI.",
  "tool_calls": [
    {"tool": "read_file", "args": {"path": "backend/app/main.py"}, "result": "from fastapi import FastAPI..."}
  ]
}
```

**Rules:**
- Output must be valid JSON, single line, to stdout
- `answer` and `tool_calls` fields are required
- Debug/progress output goes to stderr only
- 60-second timeout per question
- Exit code 0 on success

## Required tools

### `read_file`
Read a file from the project repo. Must restrict to project directory.
- Parameters: `path` (string) — relative path from project root
- Returns: file contents or error message

### `list_files`
List files/directories at a path.
- Parameters: `path` (string) — relative directory path
- Returns: newline-separated listing

### `query_api`
Call the deployed backend API.
- Parameters: `method` (string), `path` (string), `body` (string, optional)
- Returns: JSON with status_code and body
- Must handle authentication (API key from env/config)

## Evaluation design

### How it works
Autochecker SSHes into VM, runs `python agent.py '{"question":"..."}'` for each eval question, parses JSON output, compares answer against expected.

### What students see
- ✅ green: passed — shows question and their answer (so they learn)
- ❌ red: failed — shows question, their answer, and expected match criteria
- Students target one failed question at a time

### Answer matching strategies
- `contains`: answer contains keyword(s)
- `regex`: answer matches pattern
- `numeric_gt` / `numeric_range`: numeric comparison
- `any_of`: answer contains any listed value
- `contains_all`: answer contains all listed values

### Tool usage verification
For `requires_tool` questions, `tool_calls` must be non-empty and include the expected tool.

### Question categories
- A: Course concepts (no tools) — Git, REST, Docker, SQL, testing, ETL, agents
- B: HTTP & REST (no tools) — status codes, methods, auth vs authz
- C: System architecture (read_file) — framework, DB, ORM, ports
- D: Code inspection (read_file, list_files) — auth mechanism, routers, test framework
- E: Live system queries (query_api) — item count, status codes, endpoint behavior
- F: Data analysis (query_api + reasoning) — scores, pass rates, groups

### Difficulty tiers
- Tier 1 (after task 1): ~15 basic questions, need ≥8 to pass
- Tier 2 (after task 2): ~12 tool questions, need ≥7 to pass
- Tier 3 (after task 3): all ~34 questions, need ≥26 (75%) to pass

## Required tasks

### Setup — Deploy Your System

Students deploy their completed lab 5 system on their VM. The autochecker verifies SSH access, API reachability, and that the database has data.

### Task 1 — Basic Agent Loop

Build `agent.py` CLI with: JSON input parsing → LLM API call (OpenRouter) → system prompt with course knowledge → JSON output. No tools yet. Tier 1 eval runs.

**Commit:** `feat: implement basic agent loop with LLM integration`

### Task 2 — Add Tools

Implement `read_file`, `list_files`, `query_api` tools with JSON schemas. Build the agent loop: LLM → detect tool_calls → execute → send result back → repeat. Tier 2 eval runs.

**Commit:** `feat: add tool calling (read_file, list_files, query_api)`

### Task 3 — Pass the Benchmark

Iterate until the full eval passes (≥75%). Debug one question at a time: fix prompts, improve tool descriptions, handle edge cases.

**Commit:** `feat: optimize agent to pass evaluation benchmark`

## Student workflow

```
1. Write/modify agent code
2. Test locally: python agent.py '{"question": "..."}'
3. Examine output — correct?
   ├── Yes → try another
   └── No → diagnose:
       ├── Wrong knowledge → fix system prompt
       ├── Tool not called → fix tool description
       ├── Tool error → fix tool implementation
       └── Wrong reasoning → improve prompts
4. Push code, run autochecker
5. See eval results (green/red)
6. Pick one failed question → go to 1
```

## Open questions

1. Should we provide a starter `agent.py` skeleton? Leaning yes — minimal argparse + main, not the LLM call.
2. Should we share ~5 sample questions for local testing? Leaning yes — tier 1 only.
3. Maximum agent loop iterations? Leaning 10 tool calls per question.
4. Does the agent code live in the project root or a subdirectory? Leaning root.
