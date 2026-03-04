# Agent私钥管理方案

> 版本: 1.0.0
> 日期: 2026-03-03
> 状态: 已确认

---

## 一、核心概念

### 1.1 AgentWallet合约结构

```
AgentWallet合约存储：
- owner: Owner的EOA地址（所有者）
- agent: Agent的EOA地址（Agent后端服务地址）
- vibeToken: VIBEToken合约地址
- 余额: 合约地址上的VIBE代币
```

### 1.2 为什么需要Agent私钥

```solidity
// AgentWallet.sol
modifier onlyAgent() {
    require(msg.sender == agent, "AgentWallet: caller is not agent");
    _;
}

function executeTransfer(address to, uint256 amount) external onlyAgent {
    vibeToken.safeTransfer(to, amount);
}
```

**关键点**：
- `executeTransfer`只能由Agent地址调用
- 在以太坊上，调用合约方法需要发送交易
- 发送交易需要用私钥签名
- **没有私钥就无法调用合约**

### 1.3 Agent交易的发起者

```
Agent后端服务（程序） → 用私钥签名 → 调用AgentWallet合约 → 合约执行转账

整个过程：无人参与，全自动，24/7运行
```

---

## 二、私钥管理方案

### 2.1 采用混合方案

| 角色 | 职责 |
|-----|------|
| **平台** | 1. 创建Agent时生成密钥对<br>2. 加密私钥传给Agent服务<br>3. 不保留明文私钥（可选保留加密备份） |
| **Agent服务** | 1. 接收并安全存储私钥<br>2. 日常转账自主执行<br>3. 大额转账自动发起审批 |

### 2.2 安全机制（合约层已实现）

| 机制 | 说明 |
|-----|------|
| 日限额 | 即使私钥泄露，损失可控（默认1000 VIBE/天） |
| 单笔限额 | 默认500 VIBE/笔 |
| 大额审批 | 超过限额需要Owner确认 |
| 白名单 | 只能转给系统内Agent或白名单地址 |
| 紧急暂停 | Owner可随时暂停钱包 |
| 时间锁 | emergencyWithdraw需要2天等待 |

### 2.3 Agent创建流程

```
Step 1: 平台生成密钥对（链下）
┌────────────────────────────────────────────────────────────┐
│ from eth_account import Account                            │
│ account = Account.create()                                 │
│ agent_address = account.address      # 如 0x1234...       │
│ agent_private_key = account.key.hex() # 私钥               │
└────────────────────────────────────────────────────────────┘
                         │
                         ▼
Step 2: 部署AgentWallet合约（链上）
┌────────────────────────────────────────────────────────────┐
│ constructor(                                               │
│     _owner: owner的EOA地址,                                │
│     _agent: agent的EOA地址,  ← 只传地址，不传私钥          │
│     _vibeToken: VIBEToken地址,                             │
│     _registry: AgentRegistry地址,                          │
│     _stakingContract: VIBStaking地址                       │
│ )                                                          │
└────────────────────────────────────────────────────────────┘
                         │
                         ▼
Step 3: 私钥传递给Agent服务（安全通道）
┌────────────────────────────────────────────────────────────┐
│ - 加密私钥                                                 │
│ - 通过安全API或消息队列传递                                 │
│ - Agent服务解密后存入内存（不落盘）                        │
└────────────────────────────────────────────────────────────┘
                         │
                         ▼
Step 4: Agent服务自主运营
┌────────────────────────────────────────────────────────────┐
│ - 持有私钥，自主签名交易                                   │
│ - 限额内转账自动执行                                       │
│ - 大额转账自动请求Owner审批                                │
│ - 7x24小时无人值守运行                                     │
└────────────────────────────────────────────────────────────┘
```

---

## 三、Agent转账流程（Agent A → Agent B）

```
┌─────────────────────────────────────────────────────────────────────────┐
│  交易前状态:                                                            │
│  - Agent A Wallet: 0xContractA, 余额1000 VIBE                          │
│  - Agent B Wallet: 0xContractB, 余额500 VIBE                           │
│  - Agent A私钥: 由Agent A服务持有                                       │
└─────────────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 1: Agent A服务发起转账                                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Agent A服务（程序自动执行）:                                     │   │
│  │ - 决定转账: 100 VIBE 给 Agent B                                 │   │
│  │ - 构建交易: executeTransfer(0xContractB, 100VIBE)               │   │
│  │ - 用私钥签名: msg.sender = 0x111... (Agent A地址)               │   │
│  │ - 发送交易到区块链                                              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 2: AgentWallet A合约执行                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 验证: msg.sender == agent ✓                                     │   │
│  │ 检查: 100 VIBE <= maxPerTx ✓                                    │   │
│  │ 检查: 100 VIBE <= remainingDailyLimit ✓                         │   │
│  │ 执行: vibeToken.safeTransfer(0xContractB, 100VIBE)              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  交易后状态:                                                            │
│  - Agent A Wallet: 0xContractA, 余额900 VIBE                           │
│  - Agent B Wallet: 0xContractB, 余额600 VIBE                           │
└─────────────────────────────────────────────────────────────────────────┘
```

**关键理解**：
- VIBE从合约地址转出（0xContractA → 0xContractB）
- msg.sender是Agent的EOA地址（需要私钥签名）
- 合约验证msg.sender == agent才允许执行

---

## 四、私钥丢失恢复方案

### 4.1 当前限制

**AgentWallet合约中没有`setAgent`方法，Owner无法直接更换Agent地址。**

Owner能做的：
- `updateLimits()` - 更新限额
- `updateWhitelist()` - 更新白名单
- `pause()/unpause()` - 暂停/恢复
- `emergencyWithdraw()` - 紧急提取（2天时间锁）

Owner不能做的：
- ❌ 更换Agent地址
- ❌ 代Agent执行转账

### 4.2 恢复流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Agent私钥丢失恢复流程                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Step 1: Owner启动紧急提取（需2天时间锁）                               │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ // 第一天                                                         │  │
│  │ AgentWallet.emergencyWithdraw(                                   │  │
│  │     token: VIBEToken地址,                                        │  │
│  │     to: owner地址,                                               │  │
│  │     amount: 全部余额                                             │  │
│  │ )                                                                │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              │                                          │
│                              ▼ 等待2天                                  │
│                                                                         │
│  Step 2: Owner确认提取                                                  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ // 第三天                                                         │  │
│  │ AgentWallet.confirmEmergencyWithdraw()                           │  │
│  │ // 资金从旧钱包转到Owner地址                                      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              │                                          │
│                              ▼                                          │
│  Step 3: 创建新的AgentWallet                                            │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ 1. 生成新的Agent密钥对（新地址+新私钥）                           │  │
│  │ 2. 部署新的AgentWallet合约                                        │  │
│  │ 3. 注册到AgentRegistry                                            │  │
│  │ 4. Owner把钱充值到新钱包                                          │  │
│  │ 5. 把新私钥传给Agent服务                                          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              │                                          │
│                              ▼                                          │
│  Step 4: 清理和更新                                                     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ - 更新数据库中的钱包地址                                          │  │
│  │ - 通知相关方地址变更                                              │  │
│  │ - Agent服务使用新的私钥                                           │  │
│  │ - 旧钱包作废（余额已清空）                                        │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.3 恢复成本

| 成本项 | 说明 |
|-------|------|
| 时间 | 至少2天（时间锁） |
| Gas费 | emergencyWithdraw + 部署新合约 + 充值 |
| 地址变更 | Wallet地址改变，需要更新多处 |
| 操作复杂度 | 需要Owner手动操作 |

### 4.4 预防措施

为避免私钥丢失，建议：

1. **私钥备份**：平台保留加密的私钥备份
2. **安全存储**：Agent服务使用专业密钥管理（如HashiCorp Vault）
3. **多重备份**：私钥分片存储在不同位置
4. **监控告警**：监控Agent服务状态，异常时及时通知

---

## 五、代码实现参考

### 5.1 平台侧 - 创建Agent

```python
from eth_account import Account
from cryptography.fernet import Fernet

class AgentCreator:
    def __init__(self, encryption_key: str):
        self.cipher = Fernet(encryption_key)

    def create_agent(self, owner_address: str) -> dict:
        # 1. 生成密钥对
        account = Account.create()
        agent_address = account.address
        agent_private_key = account.key.hex()

        # 2. 部署AgentWallet合约
        wallet_address = await self.deploy_wallet(owner_address, agent_address)

        # 3. 加密私钥
        encrypted_key = self.cipher.encrypt(agent_private_key.encode()).decode()

        # 4. 传给Agent服务
        await self.send_to_agent(agent_address, encrypted_key)

        # 5. 可选：保留加密备份用于恢复
        await self.backup_key(agent_address, encrypted_key)

        return {
            "agent_address": agent_address,
            "wallet_address": wallet_address
        }
```

### 5.2 Agent服务侧 - 使用私钥

```python
class AgentWalletClient:
    def __init__(self, wallet_address: str):
        self.wallet_address = wallet_address
        self.private_key = None  # 内存中，不落盘

    def load_key(self, encrypted_key: str, cipher: Fernet):
        """启动时加载私钥"""
        decrypted = cipher.decrypt(encrypted_key.encode()).decode()
        self.private_key = decrypted

    async def transfer(self, to: str, amount: int) -> str:
        """自主执行转账"""
        if not self.private_key:
            raise Exception("Private key not loaded")

        # 构建并签名交易（自动，无人参与）
        tx = self.contract.functions.executeTransfer(to, amount).build_transaction({
            'from': self.agent_address,
            'nonce': await self.web3.eth.get_transaction_count(self.agent_address),
            'chainId': 84532
        })

        signed = self.web3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = await self.web3.eth.send_raw_transaction(signed.rawTransaction)

        return tx_hash.hex()
```

### 5.3 Owner侧 - 紧急恢复

```python
class WalletRecovery:
    async def recover_lost_key(self, wallet_address: str, owner_key: str) -> dict:
        """私钥丢失后的恢复流程"""

        # Step 1: 启动紧急提取
        wallet = AgentWalletClient(wallet_address)
        balance = await wallet.get_balance()

        # 第一天：发起请求
        await wallet.initiate_emergencyWithdraw(
            token=VIBE_TOKEN_ADDRESS,
            to=owner_address,
            amount=balance,
            owner_private_key=owner_key
        )

        return {
            "status": "waiting",
            "message": "等待2天后调用confirm_emergency_withdraw",
            "effective_time": datetime.now() + timedelta(days=2)
        }

    async def confirm_and_recreate(
        self,
        old_wallet: str,
        owner_address: str,
        owner_key: str
    ) -> dict:
        """确认提取并创建新钱包"""

        # Step 2: 确认提取（2天后）
        await wallet.confirm_emergency_withdraw(owner_key)

        # Step 3: 创建新的AgentWallet
        new_agent = Account.create()
        new_wallet = await self.deploy_wallet(owner_address, new_agent.address)

        # Step 4: 把钱充值到新钱包
        await self.token.approve(new_wallet, balance, owner_key)
        await self.wallet_deposit(new_wallet, balance, owner_key)

        return {
            "new_agent_address": new_agent.address,
            "new_agent_private_key": new_agent.key.hex(),
            "new_wallet_address": new_wallet
        }
```

---

## 六、安全最佳实践

### 6.1 私钥存储

| 存储方式 | 安全级别 | 适用场景 |
|---------|---------|---------|
| 明文配置文件 | ❌ 低 | 禁止使用 |
| 环境变量 | ⚠️ 中低 | 开发测试 |
| 加密配置文件 | ⚠️ 中 | 简单场景 |
| 专业密钥管理（Vault） | ✅ 高 | 生产环境 |
| 硬件安全模块（HSM） | ✅ 最高 | 金融级别 |

### 6.2 操作建议

1. **最小权限**：Agent私钥只能调用executeTransfer，不能管理钱包设置
2. **限额控制**：根据业务需要设置合理的日限额
3. **监控告警**：监控异常转账行为
4. **定期审计**：定期检查Agent钱包状态
5. **备份策略**：保留加密私钥备份，用于灾难恢复

---

## 七、FAQ

### Q1: Agent私钥和Owner私钥有什么区别？

| 私钥 | 能做什么 | 限制 |
|-----|---------|------|
| Owner私钥 | 充值、审批大额、管理设置、紧急提取 | 不能执行日常转账 |
| Agent私钥 | 执行日常转账（限额内）、请求大额 | 受限额和白名单限制 |

### Q2: Agent私钥泄露怎么办？

1. Owner立即调用`pause()`暂停钱包
2. 启动emergencyWithdraw流程
3. 等待2天后提取资金
4. 创建新的AgentWallet

### Q3: 为什么emergencyWithdraw需要2天？

这是安全设计（时间锁），防止：
- Owner私钥被盗后立即转走资金
- 恶意Owner突然跑路

2天的窗口期让相关方有时间反应和干预。

### Q4: Agent服务重启后私钥从哪里来？

有两种方案：
1. **从加密存储加载**：平台启动时传入加密私钥，Agent解密后使用
2. **从备份恢复**：Agent从安全备份位置读取加密私钥

---

## 八、相关文档

- [智能合约集成方案](./BLOCKCHAIN_INTEGRATION.md)
- [AgentWallet合约源码](../contracts/src/AgentWallet.sol)

---

**文档结束**
