"""
Test configuration for pytest.

This conftest.py provides shared fixtures and configuration for all test types:
- Unit tests: Fast, isolated tests with mocked dependencies
- Integration tests: Tests with real dependencies (database, services)
- E2E tests: Full system tests
"""
import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Generator, AsyncGenerator

import pytest

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


# ============================================================================
# Event Loop Configuration
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Core Element Fixtures
# ============================================================================

@pytest.fixture
def sample_agent():
    """Create a sample agent for testing."""
    from usmsb_sdk.core.elements import Agent, AgentType
    return Agent(
        name="TestAgent",
        type=AgentType.AI_AGENT,
        capabilities=["reasoning", "planning"],
    )


@pytest.fixture
def sample_environment():
    """Create a sample environment for testing."""
    from usmsb_sdk.core.elements import Environment, EnvironmentType
    return Environment(
        name="TestEnvironment",
        type=EnvironmentType.SOCIAL,
        state={"test": True},
    )


@pytest.fixture
def sample_goal():
    """Create a sample goal for testing."""
    from usmsb_sdk.core.elements import Goal
    return Goal(
        name="TestGoal",
        description="A test goal",
        priority=1,
    )


# ============================================================================
# Agent SDK Fixtures
# ============================================================================

@pytest.fixture
def agent_config() -> dict[str, Any]:
    """Create a sample agent configuration."""
    return {
        "name": "TestAgent",
        "description": "A test agent for unit testing",
        "version": "1.0.0",
        "capabilities": ["reasoning", "planning", "execution"],
        "endpoint": "http://localhost:8080",
        "metadata": {
            "author": "test",
            "tags": ["test", "unit"],
        },
    }


@pytest.fixture
def mock_llm_response() -> str:
    """Create a mock LLM response."""
    return "This is a mock LLM response for testing."


@pytest.fixture
def mock_agent_state() -> dict[str, Any]:
    """Create a mock agent state."""
    return {
        "status": "active",
        "current_task": None,
        "memory": [],
        "context": {},
    }


# ============================================================================
# Protocol Fixtures
# ============================================================================

@pytest.fixture
def sample_message() -> dict[str, Any]:
    """Create a sample protocol message."""
    return {
        "id": "msg-001",
        "type": "request",
        "sender": "agent-001",
        "receiver": "agent-002",
        "content": {
            "action": "query",
            "data": {"question": "What is the weather?"},
        },
        "timestamp": "2024-01-01T00:00:00Z",
        "metadata": {},
    }


@pytest.fixture
def sample_a2a_message() -> dict[str, Any]:
    """Create a sample A2A protocol message."""
    return {
        "jsonrpc": "2.0",
        "method": "agent.execute",
        "params": {
            "agent_id": "agent-001",
            "task": "analyze",
            "input": {"data": "sample"},
        },
        "id": "req-001",
    }


# ============================================================================
# Storage Fixtures
# ============================================================================

@pytest.fixture
def temp_storage_path(tmp_path: Path) -> Path:
    """Create a temporary storage path."""
    storage_path = tmp_path / "storage"
    storage_path.mkdir(parents=True, exist_ok=True)
    return storage_path


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Create a temporary database path."""
    return tmp_path / "test.db"


# ============================================================================
# API Fixtures
# ============================================================================

@pytest.fixture
def api_headers() -> dict[str, str]:
    """Create default API headers."""
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


@pytest.fixture
def auth_headers(api_headers: dict[str, str]) -> dict[str, str]:
    """Create authenticated API headers."""
    headers = api_headers.copy()
    headers["Authorization"] = "Bearer test-token"
    return headers


# ============================================================================
# Test Environment Configuration
# ============================================================================

@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch: pytest.MonkeyPatch):
    """Set up test environment variables."""
    monkeypatch.setenv("USMSB_ENV", "test")
    monkeypatch.setenv("USMSB_DEBUG", "true")
    monkeypatch.setenv("USMSB_LOG_LEVEL", "DEBUG")


# ============================================================================
# Markers Configuration
# ============================================================================

def pytest_configure(config: pytest.Config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_llm: mark test as requiring LLM access"
    )
    config.addinivalue_line(
        "markers", "requires_network: mark test as requiring network access"
    )
