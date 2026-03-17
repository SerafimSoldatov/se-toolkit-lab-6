"""Shared fixtures and configuration for all tests"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import os
import pytest
import subprocess
import json

# Load environment variables from both .env files
env_files = [
    project_root / '.env.agent.secret',
    project_root / '.env.docker.secret'
]

for env_file in env_files:
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    value = value.strip('\'"')
                    os.environ[key] = value
                    print(f"Loaded: {key}")

# Verify required variables
required_vars = ['LMS_API_KEY', 'LLM_API_KEY', 'LLM_API_BASE']
missing = [var for var in required_vars if var not in os.environ]
if missing:
    print(f"⚠️  Warning: Missing environment variables: {missing}")
    print("Some tests may fail!")

@pytest.fixture
def run_agent():
    """Helper to run the agent and return parsed output"""
    def _run_agent(question):
        # Pass all environment variables to subprocess
        env = os.environ.copy()
        
        result = subprocess.run(
            ["python", "agent.py", question],
            capture_output=True,
            text=True,
            timeout=60,  # Increased timeout for complex questions
            env=env
        )
        
        assert result.returncode == 0, f"Agent failed with stderr: {result.stderr}"
        
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            raise e
    
    return _run_agent

@pytest.fixture
def wiki_files():
    """Return list of expected wiki files"""
    wiki_dir = project_root / "wiki"
    if wiki_dir.exists():
        return [f.name for f in wiki_dir.glob("*.md")]
    return []
