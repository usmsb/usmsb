# VIBE 合约开发计划

> 最后更新: 2026-02-24
> 状态: ✅ 开发完成，准备测试

---

## 一、开发顺序

### Phase 1: 核心合约（先做）

| 顺序 | 合约 | 文件名 | 依赖 | 状态 |
|------|------|--------|------|------|
| 1 | PriceOracle | PriceOracle.sol | Chainlink, Uniswap V3 | ✅ 完成 |
| 2 | EmissionController | EmissionController.sol | VIBEToken, PriceOracle | ✅ 完成 |
| 3 | 修改 VIBEToken | VIBEToken.sol | EmissionController | ✅ 完成 |
| 4 | 修改 VIBStaking | VIBStaking.sol | EmissionController | ✅ 完成 |

### Phase 2: 资金管理合约

| 顺序 | 合约 | 文件名 | 依赖 | 状态 |
|------|------|--------|------|------|
| 5 | CommunityStableFund | CommunityStableFund.sol | VIBEToken, PriceOracle | ✅ 完成 |
| 6 | LiquidityManager | LiquidityManager.sol | VIBEToken | ✅ 完成 |

### Phase 3: 分发合约

| 顺序 | 合约 | 文件名 | 依赖 | 状态 |
|------|------|--------|------|------|
| 7 | AirdropDistributor | AirdropDistributor.sol | VIBEToken, CommunityStableFund | ✅ 完成 |
| 8 | 修改 VIBGovernance | VIBGovernance.sol | EmissionController | ✅ 完成 |

---

## 二、合约详细规格

### 1. PriceOracle.sol

```
功能：多源价格聚合
来源：
├── Chainlink VIBE/ETH
├── Uniswap V3 TWAP (1小时)
└── SushiSwap TWAP

输出：
├── getVIBEPrice() - 返回 VIBE/ETH 价格
├── getTWAP(uint256 window) - 返回 TWAP
└── getMedianPrice() - 返回中位数价格
```

### 2. EmissionController.sol

```
功能：激励池释放与分配
总量：6.3亿 VIBE，5年线性释放

分配比例：
├── 质押奖励 45% → VIBStaking
├── 生态激励 30% → EcosystemPool
├── 治理奖励 15% → VIBGovernance
└── 储备 10% → ReservePool

触发机制：
├── epochDistribute() - 7天周期释放
├── emergencyRefill() - 紧急补充
└── 触发者获得奖励
```

### 3. CommunityStableFund.sol

```
功能：护盘回购、流动性注入
资金：6000万 VIBE

触发条件：
├── 价格 < 7日均价 × 80% → 自动回购销毁
├── DEX流动性 < 阈值 → 自动注入流动性
└── 任何人可调用，条件满足才执行
```

### 4. AirdropDistributor.sol

```
功能：空投分发
总量：7000万 VIBE

时间机制：
├── 第1-6月：100% 可领取
├── 第7-12月：50% 可领取（另一半→稳定基金）
└── 12月后：未领取 → 稳定基金

验证：Merkle Tree
```

### 5. LiquidityManager.sol

```
功能：DEX流动性管理
资金：1.2亿 VIBE

功能：
├── 初始添加流动性
├── LP代币永久锁定
├── 收益自动复投
└── 无人可提取
```

---

## 三、修改现有合约

### VIBEToken.sol 修改

```diff
+ address public emissionController;

+ function setEmissionController(address _controller) external onlyOwner {
+     emissionController = _controller;
+ }

+ function mintByController(address to, uint256 amount) external {
+     require(msg.sender == emissionController);
+     _mint(to, amount);
+ }
```

### VIBStaking.sol 修改

```diff
+ address public emissionController;

+ function receiveRewards(uint256 amount) external {
+     require(msg.sender == emissionController);
+     // 添加到奖励池
+ }
```

### VIBGovernance.sol 修改

```diff
+ // 治理奖励机制
+ function claimGovernanceReward() external {
+     // 投票/提案奖励
+ }
```

---

## 四、文件结构

```
contracts/src/
├── core/
│   ├── VIBEToken.sol (修改)
│   ├── VIBStaking.sol (修改)
│   ├── VIBVesting.sol
│   ├── VIBInflationControl.sol
│   └── VIBGovernance.sol (修改)
├── automation/
│   ├── PriceOracle.sol (新建)
│   ├── EmissionController.sol (新建)
│   ├── CommunityStableFund.sol (新建)
│   ├── AirdropDistributor.sol (新建)
│   └── LiquidityManager.sol (新建)
├── agent/
│   ├── AgentRegistry.sol
│   ├── AgentWallet.sol
│   └── ZKCredential.sol
├── defi/
│   ├── AssetVault.sol
│   ├── JointOrder.sol
│   ├── VIBDividend.sol
│   └── VIBTreasury.sol
└── interfaces/
    └── ...
```

---

## 五、下一步

1. [x] 创建 automation 文件夹
2. [x] 编写 PriceOracle.sol
3. [x] 编写 EmissionController.sol
4. [x] 修改 VIBEToken.sol
5. [x] 修改 VIBStaking.sol
6. [x] 编写 CommunityStableFund.sol
7. [x] 编写 LiquidityManager.sol
8. [x] 编写 AirdropDistributor.sol
9. [x] 修改 VIBGovernance.sol
10. [ ] 编写部署脚本
11. [ ] 编写测试
12. [ ] 部署测试网

---

## 六、已完成合约摘要

### 新建合约 (5个)

| 合约 | 功能 | 关键参数 |
|------|------|----------|
| PriceOracle | 多源价格聚合 | Chainlink + Uniswap TWAP + Sushi TWAP, 15%偏差过滤 |
| EmissionController | 6.3亿 VIBE 5年释放 | 质押45%/生态30%/治理15%/储备10%, 7天周期+紧急补充 |
| CommunityStableFund | 护盘回购+流动性注入 | 价格下跌20%触发回购销毁, 流动性低于阈值自动注入 |
| AirdropDistributor | 空投分发 | 6个月100%/7-12个月50%, Merkle验证 |
| LiquidityManager | DEX流动性管理 | 1.2亿VIBE, LP永久锁定, 手续费自动复投 |

### 修改合约 (3个)

| 合约 | 新增功能 |
|------|----------|
| VIBEToken | 添加 emissionController, EmissionControllerUpdated 事件 |
| VIBStaking | 添加 emissionController, receiveRewards() 接收激励池释放 |
| VIBGovernance | 添加治理奖励机制, claimGovernanceReward() 领取奖励 |

---

*✅ 合约开发完成，编译通过，准备进入测试阶段*
