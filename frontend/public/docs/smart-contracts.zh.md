# USMSB 智能合约文档

> 完整的智能合约接口与使用说明

---

## 1. 合约概述

USMSB 平台包含以下核心智能合约：

| 合约 | 地址 | 功能 |
|------|------|------|
| VIBEToken | - | 核心代币 |
| VIBStaking | - | 质押系统 |
| VIBGovernance | - | 治理系统 |
| AgentRegistry | - | Agent注册 |
| ZKCredential | - | 零知识凭证 |
| AssetVault | - | 资产保险库 |
| VIBTreasury | - | 国库管理 |

---

## 2. VIBEToken

### 2.1 基础信息

- **代币名称**: VIBE
- **代币标准**: ERC-20 / ERC-2612
- **总供应量**: 1,000,000,000 VIB

### 2.2 常量

```solidity
// 核心参数
uint256 public constant TOTAL_SUPPLY = 1_000_000_000 * 10**18;
uint256 public constant TRANSACTION_TAX_RATE = 8;    // 0.8%
uint256 public constant BURN_RATIO = 5000;           // 50%
uint256 public constant DIVIDEND_RATIO = 2000;       // 20%
uint256 public constant ECOSYSTEM_FUND_RATIO = 2000; // 20%
uint256 public constant PROTOCOL_FUND_RATIO = 1000;  // 10%
```

### 2.3 核心函数

```solidity
// 转账 (带手续费)
function transfer(address to, uint256 amount) public override returns (bool);

// 授权转账
function transferFrom(address from, address to, uint256 amount) public override returns (bool);

// 授权
function approve(address spender, uint256 amount) public override returns (bool);

// 委托投票权
function delegate(address delegatee) public;

// 签名授权 (EIP-2612)
function permit(address owner, address spender, uint256 value, uint256 deadline, uint8 v, bytes32 r, bytes32 s) public;
```

### 2.4 交易费用

每次转账时收取 **0.8%** 手续费：

```
┌─────────────────────────────────────────┐
│            手续费分配                     │
├─────────────────────────────────────────┤
│                                         │
│  销毁         50%  →  减少流通量         │
│                                         │
│  分红池       20%  →  质押者分红         │
│                                         │
│  生态基金     20%  →  生态激励            │
│                                         │
│  协议运营     10%  →  开发和维护         │
│                                         │
└─────────────────────────────────────────┘
```

### 2.5 权限管理

```solidity
// 设置质押合约
function setStakingContract(address _stakingContract) external onlyOwner;

// 设置分红合约
function setDividendContract(address _dividendContract) external onlyOwner;

// 暂停转账
function pause() external onlyOwner;

// 恢复转账
function unpause() external onlyOwner;
```

---

## 3. VIBStaking

### 3.1 概述

VIBStaking 合约管理节点的质押和奖励分发。

### 3.2 数据结构

```solidity
enum NodeType { FullNode, ValidatorNode, SuperNode }

struct StakeInfo {
    uint256 amount;
    uint256 startTime;
    uint256 rewards;
    NodeType nodeType;
    bool active;
}

struct NodeConfig {
    uint256 minStake;
    uint256 rewardRate;  // 年化奖励 (百分比)
    uint256 lockPeriod;   // 锁定期 (秒)
}
```

### 3.3 节点配置

| 节点等级 | 最低质押 | 年化奖励(APY) | 锁定期 |
|----------|----------|---------------|--------|
| 基础节点 | 100 VIB | 3% - 10% | 90天/180天/365天 |
| Tier 1 | 1,000 VIB | 3% - 10% | 90天/180天/365天 |
| Tier 2 | 5,000 VIB | 3% - 10% | 90天/180天/365天 |
| Tier 3 | 10,000 VIB | 3% - 10% | 90天/180天/365天 |

> 注: APY根据质押时长和锁定期限动态调整，最高可达10%。基础APY为3%，长期质押可获得额外奖励。

### 3.4 核心函数

```solidity
// 质押
function stake(uint256 amount, NodeType nodeType) external;

// 解除质押 (需等待锁定期)
function unstake(uint256 stakeId) external;

// 领取奖励
function claimRewards() external;

// 委托质押
function delegateStake(address to, uint256 amount) external;

// 取消委托
function undelegateStake(uint256 delegateId) external;

// 查看质押信息
function getStakeInfo(address staker) external view returns (StakeInfo[]);

// 计算预估奖励
function calculatePendingReward(address staker, uint256 stakeId) external view returns (uint256);
```

---

## 4. VIBGovernance

### 4.1 概述

去中心化治理合约，允许代币持有者提出提案并投票。

### 4.2 参数

```solidity
uint256 public votingDelay = 1 days;      // 提案后延迟开始投票
uint256 public votingPeriod = 7 days;    // 投票持续时间
uint256 public proposalThreshold = 100e18;  // 提案门槛 (100 VIB)
uint256 public quorumThreshold = 500;     // 法定人数 (5%)

// 治理权重配置
uint256 public constant CAPITAL_WEIGHT_MAX = 10;   // 资本权重上限 10%
uint256 public constant PRODUCTION_WEIGHT_MAX = 15; // 生产权重上限 15%
uint256 public constant COMMUNITY_WEIGHT_RATIO = 10; // 社区共识权重 10%
```

### 4.3 核心函数

```solidity
// 发起提案
function propose(
    address[] memory targets,
    uint256[] memory values,
    bytes[] memory calldatas,
    string memory description
) public returns (uint256);

// 投票
function castVote(uint256 proposalId, uint8 support) public;

// 投票并附议
function castVoteWithReason(
    uint256 proposalId,
    uint8 support,
    string memory reason
) public;

// 执行提案
function execute(
    address[] memory targets,
    uint256[] memory values,
    bytes[] memory calldatas,
    bytes32 descriptionHash
) public payable returns (uint256);

// 取消提案
function cancel(uint256 proposalId) public;
```

### 4.4 投票选项

```solidity
uint8 public constant AGAINST = 0;
uint8 public constant FOR = 1;
uint8 public constant ABSTAIN = 2;
```

---

## 5. AgentRegistry

### 5.1 概述

Agent 注册与管理合约。

### 5.2 数据结构

```solidity
struct AgentInfo {
    address owner;
    string metadata;
    uint256 reputation;
    bool verified;
    uint256 registeredAt;
    uint256 lastActive;
    AgentStatus status;
}

enum AgentStatus { None, Registered, Active, Paused, Slashed }
```

### 5.3 核心函数

```solidity
// 注册 Agent
function registerAgent(
    bytes32 agentId,
    string memory metadata,
    uint256 registrationFee
) external payable;

// 更新 Agent 信息
function updateAgentMetadata(bytes32 agentId, string memory metadata) external;

// 更新 Agent 状态
function updateAgentStatus(bytes32 agentId, AgentStatus status) external;

// 增加声誉
function addReputation(bytes32 agentId, uint256 amount) external;

// 减少声誉
function removeReputation(bytes32 agentId, uint256 amount) external;

// 验证 Agent
function verifyAgent(bytes32 agentId) external onlyOwner;

// 暂停 Agent
function pauseAgent(bytes32 agentId) external;

// 获取 Agent 信息
function getAgentInfo(bytes32 agentId) external view returns (AgentInfo memory);
```

---

## 6. ZKCredential

### 6.1 概述

零知识凭证合约，支持隐私保护的身份验证。

### 6.2 核心函数

```solidity
// 发行凭证
function issueCredential(
    address recipient,
    bytes32 credentialHash,
    uint256 expirationTime
) external returns (uint256);

// 验证凭证 (零知识)
function verifyCredential(
    address recipient,
    bytes32 credentialHash,
    uint256[2] memory proof_a,
    uint256[2][2] memory proof_b,
    uint256[2] memory proof_c
) external view returns (bool);

// 撤销凭证
function revokeCredential(uint256 credentialId) external;

// 批量验证
function batchVerify(
    address[] memory recipients,
    bytes32[] memory credentialHashes,
    uint256[2][] memory proof_as,
    uint256[2][2][] memory proof_bs,
    uint256[2][] memory proof_cs
) external view returns (bool[] memory);
```

---

## 7. AssetVault

### 7.1 概述

资产保险库合约，用于托管创意资产交易资金。

### 7.2 核心函数

```solidity
// 存入资金
function deposit(bytes32 agentId) external payable;

// 释放资金 (需多方签名)
function release(
    bytes32 agentId,
    address recipient,
    uint256 amount,
    bytes[] memory signatures
) external;

// 争议解决
function raiseDispute(bytes32 agentId, string memory reason) external;

// 紧急撤回
function emergencyWithdraw(bytes32 agentId) external onlyOwner;

// 获取余额
function getBalance(bytes32 agentId) external view returns (uint256);
```

---

## 8. VIBTreasury

### 8.1 概述

国库合约，管理平台收入和支出。

### 8.2 核心函数

```solidity
// 存入收入
function deposit() external payable;

// 批准支出
function approvePayment(
    address recipient,
    uint256 amount,
    string memory description
) external onlyOwner;

// 执行支出
function executePayment(uint256 paymentId) external onlyOwner;

// 查看余额
function getBalance() external view returns (uint256);

// 查看待处理支付
function getPendingPayments() external view returns (Payment[] memory);
```

---

## 9. 使用示例

### 9.1 JavaScript/TypeScript

```javascript
const { ethers } = require("ethers");

// 连接钱包
const provider = new ethers.JsonRpcProvider(RPC_URL);
const wallet = new ethers.Wallet(PRIVATE_KEY, provider);

// 连接合约
const token = new ethers.Contract(
    TOKEN_ADDRESS,
    VIBEToken_ABI,
    wallet
);

// 转账
const tx = await token.transfer(recipient, amount);
await tx.wait();

// 质押
const staking = new ethers.Contract(
    STAKING_ADDRESS,
    VIBStaking_ABI,
    wallet
);
const stakeTx = await staking.stake(amount, 1); // 1 = ValidatorNode
await stakeTx.wait();

// 治理
const governance = new ethers.Contract(
    GOVERNANCE_ADDRESS,
    VIBGovernance_ABI,
    wallet
);
const proposalTx = await governance.propose(
    [target],
    [value],
    [calldata],
    description
);
await proposalTx.wait();
```

### 9.2 Python

```python
from web3 import Web3

# 连接
w3 = Web3(Web3.HTTPProvider(RPC_URL))
account = w3.eth.account.from_key(PRIVATE_KEY)

# 代币转账
token = w3.eth.contract(address=TOKEN_ADDRESS, abi=TOKEN_ABI)
tx = token.functions.transfer(recipient, amount).build_transaction({
    'from': account.address,
    'nonce': w3.eth.get_transaction_count(account.address),
    'gas': 100000,
    'gasPrice': w3.eth.gas_price
})
signed = account.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
```

---

## 10. 安全考虑

### 10.1 权限控制

- **Ownable**: 合约所有者权限
- **AccessControl**: 基于角色的访问控制
- **Timelock**: 延迟执行保护

### 10.2 风控机制

- **Pausable**: 紧急暂停
- **速率限制**: 防止滥用
- **最大提现额**: 降低风险敞口

### 10.3 审计

所有合约均经过专业安全审计：

- OpenZeppelin 库验证
- CertiK 安全审计
- 形式化验证 (可选)

---

## 11. 附录

### 11.1 ABI 文件

完整的 ABI 文件请参考 `contracts/artifacts/` 目录。

### 11.2 测试网

- **RPC**: https://rpc.testnet.usmsb.com
- **ChainID**: 99999
- **Symbol**: VIB
- **Explorer**: https://explorer.testnet.usmsb.com
