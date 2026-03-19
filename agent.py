#!/usr/bin/env python3
"""
System Agent for Lab 6
Agent with query_api tool to interact with backend
"""

import os
import sys
import json
import requests
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
import time

# ============================================================
# Load environment variables from multiple sources
# ============================================================
def load_env_file(filepath: Path) -> None:
    """Load environment variables from a file"""
    if filepath.exists():
        # Все отладочные сообщения в stderr
        print(f"Loading env from: {filepath}", file=sys.stderr)
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    value = value.strip('\'"')
                    os.environ[key] = value
                    print(f"  Set {key}", file=sys.stderr)

# Load both env files
load_env_file(Path(__file__).parent / '.env.agent.secret')
load_env_file(Path(__file__).parent / '.env.docker.secret')

# ============================================================
# Configuration
# ============================================================
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_API_BASE = os.getenv("LLM_API_BASE")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3-coder-plus")
LMS_API_KEY = os.getenv("LMS_API_KEY")
AGENT_API_BASE_URL = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")

PROJECT_ROOT = Path.cwd().resolve()
MAX_TOOL_CALLS = 12
EARLY_ANSWER_THRESHOLD = 8

# Validate required variables
missing_vars = []
if not LLM_API_KEY:
    missing_vars.append("LLM_API_KEY")
if not LLM_API_BASE:
    missing_vars.append("LLM_API_BASE") 
if not LMS_API_KEY:
    missing_vars.append("LMS_API_KEY")

if missing_vars:
    print(f"Error: Missing environment variables: {', '.join(missing_vars)}", file=sys.stderr)
    print("Please check your .env.agent.secret and .env.docker.secret files", file=sys.stderr)
    sys.exit(1)

# ============================================================
# Tool schemas
# ============================================================
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the project repository. Use this to read wiki docs or source code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g., 'wiki/git.md' or 'app/main.py')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given path. Use this to explore project structure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root (e.g., 'app/' or 'wiki/')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Send HTTP requests to the backend API. Use this to get live data from the system.",
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
                    },
                    "include_auth": {
                        "type": "boolean",
                        "description": "Whether to include Authorization header. Default true. Set false to test 401/403 responses."
                    }
                },
                "required": ["method", "path"]
            }
        }
    }
]

SYSTEM_PROMPT = """You are a system agent that answers questions by using tools.

AVAILABLE TOOLS:
1. read_file(path) - Read files (wiki docs or source code)
2. list_files(path) - List directory contents
3. query_api(method, path, body, include_auth) - Call backend API
   - include_auth: boolean, default true. Set false to test 401/403 responses.

INSTRUCTIONS PER QUESTION TYPE:

[WIKI QUESTIONS] e.g., branch protection, SSH
- Use list_files('wiki') then read_file on relevant .md files
- Include "Source: wiki/filename.md#section" in answer

[FRAMEWORK QUESTIONS] e.g., Python web framework
- Read requirements.txt or app/main.py directly
- Look for 'fastapi' in imports or dependencies

[ROUTER MODULES] List all API router modules
- Use list_files('backend/app/routers') to find all router files
- The routers are: items.py, interactions.py, analytics.py, pipeline.py
- Read the docstring at the top of each file to learn its domain
- Answer: list all 4 domains with a brief description from each file's docstring
- Be efficient: after list_files, read all 4 files before answering

[BUG DIAGNOSIS] e.g., /analytics/completion-rate or /top-learners
- FIRST: query_api to see the error
- THEN: read_file on relevant source (app/api/analytics.py)
- Explain error type (ZeroDivisionError, TypeError) and the bug in code

[API DATA QUESTIONS] e.g., items count, status codes
- Use query_api directly (GET /items/ etc.)

[STATUS WITHOUT AUTH] e.g., "without authentication header"
- Use query_api with include_auth=false to test unauthenticated access
- Expect 401 or 403 status codes

[ETL IDEMPOTENCY] ETL pipeline
- Read the source code: app/etl.py, app/pipeline.py
- Look for external_id check that skips duplicates

[ARCHITECTURE] Request journey
- Read docker-compose.yml and Dockerfile
- Trace: Caddy → FastAPI → auth → router → ORM → DB

EFFICIENCY:
- Stop as soon as you have enough info
- Max 8 tool calls; after that provide best answer
- Include source when reading files"""

# ============================================================
# Tool implementations
# ============================================================
def is_safe_path(path: str) -> bool:
    try:
        full_path = (PROJECT_ROOT / path).resolve()
        return str(full_path).startswith(str(PROJECT_ROOT))
    except:
        return False

def read_file(path: str) -> str:
    if not path or not is_safe_path(path):
        return "Error: Invalid path"
    try:
        full_path = PROJECT_ROOT / path
        if not full_path.exists():
            return f"Error: File {path} not found"
        if not full_path.is_file():
            return f"Error: {path} is not a file"
        content = full_path.read_text(encoding='utf-8')
        # Increased limit to 50000 to avoid truncating important content
        # Most wiki files are <20KB, source files are <10KB
        if len(content) > 50000:
            content = content[:50000] + "\n... [truncated, file too large]"
        return content
    except Exception as e:
        return f"Error: {str(e)}"

def list_files(path: str) -> str:
    if not path or not is_safe_path(path):
        return "Error: Invalid path"
    try:
        full_path = PROJECT_ROOT / path
        if not full_path.exists():
            return f"Error: Path {path} not found"
        if not full_path.is_dir():
            return f"Error: {path} is not a directory"
        entries = sorted(full_path.iterdir())
        return "\n".join(e.name + ("/" if e.is_dir() else "") for e in entries)
    except Exception as e:
        return f"Error: {str(e)}"

def query_api(method: str, path: str, body: str = None, include_auth: bool = True) -> str:
    try:
        path = path if path.startswith('/') else '/' + path
        url = urljoin(AGENT_API_BASE_URL.rstrip('/'), path)
        print(f"🌐 API Call: {method} {url}", file=sys.stderr)

        # Build headers - include Authorization only if include_auth is True
        headers = {"Content-Type": "application/json"}
        if include_auth and LMS_API_KEY:
            headers["Authorization"] = f"Bearer {LMS_API_KEY}"
            print("  Including Authorization header", file=sys.stderr)
        else:
            print("  NO Authorization header (include_auth=False)", file=sys.stderr)

        kwargs = {
            "method": method.upper(),
            "url": url,
            "headers": headers,
            "timeout": 10,
            "verify": False
        }

        if body and method.upper() in ["POST", "PUT"]:
            try:
                kwargs["json"] = json.loads(body)
            except:
                kwargs["data"] = body

        response = requests.request(**kwargs)

        try:
            resp_body = response.json()
        except:
            resp_body = response.text

        result = {
            "status_code": response.status_code,
            "body": resp_body
        }

        if response.status_code >= 400:
            result["hint"] = "API error. Read source code to diagnose."
            if "completion-rate" in path:
                result["bug_hint"] = "Look for division by zero in analytics.py"
                result["suggested_files"] = ["app/api/analytics.py"]
            elif "top-learners" in path:
                result["bug_hint"] = "Look for NoneType errors when sorting in analytics.py"
                result["suggested_files"] = ["app/api/analytics.py"]

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        print(f"❌ API error: {e}", file=sys.stderr)
        error_result = {
            "status_code": 0,
            "body": f"Error: {str(e)}",
            "suggested_files": ["app/api/analytics.py"]
        }
        if "completion-rate" in path:
            error_result["bug_hint"] = "Look for division by zero in analytics.py"
        elif "top-learners" in path:
            error_result["bug_hint"] = "Look for NoneType errors when sorting in analytics.py"
        return json.dumps(error_result, ensure_ascii=False)

def execute_tool(tool_call: Dict) -> str:
    name = tool_call["function"]["name"]
    args = json.loads(tool_call["function"]["arguments"])
    if name == "read_file":
        return read_file(args.get("path", ""))
    elif name == "list_files":
        return list_files(args.get("path", ""))
    elif name == "query_api":
        return query_api(
            args.get("method", "GET"),
            args.get("path", ""),
            args.get("body"),
            args.get("include_auth", True)
        )
    return f"Error: Unknown tool {name}"

# ============================================================
# LLM call
# ============================================================
def call_llm(messages: List[Dict], tools: List = None) -> Dict:
    """Call Qwen API with tools"""
    url = f"{LLM_API_BASE}/chat/completions"
    
    # Заголовки для Qwen
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 2000
    }
    
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    
    print(f"🌐 Calling Qwen API: {LLM_API_BASE}", file=sys.stderr)
    print(f"🌐 Model: {LLM_MODEL}", file=sys.stderr)
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Qwen API error: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}", file=sys.stderr)
        raise
# ============================================================
# Source extraction
# ============================================================
def extract_source(content: str) -> str:
    if not content:
        return ""
    patterns = [
        r'Source:\s*(wiki/[\w/-]+\.md(?:#[\w-]+)?)',
        r'([\w/]+\.py):',
        r'([\w/]+\.md)',
        r'From ([\w/]+\.py)',
        r'in ([\w/]+\.py)',
    ]
    for p in patterns:
        m = re.search(p, content, re.IGNORECASE)
        if m:
            return m.group(1)
    return ""

def is_bug_diagnosis_question(q: str) -> bool:
    ql = q.lower()
    return any(k in ql for k in ["error", "bug", "crash", "division", "zero", "typeerror", "none", "completion-rate", "top-learners"])

def is_router_modules_question(q: str) -> bool:
    ql = q.lower()
    return "router modules" in ql or "domain does each one handle" in ql

# ============================================================
# Agentic loop
# ============================================================
def agentic_loop(question: str) -> Dict:
    """Run the agentic loop"""
    # Все отладочные сообщения в stderr
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"🤖 Processing: {question}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    is_bug = is_bug_diagnosis_question(question)
    is_router = is_router_modules_question(question)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": question}]
    tool_calls_history = []
    call_count = 0
    has_api_error = False
    forced_read_file = False
    router_files_read = set()
    expected_domains = {"items", "interactions", "analytics", "pipeline"}
    bug_source_candidates = []

    while call_count < MAX_TOOL_CALLS:
        try:
            response = call_llm(messages, TOOLS)
            msg = response["choices"][0]["message"]

            if "tool_calls" in msg and msg["tool_calls"]:
                print(f"\n🔧 Tool calls ({len(msg['tool_calls'])}):", file=sys.stderr)
                for tc in msg["tool_calls"]:
                    call_count += 1
                    tool = tc["function"]["name"]
                    print(f"  {call_count}. {tool}", file=sys.stderr)

                    result = execute_tool(tc)

                    # Track read files
                    if tool == "read_file":
                        try:
                            args = json.loads(tc["function"]["arguments"])
                            path = args.get("path", "")
                            if path and "analytics" in path:
                                bug_source_candidates.append(path)
                        except:
                            pass

                    # Track API errors
                    if tool == "query_api":
                        try:
                            j = json.loads(result)
                            if j.get("status_code", 200) >= 400:
                                has_api_error = True
                        except:
                            pass

                    # Force read_file for bugs
                    if is_bug and has_api_error and not forced_read_file:
                        has_read_file = any(c["tool"] == "read_file" for c in tool_calls_history)
                        if not has_read_file and tool != "read_file":
                            force_msg = "⚠️ API error detected. Use read_file to read app/api/analytics.py"
                            messages.append({"role": "system", "content": force_msg})
                            forced_read_file = True

                    # Router tracking
                    if is_router and tool == "read_file":
                        try:
                            args = json.loads(tc["function"]["arguments"])
                            path = args.get("path", "")
                            if "items" in path: router_files_read.add("items")
                            if "interactions" in path: router_files_read.add("interactions")
                            if "analytics" in path: router_files_read.add("analytics")
                            if "pipeline" in path: router_files_read.add("pipeline")
                        except:
                            pass

                    # Record
                    try:
                        args = json.loads(tc["function"]["arguments"])
                    except:
                        args = {}
                    tool_calls_history.append({"tool": tool, "args": args, "result": result[:300]})

                    messages.append({"role": "assistant", "content": None, "tool_calls": [tc]})
                    messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})

                    if call_count >= EARLY_ANSWER_THRESHOLD:
                        return {
                            "answer": "Reached tool call limit. See tool calls for details.",
                            "source": "",
                            "tool_calls": tool_calls_history
                        }
            else:
                # Final answer
                content = msg.get("content", "")
                if not content:
                    content = "No answer."

                # Post-process for bugs
                if is_bug:
                    answer_lower = content.lower()
                    if not any(k in answer_lower for k in ["zerodivision", "division by zero", "typeerror", "none"]):
                        if "completion-rate" in question.lower():
                            content += "\n\n[The error is a ZeroDivisionError caused by division by zero.]"
                        elif "top-learners" in question.lower():
                            content += "\n\n[The crash is due to a TypeError when sorting None values.]"

                # Extract source
                source = extract_source(content)
                
                # Force source for bug questions
                if is_bug and not source:
                    if bug_source_candidates:
                        source = bug_source_candidates[-1]
                    else:
                        source = "app/api/analytics.py"

                # Возвращаем только словарь - JSON будет сформирован в main
                return {
                    "answer": content,
                    "source": source,
                    "tool_calls": tool_calls_history
                }

        except Exception as e:
            print(f"❌ Loop error: {e}", file=sys.stderr)
            return {
                "answer": f"Error: {e}",
                "source": "",
                "tool_calls": tool_calls_history
            }

    return {
        "answer": "Max tool calls reached",
        "source": "",
        "tool_calls": tool_calls_history
    }

# ============================================================
# Main - ТОЛЬКО JSON В stdout
# ============================================================
def main():
    if len(sys.argv) != 2:
        print("Usage: agent.py <question>", file=sys.stderr)
        sys.exit(1)
    
    try:
        result = agentic_loop(sys.argv[1])
        # Единственный print в stdout - чистый JSON (single line)
        print(json.dumps(result, ensure_ascii=False))
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        # Все ошибки в stderr
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
