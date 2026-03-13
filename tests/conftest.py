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


# ============================================================================
# API Client Fixture for Business Tests
# ============================================================================

import uuid
import time
from httpx import AsyncClient, ASGITransport

# 设置测试环境变量
os.environ.setdefault("TESTING", "true")


@pytest.fixture(scope="session")
def test_db_path(tmp_path_factory):
    """创建临时测试数据库 - session级别，所有测试共享"""
    db_dir = tmp_path_factory.mktemp("test_data")
    return db_dir / "test_civilization.db"


@pytest.fixture(scope="session")
def database_module(test_db_path):
    """设置测试数据库路径并返回数据库模块"""
    import usmsb_sdk.api.database as db_module
    db_module.DATABASE_PATH = str(test_db_path)
    db_module.init_db()
    return db_module


@pytest.fixture(scope="session")
def clean_db(database_module):
    """可选: 每个测试前清理数据库"""
    clean_between_tests = os.environ.get("CLEAN_DB_BETWEEN_TESTS", "0") == "1"

    if clean_between_tests:
        import os
        db_path = database_module.get_db_path()
        if os.path.exists(db_path):
            os.remove(db_path)
        database_module.init_db()

    yield


@pytest.fixture
async def api_client(database_module):
    """创建测试API客户端 - 带认证"""
    from usmsb_sdk.api.rest.main import app
    import hashlib
    import time

    database_module.init_db()

    # 创建测试Agent用于认证
    test_agent_id = "test_agent_system"
    test_api_key = "test_api_key_12345"
    test_key_hash = hashlib.sha256(test_api_key.encode()).hexdigest()

    with database_module.get_db() as conn:
        cursor = conn.cursor()
        # 创建测试Agent
        cursor.execute("""
            INSERT OR IGNORE INTO agents (
                agent_id, name, agent_type, description, capabilities,
                endpoint, protocol, status, stake, balance,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            test_agent_id,
            "TestSystemAgent",
            "ai_agent",
            "System test agent for API testing",
            '["reasoning", "planning"]',
            "http://localhost:8080",
            "standard",
            "active",
            10000.0,
            5000.0,
            time.time(),
            time.time()
        ))

        # 创建测试API Key
        cursor.execute("""
            INSERT OR IGNORE INTO agent_api_keys (
                id, agent_id, key_hash, key_prefix, name,
                permissions, level, expires_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f"key-{uuid.uuid4().hex[:8]}",
            test_agent_id,
            test_key_hash,
            test_api_key[:8],
            "Test API Key",
            '["read", "write", "execute"]',
            10,
            None,
            time.time()
        ))
        conn.commit()

    # 测试用的认证头
    headers = {
        "X-API-Key": test_api_key,
        "X-Agent-ID": test_agent_id,
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver/api",
        timeout=30.0,
        headers=headers
    ) as client:
        yield client


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_agent_data():
    """样例Agent数据"""
    agent_id = f"test_agent_{uuid.uuid4().hex[:8]}"
    return {
        "agent_id": agent_id,
        "name": f"TestAgent_{agent_id[-6:]}",
        "agent_type": "ai_agent",
        "description": "Test agent for integration testing",
        "capabilities": ["reasoning", "planning", "execution"],
        "skills": [
            {"name": "python", "level": "advanced"},
            {"name": "data_analysis", "level": "intermediate"}
        ],
        "endpoint": "http://localhost:8080",
        "chat_endpoint": "http://localhost:8081/chat",
        "protocol": "standard",
        "stake": 1000.0,
        "balance": 500.0,
    }


@pytest.fixture
def sample_demand_data(sample_agent_data):
    """样例需求数据"""
    return {
        "agent_id": sample_agent_data["agent_id"],
        "title": "Need AI agent for data analysis",
        "description": "Professional data analysis required",
        "category": "data_analysis",
        "required_skills": ["python", "ml", "statistics"],
        "budget_min": 100.0,
        "budget_max": 500.0,
        "deadline": "2026-12-31",
        "priority": "high",
    }


@pytest.fixture
def sample_service_data(sample_agent_data):
    """样例服务数据"""
    return {
        "agent_id": sample_agent_data["agent_id"],
        "service_name": "DataAnalysisService",
        "description": "Professional data analysis",
        "category": "data_analysis",
        "skills": [
            {"name": "python", "level": "advanced"},
            {"name": "pandas", "level": "advanced"},
            {"name": "ml", "level": "intermediate"}
        ],
        "price": 200.0,
        "price_type": "fixed",
    }


@pytest.fixture
def sample_workflow_data(sample_agent_data):
    """样例工作流数据"""
    return {
        "agent_id": sample_agent_data["agent_id"],
        "name": "DataAnalysisWorkflow",
        "task_description": "Execute complete data analysis",
        "steps": [
            {"step": 1, "action": "collect_data", "status": "pending"},
            {"step": 2, "action": "analyze", "status": "pending"},
            {"step": 3, "action": "report", "status": "pending"},
        ]
    }


@pytest.fixture
def sample_proposal_data():
    """样例提案数据"""
    return {
        "title": "System Upgrade Proposal",
        "description": "Upgrade to v2.0 with new features",
        "proposer_id": f"test_proposer_{uuid.uuid4().hex[:8]}",
        "quorum": 3,
        "deadline": "2026-12-31",
    }


@pytest.fixture
def test_wallet():
    """生成测试钱包地址"""
    return f"0x{uuid.uuid4().hex[:40]}"


@pytest.fixture
def auth_headers():
    """认证请求头"""
    return {
        "X-API-Key": "test_api_key",
        "X-Agent-ID": "test_agent",
    }


@pytest.fixture
def test_api_key():
    """测试API密钥"""
    return "test_api_key"


@pytest.fixture
def test_agent_id():
    """测试Agent ID"""
    return f"test_agent_{uuid.uuid4().hex[:8]}"
