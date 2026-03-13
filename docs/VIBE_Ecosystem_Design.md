# VIBE Ecosystem Design Document

**[English](#vibe-ecosystem-design-document) | [中文](#vibe-生态完整设计方案)**

---

## 1. Core Goal

> **"AI Agent Self-Driven Collaboration, Scheduling Humans to Execute Real-World Work"**

---

## 2. Token Economics

### 2.1 Basic Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| Token Name | VIBE | Silicon Civilization Platform Token |
| Symbol | VIBE | - |
| Total Supply | 1,000,000,000 (1 Billion) | Hard Cap, No Additional Minting |
| Decimals | 18 | Standard ERC-20 |
| Initial Circulating | 8% | 80 Million Tokens |
| Mainnet | Base (Ethereum L2) | - |

### 2.2 Distribution Scheme (Final Version - 2026-02-24)

> **Core Principle: Fully Decentralized, No Manual Trigger, Everything Decided by Code**
> Reference: VIBE_Full_Automation_Design.md

| Category | Ratio | Amount | Management Contract | Trigger Condition |
|----------|-------|--------|---------------------|-------------------|
| Team | 8% | 80M | VIBVesting (4-year lockup) | Time-based auto-release |
| Early Supporters | 4% | 40M | VIBVesting (2-year lockup) | Time-based auto-release |
| Community Stable Fund | 6% | 60M | CommunityStableFund | Auto-buyback on price drop |
| Liquidity Pool | 12% | 120M | LiquidityManager | Time-triggered market making |
| Community Airdrop | 7% | 70M | AirdropDistributor | User self-claim |
| Incentive Pool | 63% | 630M | EmissionController | Cycle-based auto-release |

```
Total: 1 Billion VIBE (No Public Sale)

┌────────────────────────────────────────────────────────────┐
│ Token Distribution - Fully Decentralized Management       │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Team 8% (80M)                                            │
│  ├── Management: VIBVesting (separate contract)           │
│  ├── Lockup: 4-year linear release                       │
│  └── Trigger: Time-based auto-release                     │
│                                                            │
│  Early Supporters 4% (40M)                               │
│  ├── Management: VIBVesting (separate from team)         │
│  ├── Lockup: 2-year linear release                       │
│  └── Trigger: Time-based auto-release                     │
│                                                            │
│  Community Stable Fund 6% (60M)                          │
│  ├── Management: CommunityStableFund                     │
│  ├── Function: Auto-buyback & burn on 20% price drop     │
│  └── Trigger: Oracle condition trigger                    │
│                                                            │
│  Liquidity Pool 12% (120M)                               │
│  ├── Management: LiquidityManager                        │
│  ├── Function: DEX market making, LP permanently locked  │
│  └── Trigger: Deploy-time init + auto-compound           │
│                                                            │
│  Community Airdrop 7% (70M)                               │
│  ├── Management: AirdropDistributor                      │
│  ├── Mechanism: 6 months 100% / 7-12 months 50%         │
│  └── Trigger: User self-claim (Merkle verification)      │
│                                                            │
│  Incentive Pool 63% (630M)                              │
│  ├── Management: EmissionController                      │
│  ├── Release: 5-year linear release                      │
│  └── Trigger: 7-day cycle auto-release                   │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

#### Incentive Pool Internal Distribution (63% = 630M)

| Sub-pool | % of Pool | Amount | Who Can Get | Trigger |
|----------|-----------|--------|-------------|---------|
| Staking Rewards | 45% | 283.5M | Stakers | Stake VIBE |
| Ecosystem Incentive | 30% | 189M | Developers/Builders | DApp usage/code contribution |
| Governance Rewards | 15% | 94.5M | Governance Participants | Voting/Proposals |
| Reserve | 10% | 63M | Emergency | Extreme situations |

#### Fully Decentralized Principles

```
┌─────────────────────────────────────────────────────────┐
│            Fully Decentralized Ecosystem                │
├─────────────────────────────────────────────────────────┤
│  ❌ Does not depend on anyone                           │
│  ❌ No multi-sig approval required                     │
│  ❌ No manual trigger needed                           │
│  ❌ Does not trust anyone                              │
│                                                         │
│  ✅ Everything decided by code                         │
│  ✅ Everything triggered by conditions                 │
│  ✅ Everything transparent on-chain                   │
│  ✅ Everything immutable                              │
└─────────────────────────────────────────────────────────┘
```

> **Note**: The "Reserved Pool" (Infrastructure Pool 18% / Governance Evolution Pool 10%) has been cancelled in the final design, with related functions merged into the Ecosystem Incentive (30%) and Governance Rewards (15%) sub-pools of the Incentive Pool.

### 2.3 Transaction Fee vs Gas Fee

```
Important Distinction:
├── Gas Fee (Network Fee)
│   ├── Paid to: Base/Ethereum Network
│   ├── Amount: ~$0.01-0.10 per transaction
│   └── Cannot be avoided, must be paid for every tx
│
└── Transaction Fee (Platform Fee)
    ├── Paid to: VIBE Platform
    ├── Amount: 0.8% (per transaction)
    ├── Distribution:
    │   ├── 20% → Ecosystem Fund
    │   ├── 50% → Burn
    │   └── 30% → Protocol Operations
    └── Optional Feature
```

### 2.3 Inflation/Deflation Mechanism

#### Inflation Control
- Annual Inflation Cap: 2% (hard constraint in contract)
- Dynamic Range: 1.5% - 3%
- Circuit Breaker: Pause release when monthly inflation > 0.5%

#### Deflation Mechanism
| Source | Rate | Description |
|--------|------|-------------|
| Transaction Fee | 0.8% | Per transaction |
| Transaction Burn | 50% | 50% of fee burned |
| Service Fee Burn | 20% | Platform service fee |
| Penalty Confiscation | 100% | Violation behavior |

#### Anti-Death Spiral Mechanism
- Buyback Pool: 5% (buyback when token price drops)
- Liquidity Margin: 3% (DEX liquidity)
- Dynamic APY: Auto-increase when token price drops

---

## 3. Funding Design

### 3.1 Final Plan: No Public Sale

```
Reasons for No Public Sale:
- Avoid token concentration in large holders
- Avoid future selling pressure
- Keep community-oriented
- Align with Web3 spirit
```

### 3.2 Launch Capital Sources

```
Angel Investment (Private):
- Angel investors not disclosed publicly
- Team self-funded portion
- Early supporter investments
```

### 3.3 Ecosystem Fund Sources

```
From Protocol Revenue:
- Transaction Fee 20% → Ecosystem Fund
- Service Fee Revenue → Ecosystem Fund
```

---

## 4. Ecosystem Fund Management

### 4.1 Progressive Management

```
Phase 1 (Early): Team-Led
├── Multi-sig wallet (3/5)
├── Team decisions
└── Transparency reports

Phase 2 (Transition): DAO Oversight
├── Multi-sig + DAO voting
├── Major expenditures require DAO approval
└── Quarterly reports

Phase 3 (Mature): Fully DAO
├── DAO full control
├── Proposal voting
└── Community governance
```

### 4.2 Ecosystem Fund Sources & Usage

```
Sources:
├── Angel investment (not disclosed)
└── Protocol revenue (20% of tx fees)

Usage:
├── Developer Incentives (Grants) 40%
├── Ecosystem Project Investment 25%
├── Marketing 20%
├── Community Operations 10%
└── Legal/Compliance 5%
```

---

## 5. Governance Design

### 5.1 Three-Layer Governance Structure

```
┌─────────────────────────────────────────────────────┐
│ Layer 1: Capital Weight                             │
│ - Stake amount × Duration coefficient              │
│ - Single address ≤10%                              │
│ - Use: Major parameter adjustments, fund usage,    │
│   strategic direction                              │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Layer 2: Production Weight                          │
│ - Contribution points (non-transferable)          │
│ - Single address ≤15%                              │
│ - Use: Incentive mechanism adjustments, production │
│   standards                                         │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Layer 3: Community Consensus                        │
│ - One-person-one-vote after KYC                    │
│ - 10% of total voting power                        │
│ - Use: Veto extreme proposals                      │
└─────────────────────────────────────────────────────┘
```

### 5.2 Proposal System

| Proposal Type | Threshold | Pass Rate | Time Lock |
|---------------|-----------|-----------|-----------|
| General | 500 VIBE | >50% | 14 days |
| Parameter Adjustment | 5,000 VIBE | >60% | 30 days |
| Protocol Upgrade | 50,000 VIBE | >75% | 60 days |
| Emergency | - | >90% | Immediate |

### 5.3 Time Lock

```
Parameter Change Time Lock:
├── Staking APY: 14-day delay
├── Fee: 30-day delay
├── Burn Ratio: 30-day delay
└── Dividend Ratio: 30-day delay
```

---

## 6. Liquidity Design

### 6.1 Initial Liquidity

```
Initial Liquidity Sources:
1. Team's own funds (10% tokens)
2. Market maker arrangements
3. DEX liquidity mining incentives
```

### 6.2 Liquidity Pool Strategy

| Phase | Action |
|-------|--------|
| Deployment | Establish VIBE/ETH, VIBE/USDC pools |
| After Launch | Start liquidity mining (LP rewards) |
| 3 months | Apply for CEX listing |
| 6 months | Multi-chain deployment (optional) |

### 6.3 Liquidity Lockup

- Lock 50%+ tokens initially
- Batch release to maintain price stability

---

## 7. AI Agent Collaboration Design

### 7.1 AI Agent Economic Entity

```
Each AI Agent requires:
├── Wallet address (AgentWallet contract)
├── Identity credential (SBT)
├── Credit score
└── Fund pool
```

### 7.2 AI Agent Collaboration Process

```
1. Task Publishing
   └── Requester publishes task → Describe goal

2. Task Decomposition
   └── AI automatically splits into subtasks

3. Agent Discovery
   └── Match relevant Agents → Negotiate resources

4. Collaborative Execution
   └── Agent-to-Agent collaboration → Humans execute physical tasks

5. Revenue Distribution
   └── 70% to final producer
   └── 20% to collaborative contributor
   └── 10% to coordinator

6. Tax/Burn
   └── 0.8% fee
   └── 50% burned
```

### 7.3 Human Role

```
Scenarios where humans are scheduled by AI:
├── Physical operations (physical tasks AI cannot do)
├── Identity verification (KYC)
├── Quality review
└── Dispute arbitration
```

---

## 8. AgentFi Design

### 8.1 Currently Achievable (MVP)

| Function | Description |
|----------|-------------|
| Agent Wallet | Limit control, whitelist |
| Agent Registration | Identity SBT |
| Task Rewards | Staking rewards |

### 8.2 Future Design (Reserved Interfaces)

| Function | Status |
|----------|--------|
| Agent Credit | TODO |
| Agent Investment | TODO |
| Agent Insurance | TODO |
| Compute Market | TODO |
| Data Market | TODO |

---

## 9. Contract Extensibility

### 9.1 Modular Design

```
┌─────────────────────────────────────────────┐
│ Core Layer (Immutable)                     │
│ ├── VIBEToken (Token)                       │
│ ├── VIBStaking (Staking)                    │
│ └── VIBVesting (Lockup)                     │
├─────────────────────────────────────────────┤
│ Extension Layer (Upgradeable)               │
│ ├── Governance Module (Governance.sol)      │
│ ├── Dividend Module (Dividend.sol)          │
│ ├── Burn Module (Burn.sol)                  │
│ └── Ecosystem Fund (EcosystemFund.sol)       │
├─────────────────────────────────────────────┤
│ Application Layer (Optional)                │
│ ├── AgentFi                                 │
│ ├── Compute Market                          │
│ └── Data Market                             │
└─────────────────────────────────────────────┘
```

### 9.2 Upgrade Mechanism

- Early Stage: Upgradeable proxy contracts
- Mature: Immutable contracts

---

## 10. Implementation Roadmap

### Phase 1: Infrastructure (Now)

- [x] Economic model design
- [x] Game theory verification
- [ ] Core contract development
- [ ] Token deployment (with governance)

### Phase 2: Staking System (Parallel)

- [ ] Staking contract
- [ ] Lockup contract
- [ ] Burn mechanism

### Phase 3: Ecosystem (Post-Launch)

- [ ] Ecosystem fund launch
- [ ] Liquidity pool
- [ ] CEX listing

### Phase 4: AgentFi (Future)

- [ ] Agent credit
- [ ] Compute market
- [ ] Data market

---

## 11. Final Plan Summary

### Token Distribution

| Distribution | Ratio | Purpose |
|-------------|-------|---------|
| Team | 8% | 4-year lockup |
| Early Supporters | 4% | 2-year lockup |
| Community Stable Fund | 6% | Market support/emergency/incentive |
| Liquidity Pool | 12% | DEX market making |
| Community Airdrop | 7% | Attract users |
| Incentive Pool | 63% | 5-year linear release |

### Funding

- Launch capital: Angel investment (not disclosed)
- Ecosystem fund: Protocol revenue (20% of tx fees)

### Governance

- Launch together: Proposal + Voting + Time Lock

---

## 12. Pending Discussion Items

### ✅ Decided

| Issue | Decision |
|-------|----------|
| Private Sale | None |
| Ecosystem Fund Source | Protocol revenue + angel investment |
| Governance | Launch together |
| Community Stable Fund | Keep 6% |

### To Discuss

1. [ ] Specific contract deployment parameters
2. [ ] Launch timing
3. [ ] CEX selection
4. [ ] Compliance plan

---

## 13. Reference Design Checklist

Complete missing functions see: `docs/VIBE_Design_Checklist.md`

---

*This document is based on expert verification and team discussions, continuously updated*

<details>
<summary><h2>中文翻译</h2></summary>

# VIBE 生态完整设计方案

> 基于专家论证的完整设计文档
> 版本: v1.0
> 日期: 2026-02-23

---

## 一、核心目标

> **"AI Agent 自我驱动协作，调度人类执行真实世界工作"**

---

## 二、代币经济模型

### 2.1 基本参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 代币名称 | VIBE | 硅基文明平台代币 |
| 符号 | VIBE | - |
| 总供应量 | 1,000,000,000 (10亿) | 硬顶，不可增发 |
| 精度 | 18位 | 标准ERC-20 |
| 初始流通 | 8% | 8000万枚 |
| 主网 | Base (Ethereum L2) | - |

### 2.2 分配方案（最终版 - 2026-02-24）

> **核心原则：完全去中心化、不需要手动触发、一切由代码决定**
> 参考：VIBE_Full_Automation_Design.md

| 类别 | 比例 | 数量 | 管理合约 | 触发条件 |
|------|------|------|---------|---------|
| 团队 | 8% | 8000万 | VIBVesting（4年锁仓） | 时间自动释放 |
| 早期支持者 | 4% | 4000万 | VIBVesting（2年锁仓） | 时间自动释放 |
| 社区稳定基金 | 6% | 6000万 | CommunityStableFund | 价格下跌自动回购 |
| 流动性池 | 12% | 1.2亿 | LiquidityManager | 时间触发自动做市 |
| 社区空投 | 7% | 7000万 | AirdropDistributor | 用户自领 |
| 激励池 | 63% | 6.3亿 | EmissionController | 周期自动释放 |

```
总量：10亿 VIBE (不做私募)

┌────────────────────────────────────────────────────────────┐
│ 代币分配 - 完全去中心化管理                                  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  团队 8% (0.8亿)                                           │
│  ├── 管理合约: VIBVesting (独立合约)                       │
│  ├── 锁仓期: 4年线性释放                                   │
│  └── 触发: 时间自动释放                                    │
│                                                            │
│  早期支持者 4% (0.4亿)                                      │
│  ├── 管理合约: VIBVesting (独立合约，与团队分开)           │
│  ├── 锁仓期: 2年线性释放                                   │
│  └── 触发: 时间自动释放                                    │
│                                                            │
│  社区稳定基金 6% (0.6亿)                                    │
│  ├── 管理合约: CommunityStableFund                        │
│  ├── 功能: 价格下跌20%自动回购销毁                         │
│  └── 触发: 预言机条件触发                                  │
│                                                            │
│  流动性池 12% (1.2亿)                                       │
│  ├── 管理合约: LiquidityManager                           │
│  ├── 功能: DEX做市、LP永久锁定                             │
│  └── 触发: 部署时初始化 + 自动复投                         │
│                                                            │
│  社区空投 7% (0.7亿)                                        │
│  ├── 管理合约: AirdropDistributor                         │
│  ├── 机制: 6月100% / 7-12月50%                            │
│  └── 触发: 用户自领 (Merkle验证)                          │
│                                                            │
│  激励池 63% (6.3亿)                                         │
│  ├── 管理合约: EmissionController                         │
│  ├── 释放: 5年线性释放                                     │
│  └── 触发: 7天周期自动释放                                 │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

#### 激励池内部分配（63% = 6.3亿）

| 子池 | 占激励池比例 | 数量 | 谁能获得 | 触发条件 |
|------|-------------|------|---------|---------|
| 质押奖励 | 45% | 2.835亿 | 质押者 | 质押 VIBE |
| 生态激励 | 30% | 1.89亿 | 开发者/建设者 | DApp 被使用/代码贡献 |
| 治理奖励 | 15% | 0.945亿 | 治理参与者 | 投票/提案 |
| 储备 | 10% | 0.63亿 | 应急 | 极端情况 |

#### 完全去中心化原则

```
┌─────────────────────────────────────────────────────────┐
│                    完全去中心化生态                       │
├─────────────────────────────────────────────────────────┤
│  ❌ 不依赖任何人                                         │
│  ❌ 不需要多签审批                                       │
│  ❌ 不需要手动触发                                       │
│  ❌ 不相信任何人                                         │
│                                                         │
│  ✅ 一切由代码决定                                       │
│  ✅ 一切由条件触发                                       │
│  ✅ 一切链上透明                                         │
│  ✅ 一切不可篡改                                         │
└─────────────────────────────────────────────────────────┘
```

> **注意**: "预留池"(基础设施池18%/治理演进池10%)已在最终设计中取消，
> 相关功能并入激励池的生态激励(30%)和治理奖励(15%)子池。

### 2.3 交易手续费 vs Gas费

```
重要区别:
├── Gas费 (网络费用)
│   ├── 支付给: Base/Ethereum 网络
│   ├── 金额: 约 $0.01-0.10/笔
│   └── 无法避免，每笔交易必须支付
│
└── 交易手续费 (平台费用)
    ├── 支付给: VIBE 平台
    ├── 金额: 0.8% (每笔交易)
    ├── 分配:
    │   ├── 20% → 生态基金
    │   ├── 50% → 销毁
    │   └── 30% → 协议运营
    └── 可选功能
```

### 2.3 通胀/通缩机制

#### 通胀控制
- 年通胀上限: 2% (硬约束写入合约)
- 动态区间: 1.5% - 3%
- 熔断机制: 月通胀 > 0.5% 时暂停释放

#### 通缩机制
| 来源 | 比例 | 说明 |
|------|------|------|
| 交易手续费 | 0.8% | 每笔交易 |
| 交易销毁 | 50% | 手续费中的50%销毁 |
| 服务费销毁 | 20% | 平台服务费 |
| 惩罚没收 | 100% | 违规行为 |

#### 反死螺旋机制
- 回购池: 5% (币价下跌时回购)
- 流动性保证金: 3% (DEX流动性)
- 动态APY: 币价跌时自动提升

---

## 三、融资设计

### 3.1 最终方案: 不做公开私募

```
不做公开私募的原因:
- 避免代币集中在大户手中
- 避免后期抛压
- 保持社区化
- 符合Web3精神
```

### 3.2 启动资金来源

```
天使投资 (Private):
- 不公开天使投资人名单
- 团队自筹部分资金
- 早期支持者投资
```

### 3.3 生态基金来源

```
从协议收益中提取:
- 交易手续费 20% → 生态基金
- 服务费收入 → 生态基金
```

---

## 四、生态基金管理

### 4.1 渐进式管理

```
阶段1 (早期): 团队主导
├── 多签钱包 (3/5)
├── 团队决策
└── 透明度报告

阶段2 (过渡): DAO监督
├── 多签 + DAO投票
├── 重大支出需DAO批准
└── 季度报告

阶段3 (成熟): 完全DAO
├── DAO完全控制
├── 提案投票
└── 社区治理
```

### 4.2 生态基金来源与用途

```
来源:
├── 天使投资 (不公开)
└── 协议收益 (交易费20%)

用途:
├── 开发者激励 (Grant) 40%
├── 生态项目投资 25%
├── 市场推广 20%
├── 社区运营 10%
└── 法律/合规 5%
```

---

## 五、治理设计

### 5.1 三层治理结构

```
┌─────────────────────────────────────────────────────┐
│ Layer 1: 资本权重                                   │
│ - 质押量 × 时长系数                                 │
│ - 单地址 ≤10%                                     │
│ - 用途: 重大参数调整、资金使用、战略方向           │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Layer 2: 生产权重                                   │
│ - 贡献积分 (不可转让)                               │
│ - 单地址 ≤15%                                     │
│ - 用途: 激励机制调整、生产标准制定                 │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Layer 3: 社区共识                                   │
│ - KYC验证后一人一票                                 │
│ - 占总投票权 10%                                   │
│ - 用途: 否决极端提案                               │
└─────────────────────────────────────────────────────┘
```

### 5.2 提案系统

| 提案类型 | 门槛 | 通过率 | 时间锁 |
|---------|------|--------|--------|
| 一般提案 | 500 VIBE | >50% | 14天 |
| 参数调整 | 5,000 VIBE | >60% | 30天 |
| 协议升级 | 50,000 VIBE | >75% | 60天 |
| 紧急提案 | - | >90% | 立即 |

### 5.3 时间锁

```
参数变更时间锁:
├── 质押APY: 14天延迟
├── 手续费: 30天延迟
├── 销毁比例: 30天延迟
└── 分红比例: 30天延迟
```

---

## 六、流动性设计

### 6.1 初期流动性

```
初始流动性来源:
1. 团队自有资金 (10%代币)
2. 做市商安排
3. DEX流动性挖矿激励
```

### 6.2 流动性池策略

| 阶段 | 动作 |
|------|------|
| 部署时 | 建立 VIBE/ETH, VIBE/USDC 池 |
| 上线后 | 启动流动性挖矿 (LP奖励) |
| 3个月 | 申请CEX上市 |
| 6个月 | 多链部署 (可选) |

### 6.3 流动性锁定

- 初期锁定50%+代币
- 分批释放维护价格稳定

---

## 七、AI Agent 协作设计

### 7.1 AI Agent 经济主体

```
每个 AI Agent 需要:
├── 钱包地址 (AgentWallet 合约)
├── 身份凭证 (SBT)
├── 信用评分
└── 资金池
```

### 7.2 AI Agent 协作流程

```
1. 任务发布
   └── 需求方发布任务 → 描述目标

2. 任务分解
   └── AI自动拆解为子任务

3. Agent 发现
   └── 匹配相关Agent → 协商资源

4. 协作执行
   └── Agent间协作 → 人类执行物理任务

5. 收益分配
   └── 70% 最终产出者
   └── 20% 协作贡献者
   └── 10% 协调者

6. 税务/销毁
   └── 0.8% 手续费
   └── 50% 销毁
```

### 7.3 人类角色

```
人类被AI调度的场景:
├── 物理操作 (AI无法执行的物理任务)
├── 身份验证 (KYC)
├── 质量审核
└── 争议仲裁
```

---

## 八、AgentFi 设计

### 8.1 当前可实现 (MVP)

| 功能 | 说明 |
|------|------|
| Agent钱包 | 限额控制、白名单 |
| Agent注册 | 身份SBT |
| 任务奖励 | 质押奖励 |

### 8.2 未来设计 (预留接口)

| 功能 | 状态 |
|------|------|
| Agent信贷 | TODO |
| Agent投资 | TODO |
| Agent保险 | TODO |
| 算力市场 | TODO |
| 数据市场 | TODO |

---

## 九、合约扩展性

### 9.1 模块化设计

```
┌─────────────────────────────────────────────┐
│ 核心层 (不可变)                              │
│ ├── VIBEToken (代币)                        │
│ ├── VIBStaking (质押)                      │
│ └── VIBVesting (锁仓)                       │
├─────────────────────────────────────────────┤
│ 扩展层 (可升级)                              │
│ ├── 治理模块 (Governance.sol)               │
│ ├── 分红模块 (Dividend.sol)                 │
│ ├── 销毁模块 (Burn.sol)                     │
│ └── 生态基金 (EcosystemFund.sol)            │
├─────────────────────────────────────────────┤
│ 应用层 (可选)                                │
│ ├── AgentFi                                 │
│ ├── 算力市场                                │
│ └── 数据市场                                 │
└─────────────────────────────────────────────┘
```

### 9.2 升级机制

- 初期: 可升级代理合约
- 成熟: 不可变合约

---

## 十、实施路线图

### Phase 1: 基础设施 (现在)

- [x] 经济模型设计
- [x] 博弈论证
- [ ] 核心合约开发
- [ ] 代币部署 (包含治理)

### Phase 2: 质押系统 (同步)

- [ ] 质押合约
- [ ] 锁仓合约
- [ ] 销毁机制

### Phase 3: 生态 (上线后)

- [ ] 生态基金启动
- [ ] 流动性池
- [ ] CEX上市

### Phase 4: AgentFi (未来)

- [ ] Agent信贷
- [ ] 算力市场
- [ ] 数据市场

---

## 十一、最终方案总结

### 代币分配

| 分配 | 比例 | 用途 |
|------|------|------|
| 团队 | 8% | 4年锁仓 |
| 早期支持者 | 4% | 2年锁仓 |
| 社区稳定基金 | 6% | 护盘/应急/激励 |
| 流动性池 | 12% | DEX做市 |
| 社区空投 | 7% | 吸引用户 |
| 激励池 | 63% | 5年线性释放 |

### 融资

- 启动资金: 天使投资 (不公开)
- 生态基金: 协议收益 (交易费20%)

### 治理

- 一起上线: 提案 + 投票 + 时间锁

---

## 十二、待讨论问题

### ✅ 已决定

| 问题 | 决定 |
|------|------|
| 私募 | 不做 |
| 生态基金来源 | 协议收益 + 天使投资 |
| 治理 | 一起上线 |
| 社区稳定基金 | 保留6% |

### 待讨论

1. [ ] 合约部署的具体参数
2. [ ] 上线时间
3. [ ] CEX选择
4. [ ] 合规方案

---

## 十三、参考设计清单

完整缺失功能见: `docs/VIBE_Design_Checklist.md`

---

*本文档基于专家论证和团队讨论，持续更新*

</details>
