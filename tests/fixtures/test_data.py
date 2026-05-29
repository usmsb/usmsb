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


# ============================================================================
# V2.1 因果学习系统测试数据
# ============================================================================

import numpy as np
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


class InputSize(Enum):
    """输入大小枚举"""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class InputType(Enum):
    """输入类型枚举"""
    TEXT = "text"
    CODE = "code"
    DATA = "data"
    MIXED = "mixed"
    IMAGE = "image"


class DomainArea(Enum):
    """领域区域枚举"""
    GENERAL = "general"
    DATA_ANALYSIS = "data_analysis"
    WEB_DEVELOPMENT = "web_development"
    API_INTEGRATION = "api_integration"
    TEXT_PROCESSING = "text_processing"


@dataclass
class TaskFeatures:
    """任务特征"""
    input_size: InputSize = InputSize.MEDIUM
    input_type: InputType = InputType.MIXED
    input_complexity: float = 0.5
    has_api: bool = False
    has_database: bool = False
    is_real_time: bool = False
    domain_area: DomainArea = DomainArea.GENERAL
    time_limit: Optional[float] = None
    memory_limit: Optional[float] = None
    cost_budget: Optional[float] = None
    accuracy_required: float = 0.7
    creativity_required: float = 0.3
    safety_required: float = 0.5

    def to_dict(self) -> dict:
        return {
            "input_size": self.input_size.value,
            "input_type": self.input_type.value,
            "input_complexity": self.input_complexity,
            "has_api": self.has_api,
            "has_database": self.has_database,
            "is_real_time": self.is_real_time,
            "domain_area": self.domain_area.value,
            "time_limit": self.time_limit,
            "memory_limit": self.memory_limit,
            "cost_budget": self.cost_budget,
            "accuracy_required": self.accuracy_required,
            "creativity_required": self.creativity_required,
            "safety_required": self.safety_required,
        }


@dataclass
class StrategyFeatures:
    """策略特征"""
    decomposition_depth: int = 1
    parallel_threshold: float = 0.5
    tool_count: int = 1
    llm_call_budget: int = 5
    retry_enabled: bool = True
    verify_always: bool = False
    verify_on_failure: bool = True
    verify_sample_rate: float = 0.1

    def to_dict(self) -> dict:
        return {
            "decomposition_depth": self.decomposition_depth,
            "parallel_threshold": self.parallel_threshold,
            "tool_count": self.tool_count,
            "llm_call_budget": self.llm_call_budget,
            "retry_enabled": self.retry_enabled,
            "verify_always": self.verify_always,
            "verify_on_failure": self.verify_on_failure,
            "verify_sample_rate": self.verify_sample_rate,
        }


@dataclass
class Strategy:
    """策略"""
    name: str
    features: StrategyFeatures = field(default_factory=StrategyFeatures)
    applicable_conditions: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "features": self.features.to_dict(),
            "applicable_conditions": self.applicable_conditions,
        }


@dataclass
class Outcome:
    """执行结果"""
    success: bool = True
    quality: float = 0.0
    duration: float = 0.0
    resource_cost: float = 0.0
    error_type: Optional[str] = None
    partial_success: float = 0.0
    llm_calls: int = 0
    tool_calls: int = 0
    retry_count: int = 0

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "quality": self.quality,
            "duration": self.duration,
            "resource_cost": self.resource_cost,
            "error_type": self.error_type,
            "partial_success": self.partial_success,
            "llm_calls": self.llm_calls,
            "tool_calls": self.tool_calls,
            "retry_count": self.retry_count,
        }


@dataclass
class TaskRecord:
    """任务记录"""
    task_id: str
    task_type: str
    features: TaskFeatures
    strategy: Strategy
    parameters: dict
    outcome: Outcome
    timestamp: float
    domain: str = "general"
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "features": self.features.to_dict(),
            "strategy": self.strategy.to_dict(),
            "parameters": self.parameters,
            "outcome": self.outcome.to_dict(),
            "timestamp": self.timestamp,
            "domain": self.domain,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "metadata": self.metadata,
        }


def create_causal_discovery_test_data(n_samples: int = 100, seed: int = 42) -> list[TaskRecord]:
    """
    创建用于因果发现的测试数据

    因果结构:
    input_complexity -> quality (直接因果)
    input_complexity -> duration (直接因果)
    tool_count -> quality (直接因果)
    accuracy_required -> quality (直接因果)
    """
    np.random.seed(seed)
    records = []

    for i in range(n_samples):
        # 任务特征
        complexity = np.random.beta(2, 5)  # 偏向低复杂度
        accuracy_req = np.random.uniform(0.5, 1.0)
        has_api = np.random.random() > 0.7
        tool_count = np.random.poisson(2) + 1

        features = TaskFeatures(
            input_size=InputSize.MEDIUM if complexity < 0.6 else InputSize.LARGE,
            input_type=InputType.MIXED,
            input_complexity=complexity,
            has_api=has_api,
            has_database=np.random.random() > 0.8,
            is_real_time=np.random.random() > 0.9,
            domain_area=DomainArea.GENERAL,
            accuracy_required=accuracy_req,
            creativity_required=np.random.uniform(0.2, 0.8),
            safety_required=np.random.uniform(0.3, 0.9),
        )

        # 策略
        strategy = Strategy(
            name=f"strategy_{i % 3}",
            features=StrategyFeatures(
                decomposition_depth=np.random.poisson(2) + 1,
                tool_count=tool_count,
                llm_call_budget=np.random.poisson(5) + 1,
                retry_enabled=np.random.random() > 0.3,
                verify_always=np.random.random() > 0.8,
            ),
        )

        # 结果质量 - 与特征有因果关系
        # quality = f(complexity, accuracy_req, tool_count) + noise
        base_quality = 0.3
        complexity_effect = (1 - complexity) * 0.3  # 低复杂度更容易高质量
        accuracy_effect = accuracy_req * 0.2
        tool_effect = min(tool_count / 10, 0.2)  # 工具数量有帮助但边际递减
        noise = np.random.randn() * 0.1
        quality = base_quality + complexity_effect + accuracy_effect + tool_effect + noise
        quality = min(1.0, max(0.0, quality))

        # duration 与 complexity 正相关
        duration = 1.0 + complexity * 10 + np.random.exponential(2)

        outcome = Outcome(
            success=quality > 0.3,
            quality=quality,
            duration=duration,
            resource_cost=complexity * 5 + tool_count * 0.5,
            partial_success=quality,
            llm_calls=np.random.poisson(5) + 1,
            tool_calls=tool_count,
            retry_count=np.random.poisson(1) if np.random.random() > 0.5 else 0,
        )

        record = TaskRecord(
            task_id=f"causal_task_{i}",
            task_type="data_analysis",
            features=features,
            strategy=strategy,
            parameters={},
            outcome=outcome,
            timestamp=time.time() - (n_samples - i) * 3600,  # 逐渐过去的时间
            domain="data_analysis",
        )
        records.append(record)

    return records


def create_meta_learning_test_data(n_domains: int = 3, n_tasks_per_domain: int = 10) -> tuple[list[TaskRecord], list[TaskRecord]]:
    """
    创建用于元学习的测试数据 - 支持集和查询集

    返回: (support_set, query_set)
    """
    np.random.seed(42)
    support_set = []
    query_set = []

    domains = [
        (DomainArea.DATA_ANALYSIS, "data_analysis"),
        (DomainArea.WEB_DEVELOPMENT, "web_dev"),
        (DomainArea.API_INTEGRATION, "api_integration"),
    ]

    for domain_idx, (domain_area, domain_name) in enumerate(domains):
        for task_idx in range(n_tasks_per_domain):
            complexity = np.random.beta(2, 3)
            quality = 0.5 + 0.3 * (1 - complexity) + np.random.randn() * 0.1

            features = TaskFeatures(
                input_size=InputSize.MEDIUM,
                input_type=InputType.MIXED,
                input_complexity=complexity,
                has_api=domain_idx != 0,
                has_database=domain_idx == 0,
                domain_area=domain_area,
                accuracy_required=np.random.uniform(0.6, 0.95),
            )

            strategy = Strategy(
                name=f"{domain_name}_strategy",
                features=StrategyFeatures(
                    decomposition_depth=domain_idx + 1,
                    tool_count=domain_idx + 1,
                ),
            )

            outcome = Outcome(
                success=True,
                quality=min(1.0, max(0.0, quality)),
                duration=1.0 + complexity * 5,
                llm_calls=domain_idx + 2,
                tool_calls=domain_idx + 1,
            )

            record = TaskRecord(
                task_id=f"{domain_name}_task_{task_idx}",
                task_type=domain_name,
                features=features,
                strategy=strategy,
                parameters={},
                outcome=outcome,
                timestamp=time.time() - task_idx * 100,
                domain=domain_name,
            )

            # 前部分作为支持集，后部分作为查询集
            if task_idx < n_tasks_per_domain * 0.6:
                support_set.append(record)
            else:
                query_set.append(record)

    return support_set, query_set


def create_causal_graph_test_data() -> dict:
    """
    创建用于因果规划器测试的因果图数据

    因果图结构:
    A -> B -> C
    A -> D
    B -> D
    """
    from usmsb_sdk.meta_agent.models.causal_graph import CausalGraph, CausalEdge

    graph = CausalGraph(graph_id="test_graph")
    graph.nodes = {"A", "B", "C", "D"}
    graph.edges = [
        CausalEdge(edge_id="e1", source="A", target="B", strength=0.9),
        CausalEdge(edge_id="e2", source="B", target="C", strength=0.8),
        CausalEdge(edge_id="e3", source="A", target="D", strength=0.7),
        CausalEdge(edge_id="e4", source="B", target="D", strength=0.85),
    ]

    return {
        "graph": graph,
        "target_nodes": ["C", "D"],
        "expected_paths": {
            "C": [["A", "B", "C"]],
            "D": [["A", "D"], ["A", "B", "D"]],
        },
    }


def create_reasoning_test_data() -> list[dict]:
    """
    创建用于推理增强层测试的测试数据
    """
    return [
        {
            "input": """## 推理步骤 1
分析问题：
- 用户需要一个排序算法
- 数据规模是 1000 个整数

## 推理步骤 2
选择策略：
- quicksort: 平均 O(n log n)，原地排序
- mergesort: O(n log n)，稳定排序

## 最终结论
选择 quicksort，因为平均性能好且原地排序省空间""",
            "expected_steps": 2,
            "has_conclusion": True,
        },
        {
            "input": """## 推理步骤 1
分析问题：
- 需要实现 API 集成
- 涉及多个外部服务调用

存在问题：
- 没有考虑错误处理

## 最终结论
需要添加重试机制和错误处理""",
            "expected_steps": 2,
            "has_conclusion": True,
            "has_issues": True,
        },
        {
            "input": "这个任务很简单，直接做就行了",
            "expected_steps": 0,
            "has_conclusion": False,
        },
    ]


def create_skill_gap_test_data() -> list[dict]:
    """
    创建用于 Skill 自创建系统测试的 SkillGap 数据
    """
    return [
        {
            "gap_id": "gap_001",
            "source_node": "execution",
            "target_node": "quality",
            "gap_type": "missing_skill",
            "priority": 0.9,
            "description": "需要 skill 来提升代码质量检测能力",
        },
        {
            "gap_id": "gap_002",
            "source_node": "planning",
            "target_node": "execution",
            "gap_type": "missing_causal_link",
            "priority": 0.7,
            "description": "缺少从规划到执行的有效转换策略",
        },
        {
            "gap_id": "gap_003",
            "source_node": "api_call",
            "target_node": "success",
            "gap_type": "knowledge_gap",
            "priority": 0.6,
            "description": "API 调用失败后的重试策略不明确",
        },
    ]


def create_incremental_update_test_data(n_initial: int = 50, n_incremental: int = 10) -> tuple[list[TaskRecord], list[TaskRecord]]:
    """
    创建用于增量更新测试的数据

    返回: (initial_records, new_records)
    """
    np.random.seed(100)
    initial_records = create_causal_discovery_test_data(n_samples=n_initial, seed=100)

    np.random.seed(200)
    new_records = create_causal_discovery_test_data(n_samples=n_incremental, seed=200)

    return initial_records, new_records


# Fixtures for V2.1
@pytest.fixture
def causal_discovery_data():
    """因果发现测试数据"""
    return create_causal_discovery_test_data(n_samples=100)


@pytest.fixture
def meta_learning_data():
    """元学习测试数据"""
    return create_meta_learning_test_data(n_domains=3, n_tasks_per_domain=10)


@pytest.fixture
def causal_graph_data():
    """因果图测试数据"""
    return create_causal_graph_test_data()


@pytest.fixture
def reasoning_data():
    """推理增强测试数据"""
    return create_reasoning_test_data()


@pytest.fixture
def skill_gap_data():
    """Skill Gap 测试数据"""
    return create_skill_gap_test_data()


@pytest.fixture
def incremental_update_data():
    """增量更新测试数据"""
    return create_incremental_update_test_data()
