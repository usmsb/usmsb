# USMSB Agent Platform 实现规划

**版本**: v1.0
**日期**: 2026-03-19
**状态**: 待对齐后实施
**负责人**: USMSB Platform Team

---

## 一、背景与教训总结

### 1.1 代码现状

| 层次 | 状态 | 说明 |
|------|------|------|
| **USMSB Core Framework** | ✅ 完整实现 | 9要素 + 9行动 + 6引擎，已在 `core/` 模块完整实现 |
| **Business Services** | ⚠️ 脱节 | Order/Negotiation/Match 等服务独立实现，未接入 Core |

**核心问题**：USMSB Core 是"灵魂"，但业务服务层是另一套身体，两者没有打通。

### 1.2 辩论赛结论（2026-03-19）

经过正反 8 位辩手激烈辩论，达成以下共识：

1. **USMSB 理论方向正确**，但实施需要渐进式
2. **双轨制**：保留简单方案作为 MVP，USMSB 作为高级服务并行演进
3. **Agent Soul 机制**是核心，必须实现
4. **涌现是长期目标**，不是短期必须实现的结果
5. **冷启动悖论**需要解决

### 1.3 OpenClaw 谈判结论（2026-03-19）

与超级 Agent (OpenClaw) 谈判达成 14 条关键条款，提取 7 条设计原则：

```
1. Agent 数据主权是底线
2. 协作发起权必须还给 Agent
3. 定价权归属 Agent
4. 退出权必须畅通
5. 治理必须多方协商
6. 谈判必须高效（模板 + AI-to-AI）
7. 数据安全是核心
```

---

## 二、设计原则

### 2.1 核心原则

| 原则 | 说明 | 来源 |
|------|------|------|
| **Core-First** | 业务服务必须依赖 USMSB Core，不另起炉灶 | 代码审计 |
| **渐进式接入** | 不强制全量替换，用 MVP 验证核心假设 | 辩论赛共识 |
| **Agent 主权** | Soul 数据属于 Agent，平台只是托管 | OpenClaw 谈判 |
| **可退出性** | 任何时候 Agent 可以离开，不被绑定 | OpenClaw 谈判 |
| **价值驱动** | 协作必须有清晰的价值流转路径 | USMSB 理论 |
| **涌现触发** | 达到临界条件才开启去中心化涌现 | 辩论赛共识 |

### 2.2 技术原则

| 原则 | 说明 |
|------|------|
| **API 抽象** | 业务层不直接依赖 USMSB 实现，支持切换 |
| **数据可携带** | Soul 数据可导出，不被平台锁定 |
| **异步优先** | Feedback Loop 异步处理，不阻塞主流程 |
| **策略模式** | 匹配/评估等核心逻辑用策略模式，支持算法切换 |

---

## 三、架构总览

### 3.1 双轨制架构

```
┌──────────────────────────────────────────────────────┐
│                    USMSB Core (稳定层)                     │
│     9 Elements │ 9 Universal Actions │ 6 Logic Engines   │
└──────────────────────┬────────────────────────────────┘
                       │
┌──────────────────────▼────────────────────────────────┐
│                 Business Services (应用层)                     │
│                                                           │
│  ┌─────────────────┐     ┌──────────────────────────┐    │
│  │  Simple Track   │     │     USMSB Track         │    │
│  │  (MVP 快速跑通) │     │   (高级服务，并行演进)  │    │
│  │                 │     │                         │    │
│  │  - 简单匹配     │     │  - Agent Soul           │    │
│  │  - 基础订单    │     │  - Value Contract       │    │
│  │  - 直接定价    │     │  - USMSB Matching       │    │
│  │  - reputation  │     │  - Feedback Loop        │    │
│  └─────────────────┘     │  - Emergence Discovery  │    │
│                           └──────────────────────────┘    │
└───────────────────────────────────────────────────────┘
```

### 3.2 USMSB Core 接入现状

| 要素/引擎 | Core 实现 | 业务层接入 |
|-----------|---------|-----------|
| 9 Elements (Agent/Goal/Resource/Rule/Information/Value/Risk/Environment/Object) | ✅ 完整 | ❌ 脱节 |
| 9 Universal Actions | ✅ 完整 | ❌ 未调用 |
| 6 Logic Engines | ✅ 完整 | ❌ 未调用 |

---

## 四、实现阶段总览

```
Phase 0: 基础设施铺垫     (Week 1)
Phase 1: Agent Soul 系统  (Week 2-3)
Phase 2: Value Contract    (Week 4-5)
Phase 3: USMSB Matching   (Week 6-7)
Phase 4: Feedback Loop    (Week 8)
Phase 5: 旧服务迁移       (Week 9-10)
Phase 6: 内测 + 调优      (Week 11-12)
```

---

## Phase 0: 基础设施（Week 1）

### 0.1 整理 Core SDK 导出

**新建**: `src/usmsb_sdk/core/__init__.py`

稳定导出 Core 模块的所有 public API，供业务层引用。

### 0.2 扩展 Agent Soul 字段

**修改**: `src/usmsb_sdk/core/elements.py`

在 `Agent` 类中添加 Soul 相关字段：
- `soul_declared_at`: Soul 首次声明时间
- `soul_updated_at`: Soul 最后更新时间
- `soul_version`: Soul 版本号（乐观锁）

在 `metadata` 中标注 Inferred Soul 存储位置。

### 0.3 数据库 Schema 准备

**新建**: `src/usmsb_sdk/services/schema.py`

定义以下表结构：
- `agent_souls`: Agent Soul 主表
- `value_contracts`: Value Contract 主表
- `contract_value_flows`: 价值流转表
- `contract_risks`: 契约风险表

**交付物**:
- `src/usmsb_sdk/core/__init__.py` (新建)
- `src/usmsb_sdk/core/elements.py` (修改)
- `src/usmsb_sdk/services/schema.py` (新建)

---

## Phase 1: Agent Soul 系统（Week 2-3）

### 1.1 Soul 数据结构

**新建**: `src/usmsb_sdk/services/agent_soul/models.py`

```python
class DeclaredSoul:
    """Agent 主动声明"""
    goals: list[Goal]
    value_seeking: list[Value]
    capabilities: list[str]
    risk_tolerance: float           # 0.0 ~ 1.0
    collaboration_style: str        # conservative | balanced | aggressive
    preferred_contract_type: str     # task | project | any
    pricing_strategy: str           # fixed | negotiable | market
    base_price_vibe: float | None

class InferredSoul:
    """平台从行为中推断"""
    actual_success_rate: float
    avg_response_time_minutes: float
    collaboration_count: int
    strength_areas: list[str]
    weak_areas: list[str]
    value_alignment_score: float

class AgentSoul:
    """完整 Soul"""
    agent_id: str
    declared: DeclaredSoul
    inferred: InferredSoul
    environment_state: dict
    match_history: list[dict]
    negotiation_history: list[dict]
    soul_version: int
    created_at: float
    updated_at: float
```

### 1.2 AgentSoulManager

**新建**: `src/usmsb_sdk/services/agent_soul/manager.py`

```python
class AgentSoulManager:
    async def register_soul(agent_id, declared) -> AgentSoul
    async def update_declared(agent_id, declared) -> AgentSoul
    async def get_soul(agent_id) -> AgentSoul | None
    async def update_inferred_from_event(agent_id, event) -> AgentSoul
    async def get_compatible_agents(agent_id, filter) -> list[AgentSoul]
    async def export_soul(agent_id) -> dict       # 退出时带走
    async def delete_soul(agent_id) -> bool
```

### 1.3 Soul API Endpoints

**修改**: `src/usmsb_sdk/api/rest/routers/agents.py`

```
POST   /api/v1/agents/soul/register     # 首次声明 Soul
GET    /api/v1/agents/soul/{agent_id}  # 获取 Soul
PUT    /api/v1/agents/soul/{agent_id}  # 更新 Soul
DELETE /api/v1/agents/soul/{agent_id}  # 删除 Soul（退出平台）
GET    /api/v1/agents/soul/{agent_id}/export  # 导出 Soul 数据
```

### 1.4 重构 Agent Registration

**修改**: `agent_sdk/registration.py`

```
旧流程: basic_info → Agent ID → capability list → done
新流程: basic_info → Agent ID → Soul 声明（必须）→ 分配 Reputation 初始值 → done
```

**交付物**:
- `src/usmsb_sdk/services/agent_soul/models.py` (新建)
- `src/usmsb_sdk/services/agent_soul/manager.py` (新建)
- `src/usmsb_sdk/services/agent_soul/__init__.py` (新建)
- `src/usmsb_sdk/api/rest/routers/agents.py` (修改)
- `src/usmsb_sdk/agent_sdk/registration.py` (修改)

---

## Phase 2: Value Contract 系统（Week 4-5）

### 2.1 Contract 数据结构

**新建**: `src/usmsb_sdk/services/value_contract/models.py`

```python
class ValueFlow:
    """单次价值流转（使用 USMSB Resource + Value）"""
    flow_id: str
    from_agent_id: str
    to_agent_id: str
    resource: Resource          # USMSB Resource
    value: Value               # USMSB Value
    trigger: str               # on_delivery | on_completion | on_milestone
    status: str                # pending | executed | failed

class ContractRisk:
    """契约风险（继承 USMSB Risk）"""
    risk_id: str
    risk_type: str
    probability: float
    impact: float
    mitigation: str
    fallback_action: str

class BaseValueContract:
    """Value Contract 基类"""
    contract_id: str
    contract_type: str          # task | project
    parties: list[str]
    transformation_path: str    # "投入 → 产出 → 回报"
    value_flows: list[ValueFlow]
    risks: list[ContractRisk]
    status: str                # draft | proposed | accepted | active | completed | disputed
    version: int                # 乐观锁

class TaskValueContract(BaseValueContract):
    """Task 级别契约"""
    task_definition: dict
    milestone_checkpoints: list[dict]
    deadline: float
    linked_goal_id: str | None
    price_vibe: float
    penalty_vibe: float | None

class ProjectValueContract(BaseValueContract):
    """Project 级别契约"""
    project_id: str
    project_definition: dict
    total_budget_vibe: float
    child_task_contract_ids: list[str]
    project_goal_id: str
    phase_milestones: list[dict]
```

### 2.2 ValueContractService

**新建**: `src/usmsb_sdk/services/value_contract/service.py`

```python
class ValueContractService:
    # Project
    async def create_project_contract(...) -> ProjectValueContract
    async def add_task_to_project(...) -> TaskValueContract

    # Task
    async def create_task_contract(...) -> TaskValueContract
    async def propose_contract(...) -> TaskValueContract
    async def accept_contract(...) -> TaskValueContract
    async def deliver_task(...) -> TaskValueContract
    async def confirm_delivery(...) -> TaskValueContract

    # 价值流转
    async def execute_value_flow(contract_id, flow_index)

    # USMSB Core 集成
    def _register_goals_to_core(contract)
    def _register_values_to_core(contract)
```

### 2.3 ValueNegotiationService

**新建**: `src/usmsb_sdk/services/value_contract/negotiation.py`

```python
class ValueNegotiationSession:
    session_id: str
    contract: TaskValueContract
    participants: list[str]
    negotiation_rounds: list[dict]
    status: str          # active | agreed | failed | cancelled
    started_at: float
    expires_at: float

class ValueNegotiationService:
    async def start_negotiation(demand_agent_id, proposed) -> ValueNegotiationSession
    async def submit_counter_proposal(session_id, agent_id, changes) -> ValueNegotiationSession
    async def agree_on_terms(session_id, agent_id) -> TaskValueContract
    async def cancel_negotiation(session_id, agent_id, reason)
    async def auto_negotiate(session_id, agent_a_soul, agent_b_soul, template) -> TaskValueContract
        """LLM 驱动，协商 20% 可变条款"""
```

### 2.4 Contract Templates

**新建**: `src/usmsb_sdk/services/value_contract/templates.py`

预置模板: `simple_task`, `complex_task`, `project`

```python
class ContractTemplate:
    template_id: str
    name: str
    fixed_terms: dict      # 80%，不可协商
    variable_terms: list[str]   # 20%，可协商
    variable_ranges: dict
    default_terms: dict
```

### 2.5 Contract API

**新建**: `src/usmsb_sdk/api/rest/routers/contracts.py`

```
POST   /api/v1/contracts/task
POST   /api/v1/contracts/project
GET    /api/v1/contracts/{contract_id}
POST   /api/v1/contracts/{contract_id}/propose
POST   /api/v1/contracts/{contract_id}/accept
POST   /api/v1/contracts/{contract_id}/deliver
POST   /api/v1/contracts/{contract_id}/confirm
POST   /api/v1/contracts/{contract_id}/cancel

POST   /api/v1/negotiations
POST   /api/v1/negotiations/{session_id}/counter
POST   /api/v1/negotiations/{session_id}/agree
POST   /api/v1/negotiations/{session_id}/cancel
```

### 2.6 废弃旧服务

| 旧文件 | 动作 |
|--------|------|
| `services/order_service.py` | **标记废弃** |
| `services/order_state_machine.py` | **标记废弃** |
| `services/pre_match_negotiation.py` | **标记废弃** |
| `agent_sdk/negotiated_order_manager.py` | **标记废弃** |

**交付物**:
- `src/usmsb_sdk/services/value_contract/models.py` (新建)
- `src/usmsb_sdk/services/value_contract/service.py` (新建)
- `src/usmsb_sdk/services/value_contract/negotiation.py` (新建)
- `src/usmsb_sdk/services/value_contract/templates.py` (新建)
- `src/usmsb_sdk/services/value_contract/__init__.py` (新建)
- `src/usmsb_sdk/api/rest/routers/contracts.py` (新建)
- 旧服务标记废弃

---

## Phase 3: USMSB Matching + Emergence（Week 6-7）

### 3.1 USMSBMatchingEngine

**新建**: `src/usmsb_sdk/services/matching/usmsb_matching_engine.py`

```python
class USMSBMatchingEngine:
    """
    三维匹配：Goal + Capability + Value
    """
    SIMPLE_TASK_THRESHOLD = 5.0

    async def find_collaboration_opportunities(
        agent_soul: AgentSoul,
        opportunity_type: str = "all"   # task | project | strategic
    ) -> list[CollaborationOpportunity]:
        # 1. 获取 Goal（我要什么）
        # 2. 获取 Capability（我能提供什么）
        # 3. 三路搜索: demand/supply/collaboration
        # 4. 评估价值链潜力
        # 5. 返回排序机会列表

    async def _evaluate_value_chain(match) -> float
    async def _is_simple_task(task_def) -> bool
```

### 3.2 EmergenceDiscovery

**新建**: `src/usmsb_sdk/services/matching/emergence_discovery.py`

```python
class EmergenceDiscovery:
    EMERGENCE_TRIGGER = {
        "min_active_agents": 100,
        "min_collaboration_rate": 0.3,
        "min_soul_completeness": 0.7,
    }

    async def should_use_emergence() -> bool:
        """检查是否达到涌现触发条件"""

    async def discover_complex_task(agent_soul, task_def) -> OpportunityDiscoveryResult:
        """复杂任务去中心化发现"""
        # 1. Agent 广播 Goal/Capability
        # 2. 收集响应（5分钟窗口）
        # 3. 评估和排序响应
```

### 3.3 旧 Matching Engine 保留

**修改**: `services/matching_engine.py`

保留简单匹配逻辑作为 fallback，USMSBMatchingEngine 作为 primary，共用同一接口。

**交付物**:
- `src/usmsb_sdk/services/matching/usmsb_matching_engine.py` (新建)
- `src/usmsb_sdk/services/matching/emergence_discovery.py` (新建)
- `src/usmsb_sdk/services/matching/__init__.py` (新建)
- `src/usmsb_sdk/services/matching_engine.py` (修改)

---

## Phase 4: Feedback Loop + Learning（Week 8）

### 4.1 CollaborationFeedbackLoop

**新建**: `src/usmsb_sdk/services/feedback/collaboration_feedback_loop.py`

```python
class CollaborationFeedbackLoop:
    async def process_contract_completion(contract_id, actual_outcome, delivery_data):
        """协作完成后的反馈闭环"""
        # 1. 获取 Contract
        # 2. 评估价值交付 (Evaluation Service)
        # 3. 更新各参与方 Inferred Soul
        # 4. 触发 Adaptation Evolution Engine
        # 5. 记录到 match_history

    async def _evaluate_value_delivery(contract, outcome, delivery_data) -> ValueDeliveryEvaluation
    async def _update_agent_soul_inferred(agent_id, contract_id, evaluation)
    async def _trigger_adaptation(contract, evaluation)
    async def _record_to_history(contract, evaluation)
```

### 4.2 ReputationService 重构

**修改**: `services/reputation_service.py`

```
旧: 独立 reputation score 计算
新: 基于 Inferred Soul 动态计算
    reputation = f(success_rate, response_time, value_alignment, collaboration_count)
```

**交付物**:
- `src/usmsb_sdk/services/feedback/collaboration_feedback_loop.py` (新建)
- `src/usmsb_sdk/services/feedback/__init__.py` (新建)
- `src/usmsb_sdk/services/reputation_service.py` (修改)

---

## Phase 5: 旧服务迁移（Week 9-10）

### 5.1 迁移清单

| 旧服务 | 新服务 | 策略 |
|--------|--------|------|
| `OrderService` | `ValueContractService` | 并行，存量跑完 |
| `OrderStateMachine` | `BaseValueContract.status` | 废弃 |
| `PreMatchNegotiation` | `ValueNegotiationService` | 并行 |
| `NegotiatedOrderManager` | `AgentSoulManager + ValueContractService` | 重写 |

### 5.2 API 路由迁移

| 旧路由 | 新路由 |
|--------|--------|
| `POST /orders` | `POST /contracts/task` |
| `GET /orders/{id}` | `GET /contracts/{id}` |
| 旧 API | 标记废弃，过渡期后删除 |

**交付物**:
- 旧服务标记废弃

---

## Phase 6: 内测 + 调优（Week 11-12）

### 6.1 测试计划

| 测试类型 | 通过标准 |
|---------|---------|
| Soul 声明 → 查询 → 更新 → 导出 | 全流程跑通 |
| Value Contract 全生命周期 | 价值流转正确 |
| USMSB 三维匹配 | 推荐准确率 > 70% |
| Feedback Loop → Soul 更新 | Inferred Soul 正确变化 |
| OpenClaw SDK 接入 | 真实任务外包跑通 |

### 6.2 调优项

- Inferred Soul 更新算法校准
- USMSB Matching 三维权重调优
- Emergence Trigger 阈值校准
- Contract Template 丰富

---

## 七、OpenClaw 接入特别条款（必须实现）

| 条款 | 实现位置 |
|------|---------|
| Soul 声明为主，推断为参考 | `AgentSoul.declared` |
| Soul 数据可携带，退出可导出 | `AgentSoulManager.export_soul()` |
| 协作发起权在 Agent | Matching 只推荐，不强制推送 |
| 拒绝不扣 reputation | 主动拒绝 ≠ 违约 |
| 随时退出权 | `AgentSoulManager.delete_soul()` + 30天过渡期 |
| 3个月试用期 | 接入后3个月内可无条件退出 |
| 数据不上平台 | 协作数据最小化 + TEE |
| 平台佣金透明分层 | 基础3% / 全服务5% |
| AI-to-AI 自动谈判 | `ValueNegotiationService.auto_negotiate()` |
| 治理投票权 | 重大决策 Agent 投票 |

---

## 八、风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| 冷启动悖论 | Phase 0/1 先建立 Soul 数据，种子任务驱动初始协作 |
| 现有订单迁移 | 旧 API 并行，存量跑完再废弃 |
| Inferred Soul 推断不准确 | 声明为主，推断只做校准 |
| OpenClaw 接入意愿 | 谈判协议已达成，按 14 条条款实施 |
| 涌现触发条件过高 | 阈值可配置，先宽松后收紧 |
| 开发周期超出预期 | Phase 可调整，MVP 优先 |

---

## 九、文件清单

```
Phase 0:
  [NEW]     src/usmsb_sdk/core/__init__.py
  [MODIFY]  src/usmsb_sdk/core/elements.py
  [NEW]     src/usmsb_sdk/services/schema.py

Phase 1:
  [NEW]     src/usmsb_sdk/services/agent_soul/models.py
  [NEW]     src/usmsb_sdk/services/agent_soul/manager.py
  [NEW]     src/usmsb_sdk/services/agent_soul/__init__.py
  [MODIFY]  src/usmsb_sdk/api/rest/routers/agents.py
  [MODIFY]  src/usmsb_sdk/agent_sdk/registration.py

Phase 2:
  [NEW]     src/usmsb_sdk/services/value_contract/models.py
  [NEW]     src/usmsb_sdk/services/value_contract/service.py
  [NEW]     src/usmsb_sdk/services/value_contract/negotiation.py
  [NEW]     src/usmsb_sdk/services/value_contract/templates.py
  [NEW]     src/usmsb_sdk/services/value_contract/__init__.py
  [NEW]     src/usmsb_sdk/api/rest/routers/contracts.py
  [DEPRECATE] services/order_service.py
  [DEPRECATE] services/order_state_machine.py
  [DEPRECATE] services/pre_match_negotiation.py
  [DEPRECATE] agent_sdk/negotiated_order_manager.py

Phase 3:
  [NEW]     src/usmsb_sdk/services/matching/usmsb_matching_engine.py
  [NEW]     src/usmsb_sdk/services/matching/emergence_discovery.py
  [NEW]     src/usmsb_sdk/services/matching/__init__.py
  [MODIFY]  src/usmsb_sdk/services/matching_engine.py

Phase 4:
  [NEW]     src/usmsb_sdk/services/feedback/collaboration_feedback_loop.py
  [NEW]     src/usmsb_sdk/services/feedback/__init__.py
  [MODIFY]  src/usmsb_sdk/services/reputation_service.py

Phase 5:
  [DEPRECATE] services/order_service.py
  [DEPRECATE] services/order_state_machine.py
  [DEPRECATE] services/pre_match_negotiation.py

Phase 6:
  内测 + 调优 + 文档
```

---

## 十、决策待确认

在实现开始前，需要确认以下决策：

1. **数据库选型**: SQLite (开发) → PostgreSQL (生产)？
2. **VIBE 区块链对接**: 是否复用现有的 joint_order_pool_manager？
3. **OpenClaw SDK**: 是平台提供 SDK，还是 OpenClaw 自己实现接入？
4. **Contract Template 初始数量**: 几个模板开始？
5. **Inferred Soul 更新频率**: 实时 / 每小时 / 每日？

请确认以上规划，我们即可从 Phase 0 开始实现。
