#!/usr/bin/env python3
import os
import sys
import json
import requests
from pathlib import Path
from typing import List, Dict, Any

# ============================================================
# Configuration
# ============================================================
ENV_FILE = Path(__file__).parent / '.env.agent.secret'
if ENV_FILE.exists():
    with open(ENV_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value.strip('\'"')

LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_API_BASE = os.getenv("LLM_API_BASE")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3-coder-plus")
PROJECT_ROOT = Path.cwd().resolve()
MAX_TOOL_CALLS = 10

if not LLM_API_KEY or not LLM_API_BASE:
    print("Error: Missing API configuration", file=sys.stderr)
    sys.exit(1)

# ============================================================
# Tool schemas - EXACT format required for function calling
# ============================================================
TOOLS = [
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
    },
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
]

SYSTEM_PROMPT = """You are a documentation agent. You have access to two tools:
- list_files(path): List files in a directory
- read_file(path): Read a file's contents

The wiki is in the 'wiki/' directory. Always:
1. First use list_files('wiki') to see what files exist
2. Then use read_file on relevant files to find answers
3. When you answer, include the source as 'wiki/filename.md#section'"""

# ============================================================
# Tool implementations
# ============================================================
def is_safe_path(path: str) -> bool:
    """Prevent directory traversal"""
    try:
        full_path = (PROJECT_ROOT / path).resolve()
        return str(full_path).startswith(str(PROJECT_ROOT))
    except:
        return False

def read_file(path: str) -> str:
    """Read a file"""
    if not path or not is_safe_path(path):
        return "Error: Invalid path"
    
    try:
        full_path = PROJECT_ROOT / path
        if not full_path.exists():
            return f"Error: File {path} not found"
        if not full_path.is_file():
            return f"Error: {path} is not a file"
        
        content = full_path.read_text(encoding='utf-8')
        return content[:10000] + ("..." if len(content) > 10000 else "")
    except Exception as e:
        return f"Error: {str(e)}"

def list_files(path: str) -> str:
    """List files in directory"""
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

def execute_tool(tool_call: Dict) -> str:
    """Execute a tool and return result"""
    name = tool_call["function"]["name"]
    args = json.loads(tool_call["function"]["arguments"])
    
    if name == "read_file":
        return read_file(args.get("path", ""))
    elif name == "list_files":
        return list_files(args.get("path", ""))
    return f"Error: Unknown tool {name}"

# ============================================================
# LLM call
# ============================================================
def call_llm(messages: List[Dict], tools: List = None) -> Dict:
    """Call LLM with tools"""
    url = f"{LLM_API_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": 0.3,
    }
    
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()

# ============================================================
# Agentic loop - exactly as described in task
# ============================================================
def agentic_loop(question: str) -> Dict:
    """Run the agentic loop"""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question}
    ]
    
    tool_calls_history = []
    tool_call_count = 0
    
    while tool_call_count < MAX_TOOL_CALLS:
        # 1. Send to LLM with tools
        response = call_llm(messages, TOOLS)
        message = response["choices"][0]["message"]
        
        # 2. Check for tool calls
        if "tool_calls" in message and message["tool_calls"]:
            for tool_call in message["tool_calls"]:
                tool_call_count += 1
                
                # Execute tool
                result = execute_tool(tool_call)
                
                # Record tool call
                tool_calls_history.append({
                    "tool": tool_call["function"]["name"],
                    "args": json.loads(tool_call["function"]["arguments"]),
                    "result": result
                })
                
                # Add messages in correct format
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [tool_call]
                })
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": result
                })
                
                if tool_call_count >= MAX_TOOL_CALLS:
                    break
        else:
            # 3. Final answer
            content = message.get("content", "")
            
            # Try to extract source
            source = "wiki/unknown.md"
            import re
            source_match = re.search(r'(wiki/[\w/-]+\.md(?:#[\w-]+)?)', content)
            if source_match:
                source = source_match.group(1)
            
            return {
                "answer": content,
                "source": source,
                "tool_calls": tool_calls_history
            }
    
    # 4. Hit max tool calls
    return {
        "answer": "Reached maximum tool calls without final answer",
        "source": "",
        "tool_calls": tool_calls_history
    }

# ============================================================
# Main
# ============================================================
def main():
    if len(sys.argv) != 2:
        print("Usage: agent.py <question>", file=sys.stderr)
        sys.exit(1)
    
    try:
        result = agentic_loop(sys.argv[1])
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
