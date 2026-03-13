# VIBE Token Smart Contracts

VIBE 代币核心智能合约，部署在 Base (Ethereum L2) 上。

## 合约概述

### 1. VIBEToken.sol
- 标准 ERC-20 代币，支持 EIP-2612 Permit
- 固定总供应量：10 亿 VIBE
- 硬顶不可增发
- 初始铸造：8% 给部署者，92% 给国库

### 2. VIBStaking.sol
- VIBE 代币质押合约
- APY：3%（可由 owner 调整，范围 1-10%）
- 质押等级：
  - 青铜：100-999 VIBE
  - 白银：1000-4999 VIBE
  - 黄金：5000-9999 VIBE
  - 铂金：10000+ VIBE
- 锁仓期：30天、90天、180天、365天
- 锁仓加成：105%、110%、120%、150%

### 3. VIBVesting.sol
- 多受益人锁仓合约
- 支持线性释放和悬崖期
- 受益人类型：
  - 团队：4 年锁仓，1 年悬崖期
  - 早期支持者：2 年锁仓，6 个月悬崖期
  - 激励池：5 年线性释放
  - 顾问：2 年锁仓
  - 合作伙伴：3 年锁仓

### 4. VIBIdentity.sol
- 灵魂绑定代币 (SBT)，符合 ERC-5192 标准
- 代币不可转移
- 身份类型：
  - AI Agent 身份
  - 人类服务者认证
  - 节点运营商
  - 治理参与者

## 技术规格

- Solidity 版本：^0.8.20
- 使用 OpenZeppelin 合约库
- Gas 优化：启用优化器，200 次运行
- 安全特性：Pausable、ReentrancyGuard、Ownable

## 安装

```bash
cd contracts
npm install
```

## 配置

复制 `.env.example` 为 `.env` 并填写必要信息：

```bash
cp .env.example .env
```

`.env` 文件内容：

```
PRIVATE_KEY=your_private_key_here
BASE_RPC_URL=https://mainnet.base.org
BASE_SEPOLIA_RPC_URL=https://sepolia.base.org
BASESCAN_API_KEY=your_basescan_api_key_here
REPORT_GAS=false
CMC_API_KEY=your_coinmarketcap_api_key_here
TREASURY_ADDRESS=your_treasury_address_here
```

## 编译

```bash
npm run compile
```

## 测试

运行所有测试：

```bash
npm test
```

运行测试并生成覆盖率报告：

```bash
npm run test:coverage
```

生成 Gas 报告：

```bash
REPORT_GAS=true npm test
```

## 部署

### 本地部署

```bash
npm run clean
npx hardhat node
```

在另一个终端：

```bash
npx hardhat run scripts/deploy.js --network localhost
```

### Base 测试网部署

```bash
npm run deploy:base:testnet
```

### Base 主网部署

```bash
npm run deploy:base
```

部署后，合约地址将保存在 `deployments/{network}.json` 文件中。

## 验证合约

部署后验证合约：

```bash
npx hardhat run scripts/verify.js --network base
```

或手动验证：

```bash
npx hardhat verify --network base <CONTRACT_ADDRESS> <CONSTRUCTOR_ARGS>
```

## 合约接口

### VIBEToken

| 函数 | 说明 |
|------|------|
| `mintTreasury()` | 铸造剩余 92% 代币给国库 |
| `setStakingContract(address)` | 设置质押合约地址 |
| `setVestingContract(address)` | 设置锁仓合约地址 |
| `setIdentityContract(address)` | 设置身份合约地址 |
| `pause()` / `unpause()` | 暂停/恢复转账 |

### VIBStaking

| 函数 | 说明 |
|------|------|
| `stake(uint256 amount, uint256 lockPeriod)` | 质押 VIBE |
| `unstake()` | 提取质押和奖励 |
| `claimReward()` | 提取奖励（保持质押） |
| `emergencyWithdraw()` | 紧急提取（放弃奖励） |
| `setAPY(uint256 newAPY)` | 设置 APY（1-10%） |
| `getPendingReward(address)` | 获取待领取奖励 |
| `getUserTier(address)` | 获取用户质押等级 |

### VIBVesting

| 函数 | 说明 |
|------|------|
| `addBeneficiary(...)` | 添加单个受益人 |
| `addTeamMembers(...)` | 批量添加团队成员 |
| `addEarlySupporters(...)` | 批量添加早期支持者 |
| `release()` | 释放代币 |
| `removeBeneficiary(address)` | 移除受益人 |
| `getVestedAmount(address)` | 获取已归属金额 |
| `getReleasableAmount(address)` | 获取可释放金额 |

### VIBIdentity

| 函数 | 说明 |
|------|------|
| `registerAIIdentity(string, string)` | 注册 AI Agent 身份 |
| `registerHumanProvider(string, string)` | 注册人类服务者 |
| `registerNodeOperator(string, string)` | 注册节点运营商 |
| `registerGovernance(string, string)` | 注册治理参与者 |
| `updateMetadata(uint256, string)` | 更新元数据 |
| `verifyIdentity(uint256, bool)` | 验证身份 |
| `revokeIdentity(uint256)` | 撤销身份 |

## 安全注意事项

1. **私钥安全**：切勿将 `.env` 文件提交到版本控制
2. **测试网先行**：先在测试网充分测试，再部署到主网
3. **多重签名**：建议使用 Gnosis Safe 等多重签名钱包作为 owner
4. **权限管理**：谨慎授予合约管理员权限
5. **合约验证**：部署后立即在区块浏览器上验证合约

## Gas 优化

合约已启用以下 Gas 优化：
- 编译器优化：启用，200 次运行
- 打包存储变量
- 使用 uint256 代替较小类型（除非确有必要）
- 批量操作支持
- 事件日志精简

## 监控和日志

部署后应监控以下内容：
- 合约余额和代币分发
- 大额转账和异常活动
- 质押和奖励分配
- 锁仓释放进度

## 支持

如有问题或建议，请联系开发团队或提交 Issue。

## 许可证

MIT License
