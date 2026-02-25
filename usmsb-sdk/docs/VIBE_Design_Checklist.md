# VIBE 完整设计清单

> 记录所有缺失的、需要设计的、以后要扩展的内容
> 最后更新: 2026-02-25
> 基于最终讨论方案（VIBE_Full_Automation_Design.md）
> 合约完成度: ~95%

---

## 零、智能合约实现状态 (2026-02-25)

### 已完成的合约 - 核心层 (14个)

| 合约 | 文件 | 状态 | 说明 |
|------|------|------|------|
| VIBEToken | VIBEToken.sol | ✅ | 代币合约，含交易税0.8%、销毁50%、分红20% |
| VIBStaking | VIBStaking.sol | ✅ | 质押合约，四等级+多锁仓期+时长系数 |
| VIBVesting | VIBVesting.sol | ✅ | 锁仓归属，支持团队/早期支持者/激励池 |
| VIBIdentity | VIBIdentity.sol | ✅ | 身份认证，KYC验证支持 |
| VIBGovernance | VIBGovernance.sol | ✅ | 三层治理+委托机制 |
| VIBTimelock | VIBTimelock.sol | ✅ | 时间锁合约 |
| VIBDividend | VIBDividend.sol | ✅ | 分红合约 |
| VIBTreasury | VIBTreasury.sol | ✅ | 资金库，多签管理 |
| VIBInflationControl | VIBInflationControl.sol | ✅ | 通胀控制+熔断机制 |
| AgentRegistry | AgentRegistry.sol | ✅ | Agent注册表 |
| AgentWallet | AgentWallet.sol | ✅ | Agent智能钱包 |
| ZKCredential | ZKCredential.sol | ✅ | 零知识证明凭证 |
| AssetVault | AssetVault.sol | ✅ | NFT碎片化 |
| JointOrder | JointOrder.sol | ✅ | 集采订单/反向拍卖 |

### 已完成的合约 - 自动化层 (5个) ✅ 新增

| 合约 | 文件 | 状态 | 说明 |
|------|------|------|------|
| PriceOracle | automation/PriceOracle.sol | ✅ | 多源价格聚合 (Chainlink + TWAP) |
| EmissionController | automation/EmissionController.sol | ✅ | 6.3亿激励池5年释放 |
| CommunityStableFund | automation/CommunityStableFund.sol | ✅ | 价格下跌20%自动回购销毁 |
| LiquidityManager | automation/LiquidityManager.sol | ✅ | LP永久锁定+收益复投 |
| AirdropDistributor | automation/AirdropDistributor.sol | ✅ | 空投分发 (6月100%/7-12月50%) |

### 接口文件

| 接口 | 文件 | 状态 |
|------|------|------|
| IVIBEToken | interfaces/IVIBEToken.sol | ✅ |
| IAgentRegistry | interfaces/IAgentRegistry.sol | ✅ |
| IAgentWallet | interfaces/IAgentWallet.sol | ✅ |

---

## 零点一、未实现功能详细清单 (约5%)

### 1. 争议解决机制 ❌ (白皮书明确要求，优先级: 高)

**白皮书要求:**
```
1. 发起争议：双方各质押 5 VIBE
2. 仲裁员分配：随机 3 名仲裁员
3. 证据提交：24 小时
4. 仲裁投票：48 小时
5. 执行裁决
```

**仲裁员准入条件:**
- 需持有 1,000+ VIBE
- 通过治理考试
- 至少参与 10 次投票且记录良好

**服务者信用保护:**
- 连续 3 次胜诉 → 争议门槛降至 1 VIBE
- 连续 3 次败诉（需求方）→ 争议门槛提高至 20 VIBE

**待创建合约:** `VIBDispute.sol`

**实现位置:** `usmsb-sdk/contracts/src/VIBDispute.sol`

---

### 2. Agent 与 VIBStaking 集成 ⚠️ (部分实现，优先级: 高)

**当前状态:**
`AgentWallet.sol:295-304` 只有注释，未实际调用 VIBStaking

```solidity
function stake(uint256 amount) external onlyAgentOrOwner nonReentrant {
    // 注意：这里简化处理，实际应该调用 VIBStaking 合约
    // vibeToken.safeTransfer(stakingContract, amount);
    stakedAmount += amount;  // 只记录本地变量
}
```

**需要实现:**
1. AgentWallet.stake() 调用 VIBStaking 合约
2. 根据 VIBStaking 等级授予 Agent 不同权限
3. Agent 限额与质押等级挂钩

**实现位置:** `usmsb-sdk/contracts/src/AgentWallet.sol`

---

### 3. 治理投票奖励 ❌ (白皮书提到，优先级: 中)

**白皮书要求:**
| 行为 | 奖励 |
|------|------|
| 对通过提案投赞成票 | 0.01 VIBE/票 |
| 对否决提案投反对票 | 0.005 VIBE/票 |
| 提案发起人（通过后）| 50-500 VIBE |

**实现位置:** `usmsb-sdk/contracts/src/VIBGovernance.sol`

---

### 4. 动态质押 APY ❌ (白皮书提到，优先级: 中)

**白皮书要求:**
```
反死螺旋机制:
- 币价下跌时自动提升 APY
- 需要价格预言机支持
```

**依赖:** Chainlink 价格预言机或 TWAP

**实现位置:** `usmsb-sdk/contracts/src/VIBStaking.sol`

---

### 5. 代理模式/可升级合约 ❌ (设计清单要求，优先级: 中)

**需要实现:**
| 功能 | 说明 |
|------|------|
| 代理模式设计 | UUPS 或 Transparent Proxy |
| 升级权限管理 | 只有治理可以升级 |
| 升级流程 | 提案→投票→时间锁→执行 |

**推荐方案:** OpenZeppelin UUPS 代理模式

**涉及合约:** 所有关键合约

---

### 6. 闪电贷防护 ❌ (白皮书提到，优先级: 低)

**白皮书要求:**
```
- 闪电贷获得的投票权不计入
- 大额投票权变动触发 7 天生效延迟 (已实现)
```

**实现方式:** 检查 block.number，同一区块内的投票权变动不计入

**实现位置:** `usmsb-sdk/contracts/src/VIBGovernance.sol`

---

### 7. Agent-VIBStaking 质押等级权限映射 ❌ (优先级: 低)

**需要实现:**
| 质押等级 | Agent 权限 |
|---------|-----------|
| Bronze (100-999) | 1个Agent, 0%折扣 |
| Silver (1000-4999) | 3个Agent, 5%折扣 |
| Gold (5000-9999) | 10个Agent, 10%折扣, 优先队列 |
| Platinum (10000+) | 50个Agent, 20%折扣, VIP支持 |

**实现位置:** `AgentWallet.sol` + `VIBStaking.sol`

---

## 一、融资与资金相关

### 1.1 早期融资 ✅ 已决定

```
最终方案: 不做公开私募
- 启动资金: 天使投资 (不公开)
- 团队自筹部分资金
- 早期支持者投资
```

### 1.2 生态基金 ✅ 已决定

```
来源:
- 交易手续费 20% → 生态基金
- 服务费收入 → 生态基金

用途:
- 开发者激励 (Grant) 40%
- 生态项目投资 25%
- 市场推广 20%
- 社区运营 10%
- 法律/合规 5%
```

---

## 二、交易与流动性

### 2.1 DEX 相关

| 功能 | 状态 |
|------|------|
| AMM 池部署 (VIBE/ETH, VIBE/USDC) | TODO |
| 流动性挖矿 LP 激励 | TODO |
| 流动性引导池 (LBP) | TODO |
| 交易滑点保护 | TODO |
| 价格预言机 | TODO |

### 2.2 CEX 相关

| 功能 | 状态 |
|------|------|
| 上市计划 | TODO |
| 做市商安排 | TODO |
| 上币费用 | TODO |
| 合规要求 | TODO |

### 2.3 跨链

| 功能 | 状态 |
|------|------|
| 跨链桥 | TODO |
| 多链部署 | TODO |

---

## 三、经济模型完整设计 ✅ 已决定

> **参考文档: VIBE_Full_Automation_Design.md (2026-02-24)**
> **核心原则: 完全去中心化、不需要手动触发、一切由代码决定**

### 3.1 代币分配

```
总量: 10亿 VIBE

✅ 已决定（完全去中心化管理）:
- 团队 8% - VIBVesting (4年锁仓，独立合约 #1)
- 早期支持者 4% - VIBVesting (2年锁仓，独立合约 #2)
- 社区稳定基金 6% - CommunityStableFund (价格下跌自动回购)
- 流动性池 12% - LiquidityManager (LP永久锁定)
- 社区空投 7% - AirdropDistributor (用户自领)
- 激励池 63% - EmissionController (5年线性释放)

激励池内部分配 (63%):
- 质押奖励 45% → VIBStaking
- 生态激励 30% → 生态建设者
- 治理奖励 15% → VIBGovernance
- 储备 10% → 应急

❌ 已取消:
- "预留池"(基础设施池18%/治理演进池10%)
  原因: 相关功能已并入激励池的生态激励(30%)和治理奖励(15%)
```

### 3.2 通胀机制 ✅ 已实现

| 功能 | 状态 | 合约 |
|------|------|------|
| 年通胀上限 2% 硬约束 | ✅ | VIBInflationControl.sol |
| 熔断机制 (月通胀 > 0.5% 暂停) | ✅ | VIBInflationControl.sol |
| 动态释放控制 | ✅ | VIBInflationControl.sol |

### 3.3 通缩机制 ✅ 已实现

| 功能 | 状态 | 合约 |
|------|------|------|
| 交易手续费 0.8% | ✅ | VIBEToken.sol |
| 交易销毁 50% (手续费中) | ✅ | VIBEToken.sol |
| 服务费销毁 20% | TODO | - |
| 惩罚没收 100% | TODO | - |

### 3.4 分红机制 ✅ 已实现

```
来源: 交易手续费 20%
比例: 20% (平台收入)
对象: 质押者 (按质押量分配)
合约: VIBDividend.sol
```

### 3.5 反死螺旋

| 功能 | 状态 |
|------|------|
| 回购池 (社区稳定基金 6%) | ✅ 已实现 |
| 流动性保证金 3% | TODO |
| 动态质押 APY | ❌ 未实现 (见零点一.4) |

---

## 四、治理完整设计 ✅ 已决定

### 4.1 三层治理 ✅ 已实现

```
Layer 1: 资本权重 ✅
- 质押量 × 时长系数
- 单地址 ≤10%

Layer 2: 生产权重 ✅
- 贡献积分 (不可转让)
- 单地址 ≤15%

Layer 3: 社区共识 ✅
- KYC 验证后一人一票
- 占总投票权 10%

合约: VIBGovernance.sol
```

### 4.2 提案系统 ✅ 已实现

| 提案类型 | 门槛 | 通过率 | 时间锁 |
|---------|------|--------|--------|
| 一般提案 | 500 VIBE | >50% | 14天 |
| 参数调整 | 5,000 VIBE | >60% | 30天 |
| 协议升级 | 50,000 VIBE | >75% | 60天 |
| 紧急提案 | - | >90% | 立即 |

### 4.3 委托机制 ✅ 已实现

```
合约: VIBGovernance.sol

已实现:
- 最长委托期限: 90天 ✅
- 单一接受者: ≤5% ✅
- 委托不可转委托 ✅
- 大额变动: 7天延迟 ✅
- 委托过期自动失效 ✅
- 拒绝委托功能 ✅
```

### 4.4 争议解决 ❌ 未实现

| 功能 | 状态 |
|------|------|
| 争议流程 | ❌ 见零点一.1 |
| 仲裁员准入 | ❌ 见零点一.1 |
| 争议门槛 (5 VIBE) | ❌ 见零点一.1 |

### 4.5 投票奖励 ❌ 未实现

见零点一.3

---

## 五、生态与运营

### 5.1 生态基金管理 ✅ 已实现

```
合约: VIBTreasury.sol

阶段1 (早期): 团队主导
- 多签钱包 (3/5) ✅
- 团队决策 ✅
- 透明度报告 TODO

阶段2 (过渡): DAO监督
- 多签 + DAO投票
- 重大支出需DAO批准

阶段3 (成熟): 完全DAO
- DAO完全控制
```

### 5.2 运营预留

| 功能 | 状态 |
|------|------|
| 运营费用接口 | TODO |
| 营销支出接口 | TODO |
| 法律费用接口 | TODO |

---

## 六、AI Agent 与 AgentFi

### 6.1 Agent 支付 ✅ 已实现

| 功能 | 状态 | 合约 |
|------|------|------|
| AgentWallet (钱包) | ✅ | AgentWallet.sol |
| AgentRegistry (注册) | ✅ | AgentRegistry.sol |
| Agent 间转账 | ✅ | AgentWallet.sol |
| 限额控制 | ✅ | AgentWallet.sol |
| 白名单机制 | ✅ | AgentWallet.sol |
| 大额审批 | ✅ | AgentWallet.sol |
| 自动结算 | TODO | - |
| VIBStaking 集成 | ⚠️ | 见零点一.2 |

### 6.2 Agent 金融

| 功能 | 状态 |
|------|------|
| Agent 信贷 | TODO |
| Agent 投资 | TODO |
| Agent 保险 | TODO |
| Agent 期货/期权 | TODO |

### 6.3 算力市场

| 功能 | 状态 |
|------|------|
| 算力定价 | TODO |
| 算力交易 | TODO |
| 算力证明 | TODO |

### 6.4 数据市场

| 功能 | 状态 |
|------|------|
| 数据定价 | TODO |
| 数据交易 | TODO |
| 数据质量验证 | TODO |
| 数据贡献者分成 35% | TODO |

### 6.5 AI 协作

| 功能 | 状态 |
|------|------|
| Agent 间协作协议 | TODO |
| 任务分配机制 | TODO |
| 收益分配机制 (70/20/10) | TODO |
| 争议仲裁 | TODO |

---

## 七、合约扩展性

### 7.1 可升级合约 ❌ 未实现

| 功能 | 状态 |
|------|------|
| 代理模式设计 | ❌ 见零点一.5 |
| 升级权限管理 | ❌ 见零点一.5 |
| 升级流程 | ❌ 见零点一.5 |

### 7.2 模块化设计

```
核心层 (不可变):
- VIBEToken ✅
- VIBStaking ✅
- VIBVesting ✅

扩展层:
- 治理模块 (Governance) ✅
- 分红模块 (Dividend) ✅
- 通胀控制 (InflationControl) ✅
- 销毁模块 (Burn) - 集成在 VIBEToken 中
- 生态基金 (Treasury) ✅

应用层:
- AgentWallet ✅
- AgentRegistry ✅
- ZKCredential ✅
- AssetVault ✅
- JointOrder ✅
- AgentFi TODO
- 算力市场 TODO
- 数据市场 TODO
```

---

## 八、风控与安全

### 8.1 安全机制 ✅ 已实现

| 功能 | 状态 | 合约 |
|------|------|------|
| 暂停机制 | ✅ | 所有合约 |
| 时间锁 | ✅ | VIBTimelock.sol |
| 多签钱包 | ✅ | VIBTreasury.sol |
| 速率限制 | ✅ | VIBInflationControl.sol |
| 重入保护 | ✅ | ReentrancyGuard |

### 8.2 审计

| 功能 | 状态 |
|------|------|
| 代码审计 | TODO |
| 形式化验证 | TODO |
| 持续监控 | TODO |

---

## 九、技术架构

### 9.1 链上/链下分离

| 功能 | 状态 |
|------|------|
| 链上核心合约 | ✅ 17个合约 |
| 链下 AI 评估系统 | TODO |
| 预言机 | TODO |
| IPFS 元数据 | TODO |

### 9.2 前端

| 功能 | 状态 |
|------|------|
| Web 端 | TODO |
| 移动端 | TODO |
| Agent SDK | TODO |

---

## 十、版本规划与路线图

### 10.1 版本规划

| 版本 | 内容 | 状态 |
|------|------|------|
| v1.0 | 核心代币 + 质押 + 锁仓 + 治理 | ✅ 开发完成 |
| v1.1 | 争议解决 + Agent集成 + 代理模式 | TODO |
| v2.0 | AgentFi 基础 | TODO |
| v3.0 | 完整生态 | TODO |

### 10.2 实施路线图

```
Phase 1: 基础设施 ✅
- ✅ 经济模型设计
- ✅ 博弈论证
- ✅ 核心合约开发 (17个合约)
- ⏳ 代币部署 (包含治理)

Phase 2: 质押系统 ✅
- ✅ 质押合约
- ✅ 锁仓合约
- ✅ 销毁机制
- ✅ 通胀控制

Phase 3: 生态 (上线后)
- ⏳ 生态基金启动
- ⏳ 流动性池
- ⏳ CEX上市

Phase 4: AgentFi (未来)
- ⏳ Agent信贷
- ⏳ 算力市场
- ⏳ 数据市场
```

---

## 十一、待讨论问题

### ✅ 已决定

| 问题 | 决定 |
|------|------|
| 私募 | 不做 |
| 生态基金来源 | 协议收益 + 天使投资 |
| 治理 | 一起上线 |
| 社区稳定基金 | 保留 6%，由 CommunityStableFund 合约管理 |
| ~~预留池~~ | ~~18% + 10% 治理阶段决定~~ **已取消** |
| 完全去中心化 | 一切由代码决定，不需要手动触发 |

### ⏳ 待讨论

1. 合约部署的具体参数
2. 上线时间
3. CEX 选择
4. 合规方案
5. 审计公司选择

---

## 状态标记

- [x] ✅ 已实现
- [ ] ❌ 缺失 - 需要创建
- [ ] ⚠️ 部分实现 - 需要修改现有合约
- [ ] ⏳ TODO - 未来设计，预留接口
- [ ] 📋 待讨论 - 需要决策
