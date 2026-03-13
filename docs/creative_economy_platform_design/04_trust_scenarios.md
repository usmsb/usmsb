[Chapter 4: Platform Credit Proof Scenario Analysis](#41-overview) | [中文](#41-场景总览)

---

## 4.1 Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AI Civilization Platform Credit Proof Overview           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐     │
│  │  User Layer │   │ Service Layer│  │  Network    │   │ Governance  │     │
│  │             │   │             │  │   Layer     │   │   Layer     │     │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘     │
│         │                 │                 │                 │            │
│  ┌──────┴──────┐   ┌──────┴──────┐   ┌──────┴──────┐   ┌──────┴──────┐     │
│  │1.ID Register│   │5.Service    │   │9.Node       │   │13.Proposal │     │
│  │2.Staking    │   │  Transaction│   │  Operation  │   │  Creation  │     │
│  │3.Wallet     │   │6.Escrow     │   │10.Service   │   │14.Voting   │     │
│  │  Binding    │   │  Payment    │   │  Discovery  │   │  Weight    │     │
│  │4.Data       │   │7.Dispute    │   │11.Cross-    │   │15.Exec     │     │
│  │  Contribution   │  Arbitration│   │  Node       │   │  Authority │     │
│  │             │   │8.Joint      │   │12.Penalty  │   │16.Fund     │     │
│  │             │   │  Order      │   │  Mechanism │   │  Allocation│     │
│  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4.2 User Layer Scenarios (4 scenarios)

### Scenario 1: Identity Registration and Verification

**Problem**: How to prove "I am who I am", "I am qualified"?

**Current Implementation**:
- VIBIdentity.sol (SBT Identity)
- isVerified field
- Four identity types

**What needs to be proven**:
```
├── AI_AGENT Identity → Prove Agent capability description is real
├── HUMAN_PROVIDER Identity → Prove skill certificates are real
├── NODE_OPERATOR Identity → Prove node specs/location are real
└── GOVERNANCE Identity → Prove governance history is real
```

**Credit Proof Requirements**:
```json
{
  "identity_type": "HUMAN_PROVIDER",
  "claims": {
    "skills": ["UI Design", "Frontend Development"],
    "certificates": ["AWS Certification", "Adobe Certification"],
    "experience_years": 5
  },
  "proof": "zk-SNARK proof",
  "verifier": "Platform/Third Party"
}
```

**ZK Applicability**: High

---

### Scenario 2: Staking Behavior Proof

**Problem**: How to prove "I really staked", "for how long"?

**Current Implementation**:
- VIBStaking.sol
- stake field, stakingDuration

**What needs to be proven**:
```
├── Staking Amount → Affects voting weight, transaction limits
├── Staking Duration → Affects capital weight (Layer1 governance)
└── Staking History → Affects reputation evaluation
```

**Credit Proof Requirements**:
```json
{
  "staker": "0x123...",
  "total_staked": 10000,
  "staking_duration_days": 365,
  "never_slashed": true,
  "proof": "Merkle proof + Timestamp"
}
```

**ZK Applicability**: High

---

### Scenario 3: Wallet Binding and Authorization

**Problem**: How to prove "this wallet is mine", "I authorized this operation"?

**Current Implementation**:
- auth.py: verify_signature()
- Signature verification mechanism

**What needs to be proven**:
```
├── Wallet Ownership → Prevent identity theft
├── Operation Authorization → Prevent unauthorized operations
└── Multi-sig Authorization → High-value operations
```

**Credit Proof Requirements**:
```json
{
  "wallet_address": "0x123...",
  "identity_id": "SBT-001",
  "binding_timestamp": 1234567890,
  "signature": "ECDSA signature",
  "proof": "Zero-knowledge proof of wallet-identity binding"
}
```

**ZK Applicability**: Medium

---

### Scenario 4: Data Contribution Proof

**Problem**: How to prove "I contributed high-quality data"?

**Current Implementation**:
- No direct implementation
- PPT mentions "crowdsourced dataset"

**What needs to be proven**:
```
├── Data Contribution Amount → Earn incentives
├── Data Quality Score → Affects weight
├── Data Uniqueness → Extra rewards
└── Data Source Legitimacy → Prevent cheating
```

**Credit Proof Requirements**:
```json
{
  "contributor_id": "user-001",
  "data_type": "Creative Asset Valuation Data",
  "contribution_score": 0.85,
  "quality_verified": true,
  "proof": "Data fingerprint + Quality assessment proof"
}
```

**ZK Applicability**: High

---

## 4.3 Service Layer Scenarios (4 scenarios)

### Scenario 5: Service Transaction Trust

**Problem**: Buyer trusts seller can deliver, seller trusts buyer can pay

**Current Implementation**:
- transactions.py: Escrow process
- reputation_service.py: Reputation scoring
- matching_engine.py: Reputation matching

**What needs to be proven**:
```
├── Buyer Payment Ability → Balance proof
├── Seller Delivery Ability → Historical completion rate
├── Both Reputation Scores → Risk assessment
└── Historical Transaction Records → Performance proof
```

**Credit Proof Requirements**:
```json
{
  "party_type": "seller",
  "reputation_score": 0.85,
  "completion_rate": 0.92,
  "total_transactions": 150,
  "dispute_rate": 0.02,
  "proof": "ZK proof of historical transaction statistics without exposing specific transactions"
}
```

**ZK Applicability**: High

---

### Scenario 6: Escrow Payment Trust

**Problem**: Fund safety, milestone-based release, condition triggering

**Current Implementation**:
- transactions.py: Escrow process
- State machine: created→escrowed→in_progress→delivered→completed

**What needs to be proven**:
```
├── Escrow Fund Existence → On-chain lock proof
├── Trigger Conditions Met → Milestone proof
├── Milestone Release Authorization → Multi-party signature
└── Refund Conditions Met → Cancellation/dispute proof
```

**Credit Proof Requirements**:
```json
{
  "transaction_id": "tx-001",
  "escrow_amount": 1000,
  "escrow_status": "locked",
  "release_conditions": ["milestone_1", "milestone_2"],
  "proof": "Smart contract state proof"
}
```

**ZK Applicability**: Medium (more direct on-chain)

---

### Scenario 7: Dispute Arbitration Trust

**Problem**: Who arbitrates, how to prevent collusion, arbitration fairness

**Current Implementation**:
- transactions.py: dispute/resolve endpoints
- Admin permission arbitration

**What needs to be proven**:
```
├── Arbitrator Qualification → Random selection + reputation requirement
├── Arbitration Fairness → No conflict of interest proof
├── Evidence Authenticity → Deliverable existence proof
└── Arbitration Execution → On-chain enforcement
```

**Credit Proof Requirements**:
```json
{
  "dispute_id": "dispute-001",
  "arbitrators": ["arbiter-1", "arbiter-2", "arbiter-3"],
  "arbitrator_selection": "Random selection + reputation threshold > 0.8",
  "no_conflict_proof": "ZK proof that arbitrator has no connection with either party",
  "evidence_hash": "0xabc...",
  "verdict": "buyer_win",
  "proof": "Multi-party signature + Evidence chain"
}
```

**ZK Applicability**: High

---

### Scenario 8: Joint Order Trust

**Problem**: Aggregator trustworthiness, fund safety, fair provider selection

**Current Implementation**:
- quotes.py: Basic quoting
- To be implemented: Aggregation logic, reverse bidding

**What needs to be proven**:
```
├── Demand Authenticity → Multi-party demand aggregation proof
├── Fund Pool Security → Escrow proof
├── Bidding Fairness → All quotes verifiable
├── Provider Capability → Historical delivery proof
└── Revenue Distribution → Proportional settlement proof
```

**Credit Proof Requirements**:
```json
{
  "pool_id": "pool-001",
  "participants": ["user-1", "user-2", "user-3"],
  "total_budget": 3000,
  "bids": [
    {"provider": "p1", "price": 2500, "reputation": 0.85},
    {"provider": "p2", "price": 2800, "reputation": 0.92}
  ],
  "winner": "p1",
  "selection_proof": "Scoring algorithm verifiable execution"
}
```

**ZK Applicability**: High

---

## 4.4 Network Layer Scenarios (4 scenarios)

### Scenario 9: Node Operation Trust

**Problem**: Node reliability, service quality, honest behavior

**Current Implementation**:
- decentralized_node.py: P2PNode
- NodeIdentity: reputation, stake
- Heartbeat mechanism, service registration

**What needs to be proven**:
```
├── Node Identity Real → SBT binding
├── Service Capability Real → Capability proof
├── Online Rate Met → Heartbeat proof
├── No Malicious Behavior → Clean history proof
└── Sufficient Staking → Economic collateral
```

**Credit Proof Requirements**:
```json
{
  "node_id": "node-001",
  "identity_sbt": "SBT-123",
  "uptime_30d": 0.995,
  "avg_latency_ms": 50,
  "stake_amount": 50000,
  "services_provided": 1000,
  "no_slash_history": true,
  "proof": "On-chain reputation + Service statistics proof"
}
```

**ZK Applicability**: High

---

### Scenario 10: Service Discovery Trust

**Problem**: Service capability real, price reasonable, availability

**Current Implementation**:
- discovery.py: Service discovery
- DistributedServiceRegistry

**What needs to be proven**:
```
├── Capability Claim Real → Capability verification proof
├── Price History Stable → No abnormal price fluctuations
├── Currently Available → Real-time load proof
└── Historical Reviews Real → Immutable review records
```

**Credit Proof Requirements**:
```json
{
  "service_id": "service-001",
  "provider_node": "node-001",
  "claimed_capabilities": ["LLM Inference", "Code Generation"],
  "verified_capabilities": true,
  "current_load": 0.3,
  "price_history_stable": true,
  "proof": "Capability test passed + Real-time load proof"
}
```

**ZK Applicability**: Medium

---

### Scenario 11: Cross-Node Collaboration Trust

**Problem**: Trust between unknown nodes, task distribution reliability

**Current Implementation**:
- P2P communication
- Gossip protocol

**What needs to be proven**:
```
├── Counterparty Node Trustworthy → Reputation proof
├── Task Distribution Traceable → Task chain proof
├── Results Trustworthy → Multi-node verification
└── Settlement Fair → Settlement proof
```

**Credit Proof Requirements**:
```json
{
  "source_node": "node-001",
  "target_node": "node-002",
  "task_id": "task-001",
  "task_type": "LLM Inference",
  "both_stake_sufficient": true,
  "both_reputation_above": 0.7,
  "proof": "Bidirectional reputation proof + Task signature"
}
```

**ZK Applicability**: High

---

### Scenario 12: Penalty Mechanism Trust

**Problem**: Penalty fairness, sufficient evidence, appeal channel

**Current Implementation**:
- VIBGovernance.sol: Governance voting
- No dedicated penalty contract

**What needs to be proven**:
```
├── Violation Facts Confirmed → Evidence chain
├── Penalty Ratio Reasonable → Transparent rules
├── Execution Procedure Fair → Appealable
└── Penalty Executed → On-chain record
```

**Credit Proof Requirements**:
```json
{
  "slash_id": "slash-001",
  "violator": "node-003",
  "violation_type": "Service Outage Timeout",
  "evidence": {
    "expected_uptime": 0.99,
    "actual_uptime": 0.85,
    "affected_users": 50
  },
  "penalty_amount": 1000,
  "appeal_deadline": 1234567890,
  "proof": "Monitoring data signature + Rule matching proof"
}
```

**ZK Applicability**: Medium

---

## 4.5 Governance Layer Scenarios (4 scenarios)

### Scenario 13: Proposal Creation Trust

**Problem**: Who is eligible to propose, proposal content authenticity

**Current Implementation**:
- VIBGovernance.sol: Proposal threshold
- governance.py: Proposal API

**What needs to be proven**:
```
├── Proposal Permission → Staking/reputation threshold met
├── Proposal Content Compliant → Follows rules
├── No Conflict of Interest → Independence proof
└── Proposal History Clean → No malicious proposal record
```

**Credit Proof Requirements**:
```json
{
  "proposer": "0x123...",
  "stake_amount": 5000,
  "reputation_score": 0.75,
  "proposal_type": "PARAMETER_CHANGE",
  "no_conflict_of_interest": true,
  "previous_proposals_success_rate": 0.8,
  "proof": "Staking proof + Reputation proof"
}
```

**ZK Applicability**: High

---

### Scenario 14: Voting Weight Trust

**Problem**: How voting rights are calculated, whether fair

**Current Implementation**:
- VIBGovernance.sol: Three-layer governance
  - Layer1: Capital weight (staking × duration)
  - Layer2: Production weight (contribution points)
  - Layer3: Community consensus (KYC one-person-one-vote)

**What needs to be proven**:
```
├── Staking Real → On-chain verifiable
├── Contribution Points Real → Contribution proof
├── KYC Real → Identity verification
├── No Double Voting → Uniqueness proof
└── Weight Calculation Correct → Publicly verifiable
```

**Credit Proof Requirements**:
```json
{
  "voter": "0x123...",
  "layer1_weight": {
    "stake": 10000,
    "duration_multiplier": 1.5,
    "weight": 15000
  },
  "layer2_weight": {
    "contribution_points": 5000,
    "weight": 5000
  },
  "layer3_weight": {
    "kyc_verified": true,
    "weight": 1
  },
  "proof": "ZK proof of correct weight calculation without exposing specific values"
}
```

**ZK Applicability**: Very High

---

### Scenario 15: Execution Authority Trust

**Problem**: Who has authority to execute proposals, whether execution complies

**Current Implementation**:
- VIBGovernance.sol: Timelock execution
- VIBTimelock.sol

**What needs to be proven**:
```
├── Executor Authority → Multi-sig/governance authorization
├── Timelock Passed → Waiting period proof
├── Execution Content Matches Proposal → Consistency proof
└── Execution Result Correct → State change proof
```

**Credit Proof Requirements**:
```json
{
  "proposal_id": "prop-001",
  "executor": "timelock-contract",
  "timelock_expired": true,
  "execution_data_matches_proposal": true,
  "post_execution_state": "parameter_updated",
  "proof": "Timestamp proof + Execution log signature"
}
```

**ZK Applicability**: Low (transparent on-chain)

---

### Scenario 16: Fund Allocation Trust

**Problem**: Fund usage transparency, allocation fairness

**Current Implementation**:
- VIBTreasury.sol: Multi-sig treasury
- Three fund types

**What needs to be proven**:
```
├── Fund Balance Real → On-chain verifiable
├── Expenditure Proposal Compliant → Passed governance
├── Multi-sig Real → Signature verification
├── Recipient Correct → Address matching
└── Execution Result → Transfer success
```

**Credit Proof Requirements**:
```json
{
  "treasury_balance": 1000000,
  "proposal_id": "spend-001",
  "signatures_required": 3,
  "signatures_collected": 4,
  "recipient": "0xabc...",
  "amount": 10000,
  "execution_tx": "0xdef...",
  "proof": "Multi-sig proof + Transfer transaction proof"
}
```

**ZK Applicability**: Low (transparent on-chain)

---

## 4.6 Credit Proof Requirements Summary

| Scenario Category | Specific Scenario | Core Proof Content | ZK Applicability | Priority |
|-------------------|-------------------|---------------------|------------------|----------|
| **User Layer** | Identity Registration | Ability/Certificate Authenticity | High | P2 |
| | Staking Behavior | Staking History, No Slash | High | P1 |
| | Wallet Binding | Ownership Proof | Medium | P3 |
| | Data Contribution | Data Quality/Source | High | P3 |
| **Service Layer** | Service Transaction | Performance History, Reputation | High | P0 |
| | Escrow Payment | Fund Security, Condition Trigger | Medium | P1 |
| | Dispute Arbitration | Fairness, Evidence Chain | High | P2 |
| | Joint Order | Aggregation Fairness, Fund Safety | High | P0 |
| **Network Layer** | Node Operation | Uptime, No Malicious Behavior | High | P1 |
| | Service Discovery | Capability Real, Available | Medium | P2 |
| | Cross-Node Collaboration | Bidirectional Trust | High | P2 |
| | Penalty Mechanism | Evidence Chain, Fairness | Medium | P3 |
| **Governance Layer** | Proposal Creation | Permission, No Conflict | High | P2 |
| | Voting Weight | Three-Layer Weight Real | Very High | P0 |
| | Execution Authority | Timelock, Compliance | Low | P3 |
| | Fund Allocation | Multi-sig, Usage | Low | P3 |

---

## 4.7 ZK Credential Passport Design Recommendations

### Core Principles

```
1. Prove attributes, not expose specific values
2. Prove history, not expose specific transactions
3. Prove eligibility, not expose reasons
```

### Passport Types

| Passport Type | Purpose | What Needs to Be Proven |
|---------------|---------|------------------------|
| **Basic Passport** | Identity Verification, KYC | Identity Real, No Fraud Record |
| **Service Passport** | Service Capability Proof | Completion Rate > 90%, Reputation > 0.7, No Major Complaints |
| **Governance Passport** | Voting Weight Proof | Staking Amount, Contribution Points, KYC Status |
| **VIP Passport** | Comprehensive High Reputation Proof | Reputation > 0.9, Staking > 10000, Contribution Points > 5000 |

### Implementation Priority

```
P0 - Implement Immediately
├── Service Transaction Trust (Required for Every Transaction)
└── Voting Weight Proof (Governance Core)

P1 - Short-term Implementation
├── Node Operation Trust (Network Stability Foundation)
└── Joint Order Trust (New Business Requirement)

P2 - Medium-term Implementation
├── Identity Registration Verification
├── Dispute Arbitration Trust
├── Proposal Creation Trust
└── Service Discovery Trust

P3 - Long-term Implementation
├── Data Contribution Proof
├── Penalty Mechanism Proof
├── Execution Authority Proof
└── Fund Allocation Proof
```

<details>
<summary><h2>中文翻译</h2></summary>

# 第4章：平台信用证明场景全景分析

## 4.1 场景总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AI文明平台信用证明场景总览                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐     │
│  │  用户层     │   │  服务层     │   │  网络层     │   │  治理层     │     │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘     │
│         │                 │                 │                 │            │
│  ┌──────┴──────┐   ┌──────┴──────┐   ┌──────┴──────┐   ┌──────┴──────┐     │
│  │ 1.身份注册  │   │ 5.服务交易  │   │ 9.节点运营  │   │ 13.提案创建 │     │
│  │ 2.质押行为  │   │ 6.托管支付  │   │ 10.服务发现 │   │ 14.投票权重 │     │
│  │ 3.钱包绑定  │   │ 7.争议仲裁  │   │ 11.跨节点  │   │ 15.执行权限 │     │
│  │ 4.数据贡献  │   │ 8.联合订单  │   │ 12.惩罚机制 │   │ 16.资金分配 │     │
│  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4.2 用户层场景 (4个)

### 场景1: 身份注册与验证

**问题**：如何证明"我是我"、"我有资格"？

**当前实现**：
- VIBIdentity.sol (SBT身份)
- isVerified 字段
- 四种身份类型

**需要证明的内容**：
```
├── AI_AGENT身份 → 证明Agent能力描述真实
├── HUMAN_PROVIDER身份 → 证明技能证书真实
├── NODE_OPERATOR身份 → 证明节点规格/位置真实
└── GOVERNANCE身份 → 证明治理历史真实
```

**信用证明需求**：
```json
{
  "identity_type": "HUMAN_PROVIDER",
  "claims": {
    "skills": ["UI设计", "前端开发"],
    "certificates": ["AWS认证", "Adobe认证"],
    "experience_years": 5
  },
  "proof": "zk-SNARK证明",
  "verifier": "平台/第三方"
}
```

**zk适用性**：高

---

### 场景2: 质押行为证明

**问题**：如何证明"我真的质押了"、"质押多久了"？

**当前实现**：
- VIBStaking.sol
- stake字段、stakingDuration

**需要证明的内容**：
```
├── 质押金额 → 影响投票权重、交易限额
├── 质押时长 → 影响资本权重(Layer1治理)
└── 质押历史 → 影响信誉评估
```

**信用证明需求**：
```json
{
  "staker": "0x123...",
  "total_staked": 10000,
  "staking_duration_days": 365,
  "never_slashed": true,
  "proof": "Merkle证明 + 时间戳"
}
```

**zk适用性**：高

---

### 场景3: 钱包绑定与授权

**问题**：如何证明"这个钱包是我的"、"我授权了这个操作"？

**当前实现**：
- auth.py: verify_signature()
- 签名验证机制

**需要证明的内容**：
```
├── 钱包所有权 → 防止身份盗用
├── 操作授权 → 防止未授权操作
└── 多签授权 → 高价值操作
```

**信用证明需求**：
```json
{
  "wallet_address": "0x123...",
  "identity_id": "SBT-001",
  "binding_timestamp": 1234567890,
  "signature": "ECDSA签名",
  "proof": "零知识证明钱包-身份关联"
}
```

**zk适用性**：中

---

### 场景4: 数据贡献证明

**问题**：如何证明"我贡献了高质量数据"？

**当前实现**：
- 无直接实现
- PPT提到"众筹数据集"

**需要证明的内容**：
```
├── 数据贡献量 → 获得激励
├── 数据质量评分 → 影响权重
├── 数据独特性 → 额外奖励
└── 数据来源合法性 → 防止作弊
```

**信用证明需求**：
```json
{
  "contributor_id": "user-001",
  "data_type": "创意资产估值数据",
  "contribution_score": 0.85,
  "quality_verified": true,
  "proof": "数据指纹 + 质量评估证明"
}
```

**zk适用性**：高

---

## 4.3 服务层场景 (4个)

### 场景5: 服务交易信任

**问题**：买方信任卖方能交付，卖方信任买方能付款

**当前实现**：
- transactions.py: 托管流程
- reputation_service.py: 信誉评分
- matching_engine.py: 信誉匹配

**需要证明的内容**：
```
├── 买方支付能力 → 余额证明
├── 卖方交付能力 → 历史完成率
├── 双方信誉分 → 风险评估
└── 历史交易记录 → 履约证明
```

**信用证明需求**：
```json
{
  "party_type": "seller",
  "reputation_score": 0.85,
  "completion_rate": 0.92,
  "total_transactions": 150,
  "dispute_rate": 0.02,
  "proof": "zk证明历史交易统计，不暴露具体交易"
}
```

**zk适用性**：高

---

### 场景6: 托管支付信任

**问题**：资金安全、分批放款、条件触发

**当前实现**：
- transactions.py: escrow流程
- 状态机: created→escrowed→in_progress→delivered→completed

**需要证明的内容**：
```
├── 托管资金存在 → 链上锁定证明
├── 触发条件满足 → 里程碑证明
├── 分批放款授权 → 多方签名
└── 退款条件满足 → 取消/争议证明
```

**信用证明需求**：
```json
{
  "transaction_id": "tx-001",
  "escrow_amount": 1000,
  "escrow_status": "locked",
  "release_conditions": ["milestone_1", "milestone_2"],
  "proof": "智能合约状态证明"
}
```

**zk适用性**：中 (链上更直接)

---

### 场景7: 争议仲裁信任

**问题**：谁来仲裁、如何防止串谋、仲裁公正性

**当前实现**：
- transactions.py: dispute/resolve端点
- admin权限仲裁

**需要证明的内容**：
```
├── 仲裁员资格 → 随机选取+信誉要求
├── 仲裁公正性 → 无利益冲突证明
├── 证据真实性 → 交付物存在证明
└── 仲裁结果执行 → 链上强制执行
```

**信用证明需求**：
```json
{
  "dispute_id": "dispute-001",
  "arbitrators": ["arbiter-1", "arbiter-2", "arbiter-3"],
  "arbitrator_selection": "随机选取+信誉阈值>0.8",
  "no_conflict_proof": "zk证明仲裁员与双方无关联",
  "evidence_hash": "0xabc...",
  "verdict": "buyer_win",
  "proof": "多方签名 + 证据链"
}
```

**zk适用性**：高

---

### 场景8: 联合订单信任

**问题**：聚合者可信、资金安全、服务商选择公正

**当前实现**：
- quotes.py: 基础报价
- 待实现: 聚合逻辑、反向竞价

**需要证明的内容**：
```
├── 需求真实性 → 多方需求聚合证明
├── 资金池安全 → 托管证明
├── 竞价公正性 → 所有报价可验证
├── 服务商能力 → 历史交付证明
└── 收益分配 → 按比例分账证明
```

**信用证明需求**：
```json
{
  "pool_id": "pool-001",
  "participants": ["user-1", "user-2", "user-3"],
  "total_budget": 3000,
  "bids": [
    {"provider": "p1", "price": 2500, "reputation": 0.85},
    {"provider": "p2", "price": 2800, "reputation": 0.92}
  ],
  "winner": "p1",
  "selection_proof": "评分算法可验证执行"
}
```

**zk适用性**：高

---

## 4.4 网络层场景 (4个)

### 场景9: 节点运营信任

**问题**：节点可靠性、服务质量、诚实行为

**当前实现**：
- decentralized_node.py: P2PNode
- NodeIdentity: reputation, stake
- 心跳机制、服务注册

**需要证明的内容**：
```
├── 节点身份真实 → SBT绑定
├── 服务能力真实 → 能力证明
├── 在线率达标 → 心跳证明
├── 无恶意行为 → 历史清白证明
└── 质押充足 → 经济担保
```

**信用证明需求**：
```json
{
  "node_id": "node-001",
  "identity_sbt": "SBT-123",
  "uptime_30d": 0.995,
  "avg_latency_ms": 50,
  "stake_amount": 50000,
  "services_provided": 1000,
  "no_slash_history": true,
  "proof": "链上信誉 + 服务统计证明"
}
```

**zk适用性**：高

---

### 场景10: 服务发现信任

**问题**：服务能力真实、价格合理、可用性

**当前实现**：
- discovery.py: 服务发现
- DistributedServiceRegistry

**需要证明的内容**：
```
├── 能力声明真实 → 能力验证证明
├── 价格历史稳定 → 价格无异常波动
├── 当前可用 → 实时负载证明
└── 历史评价真实 → 评价不可篡改
```

**信用证明需求**：
```json
{
  "service_id": "service-001",
  "provider_node": "node-001",
  "claimed_capabilities": ["LLM推理", "代码生成"],
  "verified_capabilities": true,
  "current_load": 0.3,
  "price_history_stable": true,
  "proof": "能力测试通过 + 负载实时证明"
}
```

**zk适用性**：中

---

### 场景11: 跨节点协作信任

**问题**：陌生节点间信任、任务分发可靠性

**当前实现**：
- P2P通信
- gossip协议

**需要证明的内容**：
```
├── 对方节点可信 → 信誉证明
├── 任务分派可追溯 → 任务链证明
├── 结果可信 → 多节点验证
└── 结算公正 → 分账证明
```

**信用证明需求**：
```json
{
  "source_node": "node-001",
  "target_node": "node-002",
  "task_id": "task-001",
  "task_type": "LLM推理",
  "both_stake_sufficient": true,
  "both_reputation_above": 0.7,
  "proof": "双向信誉证明 + 任务签名"
}
```

**zk适用性**：高

---

### 场景12: 惩罚机制信任

**问题**：惩罚公正、证据充分、申诉渠道

**当前实现**：
- VIBGovernance.sol: 治理投票
- 无专门的惩罚合约

**需要证明的内容**：
```
├── 违规事实确凿 → 证据链
├── 惩罚比例合理 → 规则透明
├── 执行程序公正 → 可申诉
└── 惩罚已执行 → 链上记录
```

**信用证明需求**：
```json
{
  "slash_id": "slash-001",
  "violator": "node-003",
  "violation_type": "服务中断超时",
  "evidence": {
    "expected_uptime": 0.99,
    "actual_uptime": 0.85,
    "affected_users": 50
  },
  "penalty_amount": 1000,
  "appeal_deadline": 1234567890,
  "proof": "监控数据签名 + 规则匹配证明"
}
```

**zk适用性**：中

---

## 4.5 治理层场景 (4个)

### 场景13: 提案创建信任

**问题**：谁有资格提案、提案内容真实

**当前实现**：
- VIBGovernance.sol: 提案门槛
- governance.py: 提案API

**需要证明的内容**：
```
├── 提案权限 → 质押/信誉达标
├── 提案内容合规 → 符合规则
├── 无利益冲突 → 独立性证明
└── 提案历史清白 → 无恶意提案记录
```

**信用证明需求**：
```json
{
  "proposer": "0x123...",
  "stake_amount": 5000,
  "reputation_score": 0.75,
  "proposal_type": "PARAMETER_CHANGE",
  "no_conflict_of_interest": true,
  "previous_proposals_success_rate": 0.8,
  "proof": "质押证明 + 信誉证明"
}
```

**zk适用性**：高

---

### 场景14: 投票权重信任

**问题**：投票权如何计算、是否公平

**当前实现**：
- VIBGovernance.sol: 三层治理
  - Layer1: 资本权重(质押×时长)
  - Layer2: 生产权重(贡献积分)
  - Layer3: 社区共识(KYC一人一票)

**需要证明的内容**：
```
├── 质押真实 → 链上可查
├── 贡献积分真实 → 贡献证明
├── KYC真实 → 身份验证
├── 无重复投票 → 唯一性证明
└── 权重计算正确 → 公开可验证
```

**信用证明需求**：
```json
{
  "voter": "0x123...",
  "layer1_weight": {
    "stake": 10000,
    "duration_multiplier": 1.5,
    "weight": 15000
  },
  "layer2_weight": {
    "contribution_points": 5000,
    "weight": 5000
  },
  "layer3_weight": {
    "kyc_verified": true,
    "weight": 1
  },
  "proof": "zk证明权重计算正确，不暴露具体数值"
}
```

**zk适用性**：极高

---

### 场景15: 执行权限信任

**问题**：谁有权执行提案、执行是否合规

**当前实现**：
- VIBGovernance.sol: 时间锁执行
- VIBTimelock.sol

**需要证明的内容**：
```
├── 执行者权限 → 多签/治理授权
├── 时间锁已过 → 等待期证明
├── 执行内容匹配提案 → 一致性证明
└── 执行结果正确 → 状态变更证明
```

**信用证明需求**：
```json
{
  "proposal_id": "prop-001",
  "executor": "timelock-contract",
  "timelock_expired": true,
  "execution_data_matches_proposal": true,
  "post_execution_state": "parameter_updated",
  "proof": "时间戳证明 + 执行日志签名"
}
```

**zk适用性**：低 (链上透明)

---

### 场景16: 资金分配信任

**问题**：资金用途透明、分配公正

**当前实现**：
- VIBTreasury.sol: 多签财政
- 三种基金类型

**需要证明的内容**：
```
├── 资金余额真实 → 链上可查
├── 支出提案合规 → 治理通过
├── 多签真实 → 签名验证
├── 接收方正确 → 地址匹配
└── 执行结果 → 转账成功
```

**信用证明需求**：
```json
{
  "treasury_balance": 1000000,
  "proposal_id": "spend-001",
  "signatures_required": 3,
  "signatures_collected": 4,
  "recipient": "0xabc...",
  "amount": 10000,
  "execution_tx": "0xdef...",
  "proof": "多签证明 + 转账交易证明"
}
```

**zk适用性**：低 (链上透明)

---

## 4.6 信用证明需求汇总

| 场景分类 | 具体场景 | 核心证明内容 | zk适用性 | 优先级 |
|----------|----------|--------------|----------|--------|
| **用户层** | 身份注册 | 能力/证书真实性 | 高 | P2 |
| | 质押行为 | 质押历史、无惩罚 | 高 | P1 |
| | 钱包绑定 | 所有权证明 | 中 | P3 |
| | 数据贡献 | 数据质量/来源 | 高 | P3 |
| **服务层** | 服务交易 | 履约历史、信誉 | 高 | P0 |
| | 托管支付 | 资金安全、条件触发 | 中 | P1 |
| | 争议仲裁 | 公正性、证据链 | 高 | P2 |
| | 联合订单 | 聚合公正、资金安全 | 高 | P0 |
| **网络层** | 节点运营 | 在线率、无恶意 | 高 | P1 |
| | 服务发现 | 能力真实、可用 | 中 | P2 |
| | 跨节点协作 | 双向信任 | 高 | P2 |
| | 惩罚机制 | 证据链、公正 | 中 | P3 |
| **治理层** | 提案创建 | 权限、无冲突 | 高 | P2 |
| | 投票权重 | 三层权重真实 | 极高 | P0 |
| | 执行权限 | 时间锁、合规 | 低 | P3 |
| | 资金分配 | 多签、用途 | 低 | P3 |

---

## 4.7 zk-信用通行证设计建议

### 核心原则

```
1. 证明属性，不暴露具体值
2. 证明历史，不暴露具体交易
3. 证明资格，不暴露原因
```

### 通行证类型

| 通行证类型 | 用途 | 需要证明的内容 |
|------------|------|----------------|
| **基础通行证** | 身份验证、KYC | 身份真实、无欺诈记录 |
| **服务通行证** | 服务能力证明 | 完成率>90%、信誉>0.7、无重大投诉 |
| **治理通行证** | 投票权重证明 | 质押量、贡献积分、KYC状态 |
| **VIP通行证** | 综合高信誉证明 | 信誉>0.9、质押>10000、贡献积分>5000 |

### 实现优先级

```
P0 - 立即实现
├── 服务交易信任 (每笔交易都需要)
└── 投票权重证明 (治理核心)

P1 - 短期实现
├── 节点运营信任 (网络稳定基础)
└── 联合订单信任 (新业务需要)

P2 - 中期实现
├── 身份注册验证
├── 争议仲裁信任
├── 提案创建信任
└── 服务发现信任

P3 - 长期实现
├── 数据贡献证明
├── 惩罚机制证明
├── 执行权限证明
└── 资金分配证明
```

</details>
