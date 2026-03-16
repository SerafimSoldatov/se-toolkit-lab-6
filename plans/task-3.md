# Task 3: The System Agent - Implementation Plan

## Initial Benchmark Run (Before Implementation)

**Date:** 2026-03-16
**Score:** 3/10

**Failures observed:**
- Questions 4-5: Agent doesn't have `query_api` tool yet
- Questions 6-7: Cannot diagnose bugs without API access
- Questions 8-9: Complex reasoning failing due to missing data

## 1. New Tool: `query_api`

### Tool Schema (OpenAI function-calling format)
```json
{
  "type": "function",
  "function": {
    "name": "query_api",
    "description": "Send HTTP requests to the backend API to get live system data",
    "parameters": {
      "type": "object",
      "properties": {
        "method": {
          "type": "string",
          "enum": ["GET", "POST", "PUT", "DELETE"],
          "description": "HTTP method for the request"
        },
        "path": {
          "type": "string",
          "description": "API endpoint path (e.g., '/items/', '/analytics/completion-rate?lab=lab-99')"
        },
        "body": {
          "type": "string",
          "description": "Optional JSON request body for POST/PUT requests"
        }
      },
      "required": ["method", "path"]
    }
  }
}
```

### Implementation Details

**Configuration (from environment variables):**
- `LMS_API_KEY` - Backend API key (from `.env.docker.secret`)
- `AGENT_API_BASE_URL` - Base URL for API (default: `http://localhost:42002`)

**Request Format:**
```python
headers = {
    "X-API-Key": LMS_API_KEY,
    "Content-Type": "application/json"
}
url = urljoin(AGENT_API_BASE_URL, path)
```

**Return Format:**
```python
{
    "status_code": 200,
    "body": response_data  # Parsed JSON or raw text
}
```

**Error Handling:**
- Connection errors → return descriptive message
- HTTP errors → include status code and error body
- Timeouts → return timeout message
- Invalid JSON body → return parsing error

### Security Considerations
- Validate that paths don't try to access internal endpoints
- Limit to configured base URL (no external redirects)
- Sanitize request bodies to prevent injection

## 2. System Prompt Updates

### New Prompt Strategy

The LLM needs to distinguish between three types of questions:

| Question Type | Examples | Required Tools |
|--------------|----------|----------------|
| Documentation | "How to protect a branch?" | `list_files` + `read_file` (wiki/) |
| Source Code | "What framework does the backend use?" | `read_file` (`.py` files) |
| Live Data | "How many items in database?" | `query_api` |
| Bug Diagnosis | "Why does /analytics crash?" | `query_api` + `read_file` |

### Updated System Prompt
```
You are a system agent that can answer questions by:
1. Reading wiki documentation (use list_files + read_file on wiki/)
2. Reading source code (use read_file on Python files)
3. Querying the live backend API (use query_api)

For each question, decide which tool(s) you need:
- Documentation questions → use wiki files
- Framework/code questions → read source code
- Data questions (counts, status) → query the API
- Bug diagnosis → query API then read source code

Always explore before reading. When you have the answer, include the source if applicable.
For API responses, report the actual data you receive.
```

## 3. Environment Variables

### Required Variables
| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API key for `query_api` | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Base URL for API (optional) | Default: `http://localhost:42002` |

### Important Note
The autochecker injects its own values. No hardcoding!

## 4. Implementation Steps

### Phase 1: Basic `query_api` (Day 1)
- [x] Add tool schema to `TOOLS` list
- [ ] Implement `query_api` function with requests library
- [ ] Add environment variable loading for `LMS_API_KEY`
- [ ] Test with simple GET request to `/items/`

### Phase 2: Error Handling (Day 1)
- [ ] Add connection error handling
- [ ] Add HTTP error status handling
- [ ] Add timeout configuration
- [ ] Test with invalid endpoints

### Phase 3: Prompt Engineering (Day 2)
- [ ] Update system prompt with decision guidelines
- [ ] Test documentation questions
- [ ] Test source code questions
- [ ] Test API data questions
- [ ] Test bug diagnosis questions (API + code)

### Phase 4: Benchmark Iteration (Day 2-3)
- [ ] Run `run_eval.py` and record failures
- [ ] Fix each failing question one by one
- [ ] Track improvements

## 5. Testing Strategy

### New Regression Tests (Required)

**Test 1: Source Code Reading**
```python
def test_backend_framework_question(run_agent):
    """Test that agent reads source code to identify framework"""
    result = run_agent("What framework does the backend use?")
    assert any(call["tool"] == "read_file" for call in result["tool_calls"])
    assert "fastapi" in result["answer"].lower()
```

**Test 2: API Query**
```python
def test_items_count_question(run_agent):
    """Test that agent queries API for database item count"""
    result = run_agent("How many items are in the database?")
    assert any(call["tool"] == "query_api" for call in result["tool_calls"])
    assert any(c.isdigit() for c in result["answer"])
```

### Additional Tests
- [ ] Test authentication failure handling
- [ ] Test POST requests
- [ ] Test query parameters
- [ ] Test error responses

## 6. Benchmark Questions Analysis

### Local Benchmark (10 questions)

| # | Question | Required Tools | Current Status | Fix Strategy |
|---|----------|----------------|----------------|--------------|
| 0 | Branch protection | `read_file` (wiki) | ✅ Working | - |
| 1 | SSH connection | `read_file` (wiki) | ✅ Working | - |
| 2 | Python framework | `read_file` (code) | ✅ Working | - |
| 3 | API modules | `list_files` | ✅ Working | - |
| 4 | Items count | `query_api` | ❌ Failing | Implement `query_api` |
| 5 | Status code w/o auth | `query_api` | ❌ Failing | Implement `query_api` |
| 6 | ZeroDivisionError bug | `query_api` + `read_file` | ❌ Failing | Chain tools |
| 7 | Top learners crash | `query_api` + `read_file` | ❌ Failing | Chain tools |
| 8 | Request lifecycle | `read_file` + LLM judge | ❌ Failing | Improve reasoning |
| 9 | ETL idempotency | `read_file` + LLM judge | ❌ Failing | Improve reasoning |

### Hidden Benchmark (10 additional questions)
The autochecker tests with hidden questions including:
- Multi-step reasoning challenges
- Complex bug diagnosis scenarios
- Performance with different API states
- Edge cases in tool selection

## 7. Iteration Plan

### Iteration 1: Basic API functionality
**Goal:** Pass questions 4-5
- Implement `query_api` with GET requests
- Add authentication headers
- Return formatted responses

### Iteration 2: Error handling and bug diagnosis
**Goal:** Pass questions 6-7
- Improve error message parsing
- Chain `query_api` with `read_file`
- Help LLM correlate API errors with code

### Iteration 3: Complex reasoning
**Goal:** Pass questions 8-9
- Enhance system prompt for multi-step reasoning
- Add examples of combining multiple sources
- Fine-tune source extraction

### Iteration 4: Optimization
**Goal:** Pass all 10 local questions + hidden benchmark
- Reduce unnecessary tool calls
- Improve response speed
- Handle edge cases

## 8. Expected Challenges and Solutions

| Challenge | Solution |
|-----------|----------|
| LLM chooses wrong tool | Enhance tool descriptions, add examples |
| API errors not helpful | Parse and simplify error messages |
| Too many tool calls | Implement early stopping when answer found |
| Source missing for API answers | Make source optional, document in prompt |
| Authentication failures | Clear error messages, verify env vars |
| Rate limiting | Add delays between requests |

## 9. Success Criteria

- [ ] `query_api` tool implemented with proper schema
- [ ] Authentication works with `LMS_API_KEY`
- [ ] All config from environment variables
- [ ] `run_eval.py` passes 10/10 locally
- [ ] 2 new regression tests pass
- [ ] AGENT.md updated with system agent docs
- [ ] Passes autochecker benchmark
- [ ] PR merged with partner approval

## 10. Progress Tracking

### Initial Score: 3/10 (before implementation)
Date: 2026-03-16

### Iteration 1 Score: 5/10
Date: TBD
Improvements: Added query_api, passed questions 4-5

### Iteration 2 Score: 7/10
Date: TBD
Improvements: Bug diagnosis working, passed 6-7

### Iteration 3 Score: 9/10
Date: TBD
Improvements: Complex reasoning, passed 8-9

### Final Score: 10/10
Date: TBD
Goal achieved! Ready for autochecker.

---

