"""
测试配置 - 完整的测试基础设施

提供所有业务闭环测试的fixtures和配置

数据库策略:
- 使用临时文件数据库 (session级别，所有测试共享)
- 业务闭环测试需要测试之间共享数据
- 通过 CLEAN_DB_BETWEEN_TESTS=1 环境变量可启用测试间清理
"""
import os
import sys
import time
import uuid
import json
import asyncio
from pathlib import Path
from typing import Any, Dict, Generator, AsyncGenerator

import pytest
from httpx import AsyncClient, ASGITransport

# 添加src到path
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# 设置测试环境变量
os.environ.setdefault("TESTING", "true")


# ============================================================================
# 数据库Fixture - 临时文件数据库 (业务闭环测试策略)
# ============================================================================

@pytest.fixture(scope="session")
def test_db_path(tmp_path_factory):
    """创建临时测试数据库 - session级别，所有测试共享"""
    db_dir = tmp_path_factory.mktemp("test_data")
    return db_dir / "test_civilization.db"


@pytest.fixture(scope="session")
def database_module(test_db_path):
    """设置测试数据库路径并返回数据库模块

    业务闭环测试策略:
    - 所有测试共享同一个数据库实例
    - 测试B可以使用测试A创建的数据
    - 支持完整的数据流程验证
    """
    # 动态修改DATABASE_PATH
    import usmsb_sdk.api.database as db_module
    db_module.DATABASE_PATH = str(test_db_path)

    # 初始化数据库 (只执行一次)
    db_module.init_db()

    return db_module


@pytest.fixture(scope="function")
def clean_db(database_module):
    """可选: 每个测试前清理数据库

    默认不清理，支持业务闭环测试
    设置环境变量 CLEAN_DB_BETWEEN_TESTS=1 启用清理
    """
    clean_between_tests = os.environ.get("CLEAN_DB_BETWEEN_TESTS", "0") == "1"

    if clean_between_tests:
        db_path = database_module.get_db_path()
        if os.path.exists(db_path):
            os.remove(db_path)
        database_module.init_db()

    yield

    # 测试后不清理，保留现场便于调试


# ============================================================================
# API Client Fixture
# ============================================================================

@pytest.fixture(scope="session")
async def api_client(database_module):
    """创建测试API客户端"""
    from usmsb_sdk.api.rest.main import app

    # 确保数据库初始化
    database_module.init_db()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver"
    ) as client:
        yield client


# ============================================================================
# 认证相关Fixtures
# ============================================================================

@pytest.fixture
def test_wallet():
    """生成测试钱包地址"""
    return f"0x{uuid.uuid4().hex[:40]}"


@pytest.fixture
def test_api_key():
    """生成测试API密钥"""
    return f"sk_test_{uuid.uuid4().hex}"


@pytest.fixture
def authenticated_headers(test_wallet, test_api_key):
    """认证请求头"""
    return {
        "X-Wallet-Address": test_wallet,
        "X-API-Key": test_api_key,
    }


# ============================================================================
# 区块链测试Fixture
# ============================================================================

@pytest.fixture(scope="session")
def test_private_key():
    """测试私钥 (本地测试用)"""
    return os.environ.get("TEST_PRIVATE_KEY", "0x" + "01" * 32)


@pytest.fixture(scope="session")
def testnet_rpc_url():
    """测试网RPC URL"""
    return os.environ.get("ETH_TESTNET_RPC", "https://sepolia.infura.io/v3/YOUR_PROJECT_ID")


# ============================================================================
# LLM测试Fixture
# ============================================================================

@pytest.fixture(scope="session")
def llm_config():
    """LLM配置"""
    return {
        "provider": os.environ.get("LLM_PROVIDER", "openai"),
        "api_key": os.environ.get("OPENAI_API_KEY", ""),
        "model": os.environ.get("LLM_MODEL", "gpt-4-turbo-preview"),
    }


# ============================================================================
# 业务数据Fixtures
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
        "skills": ["python", "data_analysis"],
        "endpoint": "http://localhost:8080",
        "chat_endpoint": "http://localhost:8081/chat",
        "protocol": "standard",
        "stake": 1000.0,
        "balance": 500.0,
    }


@pytest.fixture
def sample_user_data():
    """样例用户数据"""
    return {
        "id": f"test_user_{uuid.uuid4().hex[:8]}",
        "wallet_address": f"0x{uuid.uuid4().hex[:40]}",
        "did": f"did:vibe:test:{uuid.uuid4().hex[:16]}",
        "stake": 2000.0,
        "reputation": 0.75,
        "vibe_balance": 10000.0,
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
        "skills": ["python", "pandas", "ml"],
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


# ============================================================================
# 业务流程Fixtures - 完整闭环
# ============================================================================

@pytest.fixture
async def full_agent_flow(api_client, sample_agent_data):
    """完整的Agent注册流程"""
    # 1. 创建Agent
    response = await api_client.post("/agents", json=sample_agent_data)
    assert response.status_code == 201
    agent = response.json()

    # 2. 发送心跳
    heartbeat_response = await api_client.post(
        f"/agents/{agent['agent_id']}/heartbeat",
        json={"status": "online"}
    )
    assert heartbeat_response.status_code == 200

    return agent


@pytest.fixture
async def full_matching_flow(api_client, sample_agent_data, sample_demand_data, sample_service_data):
    """完整的匹配流程"""
    # 1. 创建Agent
    agent_response = await api_client.post("/agents", json=sample_agent_data)
    agent = agent_response.json()

    # 2. 创建需求
    demand_data = sample_demand_data.copy()
    demand_response = await api_client.post("/demands", json=demand_data)
    demand = demand_response.json()

    # 3. 创建服务
    service_data = sample_service_data.copy()
    service_response = await api_client.post("/services", json=service_data)
    service = service_response.json()

    # 4. 执行匹配
    match_response = await api_client.post("/matching/match", json={
        "demand_id": demand["id"],
        "agent_id": agent["agent_id"]
    })
    match_result = match_response.json()

    return {
        "agent": agent,
        "demand": demand,
        "service": service,
        "match": match_result,
    }


@pytest.fixture
async def full_collaboration_flow(api_client, full_matching_flow):
    """完整的协作流程"""
    match_data = full_matching_flow

    # 5. 创建协作
    collab_response = await api_client.post("/collaborations", json={
        "goal": "Complete data analysis project",
        "participants": [match_data["agent"]["agent_id"]]
    })
    collaboration = collab_response.json()

    # 6. 更新协作状态
    update_response = await api_client.put(
        f"/collaborations/{collaboration['session_id']}/status",
        json={"status": "active"}
    )

    return {
        **match_data,
        "collaboration": collaboration,
    }


# ============================================================================
# 测试辅助函数
# ============================================================================

def assert_response_success(response, expected_status=200):
    """断言响应成功"""
    assert response.status_code == expected_status, (
        f"Expected {expected_status}, got {response.status_code}: {response.text}"
    )


def assert_field_in_response(response_json, field: str, expected_value=None):
    """断言响应包含指定字段"""
    assert field in response_json, f"Field '{field}' not in response: {response_json}"
    if expected_value is not None:
        assert response_json[field] == expected_value, (
            f"Field '{field}' mismatch: expected {expected_value}, got {response_json[field]}"
        )


# ============================================================================
# Mock外部依赖
# ============================================================================

@pytest.fixture(autouse=True)
def mock_time():
    """统一时间戳"""
    return time.time()
