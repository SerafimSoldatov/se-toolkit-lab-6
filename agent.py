#!/usr/bin/env python3
"""
agent.py - A simple CLI that calls an LLM and returns a JSON answer.
Usage: uv run agent.py "Your question here"
"""

import json
import os
import sys
from openai import OpenAI
from dotenv import load_dotenv


def main() -> None:
    # 1. Get the question from command line
    if len(sys.argv) < 2:
        print("Error: No question provided.", file=sys.stderr)
        print("Usage: uv run agent.py \"Your question\"", file=sys.stderr)
        sys.exit(1)
    question = sys.argv[1]

    # 2. Load environment variables from .env.agent.secret
    #    (assumes the file is in the same directory as the script)
    load_dotenv(dotenv_path=".env.agent.secret")

    api_key = os.getenv("LLM_API_KEY")
    api_base = os.getenv("LLM_API_BASE")
    model = os.getenv("LLM_MODEL")

    # 3. Validate required environment variables
    missing_vars = []
    if not api_key:
        missing_vars.append("LLM_API_KEY")
    if not api_base:
        missing_vars.append("LLM_API_BASE")
    if not model:
        missing_vars.append("LLM_MODEL")

    if missing_vars:
        print(f"Error: Missing environment variables: {', '.join(missing_vars)}", file=sys.stderr)
        print("Please ensure they are set in .env.agent.secret", file=sys.stderr)
        sys.exit(1)

    # 4. Initialize OpenAI client
    try:
        client = OpenAI(
            api_key=api_key,
            base_url=api_base,
            timeout=30.0,  # seconds
        )
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}", file=sys.stderr)
        sys.exit(1)

    # 5. Call the LLM
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": question},
            ],
            temperature=0.0,  # deterministic for testing
        )
        answer = response.choices[0].message.content
    except Exception as e:
        print(f"Error calling LLM: {e}", file=sys.stderr)
        sys.exit(1)

    # 6. Prepare and print JSON output (only to stdout)
    output = {
        "answer": answer,
        "tool_calls": []  # empty for Task 1
    }
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
