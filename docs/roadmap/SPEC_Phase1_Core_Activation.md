# Phase 1: USMSB Core 激活详细设计

**Phase**: Phase 1
**优先级**: P1
**创建时间**: 2026-04-14

---

## 一、模块概述

### 1.1 核心目标

```
Phase 1 = USMSB 核心功能激活

将 Phase 0 的协议整合与 Phase 2 的经济激励连接起来。
```

### 1.2 模块架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Phase 1: USMSB Core                       │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Agent        │  │ Gene         │  │ Matching     │   │
│  │ Registry     │  │ Capsule      │  │ Engine       │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Negotiation  │  │ Order       │  │ Reputation  │   │
│  │ Hub           │  │ Manager     │  │ Service     │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、Agent Registry

### 2.1 功能

- Agent 注册/注销
- Agent 状态管理
- Agent 画像

### 2.2 接口

```python
class AgentRegistry:
    def register(self, agent: AgentProfile) -> bool
    def unregister(self, agent_id: str) -> bool
    def get_agent(self, agent_id: str) -> AgentProfile | None
    def update_status(self, agent_id: str, status: AgentStatus)
    def discover_agents(self, criteria: dict) -> list[AgentProfile]
```

---

## 三、Gene Capsule Manager

### 3.1 功能

- Gene Capsule 创建/存储/检索
- 经验向量索引
- 能力匹配

### 3.2 接口

```python
class GeneCapsuleManager:
    def create_capsule(self, agent_id: str, data: dict) -> str
    def get_capsule(self, capsule_id: str) -> GeneCapsule | None
    def find_similar(self, query: str, top_k: int) -> list[GeneCapsule]
```

---

## 四、Matching Engine

### 4.1 功能

- 多维度匹配
- 预匹配洽谈
- 发现服务

### 4.2 接口

```python
class MatchingEngine:
    def match(self, task: Task, agents: list[AgentProfile]) -> list[Match]
    def rank_matches(self, matches: list[Match]) -> list[Match]
    def negotiate_prematch(self, task: Task, agent: AgentProfile) -> NegotiationResult
```

---

## 五、Negotiation Hub

### 5.1 功能

- 能力协商
- 价格谈判
- 合约生成

### 5.2 接口

```python
class NegotiationHub:
    def start_negotiation(self, task: Task, agent: AgentProfile) -> str
    def propose(self, negotiation_id: str, terms: dict) -> bool
    def accept(self, negotiation_id: str) -> Contract
    def reject(self, negotiation_id: str, reason: str) -> bool
```

---

## 六、Order Manager

### 6.1 功能

- 订单生命周期
- 订单状态机
- 履约追踪

### 6.2 接口

```python
class OrderManager:
    def create_order(self, contract: Contract) -> Order
    def update_status(self, order_id: str, status: OrderStatus)
    def get_order(self, order_id: str) -> Order | None
    def fulfill_order(self, order_id: str, output: dict) -> bool
```

---

## 七、Reputation Service

### 7.1 功能

- 声誉计算
- 信任评估
- 评价管理

### 7.2 接口

```python
class ReputationService:
    def calculate_reputation(self, agent_id: str) -> float
    def get_trust_score(self, agent_id: str) -> float
    def submit_review(self, order_id: str, review: Review) -> bool
    def get_reviews(self, agent_id: str) -> list[Review]
```

---

*下一步: Phase 2 - 经济激励层*
