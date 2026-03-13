# Service Layer

**[English](#1-service-list) | [中文](#1-服务列表)**

---

## 1. Service List

| Service | Path | Description |
|---------|------|-------------|
| **BehaviorPredictionService** | `services/behavior_prediction_service.py` | Behavior Prediction Service |
| **AgenticWorkflowService** | `services/agentic_workflow_service.py` | Agentic Workflow Service |
| **DecisionSupportService** | `services/decision_support_service.py` | Decision Support Service |
| **SystemSimulationService** | `services/system_simulation_service.py` | System Simulation Service |
| **ActiveMatchingService** | `services/active_matching_service.py` | Active Matching Service |
| **SupplyDemandMatchingService** | `services/supply_demand_matching_service.py` | Supply-Demand Matching Service |
| **AgentNetworkExplorer** | `services/agent_network_explorer.py` | Agent Network Explorer |
| **CollaborativeMatchingService** | `services/collaborative_matching_service.py` | Collaborative Matching Service |
| **ProactiveLearningService** | `services/proactive_learning_service.py` | Proactive Learning Service |
| **DynamicPricingService** | `services/dynamic_pricing_service.py` | Dynamic Pricing Service |
| **JointOrderService** | `services/joint_order_service.py` | Joint Order Service |
| **AssetFractionalizationService** | `services/asset_fractionalization_service.py` | Asset Fractionalization Service |
| **ZKCredentialService** | `services/zk_credential_service.py` | ZK Credential Service |
| **GovernanceService** | `services/governance_service.py` | Governance Service |
| **LearningService** | `services/learning_service.py` | Learning Service |
| **ReputationService** | `services/reputation_service.py` | Reputation Service |

---

## 2. Matching Services

### 2.1 ActiveMatchingService

- Intelligent supply-demand matching
- Negotiation session management
- Search strategy optimization
- Match scoring calculation

```python
from usmsb_sdk.services import ActiveMatchingService

service = ActiveMatchingService()
opportunities = await service.find_opportunities(
    agent_id="agent_123",
    criteria={"skill": "python", "budget": 1000}
)
```

### 2.2 SupplyDemandMatchingService

- Supplier management
- Demander management
- Intelligent matching algorithm
- Match statistics

```python
from usmsb_sdk.services import SupplyDemandMatchingService

service = SupplyDemandMatchingService()
match = await service.match_supply_demand(
    demand={"skill": "python", "budget": 1000},
    supply=[{"skill": "python", "price": 800}]
)
```

---

## 3. Collaborative Services (CollaborativeMatchingService)

### 3.1 Features

- Inter-Agent communication
- Task delegation
- Resource coordination
- Collaboration plan generation

```python
from usmsb_sdk.services import CollaborativeMatchingService

service = CollaborativeMatchingService()
session = await service.create_collaboration(
    participants=["agent_1", "agent_2", "agent_3"],
    goal="Complete large project"
)
```

---

## 4. Governance Service (GovernanceService)

### 4.1 Features

- Proposal management
- Voting mechanism
- Access control
- Community governance

```python
from usmsb_sdk.services import GovernanceService

service = GovernanceService()
proposal = await service.create_proposal(
    title="Parameter Adjustment Proposal",
    description="Adjust staking APY",
    votes_for=1000,
    votes_against=200
)
```

---

## 5. Learning Services (ProactiveLearningService)

### 5.1 Features

- Market insight analysis
- Optimization strategy learning
- Behavior pattern recognition
- Knowledge accumulation

```python
from usmsb_sdk.services import ProactiveLearningService

service = ProactiveLearningService()
insights = await service.analyze_market(
    agent_id="agent_123",
    historical_data=data
)
```

---

## 6. Related Documentation

- [System Architecture](../03_architecture/system_architecture.md) - Overall system architecture
- [REST API](../06_api/rest_api.md) - API reference
- [Python SDK](../06_api/python_sdk.md) - Python SDK usage guide

<details>
<summary><h2>中文翻译</h2></summary>

# 服务层

---

## 1. 服务列表

| 服务 | 路径 | 功能 |
|------|------|------|
| **BehaviorPredictionService** | `services/behavior_prediction_service.py` | 行为预测服务 |
| **AgenticWorkflowService** | `services/agentic_workflow_service.py` | Agentic工作流服务 |
| **DecisionSupportService** | `services/decision_support_service.py` | 决策支持服务 |
| **SystemSimulationService** | `services/system_simulation_service.py` | 系统仿真服务 |
| **ActiveMatchingService** | `services/active_matching_service.py` | 主动匹配服务 |
| **SupplyDemandMatchingService** | `services/supply_demand_matching_service.py` | 供需匹配服务 |
| **AgentNetworkExplorer** | `services/agent_network_explorer.py` | Agent网络探索 |
| **CollaborativeMatchingService** | `services/collaborative_matching_service.py` | 协作匹配服务 |
| **ProactiveLearningService** | `services/proactive_learning_service.py` | 主动学习服务 |
| **DynamicPricingService** | `services/dynamic_pricing_service.py` | 动态定价服务 |
| **JointOrderService** | `services/joint_order_service.py` | 联合订单服务 |
| **AssetFractionalizationService** | `services/asset_fractionalization_service.py` | 资产碎片化服务 |
| **ZKCredentialService** | `services/zk_credential_service.py` | ZK凭证服务 |
| **GovernanceService** | `services/governance_service.py` | 治理服务 |
| **LearningService** | `services/learning_service.py` | 学习服务 |
| **ReputationService** | `services/reputation_service.py` | 信誉服务 |

---

## 2. 匹配服务

### 2.1 主动匹配服务 (ActiveMatchingService)

- 智能供需匹配
- 协商会话管理
- 搜索策略优化
- 匹配评分计算

```python
from usmsb_sdk.services import ActiveMatchingService

service = ActiveMatchingService()
opportunities = await service.find_opportunities(
    agent_id="agent_123",
    criteria={"skill": "python", "budget": 1000}
)
```

### 2.2 供需匹配服务 (SupplyDemandMatchingService)

- 供给方管理
- 需求方管理
- 智能匹配算法
- 匹配统计

```python
from usmsb_sdk.services import SupplyDemandMatchingService

service = SupplyDemandMatchingService()
match = await service.match_supply_demand(
    demand={"skill": "python", "budget": 1000},
    supply=[{"skill": "python", "price": 800}]
)
```

---

## 3. 协作服务 (CollaborativeMatchingService)

### 3.1 功能

- Agent间通信
- 任务委托
- 资源协调
- 协作计划生成

```python
from usmsb_sdk.services import CollaborativeMatchingService

service = CollaborativeMatchingService()
session = await service.create_collaboration(
    participants=["agent_1", "agent_2", "agent_3"],
    goal="完成大型项目"
)
```

---

## 4. 治理服务 (GovernanceService)

### 4.1 功能

- 提案管理
- 投票机制
- 权限控制
- 社区治理

```python
from usmsb_sdk.services import GovernanceService

service = GovernanceService()
proposal = await service.create_proposal(
    title="参数调整提案",
    description="调整质押APY",
    votes_for=1000,
    votes_against=200
)
```

---

## 5. 学习服务 (ProactiveLearningService)

### 5.1 功能

- 市场洞察分析
- 优化策略学习
- 行为模式识别
- 知识积累

```python
from usmsb_sdk.services import ProactiveLearningService

service = ProactiveLearningService()
insights = await service.analyze_market(
    agent_id="agent_123",
    historical_data=data
)
```

---

## 6. 相关文档

- [系统架构](../03_architecture/system_architecture.md) - 整体系统架构
- [REST API](../06_api/rest_api.md) - API参考
- [Python SDK](../06_api/python_sdk.md) - Python SDK使用指南

</details>
