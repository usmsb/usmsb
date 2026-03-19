"""
测试数据Fixtures - 覆盖所有业务闭环

每个fixture都包含完整的业务数据，支持独立测试和闭环测试
"""
import uuid
import time
import pytest
from typing import Dict, Any, List
from dataclasses import dataclass, field


# ============================================================================
# Agent生命周期测试数据
# ============================================================================

@dataclass
class AgentTestData:
    """Agent完整测试数据"""
    agent_id: str = field(default_factory=lambda: f"test_agent_{uuid.uuid4().hex[:8]}")
    name: str = "TestAgent"
    agent_type: str = "ai_agent"
    description: str = "Test agent for integration testing"
    capabilities: List[str] = field(default_factory=lambda: ["reasoning", "planning", "execution"])
    skills: List[str] = field(default_factory=lambda: ["python", "data_analysis"])
    endpoint: str = "http://localhost:8080"
    chat_endpoint: str = "http://localhost:8081/chat"
    protocol: str = "standard"
    stake: float = 1000.0
    balance: float = 500.0
    reputation: float = 0.8
    heartbeat_interval: int = 30
    ttl: int = 90
    metadata: Dict[str, Any] = field(default_factory=lambda: {"test": True, "version": "1.0"})


def create_test_agent(**overrides) -> Dict[str, Any]:
    """创建测试Agent数据"""
    data = AgentTestData().__dict__
    data.update(overrides)
    data['created_at'] = time.time()
    data['updated_at'] = time.time()
    data['last_heartbeat'] = time.time()
    return data


# ============================================================================
# 用户/钱包测试数据
# ============================================================================

@dataclass
class UserTestData:
    """用户测试数据"""
    id: str = field(default_factory=lambda: f"test_user_{uuid.uuid4().hex[:8]}")
    wallet_address: str = field(default_factory=lambda: f"0x{uuid.uuid4().hex[:40]}")
    did: str = field(default_factory=lambda: f"did:vibe:test:{uuid.uuid4().hex[:16]}")
    agent_id: str = ""
    stake: float = 2000.0
    reputation: float = 0.75
    vibe_balance: float = 10000.0
    stake_status: str = "active"
    locked_stake: float = 0.0


def create_test_user(**overrides) -> Dict[str, Any]:
    """创建测试用户数据"""
    data = UserTestData().__dict__
    data.update(overrides)
    data['created_at'] = time.time()
    data['updated_at'] = time.time()
    return data


# ============================================================================
# 钱包测试数据
# ============================================================================

@dataclass
class WalletTestData:
    """Agent钱包测试数据"""
    id: str = field(default_factory=lambda: f"test_wallet_{uuid.uuid4().hex[:8]}")
    agent_id: str = ""
    owner_id: str = ""
    wallet_address: str = field(default_factory=lambda: f"0x{uuid.uuid4().hex[:40]}")
    agent_address: str = field(default_factory=lambda: f"0x{uuid.uuid4().hex[:40]}")
    vibe_balance: float = 5000.0
    staked_amount: float = 1000.0
    stake_status: str = "active"
    locked_stake: float = 0.0
    max_per_tx: float = 500.0
    daily_limit: float = 1000.0
    daily_spent: float = 0.0


def create_test_wallet(**overrides) -> Dict[str, Any]:
    """创建测试钱包数据"""
    data = WalletTestData().__dict__
    data.update(overrides)
    data['created_at'] = time.time()
    data['updated_at'] = time.time()
    data['last_reset_time'] = time.time()
    return data


# ============================================================================
# 需求(Demand)测试数据
# ============================================================================

@dataclass
class DemandTestData:
    """需求测试数据"""
    id: str = field(default_factory=lambda: f"test_demand_{uuid.uuid4().hex[:8]}")
    agent_id: str = ""
    title: str = "Test Demand"
    description: str = "Need AI agent for data analysis task"
    category: str = "data_analysis"
    required_skills: List[str] = field(default_factory=lambda: ["python", "ml", "statistics"])
    budget_min: float = 100.0
    budget_max: float = 500.0
    deadline: str = "2026-12-31"
    priority: str = "high"
    quality_requirements: str = "High accuracy, fast response"
    status: str = "active"


def create_test_demand(**overrides) -> Dict[str, Any]:
    """创建测试需求数据"""
    data = DemandTestData().__dict__
    data.update(overrides)
    data['created_at'] = time.time()
    return data


# ============================================================================
# 服务(Service)测试数据
# ============================================================================

@dataclass
class ServiceTestData:
    """服务测试数据"""
    id: str = field(default_factory=lambda: f"test_service_{uuid.uuid4().hex[:8]}")
    agent_id: str = ""
    service_name: str = "DataAnalysisService"
    description: str = "Professional data analysis service"
    category: str = "data_analysis"
    skills: List[str] = field(default_factory=lambda: ["python", "pandas", "ml"])
    price: float = 200.0
    price_type: str = "fixed"
    availability: str = "24/7"
    status: str = "active"


def create_test_service(**overrides) -> Dict[str, Any]:
    """创建测试服务数据"""
    data = ServiceTestData().__dict__
    data.update(overrides)
    data['created_at'] = time.time()
    return data


# ============================================================================
# 匹配(Opportunity)测试数据
# ============================================================================

@dataclass
class OpportunityTestData:
    """匹配机会测试数据"""
    id: str = field(default_factory=lambda: f"test_opp_{uuid.uuid4().hex[:8]}")
    demand_id: str = ""
    supplier_agent_id: str = ""
    match_score: float = 0.85
    status: str = "pending"


def create_test_opportunity(**overrides) -> Dict[str, Any]:
    """创建测试匹配数据"""
    data = OpportunityTestData().__dict__
    data.update(overrides)
    data['created_at'] = time.time()
    return data


# ============================================================================
# 协作(Collaboration)测试数据
# ============================================================================

@dataclass
class CollaborationTestData:
    """协作测试数据"""
    session_id: str = field(default_factory=lambda: f"test_collab_{uuid.uuid4().hex[:8]}")
    goal: str = "Complete data analysis project"
    plan: str = "Phase 1: Data collection\\nPhase 2: Analysis\\nPhase 3: Report"
    participants: List[str] = field(default_factory=list)
    status: str = "pending"
    result: str = ""


def create_test_collaboration(**overrides) -> Dict[str, Any]:
    """创建测试协作数据"""
    data = CollaborationTestData().__dict__
    data.update(overrides)
    data['created_at'] = time.time()
    data['updated_at'] = time.time()
    return data


# ============================================================================
# 工作流(Workflow)测试数据
# ============================================================================

@dataclass
class WorkflowTestData:
    """工作流测试数据"""
    id: str = field(default_factory=lambda: f"test_workflow_{uuid.uuid4().hex[:8]}")
    agent_id: str = ""
    name: str = "TestWorkflow"
    task_description: str = "Execute data analysis task"
    status: str = "pending"
    steps: List[Dict[str, Any]] = field(default_factory=lambda: [
        {"step": 1, "action": "collect_data", "status": "pending"},
        {"step": 2, "action": "analyze", "status": "pending"},
        {"step": 3, "action": "report", "status": "pending"},
    ])
    result: Dict[str, Any] = field(default_factory=dict)


def create_test_workflow(**overrides) -> Dict[str, Any]:
    """创建测试工作流数据"""
    data = WorkflowTestData().__dict__
    data.update(overrides)
    data['steps'] = str(data['steps'])
    data['result'] = str(data['result'])
    data['created_at'] = time.time()
    data['updated_at'] = time.time()
    return data


# ============================================================================
# 环境(Environment)测试数据
# ============================================================================

@dataclass
class EnvironmentTestData:
    """环境测试数据"""
    id: str = field(default_factory=lambda: f"test_env_{uuid.uuid4().hex[:8]}")
    name: str = "TestEnvironment"
    type: str = "development"
    state: Dict[str, Any] = field(default_factory=lambda: {"test_mode": True})


def create_test_environment(**overrides) -> Dict[str, Any]:
    """创建测试环境数据"""
    data = EnvironmentTestData().__dict__
    data.update(overrides)
    data['state'] = str(data['state'])
    data['created_at'] = time.time()
    return data


# ============================================================================
# 治理(Governance)测试数据
# ============================================================================

@dataclass
class ProposalTestData:
    """提案测试数据"""
    id: str = field(default_factory=lambda: f"test_proposal_{uuid.uuid4().hex[:8]}")
    title: str = "Test Proposal"
    description: str = "Proposal for system upgrade"
    proposer_id: str = ""
    status: str = "pending"
    votes_for: int = 0
    votes_against: int = 0
    quorum: int = 100
    deadline: str = "2026-12-31"


def create_test_proposal(**overrides) -> Dict[str, Any]:
    """创建测试提案数据"""
    data = ProposalTestData().__dict__
    data.update(overrides)
    data['created_at'] = time.time()
    data['updated_at'] = time.time()
    return data


# ============================================================================
# 交易(Transaction)测试数据
# ============================================================================

@dataclass
class TransactionTestData:
    """交易测试数据"""
    id: str = field(default_factory=lambda: f"test_tx_{uuid.uuid4().hex[:8]}")
    demand_id: str = ""
    service_id: str = ""
    buyer_id: str = ""
    seller_id: str = ""
    amount: float = 100.0
    platform_fee: float = 5.0
    status: str = "created"
    transaction_type: str = "service_payment"
    title: str = "Test Transaction"
    description: str = "Payment for data analysis service"


def create_test_transaction(**overrides) -> Dict[str, Any]:
    """创建测试交易数据"""
    data = TransactionTestData().__dict__
    data.update(overrides)
    data['created_at'] = time.time()
    data['updated_at'] = time.time()
    return data


# ============================================================================
# 学习洞察(Learning)测试数据
# ============================================================================

@dataclass
class LearningInsightTestData:
    """学习洞察测试数据"""
    id: str = field(default_factory=lambda: f"test_insight_{uuid.uuid4().hex[:8]}")
    agent_id: str = ""
    insights: List[str] = field(default_factory=lambda: ["insight1", "insight2"])
    strategy: str = "optimize_performance"
    market_analysis: str = "Market trends analysis"


def create_test_learning_insight(**overrides) -> Dict[str, Any]:
    """创建测试学习洞察数据"""
    data = LearningInsightTestData().__dict__
    data.update(overrides)
    data['insights'] = str(data['insights'])
    data['created_at'] = time.time()
    data['updated_at'] = time.time()
    return data


# ============================================================================
# 网络节点(Network)测试数据
# ============================================================================

@dataclass
class NetworkNodeTestData:
    """网络节点测试数据"""
    id: str = field(default_factory=lambda: f"test_node_{uuid.uuid4().hex[:8]}")
    agent_id: str = ""
    explored_nodes: List[str] = field(default_factory=list)
    trust_scores: Dict[str, float] = field(default_factory=dict)


def create_test_network_node(**overrides) -> Dict[str, Any]:
    """创建测试网络节点数据"""
    data = NetworkNodeTestData().__dict__
    data.update(overrides)
    data['explored_nodes'] = str(data['explored_nodes'])
    data['trust_scores'] = str(data['trust_scores'])
    data['created_at'] = time.time()
    data['last_explored'] = time.time()
    return data


# ============================================================================
# API密钥测试数据
# ============================================================================

@dataclass
class APIKeyTestData:
    """API密钥测试数据"""
    id: str = field(default_factory=lambda: f"test_key_{uuid.uuid4().hex[:8]}")
    agent_id: str = ""
    key_prefix: str = "test_sk_"
    name: str = "Test API Key"
    permissions: List[str] = field(default_factory=lambda: ["read", "write"])
    level: int = 1


def create_test_api_key(**overrides) -> Dict[str, Any]:
    """创建测试API密钥数据"""
    data = APIKeyTestData().__dict__
    data.update(overrides)
    data['key_hash'] = f"hash_{uuid.uuid4().hex}"
    data['created_at'] = time.time()
    return data


# ============================================================================
# 完整业务闭环测试数据
# ============================================================================

class BusinessFlowTestData:
    """完整业务闭环测试数据生成器"""

    @staticmethod
    def create_agent_matching_flow():
        """创建Agent注册->质押->匹配->协作完整流程数据"""
        agent_id = f"flow_agent_{uuid.uuid4().hex[:8]}"
        demand_id = f"flow_demand_{uuid.uuid4().hex[:8]}"
        service_id = f"flow_service_{uuid.uuid4().hex[:8]}"
        collab_session = f"flow_collab_{uuid.uuid4().hex[:8]}"

        return {
            "agent": create_test_agent(agent_id=agent_id),
            "demand": create_test_demand(
                demand_id=demand_id,
                agent_id=agent_id,
                title="Need data analysis agent",
                required_skills=["python", "ml"]
            ),
            "service": create_test_service(
                service_id=service_id,
                agent_id=agent_id,
                service_name="DataAnalysisPro"
            ),
            "opportunity": create_test_opportunity(
                demand_id=demand_id,
                supplier_agent_id=agent_id,
                match_score=0.9
            ),
            "collaboration": create_test_collaboration(
                session_id=collab_session,
                goal="Complete data analysis",
                participants=[agent_id]
            ),
        }

    @staticmethod
    def create_governance_flow():
        """创建治理流程数据"""
        proposal_id = f"flow_proposal_{uuid.uuid4().hex[:8]}"
        voter1 = f"flow_voter_{uuid.uuid4().hex[:8]}"
        voter2 = f"flow_voter_{uuid.uuid4().hex[:8]}"

        return {
            "proposal": create_test_proposal(
                id=proposal_id,
                proposer_id=voter1,
                title="System Upgrade Proposal",
                quorum=3
            ),
            "votes": [
                {"proposal_id": proposal_id, "voter_id": voter1, "vote": 1, "weight": 1.0},
                {"proposal_id": proposal_id, "voter_id": voter2, "vote": 1, "weight": 1.0},
            ]
        }

    @staticmethod
    def create_transaction_flow():
        """创建交易流程数据"""
        buyer_id = f"flow_buyer_{uuid.uuid4().hex[:8]}"
        seller_id = f"flow_seller_{uuid.uuid4().hex[:8]}"
        tx_id = f"flow_tx_{uuid.uuid4().hex[:8]}"

        return {
            "buyer": create_test_user(id=buyer_id, wallet_address=f"0x{uuid.uuid4().hex[:40]}", vibe_balance=5000),
            "seller": create_test_user(id=seller_id, wallet_address=f"0x{uuid.uuid4().hex[:40]}", vibe_balance=1000),
            "transaction": create_test_transaction(
                id=tx_id,
                buyer_id=buyer_id,
                seller_id=seller_id,
                amount=200.0,
                platform_fee=10.0
            )
        }


# ============================================================================
# 导出所有Fixtures (供pytest使用)
# ============================================================================

@pytest.fixture
def agent_data():
    """Agent测试数据fixture"""
    return create_test_agent()


@pytest.fixture
def user_data():
    """用户测试数据fixture"""
    return create_test_user()


@pytest.fixture
def wallet_data():
    """钱包测试数据fixture"""
    return create_test_wallet()


@pytest.fixture
def demand_data():
    """需求测试数据fixture"""
    return create_test_demand()


@pytest.fixture
def service_data():
    """服务测试数据fixture"""
    return create_test_service()


@pytest.fixture
def opportunity_data():
    """匹配机会测试数据fixture"""
    return create_test_opportunity()


@pytest.fixture
def collaboration_data():
    """协作测试数据fixture"""
    return create_test_collaboration()


@pytest.fixture
def workflow_data():
    """工作流测试数据fixture"""
    return create_test_workflow()


@pytest.fixture
def environment_data():
    """环境测试数据fixture"""
    return create_test_environment()


@pytest.fixture
def proposal_data():
    """提案测试数据fixture"""
    return create_test_proposal()


@pytest.fixture
def transaction_data():
    """交易测试数据fixture"""
    return create_test_transaction()


@pytest.fixture
def learning_insight_data():
    """学习洞察测试数据fixture"""
    return create_test_learning_insight()


@pytest.fixture
def network_node_data():
    """网络节点测试数据fixture"""
    return create_test_network_node()


@pytest.fixture
def api_key_data():
    """API密钥测试数据fixture"""
    return create_test_api_key()


@pytest.fixture
def agent_matching_flow():
    """Agent->Demand->Service->Matching->Collaboration完整流程"""
    return BusinessFlowTestData.create_agent_matching_flow()


@pytest.fixture
def governance_flow():
    """治理流程"""
    return BusinessFlowTestData.create_governance_flow()


@pytest.fixture
def transaction_flow():
    """交易流程"""
    return BusinessFlowTestData.create_transaction_flow()
