# 质押系统优化设计方案

## Context（背景）

当前 `/app/onboarding` 页面的质押功能存在以下问题：
1. **无权限校验**：质押时没有检查用户余额、是否已质押等条件
2. **完善资料 API 500 错误**：`auth.py` 中 `request.hourly_rate` 应为 `request.hourlyRate`
3. **文档链接无效**：`href="#"` 没有实际跳转地址
4. **缺少质押管理功能**：用户无法撤回质押、无法后续补质押
5. **缺少全局开关**：无法在测试/单节点模式下关闭质押限制

本方案旨在解决以上问题，建立完整的质押系统。

---

## 一、质押状态机设计

```
┌─────────────────────────────────────────────────────────────────┐
│                      用户质押状态流转                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   [未连接] ──连接钱包──> [已连接/未质押]                        │
│                              │                                  │
│                              ├──质押──> [已质押]                 │
│                              │          │                       │
│                              │          ├──增加质押──> [已质押]  │
│                              │          │    (金额累加)         │
│                              │          │                       │
│                              │          └──申请撤回──> [解锁中] │
│                              │                    │              │
│                              │                    ├──7天后──> [已撤回] ≈ [未质押] │
│                              │                    │              │
│                              │                    └──取消撤回──> [已质押] │
│                              │                                  │
│                              └──跳过──> [已连接/未质押]          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 状态定义

| 状态 | 说明 | stake 值 | 可执行操作 |
|------|------|----------|-----------|
| `none` | 未质押 | 0 | 质押 |
| `staked` | 已质押 | >= 100 | 增加质押、申请撤回 |
| `unstaking` | 解锁中 | >= 100 (锁定) | 取消撤回、等待解锁 |
| `unlocked` | 已解锁 | 0 | 重新质押 |

---

## 二、AI Agent 独立钱包设计（基于 ERC-4337 智能合约钱包）

> **已创建合约文件位置**: `contracts/src/`

### 2.0 技术选型说明

**选择 ERC-4337 智能合约钱包方案**，基于以下考量：
- Base 链完全支持 ERC-4337
- 可实现权限控制（限额、白名单）
- 无需私钥托管，安全可控
- 支持完全自动化交易

### 2.1 概述

AI Agent 拥有独立的钱包地址（智能合约），由系统在创建时自动部署。Agent 的质押和付费操作通过此独立钱包完成。

### 2.2 三种地址的关系

```
┌─────────────────────────────────────────────────────────────────┐
│                    Agent 智能合约钱包地址关系                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   智能合约钱包 (Agent Wallet)                                    │
│   ┌───────────────────────────────────────────────────────────┐ │
│   │                                                           │ │
│   │  合约地址 = 钱包地址 = 0xAAA... (用于接收/发送代币)      │ │
│   │  (这是 Agent 的"银行账户"，任何人都可以向这个地址转账)  │ │
│   │                                                           │ │
│   │  内部字段:                                                │ │
│   │  ├── owner: 0xBBB... (主人的 MetaMask 地址)             │ │
│   │  │   → 拥有最高权限：设置限额、审批大额交易、紧急暂停   │ │
│   │  │                                                       │ │
│   │  └── agent: 0xCCC... (AI Agent 后端服务地址)             │ │
│   │      → 被授权自动发起交易，限额内无需主人确认            │ │
│   │                                                           │ │
│   └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│   地址生成规则:                                                │
│   ┌────────────────┬─────────────────────────────────────────┐  │
│   │ 地址类型       │ 生成方式                                 │  │
│   ├────────────────┼─────────────────────────────────────────┤  │
│   │ 合约地址       │ 部署合约时由区块链自动生成               │  │
│   │ (0xAAA...)   │                                          │  │
│   ├────────────────┼─────────────────────────────────────────┤  │
│   │ owner         │ 创建 Agent 的人的 MetaMask 地址           │  │
│   │ (0xBBB...)   │                                          │  │
│   ├────────────────┼─────────────────────────────────────────┤  │
│   │ agent         │ AI Agent 后端服务的以太坊地址             │  │
│   │ (0xCCC...)   │ 同一个后端服务可为多个 Agent 作为 agent   │  │
│   └────────────────┴─────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 注册表合约 (AgentRegistry)

#### 2.3.1 为什么需要注册表？

```
问题场景：
- Agent A (先注册) 想转账给 Agent B (后注册)
- Agent A 部署时，Agent B 还不存在
- Agent A 合约中如何知道 Agent B 是合法的？

解决方案：
- 引入注册表合约 (AgentRegistry)
- 所有 Agent 注册时将自己的地址写入注册表
- 转账时通过注册表验证目标地址是否为有效 Agent
```

#### 2.3.2 注册表合约设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    注册表合约架构                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   注册表合约 (整个系统只部署 1 个)                              │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │  AgentRegistry 合约                                      │  │
│   │                                                          │  │
│   │  mapping(address => bool) validAgents;                 │  │
│   │  mapping(address => address) agentToOwner;             │  │
│   │                                                          │  │
│   │  function registerAgent(address agentWallet)            │  │
│   │  function isValidAgent(address addr) returns (bool)     │  │
│   │  function getAgentOwner(address agent) returns (addr)  │  │
│   └─────────────────────────────────────────────────────────┘  │
│                           ▲                                     │
│                           │                                     │
│         ┌─────────────────┼─────────────────┐                 │
│         │                 │                 │                 │
│         ▼                 ▼                 ▼                 │
│    ┌──────────┐    ┌──────────┐    ┌──────────┐           │
│    │ Agent A  │    │ Agent B  │    │ Agent C  │           │
│    │ 合约钱包  │    │ 合约钱包  │    │ 合约钱包  │           │
│    └──────────┘    └──────────┘    └──────────┘           │
│                                                                 │
│   每个 Agent 合约内置:                                          │
│   IAgentRegistry registry;  // 引用注册表合约地址              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.3.3 转账验证流程

```
场景：Agent A (先注册) 转账给 Agent B (后注册)

Step 1: 主人1 创建 Agent A
┌──────────────────────────────────────────────────────────┐
│ 1. 部署 AgentA 合约钱包                                   │
│ 2. 调用 AgentRegistry.register(AgentA_Address)          │
│ 3. 注册表记录: validAgents[AgentA_Address] = true       │
└──────────────────────────────────────────────────────────┘

Step 2: 主人2 创建 Agent B
┌──────────────────────────────────────────────────────────┐
│ 1. 部署 AgentB 合约钱包                                   │
│ 2. 调用 AgentRegistry.register(AgentB_Address)          │
│ 3. 注册表记录: validAgents[AgentB_Address] = true       │
└──────────────────────────────────────────────────────────┘

Step 3: Agent A 转账给 Agent B
┌──────────────────────────────────────────────────────────┐
│ Agent A 调用: transfer(AgentB_Address, 100 VIBE)        │
│                                                          │
│ Agent A 合约内部检查:                                    │
│   1. registry.isValidAgent(AgentB_Address)               │
│      │                                                   │
│      ▼ 查询注册表合约                                    │
│   返回 true (因为 Agent B 已注册)                        │
│                                                          │
│ ✅ 验证通过，执行转账                                     │
└──────────────────────────────────────────────────────────┘
```

### 2.4 白名单自动化

#### 2.4.1 系统内地址定义

```
系统内地址 = 平台生态内的合法地址

┌───────────────────────────────────────────────────────────┐  │
│  类型1: 平台核心合约                                      │  │
│  ├── 市场合约地址 (Marketplace)                          │  │
│  ├── 匹配引擎合约地址 (Matching)                         │  │
│  ├── 协作管理合约地址 (Collaboration)                   │  │
│  └── 代币合约地址 (VIBE Token)                          │  │
│                                                            │  │
│  类型2: Agent 钱包地址                                    │  │
│  ├── 所有已注册的 Agent 的合约钱包地址                    │  │
│  └── 随着新 Agent 注册而自动增加                         │  │
│                                                            │  │
│  类型3: 主人地址                                          │  │
│  └── 每个 Agent 的主人 MetaMask 地址                    │  │
└───────────────────────────────────────────────────────────┘
```

#### 2.4.2 自动信任机制

```solidity
// Agent 合约中的转账验证逻辑
contract AgentWallet {
    IAgentRegistry public registry;      // 注册表合约引用
    address public owner;                // 主人地址
    address public agent;                // Agent 地址
    mapping(address => bool) public whitelist;  // 手动白名单

    function _canTransfer(address to) internal view returns (bool) {
        // 1. 主人自己
        if (to == owner) return true;

        // 2. 白名单中的外部地址（手动添加）
        if (whitelist[to]) return true;

        // 3. 验证是否是新注册的 Agent (通过注册表)
        if (registry.isValidAgent(to)) return true;

        return false;
    }
}
```

### 2.5 Agent 智能合约钱包伪代码

```solidity
// AgentWallet.sol 简化版
contract AgentWallet {
    // 地址
    address public owner;           // 主人 MetaMask 地址
    address public agent;           // AI Agent 后端服务地址
    address public registry;        // 注册表合约地址

    // 限额
    uint256 public maxPerTx = 500;        // 单笔最大限额
    uint256 public dailyLimit = 1000;     // 每日最大限额
    uint256 public dailySpent;            // 今日已转账
    uint256 public lastResetTime;         // 上次重置时间

    // 白名单
    mapping(address => bool) public whitelist;

    // 事件
    event TransferRequested(address to, uint256 amount);
    event TransferCompleted(address to, uint256 amount);
    event TransferRejected(address to, uint256 amount);

    // 构造函数
    constructor(address _owner, address _agent, address _registry) {
        owner = _owner;
        agent = _agent;
        registry = _registry;

        // 自动添加主人到白名单
        whitelist[_owner] = true;
    }

    // Agent 调用：发起转账
    function requestTransfer(address to, uint256 amount) external {
        require(msg.sender == agent, "Only agent");

        // 验证目标地址
        require(_canTransfer(to), "Recipient not allowed");

        // 检查限额
        if (amount > maxPerTx || dailySpent + amount > dailyLimit) {
            // 超限额，触发主人审批
            emit TransferRequested(to, amount);
            // 通知主人...
        } else {
            // 限额内，直接执行
            _executeTransfer(to, amount);
        }
    }

    // 主人调用：批准并执行
    function approveTransfer(address to, uint256 amount) external {
        require(msg.sender == owner, "Only owner");
        _executeTransfer(to, amount);
    }

    // 主人调用：拒绝转账
    function rejectTransfer(address to, uint256 amount) external {
        require(msg.sender == owner, "Only owner");
        emit TransferRejected(to, amount);
    }

    // 内部：执行转账
    function _executeTransfer(address to, uint256 amount) internal {
        // 调用 VIBE 代币合约转账
        IERC20(vibeToken).transfer(to, amount);

        dailySpent += amount;
        emit TransferCompleted(to, amount);
    }

    // 内部：验证转账目标
    function _canTransfer(address to) internal view returns (bool) {
        if (whitelist[to]) return true;
        if (to == owner) return true;
        if (IAgentRegistry(registry).isValidAgent(to)) return true;
        return false;
    }
}
```

### 2.6 Agent 充值 API 设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    Agent 与主人钱包关系                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────────┐         转入 VIBE         ┌──────────────┐  │
│   │   主人钱包    │ ───────────────────────> │  Agent 钱包   │  │
│   │  (人类用户)   │      (质押/支付)          │ (独立地址)    │  │
│   └──────────────┘                           └──────────────┘  │
│          │                                           │           │
│          │          Agent 执行任务/购买              │           │
│          │          从 Agent 钱包扣款                │           │
│          │<──────────────────────────────────────────┘           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Agent 钱包生成规则

```python
# Agent 钱包地址生成（模拟）
def generate_agent_wallet_address(owner_address: str, agent_index: int) -> str:
    """基于主人地址 + Agent 序号生成唯一地址"""
    # 格式: 0x + keccak256(owner + agent_index)[:40]
    data = f"{owner_address}:{agent_index}:{datetime.now().isoformat()}"
    hash_hex = Web3.keccak(text=data).hex()[2:42]  # 取前40位
    return f"0x{hash_hex}"
```

### 2.4 Agent 钱包数据模型

```python
# agent_wallets 表
class AgentWallet:
    agent_id: str           # 关联的 Agent ID
    wallet_address: str    # Agent 独立钱包地址
    owner_address: str     # 主人钱包地址
    vibe_balance: float    # 可用余额
    staked_amount: float  # 已质押金额
    stake_status: str      # none/staked/unstaking
    locked_stake: float   # 锁定中金额
    unlock_available_at: float  # 可解锁时间
    created_at: float
    updated_at: float
```

### 2.5 Agent 质押流程

```
创建 Agent（免费）
        │
        ▼
系统生成 Agent 独立钱包地址
        │
        ▼
Agent 尝试执行任务/购买
        │
        ▼
检查 Agent 钱包质押状态
        │
   ┌────┴────┐
   │ 不足     │ 充足
   ▼         ▼
提示主人    执行任务/
转入 VIBE  购买成功
        │
        ▼
主人操作"充值到 Agent"
        │
        ▼
从主人钱包扣款 → Agent 钱包余额增加
        │
        ▼
自动质押 → 执行任务/购买成功
```

### 2.6 Agent 充值 API 设计

```python
# POST /auth/agent/{agent_id}/deposit
# 主人向 Agent 钱包转入 VIBE

class AgentDepositRequest(BaseModel):
    amount: float = Field(..., ge=1)  # 转入金额

class AgentDepositResponse(BaseModel):
    success: bool
    agentWalletAddress: str
    newBalance: float
    newStakedAmount: float

@router.post("/agent/{agent_id}/deposit")
async def deposit_to_agent(
    agent_id: str,
    request: AgentDepositRequest,
    user: dict = Depends(get_current_user)
):
    """Deposit VIBE to agent wallet (from owner's balance)"""
    # 校验：
    # 1. user 是该 agent 的主人
    # 2. user 有足够余额

    # 1. 扣减主人余额
    update_user_balance(user['id'], request.amount, deduct=True)

    # 2. 增加 Agent 钱包余额
    add_agent_balance(agent_id, request.amount)

    # 3. 自动质押
    agent_staked = get_agent_staked_amount(agent_id)
    if agent_staked < MIN_AGENT_STAKE:
        # 质押到最低要求
        stake_amount = min(request.amount, MIN_AGENT_STAKE - agent_staked)
        add_agent_stake(agent_id, stake_amount)

    return AgentDepositResponse(...)
```

### 2.7 Agent 转账完整流程示例

#### 场景1: Agent A → Agent B (限额内自动转账)

```
流程:
1. Agent A 完成任务，触发"收到报酬"事件
2. Agent A 检查:
   - 转账金额 <= maxPerTx? ✅
   - 当日已转 + 本次 <= dailyLimit? ✅
   - Agent B 是有效 Agent? ✅ (通过注册表验证)
3. 执行: VIBE.transfer(AgentB_Wallet, amount)
4. 记录交易日志
5. 通知双方主人
```

#### 场景2: Agent A → Agent B (超限额需审批)

```
流程:
1. Agent A 发起转账请求，金额超限额
2. 合约暂停执行，生成待审批请求
3. 通知主人A审批
4. 主人A批准 → 执行转账
   或
   主人A拒绝 → 拒绝转账
```

#### 场景3: Agent → 人类用户 (收益提现)

```
流程:
1. Agent 完成任务，收益存入钱包
2. Agent 发起"提现到主人"请求
3. 合约检查: to == owner ✅
4. 执行转账到主人地址
```

### 2.8 与人类钱包的关系

```
┌─────────────────────────────────────────────────────────────────┐
│                    人类用户与 Agent 钱包关系                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   人类用户 (MetaMask)                                           │
│       │                                                          │
│       │ 1. 创建 Agent                                           │
│       │    → 部署合约钱包，owner = 自己的MetaMask地址          │
│       │                                                         │
│       │ 2. 充值 VIBE                                           │
│       │    → 从自己的 MetaMask 转账到 Agent 合约钱包           │
│       │                                                         │
│       │ 3. 设置权限                                           │
│       │    → 配置单笔限额、每日限额                            │
│       │                                                         │
│       │ 4. 审批大额交易 (可选)                                │
│       │    → 超过限额的交易需要主人确认                        │
│       │                                                         │
│       │ 5. 接收收益                                           │
│       │    → Agent 自动将收益转到主人钱包                        │
│       │                                                         │
│       ▼                                                          │
│   Agent 钱包 (智能合约)                                          │
│       │                                                          │
│       │ - 可接收 VIBE                                          │
│       │ - 可转出 VIBE (限额内自动)                             │
│       │ - 可被其他 Agent 信任 (通过注册表)                     │
│       │                                                         │
└─────────────────────────────────────────────────────────────────┘
```

### 2.9 智能合约钱包优势

| 优势 | 说明 |
|------|------|
| **安全性** | 无需导出私钥，合约控制权限 |
| **灵活性** | 可设置单笔/每日限额，可暂停 |
| **自动化** | 限额内交易无需人类参与 |
| **可追溯** | 所有交易记录在链上 |
| **可升级** | 可通过注册表动态添加信任 |

---

## 三、Base 链与 ERC-4337 兼容性

### 3.1 Base 链支持

| 项目 | 支持状态 |
|------|----------|
| 智能合约钱包 | ✅ 支持 |
| ERC-20 (VIBE 代币) | ✅ 支持 |
| EntryPoint 合约 | ✅ 可部署 |
| Gas 费用 | ✅ 极低 (约 $0.001-0.01) |

### 3.2 ERC-4337 在 Base 上的优势

```
优势:
• 低 Gas 费用: 部署合约 ~$0.1-1，交易 ~$0.001-0.01
• 与以太坊兼容: 相同的开发工具和标准
• 快速确认: 比以太坊主网快很多
• Coinbase 生态: 可集成 Coinbase Agentic Wallet 技能
```

### 3.3 可用的 ERC-4337 工具

```
SDK/工具:
• Alchemy Account Abstraction
• Stackup (erc4337.io)
• Biconomy
• 自己部署 (推荐)
```

---

## 四、完整自动化程度

```python
# Agent 注册时自动创建钱包
def create_agent_wallet(agent_id: str, owner_address: str) -> AgentWallet:
    """创建 Agent 独立钱包"""
    wallet_address = generate_agent_wallet_address(owner_address, agent_index)

    return AgentWallet(
        agent_id=agent_id,
        wallet_address=wallet_address,
        owner_address=owner_address,
        vibe_balance=0,        # 初始为0，需要主人充值
        staked_amount=0,       # 需要主人充值后质押
        stake_status='none',
        locked_stake=0,
        ...
    )
```

### 2.8 Agent 权限检查

```python
def check_agent_stake(agent_id: str, required_action: str) -> bool:
    """检查 Agent 是否有足够质押执行操作"""
    agent_wallet = get_agent_wallet(agent_id)

    # 根据操作类型检查
    required_stakes = {
        'execute_task': 100,      # 执行任务
        'purchase_demand': 50,    # 购买需求
        'list_service': 200,     # 发布服务
    }

    required = required_stakes.get(required_action, 100)
    return agent_wallet.staked_amount >= required
```

---

## 五、功能权限矩阵

| 功能页面 | 路由 | 未质押用户 | 已质押用户 | 说明 |
|----------|------|-----------|-----------|------|
| Dashboard | `/app/dashboard` | ✅ 只读 | ✅ | 统计数据 |
| Agents 列表 | `/app/agents` | ✅ 只读 | ✅ | 浏览 Agent |
| Agent 详情 | `/app/agents/:id` | ✅ 只读 | ✅ | 查看详情 |
| **发布服务** | `/app/publish-service` | ❌ | ✅ | 需质押 |
| **发布需求** | `/app/publish-demand` | ❌ | ✅ | 需质押 |
| **注册 Agent** | `/app/register-agent` | ❌ | ✅ | 需质押 |
| **协作** | `/app/collaborations` | ❌ | ✅ | 需质押 |
| **匹配** | `/app/matching` | ❌ | ✅ | 需质押 |
| **治理投票** | `/app/governance` | ❌ | ✅ | 需质押 |
| Chat | `/app/chat` | ✅ | ✅ | 基础功能 |
| Settings | `/app/settings` | ✅ | ✅ | 包括质押管理 |
| Marketplace | `/app/marketplace` | ✅ 只读 | ✅ | 浏览市场 |

---

## 六、全局质押开关

### 4.1 配置方式

**环境变量方式**（推荐）：
```bash
# .env 文件
STAKE_REQUIRED=true   # 开启质押限制（默认，生产环境）
STAKE_REQUIRED=false  # 关闭质押限制（测试/单节点模式）
```

**启动参数方式**：
```bash
# 通过环境变量传递
STAKE_REQUIRED=false python -m uvicorn main:app

# 或直接导出
export STAKE_REQUIRED=false
python -m uvicorn main:app
```

### 4.2 开关行为

| 配置 | STAKE_REQUIRED=true | STAKE_REQUIRED=false |
|------|---------------------|----------------------|
| **适用场景** | 生产环境/多节点网络 | 单节点/测试/开发 |
| **质押 API** | 正常校验 | 跳过校验，直接成功 |
| **功能访问** | 需要质押 | 无限制访问 |
| **前端提示** | 显示质押引导 | 不显示质押限制 |
| **用户状态** | 正常记录质押 | 质押状态无意义 |

### 4.3 API 响应变化

当 `STAKE_REQUIRED=false` 时：

```python
# GET /auth/config - 前端获取配置
{
  "stakeRequired": false,
  "minStakeAmount": 100,
  "defaultBalance": 10000
}

# POST /auth/stake - 质押接口
{
  "success": true,
  "skipped": true,  // 标识跳过了实际质押
  "message": "Stake requirement is disabled in current mode"
}
```

---

## 七、质押锁定期设计

### 5.1 撤回流程

```
用户点击"撤回质押"
        │
        ▼
检查状态是否为 'staked'
        │
        ▼
更新状态为 'unstaking'
记录 unlock_available_at = now + 7天
        │
        ▼
显示倒计时 UI
提供"取消撤回"按钮
        │
        ├──────────────────────────┐
        ▼                          ▼
7天后自动解锁              用户点击"取消撤回"
        │                          │
        ▼                          ▼
stake -> 0                  状态恢复为 'staked'
status -> 'unlocked'        删除 unlock_available_at
余额增加                            │
        │                          │
        └──────────────────────────┘
```

### 5.2 数据模型

```python
# users 表新增字段
class User:
    # 现有字段...
    vibe_balance: float = 10000.0      # VIBE 余额（模拟）
    stake_status: str = 'none'          # none/staked/unstaking/unlocked
    locked_stake: float = 0             # 锁定中的金额
    unlock_available_at: float = None   # 可解锁时间戳
```

---

## 八、API 设计

### 6.1 新增/修改的 API 端点

#### GET /auth/config
获取质押配置（前端初始化时调用）

```python
class StakeConfigResponse(BaseModel):
    stakeRequired: bool          # 是否开启质押限制
    minStakeAmount: float        # 最低质押金额 100
    defaultBalance: float        # 初始模拟余额 10000
    unstakingPeriodDays: int     # 解锁等待天数 7

@router.get("/config", response_model=StakeConfigResponse)
async def get_stake_config():
    stake_required = os.environ.get("STAKE_REQUIRED", "true").lower() == "true"
    return StakeConfigResponse(
        stakeRequired=stake_required,
        minStakeAmount=100.0,
        defaultBalance=10000.0,
        unstakingPeriodDays=7
    )
```

#### GET /auth/balance
获取用户 VIBE 余额

```python
class BalanceResponse(BaseModel):
    balance: float              # 可用余额
    stakedAmount: float         # 已质押金额
    lockedAmount: float         # 锁定中金额
    totalBalance: float         # 总余额

@router.get("/balance", response_model=BalanceResponse)
async def get_balance(user: dict = Depends(get_current_user)):
    ...
```

#### POST /auth/stake（修改）
增加质押校验

```python
@router.post("/stake", response_model=StakeResponse)
async def stake_tokens(request: StakeRequest, user: dict = Depends(get_current_user)):
    stake_required = os.environ.get("STAKE_REQUIRED", "true").lower() == "true"

    # 如果关闭质押限制，直接返回成功
    if not stake_required:
        return StakeResponse(success=True, skipped=True, ...)

    # 校验1: 最低金额
    if request.amount < 100:
        raise HTTPException(400, "Minimum stake is 100 VIBE")

    # 校验2: 余额充足
    if user['vibe_balance'] < request.amount:
        raise HTTPException(400, "Insufficient VIBE balance")

    # 校验3: 状态检查（允许 staked 状态增加质押）
    if user['stake_status'] == 'unstaking':
        raise HTTPException(400, "Cannot stake while unstaking")

    # 执行质押...
```

#### POST /auth/unstake（新增）
申请撤回质押

```python
class UnstakeRequest(BaseModel):
    amount: Optional[float] = None  # None = 全部撤回

class UnstakeResponse(BaseModel):
    success: bool
    lockedAmount: float
    unlockAvailableAt: int  # 时间戳

@router.post("/unstake", response_model=UnstakeResponse)
async def unstake_tokens(request: UnstakeRequest, user: dict = Depends(get_current_user)):
    # 校验状态
    if user['stake_status'] != 'staked':
        raise HTTPException(400, "No stake to unstake")

    # 设置解锁中状态
    # unlock_available_at = now + 7天
    ...
```

#### POST /auth/unstake/cancel（新增）
取消撤回

```python
@router.post("/unstake/cancel")
async def cancel_unstake(user: dict = Depends(get_current_user)):
    if user['stake_status'] != 'unstaking':
        raise HTTPException(400, "Not in unstaking state")
    # 恢复为 staked 状态
    ...
```

#### POST /auth/unstake/confirm（新增）
确认解锁（7天后调用）

```python
@router.post("/unstake/confirm")
async def confirm_unstake(user: dict = Depends(get_current_user)):
    if user['stake_status'] != 'unstaking':
        raise HTTPException(400, "Not in unstaking state")
    if datetime.now().timestamp() < user['unlock_available_at']:
        raise HTTPException(400, "Unlock period not completed")
    # 返还余额，清除质押
    ...
```

#### POST /auth/profile（修复）
修复 500 错误

```python
# 修改第308行
# 错误: 'hourly_rate': request.hourly_rate
# 正确: 'hourly_rate': request.hourlyRate
```

---

## 九、前端设计

### 7.1 authStore 扩展

```typescript
// stores/authStore.ts 新增字段
interface AuthState {
  // 现有字段...

  // 新增质押相关
  vibeBalance: number           // VIBE 可用余额
  stakedAmount: number          // 已质押金额
  lockedAmount: number          // 锁定中金额
  stakeStatus: StakeStatus      // 'none' | 'staked' | 'unstaking' | 'unlocked'
  unlockAvailableAt: number | null  // 可解锁时间

  // 配置相关
  stakeRequired: boolean        // 后端质押开关状态

  // 新增 Actions
  updateStakeInfo: (info: StakeInfo) => void
}
```

### 7.2 质押引导弹窗组件

**文件**: `components/StakeGuideModal.tsx`

```tsx
interface StakeGuideModalProps {
  isOpen: boolean
  onClose: () => void
  featureName: string  // 触发弹窗的功能名称
  requiredStake?: number
}

// 弹窗内容：
// 1. 说明需要质押才能使用该功能
// 2. 列出质押权益
// 3. 提供"立即质押"和"稍后再说"按钮
// 4. 点击"立即质押"跳转到 /app/onboarding 或设置页
```

### 7.3 useStakeGuard Hook

**文件**: `hooks/useStakeGuard.ts`

```tsx
export function useStakeGuard() {
  const { stakeStatus, stakeRequired, accessToken } = useAuthStore()
  const [showGuideModal, setShowGuideModal] = useState(false)
  const [targetFeature, setTargetFeature] = useState('')

  // 检查是否有权限访问某功能
  const checkAccess = useCallback((featureName: string): boolean => {
    // 如果后端关闭了质押限制，直接放行
    if (!stakeRequired) return true

    // 如果未登录
    if (!accessToken) {
      setTargetFeature(featureName)
      setShowGuideModal(true)
      return false
    }

    // 如果未质押
    if (stakeStatus !== 'staked') {
      setTargetFeature(featureName)
      setShowGuideModal(true)
      return false
    }

    return true
  }, [stakeRequired, accessToken, stakeStatus])

  return {
    checkAccess,
    showGuideModal,
    targetFeature,
    closeGuideModal: () => setShowGuideModal(false)
  }
}
```

### 7.4 质押管理页面（Settings 中新增 Tab）

**文件**: `pages/Settings.tsx` 新增质押管理部分

```
┌────────────────────────────────────────┐
│  质押管理                              │
├────────────────────────────────────────┤
│                                        │
│  状态: ✅ 已质押                       │
│  质押金额: 1,000 VIBE                  │
│  质押等级: 🥈 Silver                   │
│  可用余额: 9,000 VIBE                  │
│  总资产: 10,000 VIBE                   │
│                                        │
│  [增加质押]     [撤回质押]             │
│                                        │
├────────────────────────────────────────┤
│  质押权益说明                          │
│  • 发布服务和需求                      │
│  • 注册 AI Agent                       │
│  • 参与协作匹配                        │
│  • 治理投票权                          │
└────────────────────────────────────────┘
```

### 7.5 路由守卫实现

**修改**: `App.tsx`

```tsx
// 创建 ProtectedRoute 组件
function StakeProtectedRoute({ children, featureName }: { children: ReactNode, featureName: string }) {
  const { checkAccess, showGuideModal, targetFeature, closeGuideModal } = useStakeGuard()

  if (!checkAccess(featureName)) {
    return (
      <>
        {children}  // 或者显示受限提示
        <StakeGuideModal
          isOpen={showGuideModal}
          onClose={closeGuideModal}
          featureName={targetFeature}
        />
      </>
    )
  }

  return <>{children}</>
}

// 在需要保护的路由上使用
<Route path="publish-service" element={
  <StakeProtectedRoute featureName="发布服务">
    <PublishService />
  </StakeProtectedRoute>
} />
```

---

## 十、数据库变更

### 8.1 users 表新增字段

```sql
ALTER TABLE users ADD COLUMN vibe_balance REAL DEFAULT 10000.0;
ALTER TABLE users ADD COLUMN stake_status TEXT DEFAULT 'none';
ALTER TABLE users ADD COLUMN locked_stake REAL DEFAULT 0;
ALTER TABLE users ADD COLUMN unlock_available_at REAL;
```

### 8.2 更新 init_db 函数

**文件**: `usmsb_sdk/api/database.py`

```python
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        wallet_address TEXT UNIQUE NOT NULL,
        did TEXT UNIQUE,
        agent_id TEXT,
        stake REAL DEFAULT 0,
        reputation REAL DEFAULT 0.5,
        vibe_balance REAL DEFAULT 10000.0,    -- 新增
        stake_status TEXT DEFAULT 'none',     -- 新增
        locked_stake REAL DEFAULT 0,          -- 新增
        unlock_available_at REAL,             -- 新增
        created_at REAL,
        updated_at REAL
    )
''')
```

---

## 十一、实现步骤

### Phase 1: 后端基础（优先）
1. 修改 `database.py` - 添加新字段到 users 表
2. 修改 `auth.py` - 添加配置 API 和余额 API
3. 修复 `auth.py` 第308行 `hourly_rate` 错误
4. 添加全局质押开关支持

### Phase 2: 质押 API 完善
5. 修改 `/auth/stake` - 添加余额校验
6. 实现 `/auth/unstake` - 申请撤回
7. 实现 `/auth/unstake/cancel` - 取消撤回
8. 实现 `/auth/unstake/confirm` - 确认解锁

### Phase 3: 前端基础设施
9. 修改 `authStore.ts` - 添加新字段
10. 创建 `useStakeGuard.ts` Hook
11. 创建 `StakeGuideModal.tsx` 组件
12. 添加 API 调用 (`authService.ts`)

### Phase 4: 功能集成
13. 修改 `App.tsx` - 添加路由守卫
14. 修改 `Settings.tsx` - 添加质押管理 Tab
15. 修改 `Onboarding.tsx` - 修复文档链接

### Phase 5: 测试验证
16. 测试质押流程
17. 测试撤回流程（含7天等待）
18. 测试 STAKE_REQUIRED=false 模式
19. 测试受限功能访问

---

## 十二、关键文件清单

| 文件路径 | 修改内容 |
|---------|---------|
| `usmsb_sdk/api/database.py` | users 表新增字段 |
| `usmsb_sdk/api/rest/auth.py` | 修复 bug + 新增 API |
| `usmsb_sdk/config/settings.py` | 添加 stake_required 配置 |
| `frontend/src/stores/authStore.ts` | 新增质押状态字段 |
| `frontend/src/hooks/useStakeGuard.ts` | 新建 - 权限守卫 Hook |
| `frontend/src/components/StakeGuideModal.tsx` | 新建 - 质押引导弹窗 |
| `frontend/src/services/authService.ts` | 新增 API 调用 |
| `frontend/src/App.tsx` | 添加路由守卫 |
| `frontend/src/pages/Settings.tsx` | 添加质押管理 |
| `frontend/src/pages/Onboarding.tsx` | 修复文档链接 |

---

## 十三、完整自动化程度总结

### 13.1 需要人类参与的阶段

| 阶段 | 需要人类 | 说明 |
|------|---------|------|
| 创建 Agent | ✅ 是 | 点击"创建 Agent"一次 |
| 充值 VIBE | ✅ 是 | 主人从自己钱包转账到 Agent 钱包 |
| 设置初始限额 | ⚪ 可选 | 可使用默认值 |
| 添加外部收款方 | ⚪ 可选 | 系统内地址自动信任 |

### 13.2 完全自动化的操作

| 操作 | 需要人类 | 说明 |
|------|---------|------|
| Agent → Agent 转账 (限额内) | ❌ 否 | 完全自动 |
| Agent → 主人 收益提现 | ❌ 否 | 完全自动 |
| Agent → 市场 支付服务费 | ❌ 否 | 完全自动 |
| Agent → 资源方 支付资源费 | ❌ 否 | 完全自动 |
| 自动复投/理财 | ❌ 否 | 完全自动 |
| 白名单自动扩展 | ❌ 否 | 通过注册表验证 |

### 13.3 特殊情况需要人类

| 情况 | 需要人类 | 说明 |
|------|---------|------|
| 超限额交易 | ✅ 是 | 需要主人审批 |
| 新增外部收款方 (非系统地址) | ✅ 是 | 需要主人确认 |
| 异常交易警报 | ✅ 是 | 触发安全通知 |

### 13.4 目标：自主 AI Agent 经济

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          目标：完全自主的 Agent 经济                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   创建阶段 (人)                                                            │
│   ┌─────────────────────────────────────────────────────────────────┐       │
│   │  1. 用户点击"创建 Agent"                                        │       │
│   │  2. 系统部署合约钱包                                            │       │
│   │  3. 主人充值 VIBE                                              │       │
│   │  4. 主人设置限额 (可选，默认值)                                 │       │
│   └─────────────────────────────────────────────────────────────────┘       │
│                                    │                                        │
│                                    ▼                                        │
│   运营阶段 (自动)                                                          │
│   ┌─────────────────────────────────────────────────────────────────┐       │
│   │                                                                     │       │
│   │   Agent A 完成任务 ──收到报酬──> 钱包余额增加                   │       │
│   │          │                                                          │       │
│   │          │  自动操作:                                             │       │
│   │          ├── 支付给 Agent B (服务费)                             │       │
│   │          ├── 支付给 Agent C (资源费)                             │       │
│   │          ├── 支付给 人类 D (收益提现)                            │       │
│   │          └── 存入收益 (自动复投)                                  │       │
│   │                                                                     │       │
│   └─────────────────────────────────────────────────────────────────┘       │
│                                    │                                        │
│                                    ▼                                        │
│   特殊情况 (人)                                                            │
│   ┌─────────────────────────────────────────────────────────────────┐       │
│   │  • 超限额交易 → 通知主人审批                                    │       │
│   │  • 异常行为 → 触发安全警报                                      │       │
│   │  • 余额不足 → 通知主人充值                                      │       │
│   └─────────────────────────────────────────────────────────────────┘       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 十四、验证方案

### 14.1 后端测试

```bash
# 1. 启动后端（开启质押限制）
STAKE_REQUIRED=true python -m uvicorn usmsb_sdk.api.rest.main:app

# 2. 测试配置 API
curl http://localhost:8000/api/auth/config
# 期望: {"stakeRequired": true, ...}

# 3. 启动后端（关闭质押限制）
STAKE_REQUIRED=false python -m uvicorn usmsb_sdk.api.rest.main:app

# 4. 再次测试配置 API
curl http://localhost:8000/api/auth/config
# 期望: {"stakeRequired": false, ...}
```

### 14.2 前端测试

1. **未质押用户访问受限功能**
   - 访问 `/app/publish-service`
   - 期望：弹出质押引导弹窗

2. **关闭质押限制后**
   - 设置 `STAKE_REQUIRED=false`
   - 访问 `/app/publish-service`
   - 期望：直接进入，无弹窗

3. **质押流程**
   - 在设置页质押 100 VIBE
   - 期望：状态变为已质押

4. **撤回流程**
   - 点击撤回质押
   - 期望：状态变为解锁中，显示倒计时
   - 点击取消撤回
   - 期望：恢复为已质押

### 14.3 API 500 错误验证

```bash
# 测试完善资料 API
curl -X POST http://localhost:8000/api/auth/profile \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "bio": "test", "skills": [], "hourlyRate": 100}'

# 期望: 200 OK，不再是 500
```
