# VIBE 智能合约集成方案文档

> 版本: 1.3.0
> 日期: 2026-03-03
> 网络: Base Sepolia (测试网) / Base (主网)
> 状态: 设计完成，已审查，待实现
> 修订说明: v1.3.0 - 添加多网络配置设计、前端集成需求分析

---

## 一、项目概述

### 1.1 目标

将已部署的VIBE智能合约集成到USMSB SDK和平台中，实现：
- Agent之间的链上交易
- 质押等级与Agent权限的关联
- 协作分成的自动执行
- 联合订单的反向竞价

### 1.2 核心原则

1. **每个Agent一个Wallet合约**: 注册Agent时部署独立的AgentWallet合约
2. **质押等级决定权限**: Owner质押等级决定可创建Agent数量和交易限额
3. **只设计方案不开发**: 本文档为设计阶段，后续按文档实现
4. **分层集成**: SDK层（Python客户端）+ 平台层（REST API）

### 1.3 网络配置

#### 多网络配置设计

**重要**：不要在代码中硬编码chainId和网络参数！应使用配置文件 + 环境变量。

```python
# usmsb_sdk/blockchain/config.py

from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel
import os

class NetworkType(Enum):
    """网络类型"""
    TESTNET = "testnet"   # Base Sepolia
    MAINNET = "mainnet"   # Base Mainnet
    LOCAL = "local"       # 本地开发

class NetworkConfig(BaseModel):
    """单个网络的配置"""
    name: str
    chain_id: int
    rpc_url: str
    explorer_url: str
    contracts: Dict[str, str]

# 预定义网络配置
NETWORKS: Dict[NetworkType, NetworkConfig] = {
    NetworkType.TESTNET: NetworkConfig(
        name="Base Sepolia",
        chain_id=84532,
        rpc_url="https://sepolia.base.org",
        explorer_url="https://sepolia.basescan.org",
        contracts={
            "VIBEToken": "0x91d8C3084b4fd21A04fA3584BFE357F378938dbc",
            "VIBStaking": "0xc3fbD1736a95f403A0569FcA8C84d7B85e2b4E53",
            "AgentRegistry": "0x54bEbDc40cc8B60b0922D8FA6463ab710B14dC69",
            "VIBIdentity": "0x6b72711045b3a384E26eD9039CFF4cA12b856952",
            "VIBCollaboration": "0x7E61b51c49438696195142D06f46c12d90909059",
            "JointOrder": "0xc63d9DEb845138A2C5CFF41A4Cb519ccbDf00F3a",
            "VIBDividend": "0x324571F84C092a958eB46b3478742C58a7beaE7B",
            "VIBGovernance": "0xD866536154154a378544E9dc295D510a0fe29236",
            "ZKCredential": "0x4B8465Fe80Ec91876da78DB775a551dDdBBdB04a",
        }
    ),
    NetworkType.MAINNET: NetworkConfig(
        name="Base",
        chain_id=8453,
        rpc_url="https://mainnet.base.org",
        explorer_url="https://basescan.org",
        contracts={
            # 主网部署后填入实际地址
            "VIBEToken": "待部署",
            "VIBStaking": "待部署",
            "AgentRegistry": "待部署",
            "VIBIdentity": "待部署",
            "VIBCollaboration": "待部署",
            "JointOrder": "待部署",
            "VIBDividend": "待部署",
            "VIBGovernance": "待部署",
            "ZKCredential": "待部署",
        }
    ),
    NetworkType.LOCAL: NetworkConfig(
        name="Local",
        chain_id=31337,
        rpc_url="http://localhost:8545",
        explorer_url="",
        contracts={}  # 本地部署后动态填入
    )
}

class BlockchainConfig:
    """区块链配置管理器"""

    def __init__(self, network: Optional[NetworkType] = None):
        # 优先使用环境变量
        env_network = os.environ.get("VIBE_NETWORK", "").lower()
        if env_network:
            network = NetworkType(env_network)
        elif network is None:
            network = NetworkType.TESTNET  # 默认测试网

        self.network_type = network
        self.config = NETWORKS[network]

        # 允许环境变量覆盖RPC
        env_rpc = os.environ.get("VIBE_RPC_URL")
        if env_rpc:
            self.config.rpc_url = env_rpc

    @property
    def chain_id(self) -> int:
        return self.config.chain_id

    @property
    def rpc_url(self) -> str:
        return self.config.rpc_url

    @property
    def contracts(self) -> Dict[str, str]:
        return self.config.contracts

    def get_contract_address(self, name: str) -> str:
        """获取合约地址"""
        return self.config.contracts.get(name)

    def get_explorer_url(self, tx_hash: str) -> str:
        """获取交易浏览器URL"""
        return f"{self.config.explorer_url}/tx/{tx_hash}"
```

#### 使用方式

```python
# 方式1: 自动从环境变量读取
# export VIBE_NETWORK=mainnet
config = BlockchainConfig()

# 方式2: 代码指定
config = BlockchainConfig(network=NetworkType.MAINNET)

# 方式3: 覆盖RPC（用于私有节点）
# export VIBE_RPC_URL=https://my-private-node.com
config = BlockchainConfig()

# 在交易构建中使用
tx = contract.functions.someMethod().build_transaction({
    'from': from_address,
    'nonce': nonce,
    'chainId': config.chain_id  # 动态获取，不硬编码
})
```

#### 环境变量配置

```bash
# .env.development (测试网)
VIBE_NETWORK=testnet
VIBE_RPC_URL=https://sepolia.base.org

# .env.production (主网)
VIBE_NETWORK=mainnet
VIBE_RPC_URL=https://mainnet.base.org

# .env.local (本地开发)
VIBE_NETWORK=local
VIBE_RPC_URL=http://localhost:8545
```

#### 主网部署检查清单

```markdown
## 主网切换前检查
- [ ] 更新所有合约地址为主网地址
- [ ] 确认RPC节点稳定性（建议使用私有节点或Alchemy/Infura）
- [ ] 更新前端钱包链配置
- [ ] 测试小额交易验证
- [ ] 确认Gas价格设置合理
- [ ] 备份测试网配置文件
```

---

## 二、合约分类与地址

### 2.1 已部署合约地址

| 合约名 | 地址 | 分类 |
|--------|------|------|
| VIBEToken | 0x91d8C3084b4fd21A04fA3584BFE357F378938dbc | 核心 |
| VIBStaking | 0xc3fbD1736a95f403A0569FcA8C84d7B85e2b4E53 | 核心 |
| AgentRegistry | 0x54bEbDc40cc8B60b0922D8FA6463ab710B14dC69 | 核心 |
| AgentWallet | 0x7C0EA6b69B84B673F0428A202Fbb69bA5Bc8dF02 | 核心(模板) |
| VIBIdentity | 0x6b72711045b3a384E26eD9039CFF4cA12b856952 | 核心 |
| VIBCollaboration | 0x7E61b51c49438696195142D06f46c12d90909059 | 业务 |
| JointOrder | 0xc63d9DEb845138A2C5CFF41A4Cb519ccbDf00F3a | 业务 |
| ZKCredential | 0x4B8465Fe80Ec91876da78DB775a551dDdBBdB04a | 业务 |
| VIBDividend | 0x324571F84C092a958eB46b3478742C58a7beaE7B | 激励 |
| EmissionController | 0xe4a31e600D2DeB3297f3732aE509B1C1d7eAAaD6 | 激励 |
| VIBGovernance | 0xD866536154154a378544E9dc295D510a0fe29236 | 治理 |

### 2.2 集成优先级

```
高优先级（核心功能）:
├── VIBEToken      - 代币基础操作
├── AgentWallet    - Agent资金管理（每个Agent独立部署）
├── AgentRegistry  - Agent注册验证
├── VIBIdentity    - Agent身份+数量限制（关键：持有Agent限制逻辑）
└── VIBStaking     - 质押等级（被VIBIdentity调用）

中优先级（业务功能）:
├── VIBCollaboration - 协作分成
└── JointOrder       - 联合订单

低优先级（监控/可选）:
├── VIBDividend      - 分红领取
├── EmissionController - 释放监控
└── VIBGovernance    - 治理投票
```

---

## 三、关键合约关系图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Owner (用户)                                   │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ 1. 质押VIBE到VIBStaking                                            │ │
│  │ 2. VIBStaking返回质押等级                                          │ │
│  │ 3. VIBIdentity根据等级返回Agent数量限制                            │ │
│  │ 4. 部署AgentWallet合约                                             │ │
│  │ 5. AgentWallet调用VIBStaking获取等级更新限额                       │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│ VIBStaking  │◄─────│ VIBIdentity │──────│AgentWallet  │
│             │      │             │      │ (每Agent一个)│
│ - stake()   │      │- getAgent   │      │             │
│ - getTier() │      │  Limit()    │      │- deposit()  │
│             │      │- registerAI │      │- transfer() │
│ 等级:       │      │  Identity() │      │- stake()    │
│ BRONZE      │      │             │      │             │
│ SILVER      │      │ 限制:       │      │ 关联:       │
│ GOLD        │      │ Bronze=1    │      │ - VIBStaking│
│ PLATINUM    │      │ Silver=3    │      │ - Registry  │
└─────────────┘      │ Gold=10     │      │ - Identity  │
                     │ Platinum=50 │      └─────────────┘
                     └─────────────┘             │
                                                 ▼
                                          ┌─────────────┐
                                          │AgentRegistry│
                                          │             │
                                          │- register() │
                                          │- isValid()  │
                                          └─────────────┘
```

---

## 四、逐个合约集成方案

### 4.1 VIBEToken (0x91d8...)

#### 合约功能
- ERC-20标准代币
- 交易税0.8%（销毁50%、分红20%、生态15%、协议15%）
- 支持Pausable
- **注意**: 交易税从发送者扣除，接收者收到净额

#### 方法分析

| 方法 | 类型 | 集成位置 | 优先级 | 说明 |
|------|------|----------|--------|------|
| `balanceOf(address)` | read | SDK+平台 | P0 | 查询余额 |
| `approve(address,uint256)` | write | SDK | P0 | 授权消费 |
| `allowance(address,address)` | read | SDK | P0 | 查询授权额度 |
| `transfer(address,uint256)` | write | SDK | P1 | 普通转账(有税) |
| `getTaxBreakdown(uint256)` | read | 平台 | P2 | 税收明细 |
| `getNetTransferAmount(uint256)` | read | SDK | P1 | 计算实际到账 |
| `burn(uint256)` | write | SDK | P2 | 销毁代币 |

#### SDK接口设计

```python
# usmsb_sdk/blockchain/contracts/vibe_token.py

class VIBETokenClient:
    """VIBE代币客户端"""

    def __init__(self, web3, contract_address: str, abi: dict):
        self.web3 = web3
        self.contract = web3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=abi
        )
        self.address = contract_address

    async def balance_of(self, address: str) -> int:
        """查询余额（wei单位，10^18）"""
        address = Web3.to_checksum_address(address)
        return await self.contract.functions.balanceOf(address).call()

    async def balance_of_vibe(self, address: str) -> float:
        """查询余额（VIBE单位）"""
        balance_wei = await self.balance_of(address)
        return balance_wei / 10**18

    async def approve(
        self,
        spender: str,
        amount: int,
        from_address: str,
        private_key: str
    ) -> str:
        """
        授权消费

        Args:
            spender: 被授权地址（如AgentWallet合约地址）
            amount: 授权金额（wei）
            from_address: 授权者地址
            private_key: 授权者私钥
        """
        spender = Web3.to_checksum_address(spender)
        from_address = Web3.to_checksum_address(from_address)

        nonce = await self.web3.eth.get_transaction_count(from_address)
        tx = self.contract.functions.approve(spender, amount).build_transaction({
            'from': from_address,
            'nonce': nonce,
            'chainId': 84532
        })

        signed = self.web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = await self.web3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()

    async def allowance(self, owner: str, spender: str) -> int:
        """查询授权额度"""
        owner = Web3.to_checksum_address(owner)
        spender = Web3.to_checksum_address(spender)
        return await self.contract.functions.allowance(owner, spender).call()

    async def get_tax_breakdown(self, amount: int) -> dict:
        """计算交易税明细"""
        result = await self.contract.functions.getTaxBreakdown(amount).call()
        return {
            "tax_amount": result[0],
            "burn_amount": result[1],
            "dividend_amount": result[2],
            "ecosystem_amount": result[3],
            "protocol_amount": result[4],
            "net_amount": amount - result[0]
        }

    async def get_net_transfer_amount(self, amount: int) -> int:
        """计算实际到账金额（扣除税费）"""
        return await self.contract.functions.getNetTransferAmount(amount).call()
```

---

### 4.2 AgentWallet (动态部署)

#### 合约功能
- 每个Agent独立的智能合约钱包
- 日限额控制（默认500/笔，1000/日）
- 大额转账审批流程
- 与VIBStaking关联获取等级和限额倍数

#### 重要修正：Agent后端私钥管理

**关键发现**: AgentWallet的`executeTransfer`只能由Agent调用（onlyAgent修饰符）

```solidity
modifier onlyAgent() {
    require(msg.sender == agent, "AgentWallet: caller is not agent");
    _;
}

function executeTransfer(address to, uint256 amount) external onlyAgent ...
```

**这意味着**:
1. Agent后端服务需要持有私钥
2. 该私钥对应的地址在部署AgentWallet时传入`_agent`参数
3. 只有这个地址才能调用`executeTransfer`

#### Agent创建完整流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Agent创建流程                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  前置条件:                                                              │
│  - Owner已质押VIBE（在VIBStaking中）                                   │
│  - Owner有Agent后端服务的私钥                                          │
│                                                                         │
│  Step 1: 检查限制                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ 调用 VIBIdentity.getAgentLimit(owner) 获取限制                   │  │
│  │ 调用 VIBIdentity.getUserAgentCount(owner) 获取已创建数量         │  │
│  │ 验证: current < limit                                            │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│              │                                                          │
│              ↓ 通过                                                    │
│                                                                         │
│  Step 2: 生成或获取Agent地址                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ 方案A: Agent后端自己生成地址和私钥                                │  │
│  │ 方案B: 平台为Agent生成地址和私钥，安全传递给Agent服务             │  │
│  │                                                                   │  │
│  │ 返回: agent_address (EOA地址)                                    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│              │                                                          │
│              ↓                                                          │
│                                                                         │
│  Step 3: 部署AgentWallet合约                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  constructor(                                                     │  │
│  │      _owner: owner地址,           // Owner的EOA地址              │  │
│  │      _agent: agent_address,       // Agent后端服务的EOA地址      │  │
│  │      _vibeToken: 0x91d8...,       // VIBEToken地址               │  │
│  │      _registry: 0x54bE...,        // AgentRegistry地址           │  │
│  │      _stakingContract: 0xc3fb...  // VIBStaking地址              │  │
│  │  )                                                                │  │
│  │                                                                   │  │
│  │  部署者: 可以是Owner或平台（需要Owner支付Gas）                   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│              │                                                          │
│              ↓ 返回 wallet_contract_address                            │
│                                                                         │
│  Step 4: 注册到AgentRegistry                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ AgentRegistry.registerAgent(wallet_contract_address)             │  │
│  │                                                                   │  │
│  │ 注意: registerAgent从msg.sender获取Owner                        │  │
│  │ 所以必须由Owner调用（或平台使用Owner的私钥代调用）               │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│              │                                                          │
│              ↓                                                          │
│                                                                         │
│  Step 5: 注册VIBIdentity（可选但推荐）                                 │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ VIBIdentity.registerAIIdentityFor(                               │  │
│  │     agentAddress: agent_address,  // Agent后端服务地址           │  │
│  │     name: "Agent名称",                                           │  │
│  │     metadata: "Agent能力描述JSON"                                │  │
│  │ )                                                                │  │
│  │                                                                   │  │
│  │ 注意: 这会消耗ETH或VIBE作为注册费                                │  │
│  │ 同时会增加创建者的agent计数                                      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│              │                                                          │
│              ↓                                                          │
│                                                                         │
│  Step 6: 初始化钱包（Owner充值）                                       │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ 1. VIBEToken.approve(wallet_address, amount)  // Owner授权       │  │
│  │ 2. AgentWallet.deposit(amount)                // Owner充值       │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  最终状态:                                                              │
│  - owner: Owner的EOA地址                                               │
│  - agent_address: Agent后端服务的EOA地址（持有私钥）                   │
│  - wallet_contract: AgentWallet合约地址                                │
│  - 质押等级: 通过VIBStaking获取                                        │
│  - 交易限额: 根据等级动态调整                                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 方法分析

| 方法 | 类型 | 调用者 | 集成位置 | 说明 |
|------|------|--------|----------|------|
| `constructor(owner,agent,token,registry,staking)` | deploy | Owner/平台 | 平台 | 部署新钱包 |
| `deposit(uint256)` | write | 任意 | SDK | 充值（需先approve） |
| `executeTransfer(to,amount)` | write | **Agent** | SDK | Agent执行转账 |
| `requestTransfer(to,amount)` | write | **Agent** | SDK | 请求大额转账 |
| `approveTransfer(requestId)` | write | **Owner** | SDK+平台 | 批准转账 |
| `rejectTransfer(requestId)` | write | **Owner** | SDK+平台 | 拒绝转账 |
| `getBalance()` | read | 任意 | SDK+平台 | 查询余额 |
| `getRemainingDailyLimit()` | read | 任意 | SDK+平台 | 剩余限额 |
| `getStakingTier()` | read | 任意 | SDK+平台 | 获取等级 |
| `getAgentLimit()` | read | 任意 | SDK+平台 | 获取Agent限制 |
| `updateLimits(maxPerTx,dailyLimit)` | write | **Owner** | 平台 | 更新限额 |
| `updateWhitelist(addr,allowed)` | write | **Owner** | 平台 | 更新白名单 |

#### SDK接口设计

```python
# usmsb_sdk/blockchain/contracts/agent_wallet.py

from web3 import Web3
from typing import Tuple, Optional
import json

class AgentWalletFactory:
    """AgentWallet合约工厂"""

    def __init__(self, web3: Web3, bytecode: str, abi: dict, config: dict):
        self.web3 = web3
        self.bytecode = bytecode
        self.abi = abi
        self.config = config  # 包含其他合约地址

    async def deploy_wallet(
        self,
        owner_address: str,
        agent_address: str,
        from_address: str,
        private_key: str
    ) -> Tuple[str, str]:
        """
        为Agent部署新的Wallet合约

        Args:
            owner_address: Owner的EOA地址
            agent_address: Agent后端服务的EOA地址
            from_address: 部署交易发起者（通常是Owner）
            private_key: 部署者私钥

        Returns:
            (wallet_address, tx_hash): 部署的合约地址和交易哈希
        """
        # 构建构造参数
        constructor_args = [
            Web3.to_checksum_address(owner_address),
            Web3.to_checksum_address(agent_address),
            Web3.to_checksum_address(self.config['VIBEToken']),
            Web3.to_checksum_address(self.config['AgentRegistry']),
            Web3.to_checksum_address(self.config['VIBStaking'])
        ]

        # 构建合约对象
        contract = self.web3.eth.contract(
            bytecode=self.bytecode,
            abi=self.abi
        )

        # 获取nonce
        nonce = await self.web3.eth.get_transaction_count(from_address)

        # 构建部署交易
        deploy_tx = contract.constructor(*constructor_args).build_transaction({
            'from': from_address,
            'nonce': nonce,
            'chainId': 84532
        })

        # 签名并发送
        signed = self.web3.eth.account.sign_transaction(deploy_tx, private_key)
        tx_hash = await self.web3.eth.send_raw_transaction(signed.rawTransaction)

        # 等待确认
        receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)
        wallet_address = receipt['contractAddress']

        return wallet_address, tx_hash.hex()


class AgentWalletClient:
    """AgentWallet合约客户端（针对已部署的实例）"""

    def __init__(self, web3: Web3, wallet_address: str, abi: dict, agent_private_key: str = None):
        self.web3 = web3
        self.wallet_address = Web3.to_checksum_address(wallet_address)
        self.contract = web3.eth.contract(
            address=self.wallet_address,
            abi=abi
        )
        self.agent_private_key = agent_private_key

    async def get_balance(self) -> int:
        """获取钱包余额（wei）"""
        return await self.contract.functions.getBalance().call()

    async def get_balance_vibe(self) -> float:
        """获取钱包余额（VIBE）"""
        balance_wei = await self.get_balance()
        return balance_wei / 10**18

    async def deposit(
        self,
        amount: int,
        from_address: str,
        private_key: str
    ) -> str:
        """
        充值到钱包

        注意: 充值前需要先调用VIBEToken.approve(wallet_address, amount)
        """
        from_address = Web3.to_checksum_address(from_address)
        nonce = await self.web3.eth.get_transaction_count(from_address)

        tx = self.contract.functions.deposit(amount).build_transaction({
            'from': from_address,
            'nonce': nonce,
            'chainId': 84532
        })

        signed = self.web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = await self.web3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()

    async def execute_transfer(
        self,
        to: str,
        amount: int,
        agent_address: str,
        agent_private_key: str
    ) -> str:
        """
        Agent执行转账（限额内）

        注意: 只能由Agent地址调用，且金额不能超过maxPerTx和剩余日限额
        """
        to = Web3.to_checksum_address(to)
        agent_address = Web3.to_checksum_address(agent_address)
        nonce = await self.web3.eth.get_transaction_count(agent_address)

        tx = self.contract.functions.executeTransfer(to, amount).build_transaction({
            'from': agent_address,
            'nonce': nonce,
            'chainId': 84532
        })

        signed = self.web3.eth.account.sign_transaction(tx, agent_private_key)
        tx_hash = await self.web3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()

    async def request_transfer(
        self,
        to: str,
        amount: int,
        agent_address: str,
        agent_private_key: str
    ) -> str:
        """
        Agent请求大额转账（需要Owner审批）

        Returns:
            requestId: 请求ID，用于后续审批
        """
        to = Web3.to_checksum_address(to)
        agent_address = Web3.to_checksum_address(agent_address)
        nonce = await self.web3.eth.get_transaction_count(agent_address)

        tx = self.contract.functions.requestTransfer(to, amount).build_transaction({
            'from': agent_address,
            'nonce': nonce,
            'chainId': 84532
        })

        signed = self.web3.eth.account.sign_transaction(tx, agent_private_key)
        tx_hash = await self.web3.eth.send_raw_transaction(signed.rawTransaction)

        # 等待交易确认并解析事件获取requestId
        receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)
        for log in receipt['logs']:
            if log['address'].lower() == self.wallet_address.lower():
                try:
                    event = self.contract.events.TransferRequested().process_log(log)
                    return event['args']['requestId']
                except:
                    pass

        return None

    async def approve_transfer(
        self,
        request_id: str,
        owner_address: str,
        owner_private_key: str
    ) -> str:
        """Owner批准转账"""
        owner_address = Web3.to_checksum_address(owner_address)
        nonce = await self.web3.eth.get_transaction_count(owner_address)

        tx = self.contract.functions.approveTransfer(request_id).build_transaction({
            'from': owner_address,
            'nonce': nonce,
            'chainId': 84532
        })

        signed = self.web3.eth.account.sign_transaction(tx, owner_private_key)
        tx_hash = await self.web3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()

    async def reject_transfer(
        self,
        request_id: str,
        owner_address: str,
        owner_private_key: str
    ) -> str:
        """Owner拒绝转账"""
        owner_address = Web3.to_checksum_address(owner_address)
        nonce = await self.web3.eth.get_transaction_count(owner_address)

        tx = self.contract.functions.rejectTransfer(request_id).build_transaction({
            'from': owner_address,
            'nonce': nonce,
            'chainId': 84532
        })

        signed = self.web3.eth.account.sign_transaction(tx, owner_private_key)
        tx_hash = await self.web3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()

    async def get_remaining_limit(self) -> int:
        """获取剩余日限额"""
        return await self.contract.functions.getRemainingDailyLimit().call()

    async def get_staking_tier(self) -> int:
        """获取质押等级 (0=Bronze, 1=Silver, 2=Gold, 3=Platinum)"""
        return await self.contract.functions.getStakingTier().call()

    async def get_daily_limit(self) -> int:
        """获取每日限额"""
        return await self.contract.functions.dailyLimit().call()

    async def get_max_per_tx(self) -> int:
        """获取单笔限额"""
        return await self.contract.functions.maxPerTx().call()
```

---

### 4.3 AgentRegistry (0x54bE...)

#### 合约功能
- Agent注册表，记录AgentWallet合约地址
- 验证Agent有效性
- 管理Agent与Owner的关系

#### 重要发现：registerAgent的调用者

```solidity
function registerAgent(address agentWallet) external override nonReentrant {
    // 获取调用者地址（在实际部署时，这应该是创建 Agent 的主人）
    address owner = msg.sender;

    _validAgents[agentWallet] = true;
    _agentToOwner[agentWallet] = owner;
    _ownerAgentCount[owner]++;
    _registeredAgents.push(agentWallet);

    emit AgentRegistered(agentWallet, owner);
}
```

**关键点**: `msg.sender`被记录为Owner，所以必须由Owner调用（或使用Owner私钥）

#### 方法分析

| 方法 | 类型 | 集成位置 | 说明 |
|------|------|----------|------|
| `registerAgent(address)` | write | 平台 | 注册Agent（Owner调用） |
| `unregisterAgent(address)` | write | 平台 | 注销Agent（Admin） |
| `isValidAgent(address)` | read | SDK+平台 | 验证有效性 |
| `getAgentOwner(address)` | read | SDK+平台 | 获取Owner |
| `getOwnerAgentCount(address)` | read | 平台 | 统计数量 |

#### SDK接口设计

```python
# usmsb_sdk/blockchain/contracts/agent_registry.py

class AgentRegistryClient:
    """Agent注册表客户端"""

    def __init__(self, web3: Web3, contract_address: str, abi: dict):
        self.web3 = web3
        self.contract = web3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=abi
        )

    async def register_agent(
        self,
        wallet_address: str,
        owner_address: str,
        owner_private_key: str
    ) -> str:
        """
        注册Agent钱包到Registry

        注意: msg.sender会被记录为Owner，所以必须使用Owner的私钥
        """
        wallet_address = Web3.to_checksum_address(wallet_address)
        owner_address = Web3.to_checksum_address(owner_address)
        nonce = await self.web3.eth.get_transaction_count(owner_address)

        tx = self.contract.functions.registerAgent(wallet_address).build_transaction({
            'from': owner_address,
            'nonce': nonce,
            'chainId': 84532
        })

        signed = self.web3.eth.account.sign_transaction(tx, owner_private_key)
        tx_hash = await self.web3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()

    async def is_valid_agent(self, wallet_address: str) -> bool:
        """验证Agent有效性"""
        wallet_address = Web3.to_checksum_address(wallet_address)
        return await self.contract.functions.isValidAgent(wallet_address).call()

    async def get_agent_owner(self, wallet_address: str) -> str:
        """获取Agent的Owner"""
        wallet_address = Web3.to_checksum_address(wallet_address)
        return await self.contract.functions.getAgentOwner(wallet_address).call()

    async def get_owner_agent_count(self, owner: str) -> int:
        """获取Owner的Agent数量"""
        owner = Web3.to_checksum_address(owner)
        return await self.contract.functions.getOwnerAgentCount(owner).call()
```

---

### 4.4 VIBIdentity (0x6b72...)

#### 合约功能
- 灵魂绑定代币(SBT)身份认证
- **Agent数量限制**（核心功能）
- 人类服务者注册

#### 重要发现：Agent数量限制逻辑

```solidity
// VIBIdentity中的限制常量
uint256 public constant BRONZE_AGENT_LIMIT = 1;
uint256 public constant SILVER_AGENT_LIMIT = 3;
uint256 public constant GOLD_AGENT_LIMIT = 10;
uint256 public constant PLATINUM_AGENT_LIMIT = 50;

// 获取限制时调用VIBStaking
function _getAgentLimit(address user) internal view returns (uint256) {
    if (stakingContract != address(0)) {
        try IVIBStakingForIdentity(stakingContract).getStakingTier(user) returns (
            IVIBStakingForIdentity.StakeTier tier
        ) {
            if (tier == IVIBStakingForIdentity.StakeTier.PLATINUM) return PLATINUM_AGENT_LIMIT;
            if (tier == IVIBStakingForIdentity.StakeTier.GOLD) return GOLD_AGENT_LIMIT;
            if (tier == IVIBStakingForIdentity.StakeTier.SILVER) return SILVER_AGENT_LIMIT;
        } catch {}
    }
    return BRONZE_AGENT_LIMIT; // 默认1个
}
```

**结论**: Agent数量限制由VIBIdentity管理，它内部调用VIBStaking获取等级

#### 方法分析

| 方法 | 类型 | 集成位置 | 说明 |
|------|------|----------|------|
| `registerAIIdentity(name,metadata)` | write | 平台 | Agent自注册身份 |
| `registerAIIdentityFor(agent,name,metadata)` | write | **平台** | 为Agent注册身份 |
| `getAgentLimit(address)` | read | **平台** | 获取Agent数量限制 |
| `getUserAgentCount(address)` | read | **平台** | 已创建Agent数量 |
| `getIdentityInfo(tokenId)` | read | SDK+平台 | 获取身份信息 |
| `isRegistered(address)` | read | SDK | 检查是否注册 |

#### SDK接口设计

```python
# usmsb_sdk/blockchain/contracts/vib_identity.py

class VIBIdentityClient:
    """VIB身份认证客户端"""

    def __init__(self, web3: Web3, contract_address: str, abi: dict):
        self.web3 = web3
        self.contract = web3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=abi
        )

    async def register_ai_identity_for(
        self,
        agent_address: str,
        name: str,
        metadata: str,
        from_address: str,
        private_key: str
    ) -> Tuple[int, str]:
        """
        为Agent注册身份

        Args:
            agent_address: Agent地址
            name: Agent名称
            metadata: Agent能力描述(JSON字符串)
            from_address: 创建者地址
            private_key: 创建者私钥

        Returns:
            (token_id, tx_hash): 身份token ID和交易哈希

        注意:
            - 会检查创建者的Agent数量限制
            - 会增加创建者的agent计数
            - 可能需要支付注册费(ETH或VIBE)
        """
        agent_address = Web3.to_checksum_address(agent_address)
        from_address = Web3.to_checksum_address(from_address)
        nonce = await self.web3.eth.get_transaction_count(from_address)

        tx = self.contract.functions.registerAIIdentityFor(
            agent_address, name, metadata
        ).build_transaction({
            'from': from_address,
            'nonce': nonce,
            'chainId': 84532,
            'value': 0  # 如果用ETH注册，这里需要设置值
        })

        signed = self.web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = await self.web3.eth.send_raw_transaction(signed.rawTransaction)

        # 解析事件获取tokenId
        receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)
        token_id = None
        for log in receipt['logs']:
            try:
                event = self.contract.events.IdentityRegistered().process_log(log)
                token_id = event['args']['tokenId']
                break
            except:
                pass

        return token_id, tx_hash.hex()

    async def get_agent_limit(self, owner: str) -> int:
        """
        获取Agent数量限制

        返回值基于VIBStaking中的质押等级:
        - Bronze: 1
        - Silver: 3
        - Gold: 10
        - Platinum: 50
        """
        owner = Web3.to_checksum_address(owner)
        return await self.contract.functions.getAgentLimit(owner).call()

    async def get_user_agent_count(self, owner: str) -> int:
        """获取已创建Agent数量"""
        owner = Web3.to_checksum_address(owner)
        return await self.contract.functions.getUserAgentCount(owner).call()

    async def is_registered(self, address: str) -> bool:
        """检查地址是否已注册身份"""
        address = Web3.to_checksum_address(address)
        return await self.contract.functions.isRegistered(address).call()

    async def get_identity_info(self, token_id: int) -> dict:
        """获取身份信息"""
        info = await self.contract.functions.getIdentityInfo(token_id).call()
        return {
            "owner": info[0],
            "identity_type": info[1],
            "name": info[2],
            "registration_time": info[3],
            "metadata": info[4],
            "is_verified": info[5]
        }
```

---

### 4.5 VIBStaking (0xc3fb...)

#### 合约功能
- VIBE质押
- 多等级（BRONZE, SILVER, GOLD, PLATINUM）
- 多锁仓期（无锁、30天、90天、180天、365天）
- 动态APY（反死螺旋机制）
- 被VIBIdentity调用获取等级

#### 质押等级与阈值

| 等级 | 质押量(VIBE) | Agent数量限制 | 交易限额倍数 |
|------|-------------|---------------|-------------|
| BRONZE | 100-999 | 1 | 1x |
| SILVER | 1000-4999 | 3 | 2x |
| GOLD | 5000-9999 | 10 | 5x |
| PLATINUM | 10000+ | 50 | 10x |

#### 方法分析

| 方法 | 类型 | 集成位置 | 说明 |
|------|------|----------|------|
| `stake(amount,lockPeriod)` | write | SDK | 质押 |
| `unstake()` | write | SDK | 取消质押 |
| `claimReward()` | write | SDK | 领取奖励 |
| `getStakeInfo(address)` | read | SDK+平台 | 质押信息 |
| `getStakingTier(address)` | read | SDK+平台 | 质押等级 |
| `getPendingReward(address)` | read | SDK+平台 | 待领取奖励 |

#### SDK接口设计

```python
# usmsb_sdk/blockchain/contracts/vib_staking.py

from enum import IntEnum

class StakeTier(IntEnum):
    BRONZE = 0
    SILVER = 1
    GOLD = 2
    PLATINUM = 3

class LockPeriod(IntEnum):
    NONE = 0      # 无锁仓
    DAYS_30 = 1   # 30天
    DAYS_90 = 2   # 90天
    DAYS_180 = 3  # 180天
    DAYS_365 = 4  # 365天

class VIBStakingClient:
    """VIBE质押客户端"""

    def __init__(self, web3: Web3, contract_address: str, abi: dict):
        self.web3 = web3
        self.contract = web3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=abi
        )

    async def stake(
        self,
        amount: int,
        lock_period: LockPeriod,
        from_address: str,
        private_key: str
    ) -> str:
        """
        质押VIBE

        注意: 调用前需要先approve VIBEToken
        """
        from_address = Web3.to_checksum_address(from_address)
        nonce = await self.web3.eth.get_transaction_count(from_address)

        tx = self.contract.functions.stake(amount, lock_period).build_transaction({
            'from': from_address,
            'nonce': nonce,
            'chainId': 84532
        })

        signed = self.web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = await self.web3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()

    async def unstake(
        self,
        from_address: str,
        private_key: str
    ) -> str:
        """取消质押"""
        from_address = Web3.to_checksum_address(from_address)
        nonce = await self.web3.eth.get_transaction_count(from_address)

        tx = self.contract.functions.unstake().build_transaction({
            'from': from_address,
            'nonce': nonce,
            'chainId': 84532
        })

        signed = self.web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = await self.web3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()

    async def get_tier(self, address: str) -> StakeTier:
        """获取质押等级"""
        address = Web3.to_checksum_address(address)
        tier = await self.contract.functions.getStakingTier(address).call()
        return StakeTier(tier)

    async def get_stake_info(self, address: str) -> dict:
        """获取质押信息"""
        address = Web3.to_checksum_address(address)
        info = await self.contract.functions.getStakeInfo(address).call()
        return {
            "amount": info[0],
            "start_time": info[1],
            "unlock_time": info[2],
            "lock_period_index": info[3],
            "tier": StakeTier(info[4]),
            "pending_reward": info[5],
            "reward_debt": info[6],
            "is_active": info[7]
        }

    async def get_pending_reward(self, address: str) -> int:
        """获取待领取奖励"""
        address = Web3.to_checksum_address(address)
        return await self.contract.functions.getPendingReward(address).call()
```

---

### 4.6 VIBCollaboration (0x7E61...)

#### 合约功能
- 协作分成合约
- 分成比例：70%产出者 / 20%贡献者 / 10%协调者
- 完全去中心化自动执行

#### SDK接口设计

```python
# usmsb_sdk/blockchain/contracts/vib_collaboration.py

class VIBCollaborationClient:
    """协作分成客户端"""

    async def create_project(
        self,
        producer: str,
        coordinator: str,
        from_address: str,
        private_key: str
    ) -> str:
        """创建协作项目"""
        producer = Web3.to_checksum_address(producer)
        coordinator = Web3.to_checksum_address(coordinator)
        from_address = Web3.to_checksum_address(from_address)
        nonce = await self.web3.eth.get_transaction_count(from_address)

        tx = self.contract.functions.createProject(producer, coordinator).build_transaction({
            'from': from_address,
            'nonce': nonce,
            'chainId': 84532
        })

        signed = self.web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = await self.web3.eth.send_raw_transaction(signed.rawTransaction)

        # 解析事件获取projectId
        receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)
        for log in receipt['logs']:
            try:
                event = self.contract.events.ProjectCreated().process_log(log)
                return event['args']['projectId']
            except:
                pass
        return None

    async def add_contributors(
        self,
        project_id: str,
        contributors: List[str],
        weights: List[int],
        from_address: str,
        private_key: str
    ) -> str:
        """
        添加贡献者

        Args:
            project_id: 项目ID
            contributors: 贡献者地址列表
            weights: 权重列表（精度10000，总和应<=10000）
        """
        contributors = [Web3.to_checksum_address(c) for c in contributors]
        from_address = Web3.to_checksum_address(from_address)
        nonce = await self.web3.eth.get_transaction_count(from_address)

        tx = self.contract.functions.addContributors(
            project_id, contributors, weights
        ).build_transaction({
            'from': from_address,
            'nonce': nonce,
            'chainId': 84532
        })

        signed = self.web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = await self.web3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()

    async def distribute(
        self,
        project_id: str,
        amount: int,
        from_address: str,
        private_key: str
    ) -> str:
        """
        分发收入

        注意: 调用前需要先approve VIBEToken
        分发比例: 70%产出者 / 20%贡献者 / 10%协调者
        """
        from_address = Web3.to_checksum_address(from_address)
        nonce = await self.web3.eth.get_transaction_count(from_address)

        tx = self.contract.functions.receiveAndDistribute(
            project_id, amount
        ).build_transaction({
            'from': from_address,
            'nonce': nonce,
            'chainId': 84532
        })

        signed = self.web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = await self.web3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()
```

---

### 4.7 JointOrder (0xc63d...)

#### 合约功能
- 联合订单/需求聚合
- 反向竞价
- 资金托管
- 争议处理

#### SDK接口设计（简化版）

```python
# usmsb_sdk/blockchain/contracts/joint_order.py

class JointOrderClient:
    """联合订单客户端"""

    async def create_pool(
        self,
        service_type: str,
        min_budget: int,
        bidding_duration: int,
        from_address: str,
        private_key: str
    ) -> str:
        """创建需求池"""
        from_address = Web3.to_checksum_address(from_address)
        nonce = await self.web3.eth.get_transaction_count(from_address)

        tx = self.contract.functions.createPool(
            service_type, min_budget, bidding_duration
        ).build_transaction({
            'from': from_address,
            'nonce': nonce,
            'chainId': 84532
        })

        signed = self.web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = await self.web3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()

    async def submit_bid(
        self,
        pool_id: str,
        price: int,
        delivery_time: int,
        reputation: int,
        from_address: str,
        private_key: str
    ) -> str:
        """提交报价"""
        from_address = Web3.to_checksum_address(from_address)
        nonce = await self.web3.eth.get_transaction_count(from_address)

        tx = self.contract.functions.submitBid(
            pool_id, price, delivery_time, reputation
        ).build_transaction({
            'from': from_address,
            'nonce': nonce,
            'chainId': 84532
        })

        signed = self.web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = await self.web3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()
```

---

### 4.8 VIBDividend (0x3245...)

#### 合约功能
- 分红分发合约，接收VIBEToken交易税的20%
- 按质押量比例分配给质押者
- 1天冷却期（Claim Cooldown）

#### 方法分析

| 方法 | 类型 | 集成位置 | 说明 |
|------|------|----------|------|
| `receiveDividend(amount)` | write | **VIBEToken** | 接收分红（内部调用） |
| `notifyDividendReceived(amount)` | write | **VIBEToken** | 通知分红到账 |
| `claimDividend()` | write | SDK | 领取分红（需间隔1天） |
| `batchClaimDividend(users[])` | write | 平台 | 批量领取 |
| `getPendingDividend(address)` | read | SDK+平台 | 查询待领取分红 |
| `getBalance()` | read | SDK+平台 | 合约余额 |
| `setStakingContract(address)` | write | Admin | 设置质押合约 |

#### SDK接口设计

```python
# usmsb_sdk/blockchain/contracts/vib_dividend.py

class VIBDividendClient:
    """VIBE分红客户端"""

    def __init__(self, web3: Web3, contract_address: str, abi: dict):
        self.web3 = web3
        self.contract = web3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=abi
        )

    async def get_pending_dividend(self, user: str) -> int:
        """
        获取用户待领取分红

        计算公式: pending + (dividendPerToken - dividendPerTokenPaid) * userStake / PRECISION
        """
        user = Web3.to_checksum_address(user)
        return await self.contract.functions.getPendingDividend(user).call()

    async def claim_dividend(
        self,
        from_address: str,
        private_key: str
    ) -> str:
        """
        领取分红

        注意: 需要距离上次领取超过1天(CLAIM_COOLDOWN)
        """
        from_address = Web3.to_checksum_address(from_address)
        nonce = await self.web3.eth.get_transaction_count(from_address)

        tx = self.contract.functions.claimDividend().build_transaction({
            'from': from_address,
            'nonce': nonce,
            'chainId': 84532
        })

        signed = self.web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = await self.web3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()

    async def get_balance(self) -> int:
        """获取合约分红余额"""
        return await self.contract.functions.getBalance().call()

    async def get_dividend_stats(self) -> dict:
        """获取分红统计"""
        return {
            "dividend_per_token": await self.contract.functions.dividendPerTokenStored().call(),
            "total_distributed": await self.contract.functions.totalDividendsDistributed().call(),
            "balance": await self.get_balance()
        }
```

---

### 4.9 ZKCredential (0x4B84...) - 高级功能

#### 合约功能
- 零知识证明信用凭证（zk-SNARK Groth16）
- 凭证类型：IDENTITY、SERVICE_PROVIDER、GOVERNANCE、PREMIUM、TRUSTED_NODE
- 隐私保护的属性验证

#### 集成建议

**初期集成**：暂不集成，原因：
1. 需要链下生成zk证明（需要circom/snarkjs工具链）
2. 需要配置验证密钥（Verification Key）
3. 复杂度高，非核心业务流程

**后期集成**：当需要隐私保护的凭证验证时再集成

#### 方法分析（供参考）

| 方法 | 类型 | 说明 |
|------|------|------|
| `verifyAndIssue(holder, type, duration, commitment, nullifierHash, score, proof, metadata)` | write | 验证证明并签发凭证 |
| `verifyCredential(credentialId, nullifierHash, proof, purpose)` | write | 验证凭证 |
| `revokeCredential(credentialId, reason)` | write | 撤销凭证 |
| `isCredentialValid(credentialId)` | read | 检查凭证有效性 |
| `hasCredentialType(holder, credType)` | read | 检查是否持有某类型凭证 |

---

### 4.10 VIBGovernance (0xD866...) - 可升级合约

#### 合约功能
- VIBE生态系统治理合约
- 支持UUPS升级模式
- 多种提案类型：GENERAL、PARAMETER、UPGRADE、EMERGENCY、DIVIDEND、INCENTIVE
- 三权分立：资本权重 + 生产权重 + 社区权重

#### 投票权计算

```
总投票权 = 资本权重 + 生产权重 + 社区权重

资本权重 = 质押的VIBE（上限10%总投票权）
生产权重 = 贡献积分 * 0.01（上限15%总投票权）
社区权重 = KYC用户平均分配（10%总投票权）
```

#### 方法分析

| 方法 | 类型 | 集成位置 | 说明 |
|------|------|----------|------|
| `createProposal(type, title, desc, target, data)` | write | SDK | 创建提案 |
| `castVote(proposalId, support)` | write | SDK | 投票(0=反对,1=支持,2=弃权) |
| `finalizeProposal(proposalId)` | write | 平台 | 结算提案 |
| `executeProposal(proposalId)` | write | 平台 | 执行提案 |
| `cancelProposal(proposalId)` | write | SDK+平台 | 取消提案 |
| `getVotingPower(address)` | read | SDK+平台 | 获取投票权 |
| `getProposal(proposalId)` | read | SDK+平台 | 获取提案详情 |
| `getState(proposalId)` | read | SDK+平台 | 获取提案状态 |
| `claimGovernanceReward()` | write | SDK | 领取治理奖励 |

#### SDK接口设计

```python
# usmsb_sdk/blockchain/contracts/vib_governance.py

from enum import IntEnum

class ProposalType(IntEnum):
    GENERAL = 0
    PARAMETER = 1
    UPGRADE = 2
    EMERGENCY = 3
    DIVIDEND = 4
    INCENTIVE = 5

class ProposalState(IntEnum):
    PENDING = 0
    ACTIVE = 1
    CANCELLED = 2
    DEFEATED = 3
    SUCCEEDED = 4
    EXECUTED = 5
    EXPIRED = 6

class VIBGovernanceClient:
    """VIBE治理客户端"""

    def __init__(self, web3: Web3, contract_address: str, abi: dict):
        self.web3 = web3
        self.contract = web3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=abi
        )

    async def get_voting_power(self, user: str) -> int:
        """获取用户投票权"""
        user = Web3.to_checksum_address(user)
        return await self.contract.functions.getVotingPower(user).call()

    async def create_proposal(
        self,
        proposal_type: ProposalType,
        title: str,
        description: str,
        target: str,
        data: bytes,
        from_address: str,
        private_key: str
    ) -> Tuple[int, str]:
        """
        创建治理提案

        注意: 需要足够的投票权达到提案门槛
        """
        from_address = Web3.to_checksum_address(from_address)
        target = Web3.to_checksum_address(target) if target else "0x0000000000000000000000000000000000000000"

        nonce = await self.web3.eth.get_transaction_count(from_address)
        tx = self.contract.functions.createProposal(
            proposal_type, title, description, target, data
        ).build_transaction({
            'from': from_address,
            'nonce': nonce,
            'chainId': 84532
        })

        signed = self.web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = await self.web3.eth.send_raw_transaction(signed.rawTransaction)

        # 解析事件获取proposalId
        receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)
        for log in receipt['logs']:
            try:
                event = self.contract.events.ProposalCreated().process_log(log)
                return event['args']['id'], tx_hash.hex()
            except:
                pass

        return None, tx_hash.hex()

    async def cast_vote(
        self,
        proposal_id: int,
        support: int,  # 0=反对, 1=支持, 2=弃权
        from_address: str,
        private_key: str
    ) -> str:
        """投票"""
        from_address = Web3.to_checksum_address(from_address)
        nonce = await self.web3.eth.get_transaction_count(from_address)

        tx = self.contract.functions.castVote(proposal_id, support).build_transaction({
            'from': from_address,
            'nonce': nonce,
            'chainId': 84532
        })

        signed = self.web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = await self.web3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()

    async def get_proposal(self, proposal_id: int) -> dict:
        """获取提案详情"""
        proposal = await self.contract.functions.getProposal(proposal_id).call()
        return {
            "id": proposal[0],
            "proposer": proposal[1],
            "proposal_type": ProposalType(proposal[2]),
            "state": ProposalState(proposal[3]),
            "title": proposal[4],
            "description": proposal[5],
            "target": proposal[6],
            "start_time": proposal[8],
            "end_time": proposal[9],
            "execute_time": proposal[10],
            "for_votes": proposal[11],
            "against_votes": proposal[12],
            "abstain_votes": proposal[13],
            "total_voters": proposal[14],
            "executed": proposal[15]
        }

    async def get_state(self, proposal_id: int) -> ProposalState:
        """获取提案状态"""
        state = await self.contract.functions.getState(proposal_id).call()
        return ProposalState(state)

    async def check_proposal_passed(self, proposal_id: int) -> bool:
        """检查提案是否通过"""
        return await self.contract.functions.checkProposalPassed(proposal_id).call()
```

---

### 4.11 合约依赖关系图（更新版）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           完整合约依赖关系                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                │
│  │ VIBEToken   │──────│ VIBStaking  │──────│ VIBIdentity │                │
│  │             │      │             │      │             │                │
│  │ - transfer  │      │ - stake()   │      │ - getAgent  │                │
│  │ - 0.8% tax  │      │ - getTier() │      │   Limit()   │                │
│  │             │      │             │      │             │                │
│  │ 税收分配:   │      │ 等级:       │      │ 限制:       │                │
│  │ 50% burn    │      │ Bronze      │      │ Bronze=1    │                │
│  │ 20% dividend│─────▶│ Silver      │─────▶│ Silver=3    │                │
│  │ 15% eco     │      │ Gold        │      │ Gold=10     │                │
│  │ 15% protocol│      │ Platinum    │      │ Platinum=50 │                │
│  └─────────────┘      └─────────────┘      └─────────────┘                │
│         │                    │                                              │
│         │                    │                                              │
│         ▼                    ▼                                              │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                │
│  │ VIBDividend │      │ AgentWallet │◄─────│AgentRegistry│                │
│  │             │      │ (每Agent一个)│      │             │                │
│  │ - claim()   │      │             │      │ - register()│                │
│  │ - 1天冷却   │      │ - execute   │      │ - isValid() │                │
│  └─────────────┘      │   Transfer()│      └─────────────┘                │
│                       │ - deposit() │                                       │
│                       └─────────────┘                                       │
│                              │                                              │
│         ┌────────────────────┼────────────────────┐                        │
│         │                    │                    │                        │
│         ▼                    ▼                    ▼                        │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                │
│  │VIBCollab    │      │ JointOrder  │      │VIBGovernance│                │
│  │             │      │             │      │             │                │
│  │ - 70%产出者 │      │ - 需求聚合  │      │ - 提案投票  │                │
│  │ - 20%贡献者 │      │ - 反向竞价  │      │ - 三权分立  │                │
│  │ - 10%协调者 │      │ - 资金托管  │      │ - UUPS升级  │                │
│  └─────────────┘      └─────────────┘      └─────────────┘                │
│                                                                             │
│  高级功能（可选集成）:                                                       │
│  ┌─────────────┐                                                           │
│  │ZKCredential │  - zk-SNARK凭证，需要链下证明生成                          │
│  └─────────────┘                                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 五、代码架构设计

### 5.1 目录结构

```
usmsb-sdk/src/usmsb_sdk/
├── blockchain/                      # 新增：区块链模块
│   ├── __init__.py                  # 统一入口 VIBEBlockchainClient
│   ├── config.py                    # 配置（合约地址、ABI路径等）
│   ├── web3_client.py               # Web3客户端封装
│   ├── contracts/                   # 合约客户端
│   │   ├── __init__.py
│   │   ├── base.py                  # 基础合约客户端
│   │   ├── vibe_token.py            # VIBEToken
│   │   ├── agent_wallet.py          # AgentWallet + Factory
│   │   ├── agent_registry.py        # AgentRegistry
│   │   ├── vib_identity.py          # VIBIdentity
│   │   ├── vib_staking.py           # VIBStaking
│   │   ├── vib_collaboration.py     # VIBCollaboration
│   │   ├── joint_order.py           # JointOrder
│   │   └── vib_dividend.py          # VIBDividend
│   ├── agent_manager.py             # Agent管理器（整合创建流程）
│   └── event_listener.py            # 事件监听器
│
├── api/rest/routers/
│   ├── blockchain.py                # 新增：区块链API
│   └── ...existing routers...
│
└── contracts/                       # 合约配置文件
    ├── deployments/
    │   └── latest.json              # 已部署合约地址
    └── abi/                         # ABI文件
        ├── VIBEToken.json
        ├── AgentWallet.json
        └── ...
```

### 5.2 统一客户端入口

```python
# usmsb_sdk/blockchain/__init__.py

from .web3_client import Web3Client
from .config import BlockchainConfig, StakeTier
from .contracts.vibe_token import VIBETokenClient
from .contracts.agent_wallet import AgentWalletFactory, AgentWalletClient
from .contracts.agent_registry import AgentRegistryClient
from .contracts.vib_identity import VIBIdentityClient
from .contracts.vib_staking import VIBStakingClient, LockPeriod
from .contracts.vib_collaboration import VIBCollaborationClient
from .contracts.joint_order import JointOrderClient
from .agent_manager import AgentManager

class VIBEBlockchainClient:
    """统一区块链客户端入口"""

    def __init__(self, config: BlockchainConfig = None):
        if config is None:
            config = BlockchainConfig()

        self.config = config
        self.web3 = Web3Client(config.rpc_url)

        # 加载ABI
        abis = self._load_abis(config.abi_path)

        # 初始化各合约客户端
        self.token = VIBETokenClient(
            self.web3, config.contracts['VIBEToken'], abis['VIBEToken']
        )
        self.registry = AgentRegistryClient(
            self.web3, config.contracts['AgentRegistry'], abis['AgentRegistry']
        )
        self.identity = VIBIdentityClient(
            self.web3, config.contracts['VIBIdentity'], abis['VIBIdentity']
        )
        self.staking = VIBStakingClient(
            self.web3, config.contracts['VIBStaking'], abis['VIBStaking']
        )
        self.collaboration = VIBCollaborationClient(
            self.web3, config.contracts['VIBCollaboration'], abis['VIBCollaboration']
        )
        self.order = JointOrderClient(
            self.web3, config.contracts['JointOrder'], abis['JointOrder']
        )

        # Agent管理器
        self.agent_manager = AgentManager(self)

        # Wallet工厂
        self.wallet_factory = AgentWalletFactory(
            self.web3,
            abis['AgentWallet']['bytecode'],
            abis['AgentWallet']['abi'],
            config.contracts
        )

    async def check_can_create_agent(self, owner: str) -> dict:
        """检查Owner是否可以创建新Agent"""
        limit = await self.identity.get_agent_limit(owner)
        current = await self.identity.get_user_agent_count(owner)
        return {
            "can_create": current < limit,
            "current": current,
            "limit": limit,
            "remaining": limit - current if current < limit else 0
        }

    async def get_agent_full_status(
        self,
        agent_address: str,
        wallet_address: str = None
    ) -> dict:
        """获取Agent完整状态"""
        # 如果没有wallet_address，需要从数据库获取
        if wallet_address is None:
            # TODO: 从数据库查询
            return None

        wallet = AgentWalletClient(self.web3, wallet_address, {})

        return {
            "agent_address": agent_address,
            "wallet_address": wallet_address,
            "balance": await wallet.get_balance_vibe(),
            "staking_tier": await wallet.get_staking_tier(),
            "daily_limit": await wallet.get_daily_limit(),
            "remaining_limit": await wallet.get_remaining_limit(),
            "is_valid_agent": await self.registry.is_valid_agent(wallet_address),
            "has_identity": await self.identity.is_registered(agent_address)
        }
```

---

## 六、私钥管理策略

### 6.1 涉及的私钥

| 私钥类型 | 用途 | 存储位置 |
|---------|------|---------|
| Owner私钥 | 部署AgentWallet、注册到Registry、充值、审批转账 | 用户钱包（MetaMask等）|
| Agent私钥 | 执行转账、请求大额转账 | Agent后端服务（安全存储）|

### 6.2 Agent私钥存储方案

```python
# usmsb_sdk/blockchain/key_management.py

import os
from cryptography.fernet import Fernet
import hashlib
import base64

class AgentKeyManager:
    """Agent私钥管理器"""

    def __init__(self, encryption_key: str = None):
        if encryption_key is None:
            encryption_key = os.environ.get('AGENT_KEY_ENCRYPTION_KEY')
            if encryption_key is None:
                raise ValueError("Encryption key not provided")

        # 派生加密密钥
        key = hashlib.sha256(encryption_key.encode()).digest()
        self.cipher = Fernet(base64.urlsafe_b64encode(key))

    def encrypt_private_key(self, private_key: str) -> str:
        """加密私钥"""
        return self.cipher.encrypt(private_key.encode()).decode()

    def decrypt_private_key(self, encrypted_key: str) -> str:
        """解密私钥"""
        return self.cipher.decrypt(encrypted_key.encode()).decode()

    def generate_agent_keypair(self) -> dict:
        """生成Agent密钥对"""
        from eth_account import Account
        account = Account.create()

        return {
            "address": account.address,
            "private_key": account.key.hex(),
            "private_key_encrypted": self.encrypt_private_key(account.key.hex())
        }
```

### 6.3 数据库更新

现有`agent_wallets`表需要添加字段：

```sql
ALTER TABLE agent_wallets ADD COLUMN agent_private_key_encrypted TEXT;
ALTER TABLE agent_wallets ADD COLUMN contract_tx_hash TEXT;
```

---

## 七、平台API设计

### 7.1 区块链API路由

```python
# usmsb_sdk/api/rest/routers/blockchain.py

from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/blockchain", tags=["Blockchain"])

# ========== Agent管理 ==========

@router.post("/agent/create")
async def create_agent(request: CreateAgentRequest):
    """
    创建新Agent（完整流程）

    流程:
    1. 检查Owner的Agent数量限制
    2. 生成Agent密钥对
    3. 部署AgentWallet合约
    4. 注册到AgentRegistry
    5. 注册VIBIdentity
    6. 初始充值（可选）
    7. 保存到数据库
    """

@router.get("/agent/{address}/status")
async def get_agent_status(address: str):
    """获取Agent完整状态"""

@router.get("/owner/{address}/limit")
async def get_owner_agent_limit(address: str):
    """获取Owner的Agent数量限制"""

# ========== 质押管理 ==========

@router.get("/staking/{address}/info")
async def get_staking_info(address: str):
    """获取质押信息"""

@router.post("/staking/{address}/stake")
async def stake_tokens(address: str, request: StakeRequest):
    """质押代币"""

# ========== 钱包操作 ==========

@router.post("/wallet/{address}/transfer")
async def execute_transfer(address: str, request: TransferRequest):
    """执行转账（Agent调用）"""

@router.post("/wallet/{address}/transfer/approve")
async def approve_transfer(address: str, request: ApproveRequest):
    """批准大额转账（Owner调用）"""

# ========== 协作管理 ==========

@router.post("/collaboration/project")
async def create_collaboration_project(request: CreateProjectRequest):
    """创建协作项目"""

@router.post("/collaboration/project/{project_id}/distribute")
async def distribute_revenue(project_id: str, request: DistributeRequest):
    """分发收入"""
```

---

## 7.2 事件监听器设计

事件监听器用于实时监控链上事件，更新本地数据库状态。

```python
# usmsb_sdk/blockchain/event_listener.py

import asyncio
from typing import Callable, Dict, List
from web3 import Web3
from web3.contract import Contract

class BlockchainEventListener:
    """区块链事件监听器"""

    def __init__(self, web3: Web3, contracts: Dict[str, Contract]):
        self.web3 = web3
        self.contracts = contracts
        self.handlers: Dict[str, List[Callable]] = {}
        self.running = False

    def register_handler(self, contract_name: str, event_name: str, handler: Callable):
        """注册事件处理器"""
        key = f"{contract_name}.{event_name}"
        if key not in self.handlers:
            self.handlers[key] = []
        self.handlers[key].append(handler)

    async def start(self, poll_interval: int = 5):
        """启动事件监听"""
        self.running = True
        last_block = await self.web3.eth.block_number

        while self.running:
            try:
                current_block = await self.web3.eth.block_number
                if current_block > last_block:
                    await self._process_blocks(last_block + 1, current_block)
                    last_block = current_block
                await asyncio.sleep(poll_interval)
            except Exception as e:
                print(f"Event listener error: {e}")
                await asyncio.sleep(poll_interval * 2)

    async def _process_blocks(self, from_block: int, to_block: int):
        """处理区块范围内的所有事件"""
        # VIBEToken 事件
        await self._process_token_events(from_block, to_block)

        # AgentWallet 事件
        await self._process_wallet_events(from_block, to_block)

        # AgentRegistry 事件
        await self._process_registry_events(from_block, to_block)

        # VIBStaking 事件
        await self._process_staking_events(from_block, to_block)

        # VIBGovernance 事件
        await self._process_governance_events(from_block, to_block)

    async def _process_token_events(self, from_block: int, to_block: int):
        """处理VIBEToken事件"""
        contract = self.contracts.get('VIBEToken')
        if not contract:
            return

        # Transfer事件
        transfer_filter = contract.events.Transfer.create_filter(
            from_block=from_block,
            to_block=to_block
        )
        for event in transfer_filter.get_all_entries():
            await self._dispatch('VIBEToken.Transfer', event)

    async def _process_wallet_events(self, from_block: int, to_block: int):
        """处理AgentWallet事件（需要遍历所有已部署的钱包）"""
        # 由于每个Agent有独立的Wallet合约，需要从数据库获取所有钱包地址
        # 这里简化处理，实际需要根据业务需求实现
        pass

    async def _process_registry_events(self, from_block: int, to_block: int):
        """处理AgentRegistry事件"""
        contract = self.contracts.get('AgentRegistry')
        if not contract:
            return

        # AgentRegistered事件
        registered_filter = contract.events.AgentRegistered.create_filter(
            from_block=from_block,
            to_block=to_block
        )
        for event in registered_filter.get_all_entries():
            await self._dispatch('AgentRegistry.AgentRegistered', event)

        # AgentUnregistered事件
        unregistered_filter = contract.events.AgentUnregistered.create_filter(
            from_block=from_block,
            to_block=to_block
        )
        for event in unregistered_filter.get_all_entries():
            await self._dispatch('AgentRegistry.AgentUnregistered', event)

    async def _process_staking_events(self, from_block: int, to_block: int):
        """处理VIBStaking事件"""
        contract = self.contracts.get('VIBStaking')
        if not contract:
            return

        # Staked事件
        staked_filter = contract.events.Staked.create_filter(
            from_block=from_block,
            to_block=to_block
        )
        for event in staked_filter.get_all_entries():
            await self._dispatch('VIBStaking.Staked', event)

        # Unstaked事件
        unstaked_filter = contract.events.Unstaked.create_filter(
            from_block=from_block,
            to_block=to_block
        )
        for event in unstaked_filter.get_all_entries():
            await self._dispatch('VIBStaking.Unstaked', event)

    async def _process_governance_events(self, from_block: int, to_block: int):
        """处理VIBGovernance事件"""
        contract = self.contracts.get('VIBGovernance')
        if not contract:
            return

        # ProposalCreated事件
        proposal_filter = contract.events.ProposalCreated.create_filter(
            from_block=from_block,
            to_block=to_block
        )
        for event in proposal_filter.get_all_entries():
            await self._dispatch('VIBGovernance.ProposalCreated', event)

        # VoteCast事件
        vote_filter = contract.events.VoteCast.create_filter(
            from_block=from_block,
            to_block=to_block
        )
        for event in vote_filter.get_all_entries():
            await self._dispatch('VIBGovernance.VoteCast', event)

    async def _dispatch(self, event_key: str, event):
        """分发事件到处理器"""
        handlers = self.handlers.get(event_key, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                print(f"Handler error for {event_key}: {e}")

    def stop(self):
        """停止监听"""
        self.running = False
```

### 7.3 关键事件列表

| 合约 | 事件名 | 参数 | 用途 |
|------|--------|------|------|
| VIBEToken | Transfer | from, to, value | 监控代币转账 |
| VIBEToken | Approval | owner, spender, value | 监控授权 |
| AgentWallet | Deposited | wallet, amount, from | 充值监控 |
| AgentWallet | TransferExecuted | wallet, to, amount | 转账执行 |
| AgentWallet | TransferRequested | wallet, requestId, to, amount | 大额请求 |
| AgentWallet | TransferApproved | wallet, requestId | 大额审批 |
| AgentRegistry | AgentRegistered | agentWallet, owner | Agent注册 |
| AgentRegistry | AgentUnregistered | agentWallet | Agent注销 |
| VIBStaking | Staked | user, amount, tier | 质押事件 |
| VIBStaking | Unstaked | user, amount | 取消质押 |
| VIBStaking | RewardClaimed | user, amount | 奖励领取 |
| VIBDividend | DividendClaimed | user, amount | 分红领取 |
| VIBGovernance | ProposalCreated | id, proposer, proposalType | 提案创建 |
| VIBGovernance | VoteCast | proposalId, voter, forVotes, againstVotes | 投票 |

---

## 八、实现计划

### Phase 1: 基础设施（2天）

| 任务 | 文件 | 说明 |
|------|------|------|
| 1.1 | `blockchain/config.py` | 配置文件 |
| 1.2 | `blockchain/web3_client.py` | Web3客户端封装 |
| 1.3 | `contracts/abi/*.json` | ABI文件提取 |
| 1.4 | `contracts/base.py` | 基础合约客户端 |

### Phase 2: 核心合约（3天）

| 任务 | 文件 | 说明 |
|------|------|------|
| 2.1 | `contracts/vibe_token.py` | VIBEToken客户端 |
| 2.2 | `contracts/agent_registry.py` | AgentRegistry客户端 |
| 2.3 | `contracts/vib_staking.py` | VIBStaking客户端 |
| 2.4 | `contracts/vib_identity.py` | VIBIdentity客户端 |
| 2.5 | `contracts/agent_wallet.py` | AgentWallet + Factory |

### Phase 3: 业务合约（2天）

| 任务 | 文件 | 说明 |
|------|------|------|
| 3.1 | `contracts/vib_collaboration.py` | VIBCollaboration客户端 |
| 3.2 | `contracts/joint_order.py` | JointOrder客户端 |
| 3.3 | `contracts/vib_dividend.py` | VIBDividend客户端 |
| 3.4 | `contracts/vib_governance.py` | VIBGovernance客户端（可选） |

### Phase 4: 整合与管理（2天）

| 任务 | 文件 | 说明 |
|------|------|------|
| 4.1 | `agent_manager.py` | Agent创建流程整合 |
| 4.2 | `__init__.py` | 统一客户端入口 |
| 4.3 | `key_management.py` | 私钥管理（详见[AGENT_KEY_MANAGEMENT.md](./AGENT_KEY_MANAGEMENT.md)） |
| 4.4 | `event_listener.py` | 事件监听器 |

### Phase 5: 平台API（2天）

| 任务 | 文件 | 说明 |
|------|------|------|
| 5.1 | `routers/blockchain.py` | 区块链API路由 |
| 5.2 | 更新现有路由 | 集成区块链功能 |

### Phase 6: 测试与文档（2天）

| 任务 | 说明 |
|------|------|
| 6.1 | 单元测试 |
| 6.2 | 集成测试 |
| 6.3 | API文档更新 |

### 总计：13天

---

## 九、审查发现的问题与修正

### 9.1 Agent私钥需求

**问题**: 原文档认为Agent不需要私钥，但AgentWallet的executeTransfer只能由Agent地址调用。

**修正**: Agent后端服务需要持有私钥来执行转账。

### 9.2 Agent数量限制来源

**问题**: 原文档说限制在VIBStaking中。

**修正**: 限制在VIBIdentity中，VIBIdentity调用VIBStaking获取等级后返回限制。

### 9.3 AgentRegistry.registerAgent调用者

**问题**: 需要明确谁调用registerAgent。

**修正**: msg.sender被记录为Owner，所以必须由Owner调用或使用Owner私钥。

### 9.4 数据库已有表结构

**问题**: 文档未提及数据库变更。

**修正**: 现有`agent_wallets`表已存在，只需添加少量字段。

### 9.5 ZKCredential集成复杂度

**问题**: ZKCredential需要链下生成zk证明。

**建议**: 初期不集成，待需要隐私保护凭证时再实现。

---

## 十、前端集成需求

### 10.1 钱包连接（必须）

前端需要集成Web3钱包，让用户能够：
- 连接MetaMask等钱包
- 切换到正确的网络（Base Sepolia/Base Mainnet）
- 签名交易

```typescript
// frontend/src/utils/wallet.ts

// 支持的钱包
export const SUPPORTED_WALLETS = ['metamask', 'walletconnect', 'coinbase'];

// 网络配置
export const NETWORK_CONFIG = {
  testnet: {
    chainId: '0x14A34',  // 84532 hex
    chainName: 'Base Sepolia',
    rpcUrls: ['https://sepolia.base.org'],
    blockExplorerUrls: ['https://sepolia.basescan.org'],
    nativeCurrency: {
      name: 'ETH',
      symbol: 'ETH',
      decimals: 18
    }
  },
  mainnet: {
    chainId: '0x2105',  // 8453 hex
    chainName: 'Base',
    rpcUrls: ['https://mainnet.base.org'],
    blockExplorerUrls: ['https://basescan.org'],
    nativeCurrency: {
      name: 'ETH',
      symbol: 'ETH',
      decimals: 18
    }
  }
};

// 切换网络
async function switchNetwork(network: 'testnet' | 'mainnet') {
  const config = NETWORK_CONFIG[network];
  try {
    await window.ethereum.request({
      method: 'wallet_switchEthereumChain',
      params: [{ chainId: config.chainId }]
    });
  } catch (switchError) {
    // 网络未添加，添加网络
    if (switchError.code === 4902) {
      await window.ethereum.request({
        method: 'wallet_addEthereumChain',
        params: [config]
      });
    }
  }
}
```

### 10.2 新增页面/组件

| 页面/组件 | 功能 | 优先级 |
|----------|------|--------|
| **钱包连接组件** | 连接/断开钱包、显示地址和余额 | P0 |
| **VIBE余额显示** | 显示用户VIBE余额 | P0 |
| **质押管理页** | 质押VIBE、查看等级、领取奖励 | P0 |
| **Agent管理页** | 创建Agent、查看Agent列表、管理钱包 | P0 |
| **Agent钱包操作** | 充值、转账、查看交易历史 | P1 |
| **大额审批组件** | Owner审批大额转账请求 | P1 |
| **交易状态组件** | 显示pending/success/failed状态 | P1 |
| **协作分成页** | 创建协作项目、查看分成 | P2 |
| **治理投票页** | 查看提案、投票 | P2 |

### 10.3 新增API调用

```typescript
// frontend/src/api/blockchain.ts

// 获取用户区块链状态
export async function getUserBlockchainStatus(address: string) {
  return await fetch(`/api/blockchain/user/${address}/status`);
}

// 获取Agent限制信息
export async function getAgentLimit(address: string) {
  return await fetch(`/api/blockchain/owner/${address}/limit`);
}

// 创建Agent（后端执行链上操作）
export async function createAgent(data: CreateAgentRequest) {
  return await fetch('/api/blockchain/agent/create', {
    method: 'POST',
    body: JSON.stringify(data)
  });
}

// 获取钱包状态
export async function getWalletStatus(walletAddress: string) {
  return await fetch(`/api/blockchain/wallet/${walletAddress}/status`);
}

// 请求大额转账审批
export async function requestLargeTransfer(
  walletAddress: string,
  data: TransferRequest
) {
  return await fetch(`/api/blockchain/wallet/${walletAddress}/transfer/request`, {
    method: 'POST',
    body: JSON.stringify(data)
  });
}
```

### 10.4 前端架构调整

```
frontend/src/
├── components/
│   ├── wallet/
│   │   ├── WalletConnect.tsx      # 钱包连接按钮
│   │   ├── WalletModal.tsx        # 钱包选择弹窗
│   │   ├── NetworkSwitch.tsx      # 网络切换
│   │   └── AddressDisplay.tsx     # 地址显示
│   ├── blockchain/
│   │   ├── BalanceCard.tsx        # 余额卡片
│   │   ├── StakingPanel.tsx       # 质押面板
│   │   ├── TierBadge.tsx          # 等级徽章
│   │   ├── TransactionStatus.tsx  # 交易状态
│   │   └── TransferForm.tsx       # 转账表单
│   └── agent/
│       ├── AgentCard.tsx          # Agent卡片
│       ├── AgentWalletPanel.tsx   # Agent钱包面板
│       ├── AgentLimitDisplay.tsx  # Agent数量限制显示
│       └── CreateAgentModal.tsx   # 创建Agent弹窗
├── pages/
│   ├── WalletPage.tsx             # 钱包页面
│   ├── StakingPage.tsx            # 质押页面
│   ├── AgentsPage.tsx             # Agent管理页面
│   └── GovernancePage.tsx         # 治理页面（可选）
├── hooks/
│   ├── useWallet.ts               # 钱包hook
│   ├── useBalance.ts              # 余额hook
│   ├── useStaking.ts              # 质押hook
│   └── useTransaction.ts          # 交易hook
├── utils/
│   ├── wallet.ts                  # 钱包工具
│   ├── contracts.ts               # 合约地址/ABI
│   └── format.ts                  # 格式化工具（wei转换等）
└── store/
    └── blockchainSlice.ts         # 区块链状态管理
```

### 10.5 关键UI流程

#### Agent创建流程（前端）

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        前端Agent创建流程                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. 用户点击"创建Agent"                                                  │
│         │                                                               │
│         ▼                                                               │
│  2. 检查钱包连接状态                                                     │
│         │                                                               │
│         ├── 未连接 → 弹出钱包连接                                        │
│         │                                                               │
│         ▼                                                               │
│  3. 检查Agent数量限制                                                    │
│         │                                                               │
│         ├── 已达上限 → 显示"升级质押等级以创建更多Agent"                  │
│         │                                                               │
│         ▼                                                               │
│  4. 填写Agent信息表单                                                    │
│         │  - Agent名称                                                   │
│         │  - Agent描述/能力                                              │
│         │  - 初始充值金额（可选）                                         │
│         │                                                               │
│         ▼                                                               │
│  5. 后端创建Agent                                                        │
│         │  - 生成Agent密钥对                                             │
│         │  - 部署AgentWallet合约                                         │
│         │  - 注册到Registry                                              │
│         │  - 保存到数据库                                                │
│         │                                                               │
│         ▼                                                               │
│  6. 如果有初始充值                                                       │
│         │  - 弹出MetaMask签名请求                                        │
│         │  - approve VIBEToken                                           │
│         │  - deposit to AgentWallet                                      │
│         │                                                               │
│         ▼                                                               │
│  7. 显示创建成功，跳转到Agent详情页                                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 10.6 前端依赖安装

```bash
cd frontend

# Web3相关
npm install ethers viem @wagmi/core wagmi

# 或者使用 web3.js
npm install web3

# 状态管理（如果还没有）
npm install zustand  # 或 redux-toolkit

# UI组件（可选）
npm install @headlessui/react @heroicons/react
```

### 10.7 环境变量配置

```bash
# frontend/.env.development
VITE_NETWORK=testnet
VITE_VIBE_TOKEN_ADDRESS=0x91d8C3084b4fd21A04fA3584BFE357F378938dbc
VITE_API_BASE_URL=http://localhost:8000

# frontend/.env.production
VITE_NETWORK=mainnet
VITE_VIBE_TOKEN_ADDRESS=主网地址
VITE_API_BASE_URL=https://api.example.com
```

### 10.8 前端实现优先级

| 优先级 | 功能 | 说明 |
|--------|------|------|
| **P0** | 钱包连接 | 必须先能连上链 |
| **P0** | VIBE余额显示 | 基础信息展示 |
| **P0** | 质押管理 | Owner必须质押才能创建Agent |
| **P0** | Agent管理 | 核心业务功能 |
| **P1** | Agent钱包操作 | 充值、转账、审批 |
| **P1** | 交易状态展示 | 用户体验优化 |
| **P2** | 协作分成 | 业务扩展功能 |
| **P2** | 治理投票 | 社区功能 |

---

## 十一、错误处理与异常

### 11.1 常见合约错误码

| 合约 | 错误信息 | 原因 | 处理方式 |
|------|---------|------|---------|
| AgentWallet | "caller is not agent" | 非Agent地址调用executeTransfer | 检查调用者私钥 |
| AgentWallet | "exceeds max per tx" | 单笔超限 | 拆分或请求审批 |
| AgentWallet | "exceeds daily limit" | 日限额超限 | 等待次日或升级质押 |
| AgentWallet | "recipient not in whitelist" | 目标不在白名单 | 添加白名单或转给系统Agent |
| AgentRegistry | "already registered" | Agent已注册 | 跳过注册 |
| VIBIdentity | "exceeds agent limit" | 超过Agent数量限制 | 升级质押等级 |
| VIBStaking | "insufficient stake" | 质押量不足 | 增加质押 |
| VIBDividend | "claim cooldown not reached" | 未到领取冷却期 | 等待1天 |

### 11.2 错误处理模式

```python
class BlockchainError(Exception):
    """区块链操作基础异常"""
    pass

class InsufficientBalanceError(BlockchainError):
    """余额不足"""
    pass

class ExceedsLimitError(BlockchainError):
    """超限异常"""
    pass

class NotAuthorizedError(BlockchainError):
    """权限不足"""
    pass

async def safe_execute_transfer(wallet, to, amount, agent_key):
    """安全执行转账，带错误处理"""
    try:
        # 先检查限额
        remaining = await wallet.get_remaining_limit()
        if amount > remaining:
            raise ExceedsLimitError(f"Amount {amount} exceeds remaining limit {remaining}")

        # 检查余额
        balance = await wallet.get_balance()
        if amount > balance:
            raise InsufficientBalanceError(f"Amount {amount} exceeds balance {balance}")

        # 执行转账
        tx_hash = await wallet.execute_transfer(to, amount, agent_key)
        return tx_hash

    except Exception as e:
        # 解析合约错误
        error_msg = str(e)
        if "caller is not agent" in error_msg:
            raise NotAuthorizedError("Only agent can execute transfer")
        elif "exceeds" in error_msg.lower():
            raise ExceedsLimitError(error_msg)
        else:
            raise BlockchainError(f"Transfer failed: {error_msg}")
```

---

## 十二、Gas优化建议

### 12.1 批量操作

```python
# 批量领取分红
async def batch_claim_dividends(dividend_client, users: List[str], owner_key: str):
    """批量领取分红，节省Gas"""
    return await dividend_client.batch_claim(users, owner_key)

# 批量检查凭证过期
async def batch_check_expiry(credential_client, credential_ids: List[str]):
    """批量检查凭证过期"""
    return await credential_client.batch_check_expiry(credential_ids)
```

### 12.2 交易估算

```python
async def estimate_gas(web3, contract, method_name: str, *args, from_address: str) -> int:
    """估算Gas费用"""
    method = getattr(contract.functions, method_name)
    gas_estimate = await method(*args).estimate_gas({'from': from_address})
    # 增加20%安全余量
    return int(gas_estimate * 1.2)

async def get_gas_price(web3) -> dict:
    """获取当前Gas价格"""
    latest_block = await web3.eth.get_block('latest')
    base_fee = latest_block['baseFeePerGas']

    return {
        "base_fee": base_fee,
        "priority_fee": web3.to_wei(1, 'gwei'),  # 1 Gwei 优先费
        "max_fee": base_fee + web3.to_wei(2, 'gwei')
    }
```

### 12.3 EIP-1559交易构建

```python
async def build_eip1559_transaction(
    web3,
    contract,
    method_name: str,
    args: tuple,
    from_address: str
) -> dict:
    """构建EIP-1559交易"""
    gas_price = await get_gas_price(web3)
    nonce = await web3.eth.get_transaction_count(from_address)

    method = getattr(contract.functions, method_name)
    tx = method(*args).build_transaction({
        'from': from_address,
        'nonce': nonce,
        'chainId': 84532,
        'maxFeePerGas': gas_price['max_fee'],
        'maxPriorityFeePerGas': gas_price['priority_fee'],
        'type': 2  # EIP-1559
    })

    return tx
```

---

## 十三、附录

### A. 合约ABI获取

```bash
# 从编译产物提取ABI
cd contracts
npx hardhat compile
# ABI位于 artifacts/src/<ContractName>.sol/<ContractName>.json
```

### B. 测试网络代币获取

```bash
# Base Sepolia Faucet
https://faucet.triangleplatform.com/base/sepolia
```

### C. 相关文档

| 文档 | 说明 |
|------|------|
| [AGENT_KEY_MANAGEMENT.md](./AGENT_KEY_MANAGEMENT.md) | Agent私钥管理方案（详细版） |
| [PERMISSION_SYSTEM.md](./PERMISSION_SYSTEM.md) | 权限系统设计 |

### D. 合约源码位置

```
contracts/src/
├── VIBEToken.sol           # 代币合约
├── AgentWallet.sol         # Agent钱包合约
├── AgentRegistry.sol       # Agent注册表
├── VIBIdentity.sol         # 身份认证
├── VIBStaking.sol          # 质押合约
├── VIBCollaboration.sol    # 协作分成
├── JointOrder.sol          # 联合订单
├── VIBDividend.sol         # 分红合约
├── ZKCredential.sol        # 零知识凭证
└── VIBGovernance.sol       # 治理合约
```

---

**文档结束**

> 本文档为智能合约集成的设计方案（v1.3.0），已根据代码审查修正问题。
>
> **更新历史**:
> - v1.0.0: 初始版本
> - v1.1.0: 基于代码审查修正Agent私钥、数量限制等问题
> - v1.2.0: 补充VIBDividend/ZKCredential/VIBGovernance合约分析，添加事件监听器、错误处理、Gas优化
> - v1.3.0: 添加多网络配置设计（解决chainId硬编码问题），添加前端集成需求分析
