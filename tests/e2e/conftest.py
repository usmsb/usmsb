"""
E2E Test Configuration - Async compatible

Provides shared fixtures for end-to-end tests with async support.
"""

import pytest
import asyncio
import time
import subprocess
import os
import socket
import sys


def get_free_port():
    """Find an available port."""
    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port


# ---------------------------------------------------------------------------
# Backend Server (module scope - works with async tests)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def backend_server():
    """
    Start the FastAPI backend, wait for it to be ready, yield base URL, then stop.
    """
    port = get_free_port()
    base_url = f"http://127.0.0.1:{port}"

    # Get project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    env = os.environ.copy()
    env['PYTHONPATH'] = project_root

    proc = subprocess.Popen(
        [
            sys.executable, '-m', 'uvicorn',
            'usmsb_sdk.api.rest.main:app',
            '--host', '127.0.0.1',
            '--port', str(port),
            '--log-level', 'warning',
        ],
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    # Wait for server startup (max 20s)
    import requests
    for _ in range(40):
        try:
            r = requests.get(f"{base_url}/api/health", timeout=1)
            if r.status_code < 500:
                break
        except requests.exceptions.RequestException:
            pass
        time.sleep(0.5)
    else:
        proc.kill()
        raise RuntimeError(f"Backend failed to start on port {port}")

    yield base_url

    # Cleanup
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()


# ---------------------------------------------------------------------------
# UUID-based agent factories
# ---------------------------------------------------------------------------

import uuid


@pytest.fixture(scope="function")
def sdk_agent_demand(backend_server):
    """Create a unique demand agent ID and API key."""
    agent_id = f"sdk_demand_{uuid.uuid4().hex[:8]}"
    api_key = f"usmsb_sdk_demand_{uuid.uuid4().hex[:12]}"
    return agent_id, api_key


@pytest.fixture(scope="function")
def sdk_agent_supply(backend_server):
    """Create a unique supply agent ID and API key."""
    agent_id = f"sdk_supply_{uuid.uuid4().hex[:8]}"
    api_key = f"usmsb_sdk_supply_{uuid.uuid4().hex[:12]}"
    return agent_id, api_key


@pytest.fixture(scope="function")
def skill_agent_demand(backend_server):
    """Create a unique demand agent ID and API key for Agent Skill."""
    agent_id = f"skill_demand_{uuid.uuid4().hex[:8]}"
    api_key = f"usmsb_skill_demand_{uuid.uuid4().hex[:12]}"
    return agent_id, api_key


@pytest.fixture(scope="function")
def skill_agent_supply(backend_server):
    """Create a unique supply agent ID and API key for Agent Skill."""
    agent_id = f"skill_supply_{uuid.uuid4().hex[:8]}"
    api_key = f"usmsb_skill_supply_{uuid.uuid4().hex[:12]}"
    return agent_id, api_key
