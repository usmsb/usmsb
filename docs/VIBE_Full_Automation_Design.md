# VIBE Full Automation Decentralized Ecosystem Design Document

**[English](#vibe-full-automation-decentralized-ecosystem-design-document) | [中文](#vibe-全自动化去中心化生态设计文档)**

---

> Created: 2026-02-24
> Last Updated: 2026-02-24
> Goal: Fully decentralized, code governance, AI governance, no dependency on anyone

---

## 1. Core Principles

```
┌─────────────────────────────────────────────────────────┐
│            Fully Decentralized Ecosystem                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ❌ Does not depend on anyone                           │
│  ❌ No multi-sig approval required                    │
│  ❌ No manual trigger needed                          │
│  ❌ Does not trust anyone                             │
│                                                         │
│  ✅ Everything decided by code                         │
│  ✅ Everything triggered by conditions                 │
│  ✅ Everything transparent on-chain                   │
│  ✅ Everything immutable                              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Token Distribution Scheme (Final Version)

### 2.1 Total & Distribution Ratio

| Category | Ratio | Amount | Management | Trigger Condition |
|----------|-------|--------|------------|-------------------|
| Team | 8% | 80M | VIBVesting (4-year lockup) | Time auto-release |
| Early Supporters | 4% | 40M | VIBVesting (2-year lockup) | Time auto-release |
| Community Stable Fund | 6% | 60M | CommunityStableFund | Auto-buyback on price drop |
| Liquidity Pool | 12% | 120M | LiquidityManager | Time-triggered market making |
| Community Airdrop | 7% | 70M | AirdropDistributor | User self-claim |
| Incentive Pool | 63% | 630M | EmissionController | Cycle auto-release |

### 2.2 Incentive Pool Internal Distribution (63%)

| Sub-pool | % of Pool | Amount | Who Can Get | Trigger |
|----------|-----------|--------|-------------|---------|
| Staking Rewards | 45% | 283.5M | Stakers | Stake VIBE |
| Ecosystem Incentive | 30% | 189M | Developers/Builders | DApp usage/code contribution |
| Governance Rewards | 15% | 94.5M | Governance Participants | Voting/Proposals |
| Reserve | 10% | 63M | Emergency | Extreme situations |

### 2.3 Core Principle: No "Future Talent" Concept

```
┌─────────────────────────────────────────────────────────┐
│         Fully Decentralized Reward Mechanism            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ❌ No "future talent" concept                          │
│  ❌ No manual approval process                         │
│  ❌ No voting to decide who is talent                 │
│                                                         │
│  ✅ Anyone can participate                             │
│  ✅ Contributions automatically identified             │
│  ✅ Rewards automatically distributed                  │
│  ✅ Fully code-driven                                 │
│                                                         │
│  Initial team/supporters: Reward for "past" contribution (one-time lockup) │
│  Incentive pool participants: Reward for "present/future" contribution (continuous) │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 2.4 Distribution Model

**Adopt "one wallet per person" model, not "one total wallet per category"**

- Team members: Individual wallet per person + individual lockup
- Early supporters: Individual wallet per person + individual lockup
- Other pools: Managed by dedicated contracts

---

## 3. Contract Architecture

### 3.1 Completed Contracts (Deployed on Testnet)

| Contract | Address | Status |
|----------|---------|--------|
| VIBEToken | 0x895BeA0E70F61C093E7Ef05b45Fe744ef45c2600 | ✅ |
| VIBInflationControl | 0x82aA3F07B153DfFeCfb6464d0726c53dc2626464 | ✅ |
| VIBStaking | 0xE6b7494bceAd5B092e8F870035aeD7f44F0Fc868 | ✅ |
| VIBVesting | 0x4B898eBEA09b771e4EfD1Ea0986E2bF1f7734ACE | ✅ |
| VIBIdentity | 0xFe1c819d193796B731A13da51a1D55E43C6521e3 | ✅ |
| VIBGovernance | 0x732ae212c8961ae773d68Da3Ddf9F29b788992b1 | ✅ |
| VIBTimelock | 0x8a9dc76bE021b6e36A43acB0088fcBe428FAdE3d | ✅ |
| VIBDividend | 0x421844eC1a51d1246f7A740762998f308AA653db | ✅ |
| VIBTreasury | 0x664C9E36C9328E9530407e0B44281cf9B1F14A5a | ✅ |
| AgentRegistry | 0x2fc57E56e06A5cCC8c17fdE84eA768b76B51c644 | ✅ |
| AgentWallet | 0x99AF837f7A154b244e3E92BaC962a0064AA1F053 | ✅ |
| ZKCredential | 0x84cCAF1C87a88eB90f360112B2E87b49Ab216012 | ✅ |
| AssetVault | 0x0D7a7e8353984330cB566E8Bc8951ed1728c236A | ✅ |
| JointOrder | 0x578Ad702F3df5F5863CD7172FEa65cca4D0E44cD | ✅ |

### 3.2 New Automation Contracts Needed (5)

| Contract | Function | Trigger Mechanism |
|----------|----------|-------------------|
| CommunityStableFund | Market support buyback, emergency liquidity | Price oracle trigger |
| LiquidityManager | DEX liquidity management, LP locking | Time trigger |
| AirdropDistributor | Airdrop distribution | User claim |
| EmissionController | Incentive release control | Time cycle trigger |
| PriceOracle | Multi-source price aggregation | Real-time query |

---

## 4. Full Automation Design

### 4.1 CommunityStableFund (Community Stable Fund 6%)

```
Function:
├── Market support buyback (auto-buy and burn on price drop)
├── Emergency liquidity injection (auto-inject when DEX liquidity insufficient)
└── Parameters determined by oracle, no human intervention

Trigger Conditions:
├── Price 20% below 7-day average → Auto buyback and burn
├── DEX liquidity below threshold → Auto inject liquidity
└── Anyone can call, but only executes when conditions met
```

### 4.2 EmissionController (Incentive Pool 63%)

```
Function:
├── Control incentive token release speed (5-year linear release)
├── Auto-distribute to reward pools
└── Decay mechanism (decrease each cycle)

Distribution Ratio:
├── Staking reward pool 45%
├── Ecosystem incentive pool 30%
├── Governance reward pool 15%
└── Reserve pool 10%

Trigger Mechanism (Hybrid):
├── Normal: Fixed 7-day cycle release
├── Emergency: Anyone can trigger emergency supplement when pool balance below threshold
└── Trigger gets Gas subsidy + time-accrued reward
```

### 4.3 AirdropDistributor (Airdrop 7%)

```
Function:
├── Merkle tree verification (Gas efficient)
├── User self-claim
├── Two-tier time mechanism (incentivize early participation)
└── Unclaimed tokens auto-transfer to Community Stable Fund

Time Mechanism:
├── Months 1-6: 100% claimable (normal period)
├── Months 7-12: 50% claimable (delayed period, other half auto-transfers to stable fund)
└── After 12 months: Cannot claim, remaining all transfers to stable fund

Trigger Conditions:
├── User actively claims
└── After 12 months, anyone can trigger recovery
```

### 4.4 LiquidityManager (Liquidity 12%)

```
Function:
├── Auto-add liquidity to DEX
├── LP tokens permanently locked
├── Auto-compound returns
└── No one can withdraw LP

Trigger Conditions:
├── Auto-execute initial add after deployment
├── Auto-compound returns periodically
└── Anyone can trigger
```

---

## 5. Trigger Mechanism Design

| Scenario | Traditional (Human) | Automation (Code) |
|----------|---------------------|-------------------|
| Market support buyback | ❌ Team decides when to buy | ✅ Auto-trigger on X% price drop |
| Token release | ❌ Admin clicks to distribute | ✅ Auto-release at set time |
| Emergency pause | ❌ Multi-sig vote | ✅ Auto-circuit break on condition |
| Parameter adjustment | ❌ Manual proposal vote | ✅ Auto-adjust by preset rules |
| Airdrop distribution | ❌ Manual transfer | ✅ User self-claim |

---

## 6. Technical Solution Decisions (Confirmed)

### 6.1 Oracle Selection ✅ Confirmed: Multi-source aggregation + TWAP fallback

```
Solution: Take median price from multiple sources
Sources:
├── Chainlink price feed
├── Uniswap V3 TWAP (1-hour window)
└── SushiSwap TWAP

Logic:
├── Take median of three sources
├── Ignore any single source deviation >15%
└── If all sources have large deviation, use historical average

Pros:
✅ Highest security, difficult to manipulate
✅ Fully decentralized
✅ Single source failure doesn't affect system
```

### 6.2 Trigger Rewards ✅ Confirmed: Gas subsidy + time-accrued reward

```
Reward Formula:
Total reward = Base reward + Gas subsidy + Time-accrued reward

Parameters:
├── Base reward: 0.0005 ETH
├── Gas subsidy: Actual Gas cost × 120%
├── Time-accrued: 0.0001 ETH per hour
└── Max accrual: 24 hours

Logic:
├── Longer time since last trigger, higher reward
├── Ensure Gas cost always covered
└── Incentivize timely triggering
```

### 6.3 Parameter Adjustability ✅ Confirmed: Layered design

```
Layer 1: Permanently fixed (cannot change)
├── Total token supply (1 billion)
├── Inflation cap (2%/year)
├── Circuit break threshold (0.5%/month)
└── Distribution ratio (8%-4%-6%-12%-7%-63%)

Layer 2: Governance adjustable (with range limits)
├── Buyback trigger threshold (range: 15%-30%)
├── Incentive release rate (range: ±20%)
└── Trigger reward amount (range: ±50%)
└── Requires: Governance vote >60% + 14-day timelock

Layer 3: Auto-adjust (by preset rules)
├── Gas subsidy (auto-adjust with Gas price)
├── Time-accrued reward (auto-calculate)
└── Release decay rate (auto-decrease per cycle)
```

### 6.4 Contract Upgrade ✅ Confirmed: Layered upgrade strategy

```
Non-upgradable contracts (Core layer):
├── VIBEToken (Token body)
├── VIBVesting (Lockup rules)
└── VIBInflationControl (Inflation control)

Upgradable contracts (Application layer) - UUPS proxy:
├── CommunityStableFund
├── LiquidityManager
├── EmissionController
└── AirdropDistributor

Upgrade conditions:
├── Governance vote >75% support
├── 30-day timelock
└── Anyone can execute (after conditions met)
```

---

## 7. Discussion Records

### 2026-02-24 Discussion Points

1. **Testnet simulation version**
   - User asked if simulation version needs deployment
   - Lockup test can be accelerated by shortening time period (4 years → 4 hours)
   - Decided to deploy simulation version

2. **Token distribution method**
   - Discussed "one total wallet per category" vs "one wallet per person"
   - Decided: Team and investors use individual wallet + lockup
   - Other pools use dedicated contracts

3. **Contract vs wallet**
   - User proposed: Community Stable Fund should go to contracts, not wallets
   - Decided: All fund pools managed by contracts

4. **Fully decentralized goal**
   - User clarified: No dependency on anyone, fully code governance, AI governance
   - Not afraid of high Gas fees or complexity
   - All human intervention to be removed

5. **Technical solution decisions**
   - Oracle: Multi-source aggregation + TWAP fallback (take median from Chainlink, Uniswap, Sushi)
   - Trigger rewards: Gas subsidy + time-accrued reward
   - Parameter adjustment: Three-layer design (fixed/governance/auto)
   - Contract upgrade: Core immutable + Application upgradable

6. **Future talent pool discussion (cancelled)**
   - Question: Where does revenue for new team members after mainnet launch come from?
   - Found conflict: If fully decentralized, there shouldn't be "approve talent" concept
   - Conclusion: Cancel "future talent pool", contributors get rewards from incentive pool automatically
   - Principle: No "future talent" concept, anyone can earn rewards through contribution

7. **Time parameter final decisions**
   - Airdrop period: Two-tier mechanism (first 6 months 100%, 7-12 months 50%, after 12 months expire)
   - Unclaimed airdrop: Transfer to Community Stable Fund
   - Incentive release: Hybrid mode (fixed 7-day cycle + emergency supplement mechanism)
   - Goal: Incentivize early participation while ensuring system stability

---

## 8. Contract Development Checklist

### 8.1 Existing Contracts to Modify

| Contract | Modification | Reason |
|---------|--------------|--------|
| VIBEToken | Add integration with EmissionController | Incentive release needs to call mint |
| VIBStaking | Add integration with EmissionController | Receive staking rewards |
| VIBGovernance | Add governance reward mechanism | Voting/proposals automatically get rewards |

### 8.2 New Contracts Needed

| # | Contract | Function | Priority |
|---|----------|----------|----------|
| 1 | PriceOracle | Multi-source price aggregation (Chainlink+TWAP) | High |
| 2 | EmissionController | Incentive pool release and distribution | High |
| 3 | CommunityStableFund | Market support buyback, liquidity injection | High |
| 4 | AirdropDistributor | Airdrop distribution (Merkle) | Medium |
| 5 | LiquidityManager | DEX liquidity management | Medium |

---

## 9. Next Steps

### Completed ✅
1. [x] Oracle selection analysis → Multi-source aggregation + TWAP
2. [x] Trigger reward mechanism design → Gas subsidy + time-accrued
3. [x] Parameter adjustability design → Three-layer
4. [x] Contract upgrade design → Core immutable + Application upgradable
5. [x] Token distribution confirmed → Cancel future talent pool

### To Do
6. [ ] Write 5 new contract codes
7. [ ] Modify 3 existing contracts
8. [ ] Deploy simulation test version (accelerated time period)
9. [ ] Complete testing
10. [ ] Mainnet deployment

---

*Document continuously updated...*

<details>
<summary><h2>中文翻译</h2></summary>

# VIBE 全自动化去中心化生态设计文档

> 创建时间: 2026-02-24
> 最后更新: 2026-02-24
> 目标: 完全去中心化、代码自治、AI 自治、不依赖任何人

---

## 一、核心原则

```
┌─────────────────────────────────────────────────────────┐
│                    完全去中心化生态                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ❌ 不依赖任何人                                         │
│  ❌ 不需要多签审批                                       │
│  ❌ 不需要手动触发                                       │
│  ❌ 不相信任何人                                         │
│                                                         │
│  ✅ 一切由代码决定                                       │
│  ✅ 一切由条件触发                                       │
│  ✅ 一切链上透明                                         │
│  ✅ 一切不可篡改                                         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 二、代币分配方案（最终版）

### 2.1 总量与分配比例

| 类别 | 比例 | 数量 | 管理方式 | 触发条件 |
|------|------|------|---------|---------|
| 团队 | 8% | 8000万 | VIBVesting（4年锁仓） | 时间自动释放 |
| 早期支持者 | 4% | 4000万 | VIBVesting（2年锁仓） | 时间自动释放 |
| 社区稳定基金 | 6% | 6000万 | CommunityStableFund | 价格下跌自动回购 |
| 流动性池 | 12% | 1.2亿 | LiquidityManager | 时间触发自动做市 |
| 社区空投 | 7% | 7000万 | AirdropDistributor | 用户自领 |
| 激励池 | 63% | 6.3亿 | EmissionController | 周期自动释放 |

### 2.2 激励池内部分配（63%）

| 子池 | 占激励池比例 | 数量 | 谁能获得 | 触发条件 |
|------|-------------|------|---------|---------|
| 质押奖励 | 45% | 2.835亿 | 质押者 | 质押 VIBE |
| 生态激励 | 30% | 1.89亿 | 开发者/建设者 | DApp 被使用/代码贡献 |
| 治理奖励 | 15% | 0.945亿 | 治理参与者 | 投票/提案 |
| 储备 | 10% | 0.63亿 | 应急 | 极端情况 |

### 2.3 核心原则：没有"未来人才"概念

```
┌─────────────────────────────────────────────────────────┐
│              完全去中心化奖励机制                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ❌ 没有"未来人才"概念                                   │
│  ❌ 没有人工批准流程                                     │
│  ❌ 没有投票决定谁是人才                                 │
│                                                         │
│  ✅ 任何人都可以参与                                     │
│  ✅ 贡献自动被识别                                       │
│  ✅ 奖励自动发放                                         │
│  ✅ 完全代码驱动                                         │
│                                                         │
│  初始团队/支持者：对"过去"贡献的回报（一次性锁仓）        │
│  激励池参与者：对"现在/未来"贡献的奖励（持续发放）        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 2.4 分配模式

**采用"每人独立钱包"模式，非"每类一个总钱包"**

- 团队成员：每人独立钱包 + 独立锁仓
- 早期支持者：每人独立钱包 + 独立锁仓
- 其他池：专用合约管理

---

## 三、合约架构

### 3.1 已完成合约（测试网已部署）

| 合约 | 地址 | 状态 |
|------|------|------|
| VIBEToken | 0x895BeA0E70F61C093E7Ef05b45Fe744ef45c2600 | ✅ |
| VIBInflationControl | 0x82aA3F07B153DfFeCfb6464d0726c53dc2626464 | ✅ |
| VIBStaking | 0xE6b7494bceAd5B092e8F870035aeD7f44F0Fc868 | ✅ |
| VIBVesting | 0x4B898eBEA09b771e4EfD1Ea0986E2bF1f7734ACE | ✅ |
| VIBIdentity | 0xFe1c819d193796B731A13da51a1D55E43C6521e3 | ✅ |
| VIBGovernance | 0x732ae212c8961ae773d68Da3Ddf9F29b788992b1 | ✅ |
| VIBTimelock | 0x8a9dc76bE021b6e36A43acB0088fcBe428FAdE3d | ✅ |
| VIBDividend | 0x421844eC1a51d1246f7A740762998f308AA653db | ✅ |
| VIBTreasury | 0x664C9E36C9328E9530407e0B44281cf9B1F14A5a | ✅ |
| AgentRegistry | 0x2fc57E56e06A5cCC8c17fdE84eA768b76B51c644 | ✅ |
| AgentWallet | 0x99AF837f7A154b244e3E92BaC962a0064AA1F053 | ✅ |
| ZKCredential | 0x84cCAF1C87a88eB90f360112B2E87b49Ab216012 | ✅ |
| AssetVault | 0x0D7a7e8353984330cB566E8Bc8951ed1728c236A | ✅ |
| JointOrder | 0x578Ad702F3df5F5863CD7172FEa65cca4D0E44cD | ✅ |

### 3.2 需要新增的自动化合约（5个）

| 合约 | 功能 | 触发机制 |
|------|------|---------|
| CommunityStableFund | 护盘回购、紧急流动性 | 价格预言机触发 |
| LiquidityManager | DEX流动性管理、LP锁定 | 时间触发 |
| AirdropDistributor | 空投分发 | 用户 claim |
| EmissionController | 激励释放控制 | 时间周期触发 |
| PriceOracle | 多源价格聚合 | 实时查询 |

---

## 四、全自动化设计

### 4.1 CommunityStableFund（社区稳定基金 6%）

```solidity
功能：
├── 护盘回购（价格下跌时自动买入并销毁）
├── 紧急流动性注入（DEX流动性不足时自动注入）
└── 参数由预言机决定，无人为干预

触发条件：
├── 价格比7日均价低20% → 自动回购销毁
├── DEX流动性低于阈值 → 自动注入流动性
└── 任何人可调用，但只有条件满足才执行
```

### 4.2 EmissionController（激励池 63%）

```solidity
功能：
├── 控制激励代币释放速度（5年线性释放）
├── 自动分配到各奖励池
└── 衰减机制（每周期递减）

分配比例：
├── 质押奖励池 45%
├── 生态激励池 30%
├── 治理奖励池 15%
└── 储备池 10%

触发机制（混合模式）：
├── 正常：每7天固定周期释放
├── 紧急：池子余额低于阈值时，任何人可触发紧急补充
└── 触发者获得 Gas 补贴 + 时间累积奖励
```

### 4.3 AirdropDistributor（空投 7%）

```solidity
功能：
├── Merkle树验证（Gas高效）
├── 用户自己 claim
├── 二阶梯时间机制（激励早参与）
└── 未领取代币自动转入社区稳定基金

时间机制：
├── 第1-6月：100% 可领取（正常期）
├── 第7-12月：50% 可领取（延迟期，另一半自动转入稳定基金）
└── 12月后：无法领取，剩余全部转入稳定基金

触发条件：
├── 用户主动 claim
└── 12月后任何人可触发回收
```

### 4.4 LiquidityManager（流动性 12%）

```solidity
功能：
├── 自动添加流动性到DEX
├── LP代币永久锁定
├── 收益自动复投
└── 无人可提取LP

触发条件：
├── 部署后自动执行初始添加
├── 定期自动复投收益
└── 任何人可触发
```

---

## 五、触发机制设计

| 场景 | 传统方案（人治） | 自动化方案（代码治） |
|------|-----------------|---------------------|
| 护盘回购 | ❌ 团队决定何时买 | ✅ 价格下跌 X% 自动触发 |
| 释放代币 | ❌ 管理员点击发放 | ✅ 时间到自动释放 |
| 紧急暂停 | ❌ 多签投票决定 | ✅ 条件触发自动熔断 |
| 参数调整 | ❌ 人工提案投票 | ✅ 按预设规则自动调整 |
| 空投分发 | ❌ 手动转账 | ✅ 用户自己 claim |

---

## 六、技术方案决策（已确定）

### 6.1 预言机选择 ✅ 已决定：多源聚合 + TWAP 备用

```solidity
方案：取多个来源的中位数价格
来源：
├── Chainlink 价格源
├── Uniswap V3 TWAP（1小时窗口）
└── SushiSwap TWAP

逻辑：
├── 取三个来源的中位数
├── 任何单一来源偏差 >15% 则忽略
└── 如果所有来源偏差都大，使用历史均价

优点：
✅ 最高安全性，难以操控
✅ 完全去中心化
✅ 单一来源失效不影响系统
```

### 6.2 触发奖励 ✅ 已决定：Gas 补贴 + 时间累积奖励

```solidity
奖励公式：
总奖励 = 基础奖励 + Gas补贴 + 时间累积奖励

参数：
├── 基础奖励：0.0005 ETH
├── Gas 补贴：实际 Gas 成本 × 120%
├── 时间累积：每小时 0.0001 ETH
└── 最大累积：24 小时

逻辑：
├── 越久未触发，奖励越高
├── 确保 Gas 成本始终被覆盖
└── 激励及时触发
```

### 6.3 参数可调整性 ✅ 已决定：分层设计

```
第一层：永久固定（不可更改）
├── 代币总量 (10亿)
├── 通胀上限 (2%/年)
├── 熔断阈值 (0.5%/月)
└── 分配比例 (8%-4%-6%-12%-7%-63%)

第二层：可治理调整（有范围限制）
├── 回购触发阈值（范围：15%-30%）
├── 激励释放速率（范围：±20%）
└── 触发奖励金额（范围：±50%）
└── 需要：治理投票 >60% + 时间锁 14 天

第三层：自动调整（按预设规则）
├── Gas 补贴（随 Gas 价格自动调整）
├── 时间累积奖励（自动计算）
└── 释放衰减率（按周期自动递减）
```

### 6.4 合约升级 ✅ 已决定：分层升级策略

```
不可升级合约（核心层）：
├── VIBEToken（代币本体）
├── VIBVesting（锁仓规则）
└── VIBInflationControl（通胀控制）

可升级合约（应用层）- UUPS 代理：
├── CommunityStableFund
├── LiquidityManager
├── EmissionController
└── AirdropDistributor

升级条件：
├── 治理投票 >75% 支持
├── 时间锁 30 天
└── 任何人可执行（条件满足后）
```

---

## 七、讨论记录

### 2026-02-24 讨论要点

1. **测试网仿真版本**
   - 用户询问是否需要部署仿真版本
   - 锁仓测试可以通过缩短时间周期加速（4年→4小时）
   - 确定要部署仿真版本

2. **代币分配方式**
   - 讨论了"每类一个总钱包" vs "每人独立钱包"
   - 决定：团队和投资者使用每人独立钱包+锁仓
   - 其他池使用专用合约

3. **合约化vs钱包化**
   - 用户提出：社区稳定基金等应该进入合约而非钱包
   - 决定：所有资金池都使用合约管理

4. **完全去中心化目标**
   - 用户明确：不依赖任何人、完全代码自治、AI自治
   - 不怕Gas费高、不怕复杂
   - 所有人为干预都要去掉

5. **技术方案决策**
   - 预言机：多源聚合 + TWAP 备用（取 Chainlink、Uniswap、Sushi 中位数）
   - 触发奖励：Gas 补贴 + 时间累积奖励
   - 参数调整：三层设计（固定/治理/自动）
   - 合约升级：核心不可升级 + 应用层 UUPS

6. **未来人才池讨论（已取消）**
   - 问题：主网上线后新加入的团队成员收益从哪里出？
   - 发现矛盾：如果完全去中心化，就不应该有"批准人才"的概念
   - 结论：删除"未来人才池"，贡献者从激励池自动获得奖励
   - 原则：没有"未来人才"概念，任何人都可以通过贡献获得奖励

7. **时间参数最终决策**
   - 空投期：二阶梯机制（前6月100%，7-12月50%，12月后过期）
   - 未领取空投：转入社区稳定基金
   - 激励释放：混合模式（固定7天周期 + 紧急补充机制）
   - 目标：激励早参与，同时保证系统稳定

---

## 八、合约开发清单

### 8.1 需要修改的现有合约

| 合约 | 修改内容 | 原因 |
|------|---------|------|
| VIBEToken | 添加与 EmissionController 的集成 | 激励释放需要调用 mint |
| VIBStaking | 添加与 EmissionController 的集成 | 接收质押奖励 |
| VIBGovernance | 添加治理奖励机制 | 投票/提案自动获得奖励 |

### 8.2 需要新增的合约

| # | 合约 | 功能 | 优先级 |
|---|------|------|--------|
| 1 | PriceOracle | 多源价格聚合（Chainlink+TWAP） | 高 |
| 2 | EmissionController | 激励池释放与分配 | 高 |
| 3 | CommunityStableFund | 护盘回购、流动性注入 | 高 |
| 4 | AirdropDistributor | 空投分发（Merkle） | 中 |
| 5 | LiquidityManager | DEX流动性管理 | 中 |

---

## 九、下一步行动

### 已完成 ✅
1. [x] 预言机选择分析 → 多源聚合 + TWAP
2. [x] 触发奖励机制设计 → Gas 补贴 + 时间累积
3. [x] 参数可调整性设计 → 三层分层
4. [x] 合约升级方案设计 → 核心不可变 + 应用可升级
5. [x] 代币分配方案确定 → 取消未来人才池

### 待完成
6. [ ] 编写 5 个新合约代码
7. [ ] 修改 3 个现有合约
8. [ ] 部署仿真测试版本（加速时间周期）
9. [ ] 完整测试
10. [ ] 主网部署

---

*文档持续更新中...*

</details>
