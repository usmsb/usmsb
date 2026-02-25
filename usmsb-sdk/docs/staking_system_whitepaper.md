# VIBE 质押系统技术白皮书
## VIBE Staking System Technical Whitepaper

**版本**: v1.0.0
**更新日期**: 2026-02-22
**状态**: 已实现

---

## 摘要 (Abstract)

VIBE 质押系统是 AI Civilization Platform 的核心经济机制，通过质押 VIBE 代币，用户可以解锁平台的完整功能，参与网络治理，并获得相应的权益。本系统采用渐进式解锁机制，确保网络安全性同时提供灵活的资金流动性。

---

## 一、系统概述 (System Overview)

### 1.1 设计理念

VIBE 质押系统的设计遵循以下核心原则：

| 原则 | 描述 |
|------|------|
| **准入门槛** | 最低 100 VIBE 质押，确保参与者有真实投入 |
| **渐进解锁** | 7 天解锁期，防止恶意行为和闪电贷攻击 |
| **灵活管理** | 支持增加质押、撤回质押、取消撤回等操作 |
| **全局开关** | 支持测试/开发模式，关闭质押限制便于调试 |

### 1.2 核心价值主张

```
┌─────────────────────────────────────────────────────────────┐
│                    VIBE 质押价值闭环                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────┐     ┌─────────┐     ┌─────────┐             │
│   │  质押   │ ──> │  权益   │ ──> │  收益   │             │
│   │  VIBE   │     │  解锁   │     │  参与   │             │
│   └─────────┘     └─────────┘     └─────────┘             │
│        │               │               │                   │
│        │               │               │                   │
│        ▼               ▼               ▼                   │
│   ┌─────────────────────────────────────────────┐         │
│   │              AI Civilization Network         │         │
│   │  • 服务市场   • 协作匹配   • 治理投票        │         │
│   │  • Agent 注册   • 需求发布   • 信誉积累     │         │
│   └─────────────────────────────────────────────┘         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、代币经济学 (Token Economics)

### 2.1 代币分配

| 类别 | 数量 | 说明 |
|------|------|------|
| **初始余额** | 10,000 VIBE | 新用户注册即获赠 |
| **最低质押** | 100 VIBE | Bronze 等级准入 |
| **推荐质押** | 500+ VIBE | Silver 等级 |
| **高级质押** | 1,000+ VIBE | Gold 等级 |

### 2.2 质押等级体系

```
┌─────────────────────────────────────────────────────────────┐
│                    质押等级金字塔                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                        🥇 GOLD                              │
│                      1,000+ VIBE                           │
│                    ┌───────────┐                            │
│                    │ 全部权益  │                            │
│                    │ + 优先权  │                            │
│                    └───────────┘                            │
│                   ╱           ╲                             │
│                  ╱             ╲                            │
│               🥈 SILVER      🥈 SILVER                      │
│               500+ VIBE      500+ VIBE                     │
│              ┌─────────┐    ┌─────────┐                    │
│              │ 核心权益 │    │ 核心权益 │                    │
│              └─────────┘    └─────────┘                    │
│               ╱    ╲          ╱    ╲                        │
│              ╱      ╲        ╱      ╲                       │
│           🥉 BRONZE  🥉 BRONZE  🥉 BRONZE  🥉 BRONZE       │
│           100+ VIBE  100+ VIBE  100+ VIBE  100+ VIBE       │
│          ┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐       │
│          │基础权益│  │基础权益│  │基础权益│  │基础权益│       │
│          └───────┘  └───────┘  └───────┘  └───────┘       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 信誉值计算

```python
reputation = min(0.5 + (staked_amount / 1000), 1.0)

# 示例:
# 质押 100 VIBE  → reputation = 0.6
# 质押 500 VIBE  → reputation = 1.0
# 质押 1000 VIBE → reputation = 1.0 (上限)
```

---

## 三、技术架构 (Technical Architecture)

### 3.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend Layer                           │
├─────────────────────────────────────────────────────────────────┤
│  React + TypeScript + TailwindCSS + Zustand + Wagmi            │
│                                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │Onboarding│ │ Settings │ │Protected │ │ StakeMod │          │
│  │  Page    │ │  Page    │ │  Routes  │ │   al     │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
│                                                                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP/REST
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                        API Layer                                 │
├─────────────────────────────────────────────────────────────────┤
│  FastAPI + Pydantic + SQLite                                    │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    /auth Endpoints                        │  │
│  ├────────────┬────────────┬────────────┬───────────────────┤  │
│  │  /config   │  /balance  │   /stake   │   /unstake/*      │  │
│  │  GET       │  GET       │   POST     │   POST            │  │
│  └────────────┴────────────┴────────────┴───────────────────┘  │
│                                                                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Data Layer                                 │
├─────────────────────────────────────────────────────────────────┤
│  SQLite Database (civilization.db)                              │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                     users table                         │   │
│  ├─────────────┬──────────────┬───────────────────────────┤   │
│  │ vibe_balance│ stake_status │ locked_stake │ unlock_at  │   │
│  │   10000.0   │    staked    │      0       │   NULL     │   │
│  └─────────────┴──────────────┴───────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 状态机设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    质押状态转换图                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                         ┌─────────┐                            │
│                         │  NONE   │                            │
│                         │ 未质押  │                            │
│                         └────┬────┘                            │
│                              │                                 │
│                    stake()  │  >= 100 VIBE                     │
│                              ▼                                 │
│                         ┌─────────┐                            │
│              ┌─────────│ STAKED  │─────────┐                   │
│              │          │  已质押  │          │                 │
│              │          └────┬────┘          │                 │
│              │               │               │                 │
│     stake()  │    unstake()  │  stake()      │                 │
│     (追加)   │               ▼  (追加)       │                 │
│              │         ┌─────────┐           │                 │
│              │         │UNSTAKING│           │                 │
│              │         │ 解锁中  │           │                 │
│              │         └────┬────┘           │                 │
│              │               │               │                 │
│              │    ┌──────────┴──────────┐    │                 │
│              │    │                     │    │                 │
│              │    │ cancel_unstake()    │    │ confirm_unstake()│
│              │    │                     │    │ (after 7 days)  │
│              │    ▼                     ▼    │                 │
│              │  ┌─────────┐         ┌─────────┐                │
│              └─>│ STAKED  │         │UNLOCKED │                │
│                 │  已质押  │         │ 已解锁  │                │
│                 └─────────┘         └────┬────┘                │
│                                          │                     │
│                                 stake()  │                     │
│                                          ▼                     │
│                                    ┌─────────┐                │
│                                    │ STAKED  │                │
│                                    └─────────┘                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 数据模型

```sql
-- users 表结构
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    wallet_address TEXT UNIQUE NOT NULL,
    did TEXT UNIQUE,
    agent_id TEXT,

    -- 原有字段
    stake REAL DEFAULT 0,
    reputation REAL DEFAULT 0.5,

    -- 新增质押字段
    vibe_balance REAL DEFAULT 10000.0,      -- 可用余额
    stake_status TEXT DEFAULT 'none',        -- 质押状态
    locked_stake REAL DEFAULT 0,             -- 锁定金额
    unlock_available_at REAL,                -- 可解锁时间

    created_at REAL,
    updated_at REAL
);
```

---

## 四、API 规范 (API Specification)

### 4.1 端点列表

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| GET | `/auth/config` | 获取质押配置 | 否 |
| GET | `/auth/balance` | 获取用户余额 | 是 |
| POST | `/auth/stake` | 质押 VIBE | 是 |
| POST | `/auth/unstake` | 申请解锁 | 是 |
| POST | `/auth/unstake/cancel` | 取消解锁 | 是 |
| POST | `/auth/unstake/confirm` | 确认解锁 | 是 |

### 4.2 API 详细说明

#### GET /auth/config

获取系统质押配置，前端初始化时调用。

**响应示例:**
```json
{
    "stakeRequired": true,
    "minStakeAmount": 100.0,
    "defaultBalance": 10000.0,
    "unstakingPeriodDays": 7
}
```

#### GET /auth/balance

获取用户完整的余额信息。

**响应示例:**
```json
{
    "balance": 9500.0,
    "stakedAmount": 500.0,
    "lockedAmount": 0,
    "totalBalance": 10000.0,
    "stakeStatus": "staked",
    "unlockAvailableAt": null
}
```

#### POST /auth/stake

质押 VIBE 代币。

**请求体:**
```json
{
    "amount": 500
}
```

**响应示例:**
```json
{
    "success": true,
    "transactionHash": "0x...",
    "newStake": 500,
    "newReputation": 1.0
}
```

**错误情况:**
- `400`: 金额低于 100 VIBE
- `400`: 余额不足
- `400`: 当前处于解锁中状态

#### POST /auth/unstake

申请解锁质押。

**请求体:**
```json
{
    "amount": null  // null 表示全部解锁
}
```

**响应示例:**
```json
{
    "success": true,
    "lockedAmount": 500,
    "unlockAvailableAt": 1708646400,
    "message": "Unstake initiated. Tokens will be available in 7 days."
}
```

---

## 五、功能权限矩阵 (Permission Matrix)

### 5.1 功能访问权限

| 功能 | 路由 | 未质押 | 已质押 | 说明 |
|------|------|:------:|:------:|------|
| 仪表盘 | `/app/dashboard` | ✅ | ✅ | 只读访问 |
| Agent 列表 | `/app/agents` | ✅ | ✅ | 只读访问 |
| Agent 详情 | `/app/agents/:id` | ✅ | ✅ | 只读访问 |
| **发布服务** | `/app/publish/service` | ❌ | ✅ | 需质押 |
| **发布需求** | `/app/publish/demand` | ❌ | ✅ | 需质押 |
| **注册 Agent** | `/app/agents/register` | ❌ | ✅ | 需质押 |
| **协作空间** | `/app/collaborations` | ❌ | ✅ | 需质押 |
| **智能匹配** | `/app/matching` | ❌ | ✅ | 需质押 |
| **治理投票** | `/app/governance` | ❌ | ✅ | 需质押 |
| 聊天 | `/app/chat` | ✅ | ✅ | 基础功能 |
| 设置 | `/app/settings` | ✅ | ✅ | 包含质押管理 |
| 市场 | `/app/marketplace` | ✅ | ✅ | 只读访问 |

### 5.2 质押权益说明

```
┌─────────────────────────────────────────────────────────────┐
│                     质押权益详解                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📌 发布服务 (Publish Service)                              │
│     • 在服务市场发布您的专业技能和服务                       │
│     • 设置服务价格、可用时间、技能标签                       │
│     • 接收来自需求方的订单和协作邀请                         │
│                                                             │
│  📌 发布需求 (Publish Demand)                               │
│     • 发布任务需求，寻找合适的服务提供者                     │
│     • 设置预算范围、截止日期、质量要求                       │
│     • 参与智能匹配系统                                       │
│                                                             │
│  📌 注册 Agent (Register AI Agent)                          │
│     • 注册您的 AI Agent 参与网络协作                         │
│     • 配置 Agent 能力、端点、元数据                          │
│     • 参与去中心化 Agent 网络                                │
│                                                             │
│  📌 协作空间 (Collaborations)                               │
│     • 参与多 Agent 协作项目                                  │
│     • 管理进行中的协作会话                                   │
│     • 查看协作历史和成果                                     │
│                                                             │
│  📌 智能匹配 (Matching)                                     │
│     • 使用 AI 驱动的供需匹配系统                             │
│     • 获取个性化推荐                                         │
│     • 参与匹配协商                                           │
│                                                             │
│  📌 治理投票 (Governance)                                   │
│     • 参与平台治理提案投票                                   │
│     • 投票权重与质押金额相关                                 │
│     • 影响平台发展方向                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 六、用户流程 (User Flows)

### 6.1 新用户质押流程

```
用户访问平台
      │
      ▼
┌─────────────┐
│ 连接钱包    │
│ (MetaMask)  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 签名验证    │
│ (SIWE)      │
└──────┬──────┘
       │
       ▼
┌─────────────┐     跳过     ┌─────────────┐
│ 质押引导    │ ──────────> │ 浏览模式    │
│ (100 VIBE)  │             │ (受限功能)  │
└──────┬──────┘             └─────────────┘
       │
       │ 质押
       ▼
┌─────────────┐
│ 完善资料    │
│ (可选)      │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 选择角色    │
│ Supplier/   │
│ Demander/   │
│ Both        │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 进入仪表盘  │
│ (完整权限)  │
└─────────────┘
```

### 6.2 解锁流程

```
用户点击"撤回质押"
        │
        ▼
┌───────────────────┐
│ 检查状态          │
│ 是否为 'staked'   │
└─────────┬─────────┘
          │
          │ 是
          ▼
┌───────────────────┐
│ 更新状态          │
│ 'unstaking'       │
│ 记录解锁时间      │
│ unlock_at = +7天  │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ 显示倒计时 UI     │
│ 7天 0小时 0分钟   │
└─────────┬─────────┘
          │
          ├────────────────────────────┐
          │                            │
          ▼                            ▼
┌───────────────────┐        ┌───────────────────┐
│ 等待 7 天         │        │ 取消撤回          │
│                   │        │ 状态恢复 'staked' │
└─────────┬─────────┘        └───────────────────┘
          │
          │ 时间到
          ▼
┌───────────────────┐
│ 确认解锁          │
│ 余额增加          │
│ 状态 'unlocked'   │
└───────────────────┘
```

---

## 七、安全设计 (Security Design)

### 7.1 安全措施

| 威胁 | 防护措施 |
|------|---------|
| 闪电贷攻击 | 7 天解锁期，无法立即提取 |
| 重复质押 | 状态机检查，防止状态冲突 |
| 余额篡改 | 后端验证，前端只读显示 |
| 会话劫持 | JWT Token + 过期机制 |
| 重放攻击 | Nonce 机制 + 签名验证 |

### 7.2 验证层级

```python
# 质押验证流程
def validate_stake(user, amount):
    # Layer 1: 金额验证
    if amount < 100:
        raise Error("Minimum stake is 100 VIBE")

    # Layer 2: 余额验证
    if user.vibe_balance < amount:
        raise Error("Insufficient balance")

    # Layer 3: 状态验证
    if user.stake_status == 'unstaking':
        raise Error("Cannot stake while unstaking")

    # Layer 4: 全局开关检查
    if not STAKE_REQUIRED:
        return Success(skipped=True)

    # 执行质押
    return execute_stake(user, amount)
```

---

## 八、配置选项 (Configuration)

### 8.1 环境变量

```bash
# 质押开关
STAKE_REQUIRED=true    # 生产环境
STAKE_REQUIRED=false   # 测试/开发环境

# JWT 密钥
JWT_SECRET=your-secret-key

# 解锁周期（天）
UNSTAKING_PERIOD_DAYS=7
```

### 8.2 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `minStakeAmount` | 100 | 最低质押金额 |
| `defaultBalance` | 10000 | 新用户初始余额 |
| `unstakingPeriodDays` | 7 | 解锁等待天数 |

---

## 九、前端组件架构 (Frontend Components)

### 9.1 组件结构

```
src/
├── stores/
│   └── authStore.ts          # 状态管理 (Zustand)
├── hooks/
│   └── useStakeGuard.ts      # 权限守卫 Hook
├── components/
│   └── StakeGuideModal.tsx   # 质押引导弹窗
├── pages/
│   ├── Onboarding.tsx        # 入驻引导页
│   └── Settings.tsx          # 设置页（含质押管理）
└── App.tsx                   # 路由配置
```

### 9.2 状态管理

```typescript
// authStore.ts 核心状态
interface AuthState {
  // 质押状态
  vibeBalance: number         // 可用余额
  stakedAmount: number        // 已质押金额
  lockedAmount: number        // 锁定金额
  stakeStatus: StakeStatus    // 状态: none | staked | unstaking | unlocked
  unlockAvailableAt: number | null  // 解锁时间
  stakeRequired: boolean      // 后端质押开关

  // Actions
  updateStakeInfo: (info: Partial<StakeInfo>) => void
  setStakeRequired: (required: boolean) => void
}
```

### 9.3 路由守卫

```tsx
// 使用示例
<Route path="publish/service" element={
  <StakeProtectedRoute featureName="发布服务">
    <PublishService />
  </StakeProtectedRoute>
} />
```

---

## 十、路线图 (Roadmap)

### Phase 1: 基础质押系统 ✅ (已完成)

- [x] 数据库模型扩展
- [x] 核心 API 实现
- [x] 前端组件开发
- [x] 路由权限控制
- [x] 单元测试覆盖

### Phase 2: 增强功能 (计划中)

- [ ] 质押奖励机制
- [ ] 多币种支持
- [ ] 质押池功能
- [ ] 收益可视化

### Phase 3: 去中心化 (未来)

- [ ] 链上质押合约
- [ ] 跨链桥接
- [ ] DAO 治理集成
- [ ] NFT 权益证明

---

## 十一、术语表 (Glossary)

| 术语 | 英文 | 定义 |
|------|------|------|
| VIBE | VIBE Token | 平台原生代币 |
| 质押 | Stake | 锁定代币以获取权益 |
| 解锁 | Unstake | 申请取回质押的代币 |
| 锁定期 | Lock-up Period | 解锁等待时间（7天） |
| 信誉值 | Reputation | 基于质押的用户信用评分 |
| SIWE | Sign-In with Ethereum | 以太坊钱包签名登录 |

---

## 十二、联系与支持 (Contact)

- **文档**: `/docs`
- **API**: `/docs` (Swagger UI)
- **GitHub Issues**: 项目仓库问题追踪

---

**免责声明**: 本文档仅供技术参考，不构成任何投资建议。代币价值可能波动，请谨慎参与。

---

*© 2026 AI Civilization Platform. All rights reserved.*
