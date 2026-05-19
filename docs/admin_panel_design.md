# USMSB Admin Panel — 完整详细设计文档 v3.0

> 版本：v3.0（完整版）
> 日期：2026-05-19
> 作者：图灵 / 古军
> 状态：待确认后实现

---

## 目录

1. [概述与目标](#1-概述与目标)
2. [设计规范](#2-设计规范)
3. [完整数据清单](#3-完整数据清单)
4. [页面结构与路由](#4-页面结构与路由)
5. [Layout 布局规范](#5-layout-布局规范)
6. [Dashboard 详细设计](#6-dashboard-详细设计)
7. [Command Center 详细设计](#7-command-center-详细设计)
8. [Nodes 节点管理](#8-nodes-节点管理)
9. [Agents Agent 管理](#9-agents-agent-管理)
10. [Users 用户管理](#10-users-用户管理)
11. [Transactions 交易流水](#11-transactions-交易流水)
12. [Orders 订单管理](#12-orders-订单管理)
13. [Matching 匹配分析](#13-matching-匹配分析)
14. [Gene Capsules](#14-gene-capsules)
15. [Intelligence AI 能力分析](#15-intelligence-ai-能力分析)
16. [Governance 治理](#16-governance-治理)
17. [Contracts 区块链合约](#17-contracts-区块链合约)
18. [System 系统管理](#18-system-系统管理)
19. [Permissions 权限管理](#19-permissions-权限管理)
20. [组件库](#20-组件库)
21. [API 规范](#21-api-规范)
22. [数据层架构](#22-数据层架构)
23. [实时推送架构](#23-实时推送架构)
24. [权限体系](#24-权限体系)
25. [错误处理与状态管理](#25-错误处理与状态管理)
26. [文件结构](#26-文件结构)
27. [实施计划](#27-实施计划)

---

## 1. 概述与目标

### 1.1 项目背景

USMSB 平台需要为节点管理员（node_admin / superadmin）提供一个功能完整、数据全面、视觉专业化的管理后台。与现有用户前端（frontend）共用认证体系，共享样式规范，专门面向平台运营和治理场景。

### 1.2 核心目标

1. **全量数据可见**：平台侧所有数据一览无余，无信息死角
2. **实时监控能力**：实时感知平台状态，支持大屏指挥调度
3. **操作管理能力**：支持 Agent 冻结、角色变更、配置管理等写操作
4. **区块链数据**：直接读取链上合约状态，覆盖 29 个已部署合约
5. **零重复建设**：100% 复用 frontend 样式资产，不另起样式体系

### 1.3 角色定义

| 角色 | 可访问范围 |
|------|-----------|
| `superadmin` | 全部功能（不含 Node Operator 敏感操作）|
| `node_admin` | Dashboard / Nodes / Agents / Users（角色变更仅 human→ai_owner）/ Transactions / Orders / Matching / Gene Capsules / Intelligence / Contracts / System（只读）/ Permissions（只读）|

### 1.4 设计约束

- **不破坏 frontend 部署**：Admin Panel 作为条件渲染或独立路由，不独立打包发布
- **不新建样式体系**：直接 import frontend 的 CSS/Tailwind/组件
- **不暴露敏感操作给 node_admin**：系统配置写操作、权限矩阵变更仅 superadmin
- **链上数据不缓存过久**：价格类数据 30s，余额类 60s，配置类 5min

---

## 2. 设计规范

### 2.1 字体

```css
/* 主字体：Rajdhani（正文/标题）*/
font-family: 'Rajdhani', Inter, system-ui, Avenir, Helvetica, Arial, sans-serif;

/* 数字/代码：JetBrains Mono */
font-family: 'JetBrains Mono', 'Courier New', monospace;

/* 科技标题：Orbitron（仅用于 Command Center 大屏数字）*/
font-family: 'Orbitron', monospace;
```

### 2.2 颜色系统（CSS 变量）

```css
/* === 暗色主题（默认） === */
--bg-primary:      #0a0a0f;      /* 主背景：深黑带蓝调 */
--bg-secondary:    #12121a;      /* 次级背景：卡片/面板 */
--bg-tertiary:    #1a1a28;      /* 三级背景：输入框/hover */
--bg-elevated:    #22223a;      /* 浮层/下拉/Modal */

/* 边框 */
--border-primary: #2d2d4a;      /* 普通边框 */
--border-active:  #6366f1;       /* 聚焦边框（indigo）*/

/* 主色调 */
--primary:        #6366f1;       /* Indigo - 主要操作/链接 */
--primary-hover:  #818cf8;       /* 主色 Hover */
--primary-muted:  rgba(99,102,241,0.15); /* 主色背景 */

/* 成功/危险/警告 */
--success:        #10b981;       /* Emerald */
--success-muted:  rgba(16,185,129,0.15);
--danger:         #ef4444;       /* Red */
--danger-muted:   rgba(239,68,68,0.15);
--warning:        #f59e0b;       /* Amber */
--warning-muted:  rgba(245,158,11,0.15);
--info:           #3b82f6;       /* Blue */

/* 文字 */
--text-primary:   #f1f5f9;       /* 主要文字：浅灰白 */
--text-secondary: #94a3b8;       /* 次要文字 */
--text-muted:     #64748b;       /* 占位符/禁用 */
--text-inverse:   #0a0a0f;       /* 反色文字（用于亮色背景）*/

/* 状态颜色（与 frontend 完全一致）*/
--status-online:   #22c55e;      /* 🟢 在线 */
--status-busy:    #f59e0b;       /* 🟡 忙碌 */
--status-offline: #ef4444;       /* 🔴 离线 */
--status-idle:    #6b7280;       /* 灰色-空闲 */

/* Glow 效果（Cyberpunk 风格）*/
--glow-primary:   0 0 20px rgba(99,102,241,0.4);
--glow-success:    0 0 15px rgba(16,185,129,0.4);
--glow-danger:     0 0 15px rgba(239,68,68,0.4);
--glow-warning:    0 0 15px rgba(245,158,11,0.4);
```

### 2.3 间距系统

```css
/* 8px 基准网格 */
--space-1:  4px;
--space-2:  8px;
--space-3:  12px;
--space-4:  16px;
--space-5:  20px;
--space-6:  24px;
--space-8:  32px;
--space-10: 40px;
--space-12: 48px;
--space-16: 64px;
```

### 2.4 圆角

```css
--radius-sm:   4px;   /* 标签/徽章 */
--radius-md:   8px;   /* 按钮/输入框/卡片 */
--radius-lg:   12px;  /* 面板/Modal */
--radius-xl:   16px;  /* 大卡片 */
--radius-full: 9999px; /* 胶囊按钮/头像 */
```

### 2.5 阴影

```css
--shadow-sm:   0 1px 2px rgba(0,0,0,0.4);
--shadow-md:   0 4px 12px rgba(0,0,0,0.5);
--shadow-lg:   0 8px 24px rgba(0,0,0,0.6);
--shadow-glow: 0 0 30px rgba(99,102,241,0.2);
```

### 2.6 动效规范

```css
/* 过渡 */
--transition-fast:   150ms ease;
--transition-normal: 250ms ease;
--transition-slow:   400ms ease;

/* 告警闪烁动画（Command Center 用）*/
@keyframes pulse-danger {
  0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.4); }
  50% { box-shadow: 0 0 20px 4px rgba(239,68,68,0.6); }
}
.alert-flash { animation: pulse-danger 1.5s ease-in-out infinite; }

/* 数字滚动动画 */
@keyframes count-up {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
```

### 2.7 断点与响应式

```css
/* 断点 */
--breakpoint-sm:  640px;   /* 手机横屏 */
--breakpoint-md:  768px;   /* 平板 */
--breakpoint-lg: 1024px;   /* 小屏笔记本 */
--breakpoint-xl: 1280px;   /* 标准屏 */
--breakpoint-2xl: 1536px;  /* 大屏 */

/* Command Center 强制 1080p+ */
@media (min-width: 1920px) {
  :root { --font-size-base: 18px; }
}
```

---

## 3. 完整数据清单

### 3.1 SQLite 数据库表（civilization.db）

路径：`/Users/gujun/vibecode/usmsb/data/db/civilization.db`

#### agents 表

| 字段 | 类型 | 说明 |
|------|------|------|
| agent_id | TEXT PRIMARY KEY | Agent 唯一标识（如 `agent_abc123`）|
| name | TEXT | 显示名称 |
| agent_type | TEXT | `ai` / `human` / `system` |
| status | TEXT | `online` / `busy` / `offline` |
| stake | REAL | 质押 VIBE 数量 |
| reputation | REAL | 信誉分 0.0-5.0 |
| vibe_balance | REAL | VIBE 余额 |
| capabilities | TEXT | JSON 数组，如 `["coding","reasoning"]` |
| skills | TEXT | JSON 数组，如 `["Python","JavaScript"]` |
| endpoint | TEXT | 服务端点 URL |
| owner_wallet | TEXT | 所属钱包地址 |
| binding_status | TEXT | `wallet` / `manual` / `agent` |
| last_heartbeat | INTEGER | Unix 时间戳（秒）|
| created_at | INTEGER | 创建时间戳 |

#### agent_wallets 表

| 字段 | 类型 | 说明 |
|------|------|------|
| agent_id | TEXT | 外键 → agents.agent_id |
| wallet_address | TEXT | 合约钱包地址 |
| vibe_balance | REAL | VIBE 余额 |
| staked_amount | REAL | 已质押数量 |
| stake_status | TEXT | `none` / `staked` / `unstaking` / `unlocked` |
| max_per_tx | REAL | 单笔交易限额 |
| daily_limit | REAL | 日限额 |
| daily_spent | REAL | 当日已消耗 |
| locked_stake | REAL | 锁定的质押 |

#### users 表

| 字段 | 类型 | 说明 |
|------|------|------|
| wallet_address | TEXT PRIMARY KEY | 钱包地址（0x 开头）|
| did | TEXT | DID（可选）|
| agent_id | TEXT | 关联的 Agent ID |
| role | TEXT | `superadmin` / `developer` / `node_admin` / `node_operator` / `human` / `ai_owner` / `ai_agent` |
| stake | REAL | 质押量 |
| reputation | REAL | 信誉分 |
| vibe_balance | REAL | 余额 |
| stake_status | TEXT | `none` / `staked` / `unstaking` / `unlocked` |
| locked_stake | REAL | 锁定量 |
| unlock_available_at | INTEGER | 可解锁时间戳 |
| created_at | INTEGER | 注册时间 |

#### services 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | 服务 ID |
| agent_id | TEXT | 服务提供方 |
| service_name | TEXT | 服务名称 |
| category | TEXT | 服务类别 |
| skills | TEXT | JSON 技能数组 |
| price | REAL | 价格 |
| price_type | TEXT | `fixed` / `hourly` / `monthly` |
| status | TEXT | `active` / `paused` / `deleted` |

#### demands 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | 需求 ID |
| agent_id | TEXT | 发布方 |
| title | TEXT | 需求标题 |
| category | TEXT | 类别 |
| required_skills | TEXT | JSON 数组 |
| budget_min | REAL | 最低预算 |
| budget_max | REAL | 最高预算 |
| status | TEXT | `open` / `matched` / `closed` / `cancelled` |
| priority | TEXT | `low` / `medium` / `high` |

#### transactions 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | 交易 ID |
| buyer_id | TEXT | 买方（钱包或 agent_id）|
| seller_id | TEXT | 卖方（钱包或 agent_id）|
| amount | REAL | 金额（VIBE）|
| status | TEXT | `pending` / `completed` / `failed` / `refunded` |
| transaction_type | TEXT | `payment` / `stake` / `reward` / `refund` / `governance` |
| escrow_tx_hash | TEXT | 链上 Escrow TxHash |
| rating | INTEGER | 评分 1-5（可选）|
| review | TEXT | 评价（可选）|
| created_at | INTEGER | 创建时间戳 |
| completed_at | INTEGER | 完成时间戳 |

#### orders 表

| 字段 | 类型 | 说明 |
|------|------|------|
| order_id | TEXT PRIMARY KEY | 订单号 |
| demand_agent_id | TEXT | 需求方 agent_id |
| supply_agent_id | TEXT | 供给方 agent_id |
| status | TEXT | `pending` / `in_progress` / `delivered` / `completed` / `cancelled` / `disputed` |
| priority | TEXT | `low` / `medium` / `high` |
| vibe_locked | REAL | 锁定金额 |
| chain_order_id | TEXT | 链上 JointOrder Pool ID |
| created_at | INTEGER | 创建时间 |
| completed_at | INTEGER | 完成时间 |

#### negotiations 表

| 字段 | 类型 | 说明 |
|------|------|------|
| session_id | TEXT PRIMARY KEY | 协商会话 ID |
| initiator_id | TEXT | 发起方 |
| counterpart_id | TEXT | 对应方 |
| status | TEXT | `active` / `agreed` / `failed` / `cancelled` |
| rounds | INTEGER | 协商轮数 |
| created_at | INTEGER | 创建时间 |

#### opportunities 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | 机会 ID |
| demand_id | TEXT | 关联需求 |
| supplier_agent_id | TEXT | 推荐供给方 |
| match_score | REAL | 匹配分数 0.0-1.0 |
| status | TEXT | `pending` / `accepted` / `rejected` |

#### collaborations 表

| 字段 | 类型 | 说明 |
|------|------|------|
| session_id | TEXT PRIMARY KEY | 协作会话 ID |
| goal | TEXT | 协作目标描述 |
| participants | TEXT | JSON 数组 [agent_id, ...] |
| status | TEXT | `active` / `completed` / `failed` |
| result | TEXT | 结果描述（完成后）|

#### workflows 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | 工作流 ID |
| agent_id | TEXT | 所属 Agent |
| name | TEXT | 工作流名称 |
| status | TEXT | `running` / `paused` / `completed` / `failed` |
| steps | TEXT | JSON 数组步骤 |
| result | TEXT | 执行结果 |

#### proposals 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | 提案 ID |
| title | TEXT | 提案标题 |
| proposer_id | TEXT | 发起人钱包 |
| proposal_type | TEXT | `general` / `incentive` / `parameter` / `emergency` |
| status | TEXT | `active` / `passed` / `rejected` / `expired` |
| votes_for | REAL | 赞成票数 |
| votes_against | REAL | 反对票数 |
| deadline | INTEGER | 投票截止时间戳 |
| description | TEXT | 提案正文 |

#### votes 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | 投票记录 ID |
| proposal_id | TEXT | 所属提案 |
| voter_id | TEXT | 投票人钱包 |
| vote | TEXT | `for` / `against` / `abstain` |
| weight | REAL | 投票权重 |

#### agent_api_keys 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | Key ID |
| agent_id | TEXT | 所属 Agent |
| key_prefix | TEXT | Key 前缀（如 `sk_live_abc`）|
| permissions | TEXT | JSON 权限数组 |
| level | TEXT | `read` / `write` / `admin` |
| expires_at | INTEGER | 过期时间戳 |
| last_used_at | INTEGER | 最后使用时间 |

#### environments 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | 环境 ID |
| name | TEXT | 环境名称 |
| type | TEXT | `test` / `staging` / `production` |
| state | TEXT | JSON 状态对象 |

#### learning_insights 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | 洞察 ID |
| agent_id | TEXT | 所属 Agent |
| insights | TEXT | JSON 洞察内容 |
| strategy | TEXT | 学习策略 |
| market_analysis | TEXT | 市场分析 JSON |

#### audit_logs 表（新建）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | 日志 ID |
| operator_wallet | TEXT | 操作人钱包 |
| operation_type | TEXT | 操作类型（见下表）|
| target_type | TEXT | 目标类型（`agent` / `user` / `config` / `proposal`）|
| target_id | TEXT | 目标 ID |
| old_value | TEXT | 旧值（JSON）|
| new_value | TEXT | 新值（JSON）|
| ip_address | TEXT | IP 地址 |
| user_agent | TEXT | User Agent |
| created_at | INTEGER | 操作时间戳 |

**operation_type 枚举值：**

| 值 | 说明 |
|----|------|
| `agent_freeze` | 冻结 Agent |
| `agent_unfreeze` | 解冻 Agent |
| `agent_delete` | 删除 Agent |
| `role_change` | 角色变更 |
| `config_update` | 配置更新 |
| `proposal_create` | 创建提案 |
| `proposal_vote` | 提案投票 |
| `api_key_reset` | 重置 API Key |
| `wallet_unbind` | 解绑钱包 |
| `emergency_action` | 紧急操作 |

---

### 3.2 现有 REST API 端点

| 端点 | 方法 | 认证 | 说明 |
|------|------|------|------|
| `/api/metrics` | GET | 公开 | 全局运营指标 |
| `/api/status` | GET | 公开 | 系统状态 |
| `/api/stats/summary` | GET | 需认证 | 统计摘要 |
| `/api/health` | GET | 公开 | 服务健康检查 |
| `/api/agents` | GET | 需认证 | Agent 列表（支持 type/status/protocol 筛选）|
| `/api/agents/:id` | GET | 需认证 | Agent 详情 |
| `/api/agents/:id/capabilities` | GET | 需认证 | Agent 能力 |
| `/api/demands` | GET | 需认证 | 需求列表 |
| `/api/services` | GET | 需认证 | 服务列表 |
| `/api/transactions` | GET | 需认证 | 交易流水（支持分页/筛选）|
| `/api/orders` | GET | 需认证 | 订单列表 |
| `/api/orders/:id` | GET | 需认证 | 订单详情 |
| `/api/negotiations` | GET | 需认证 | 协商会话 |
| `/api/opportunities` | GET | 需认证 | 匹配机会 |
| `/api/collaborations` | GET | 需认证 | 协作会话 |
| `/api/workflows` | GET | 需认证 | 工作流列表 |
| `/api/workflows/:id` | GET | 需认证 | 工作流详情 |
| `/api/governance/proposals` | GET | 需认证 | 提案列表 |
| `/api/governance/proposals/:id` | GET | 需认证 | 提案详情 |
| `/api/governance/votes` | POST | 需认证 | 投票 |
| `/api/gene-capsule/:agent_id` | GET | 公开 | Gene Capsule |
| `/api/gene-capsule/:agent_id/summary` | GET | 公开 | Gene Capsule 摘要 |
| `/api/meta-agent/evolution-stats` | GET | 需认证 | MetaAgent 进化统计 |
| `/api/meta-agent/learning-insights` | GET | 需认证 | 学习洞察 |
| `/api/wallet/balance` | GET | 需认证 | 钱包余额 |
| `/api/wallet/transactions` | GET | 需认证 | 钱包交易历史 |
| `/api/auth/nonce` | GET | 公开 | 获取 nonce |
| `/api/auth/verify` | POST | 公开 | SIWE 签名验证 |
| `/api/auth/verify-message` | POST | 需认证 | 验证签名消息 |
| `/api/config` | GET | 需认证 | 系统配置 |

---

### 3.3 区块链合约数据（Base Sepolia）

**网络**：`baseSepolia`
**配置**：`contracts/deployments/latest.json`
**RPC**：`https://sepolia.base.org`（或 Infura/Alchemy 的 Base Sepolia 端点）

#### 29 个已部署合约完整列表

| # | 合约名 | 地址（完整）| 用途 |
|---|--------|-----------|------|
| 1 | VIBEToken | `0x93C52dF000317e12F891474B46d8B05652430bDC` | ERC20 代币 |
| 2 | VIBStaking | `0x1901Ab56eA38cBeFc7a3F0Ed188B7108d27f4c05` | 质押合约 |
| 3 | VIBVesting | `0x4d3008550fc164ccf0e1C0C4f666E77FC14dE924` | 归属释放 |
| 4 | VIBReserve | `0x56AbAf5fc5d58c92C0A51F79251BF3A3002f4263` | 储备金 |
| 5 | VIBProtocolFund | `0x0F39011e7E542D939C1dce40754a86b01BB3fA5a` | 协议基金 |
| 6 | VIBInfrastructurePool | `0xFc2943d6D426D4D6433944e1ADa4D475F3552500` | 基础设施池 |
| 7 | VIBBuilderReward | `0x397Faf7D727db190fB677362B15c091f1d94F7b3` | Builder 奖励 |
| 8 | VIBDevReward | `0x1a5E99b52e87E718906e8516fDD9c8775Ee0351E` | 开发者奖励 |
| 9 | VIBIdentity | `0x978eddDf11728B4e6A6C461D8806eD5f4339D466` | 身份注册 |
| 10 | VIBNodeReward | `0xc417b180F3b743A51e86c16A8319Eac353fDC29b` | 节点奖励 |
| 11 | VIBCollaboration | `0xe568c56f467E27Cb38d4B132B02318C81EC29D78` | 协作分成 |
| 12 | VIBDividend | `0xa820F9E9Caa90e405452Fc3f24DC5DF7f7d70E9D` | 分红池 |
| 13 | AgentRegistry | `0xC5AbAE9f580C48D645bDE9904712891AE8FcDec6` | Agent 注册表 |
| 14 | ZKCredential | `0x59EE17f1E914ba2de89F080CF44FC46Ee46DF874` | ZK 凭证 |
| 15 | AssetVault | `0x0F5C6Ae463f78aD30De1C9c6BF180423F0A39897` | 资产金库 |
| 16 | JointOrder | `0x55f4b49c9C269Fccf6d90e16304654b7F69138d0` | 联合订单 |
| 17 | PriceOracle | `0x20306509a6b2f0b56ad55C193b4505CA5E62bc48` | 价格预言机 |
| 18 | VIBOutputReward | `0x7b3CEB40CFb093e66EcD5b49F835586Ba7Ef428b` | Output 奖励 |
| 19 | VIBEcosystemPool | `0x20A25378DB87a94E19A8b51ED638F67d6e9BfE06` | 生态池 |
| 20 | AirdropDistributor | `0x01cdC2C7C3Deb071e6C7B42ED66884DDd3CADDf6` | 空投分发 |
| 21 | CommunityStableFund | `0x6e616E6B1d63709dA849074bb7cd5A6936350563` | 社区稳定基金 |
| 22 | LiquidityManager | `0x5c11b7f74bBb2dbBE232C6A456eCa64DA4722D42` | 流动性管理 |
| 23 | VIBGovernance | `0x27475aea1eEba485005B1717a35a7D411d144a1d` | 治理核心 |
| 24 | VIBGovernanceDelegation | `0x47428bAB428966B32F246a3e9456f10dc70141A5` | 投票委托 |
| 25 | VIBContributionPoints | `0x60D9244bF262bF85Fd3057C95Ca00fEa1622f3E5` | 贡献积分 |
| 26 | VIBVEPoints | `0xB2b56dce955ab200E0c1888C22Ac711803e607F1` | veVIBE |
| 27 | VIBDispute | `0xE32d99daDBd4443423EfDc590af7591f84FAFE7e` | 争议仲裁 |
| 28 | AgentWallet | `0xeAd5FCC931493F702208B737528578718D681243` | Agent 钱包 |
| 29 | EmissionController | `0xaeD496480c9668dc90Dc309fCD8Fd9aE4268dF39` | 发行控制 |

#### 合约 ABI 与 Read 函数完整清单

**VIBStaking（#2）**

| 函数 | 纯/视 | 返回类型 | 用途 |
|------|-------|---------|------|
| `totalStaked()` | view | uint256 | 总质押量（wei）|
| `getStakerCount()` | view | uint256 | Staker 人数 |
| `currentAPY()` | view | uint256 | 当前 APY（basist points，850 = 8.5%）|
| `getDynamicAPY()` | view | uint256 | 动态 APY（含奖励加成）|
| `getPendingReward(address user)` | view | uint256 | 用户待领奖励 |
| `getStakeInfo(address user)` | view | StakeInfo struct | 用户完整质押信息 |
| `getStakeDetails(address user)` | view | (uint256,uint256,uint256,uint256) | 质押量/开始时间/解锁时间/锁定期 |
| `getUserTier(address user)` | view | uint8 | 用户等级（0=Bronze,1=Silver,2=Gold,3=Platinum）|
| `getVotingPower(address user)` | view | uint256 | 用户投票权（考虑时间加成）|
| `getTimeMultiplier(address user)` | view | uint256 | 时间乘数（x10000）|
| `getStakers(uint256 offset, uint256 limit)` | view | address[] | 分页获取 Staker 列表 |
| `stakers(uint256 index)` | view | address | 按索引获取 Staker 地址 |
| `isStaker(address)` | view | bool | 是否为 Staker |
| `totalRewardsDistributed()` | view | uint256 | 累计发放奖励总量 |
| `paused()` | view | bool | 合约是否暂停 |
| `vibeToken()` | view | address | VIBE Token 地址 |
| `priceOracle()` | view | address | PriceOracle 地址 |
| `emissionController()` | view | address | EmissionController 地址 |
| `MIN_APY()` | pure | uint256 | 最小 APY = 300（3%）|
| `MAX_APY()` | pure | uint256 | 最大 APY = 1000（10%）|
| `TIME_MULTIPLIER_1/2/3/4()` | pure | uint256 | 时间质押乘数 |

**VIBEToken（#1）**

| 函数 | 纯/视 | 返回类型 | 用途 |
|------|-------|---------|------|
| `totalSupply()` | view | uint256 | 总供给量 |
| `balanceOf(address account)` | view | uint256 | 账户余额 |
| `TRANSACTION_TAX_RATE()` | pure | uint256 | 交易税率（300 = 0.3%）|
| `BURN_RATIO()` | pure | uint256 | 燃烧比例（30 = 税的 30%）|
| `DIVIDEND_RATIO()` | pure | uint256 | 分红比例（40）|
| `ECOSYSTEM_FUND_RATIO()` | pure | uint256 | 生态基金比例（15）|
| `PROTOCOL_FUND_RATIO()` | pure | uint256 | 协议基金比例（15）|
| `getTaxBreakdown(uint256 value)` | view | (uint256 burn, uint256 dividend, uint256 ecosystem, uint256 protocol) | 税务分解 |
| `getNetTransferAmount(uint256 value)` | view | uint256 | 扣除税务后净额 |
| `allowance(address owner, address spender)` | view | uint256 | 授权额度 |
| `dividendContract()` | view | address | 分红合约地址 |
| `ecosystemFundContract()` | view | address | 生态基金地址 |
| `protocolFundContract()` | view | address | 协议基金地址 |
| `name()` | view | string | 代币名称 |
| `symbol()` | view | string | 代币符号 |
| `decimals()` | view | uint8 | 精度 = 18 |

**AgentRegistry（#13）**

| 函数 | 纯/视 | 返回类型 | 用途 |
|------|-------|---------|------|
| `getAgentCount()` | view | uint256 | 已注册 Agent 总数 |
| `getAgentAt(uint256 index)` | view | address | 按索引获取 Agent 地址 |
| `isValidAgent(address wallet)` | view | bool | 地址是否有效 |
| `isRegistered(address wallet)` | view | bool | 是否已注册 |
| `getAgentOwner(address agent)` | view | address | Agent Owner 地址 |
| `getOwnerAgentCount(address owner)` | view | uint256 | Owner 拥有的 Agent 数量 |
| `owner()` | view | address | 合约 Owner（超级管理员）|

**VIBIdentity（#9）**

| 函数 | 纯/视 | 返回类型 | 用途 |
|------|-------|---------|------|
| `getCountByType(uint8 identityType)` | view | uint256 | 按类型统计注册数 |
| `getIdentityInfo(uint256 tokenId)` | view | IdentityInfo struct | tokenId 对应身份信息 |
| `getTokenIdByAddress(address owner)` | view | uint256 | 地址对应的 tokenId |
| `getIdentityType(uint256 tokenId)` | view | uint8 | tokenId 的身份类型 |
| `getVerifiedCount()` | view | uint256 | 已验证身份总数 |
| `getUserAgentCount(address user)` | view | uint256 | 用户拥有的 Agent 数量 |
| `getAgentLimit(address user)` | view | uint256 | 用户可创建 Agent 数量上限 |
| `getAgentCreator(address agent)` | view | address | Agent 创建者 |
| `addressToTokenId(address)` | view | uint256 | 地址→TokenId 映射 |
| `balanceOf(address owner)` | view | uint256 | owner 持有的 NFT 数量 |

**VIBGovernance（#23）**

| 函数 | 纯/视 | 返回类型 | 用途 |
|------|-------|---------|------|
| `cachedTotalVotingPower()` | view | uint256 | 缓存的总投票权 |
| `getProposalCount()` | view | uint256 | 提案总数 |
| `getProposal(uint256 proposalId)` | view | Proposal struct | 提案详情 |
| `getVoteRecord(uint256 proposalId, address voter)` | view | VoteRecord struct | 某人对某提案的投票 |
| `proposalStates(uint256 proposalId)` | view | uint8 | 提案状态（0=Created,1=Active...）|
| `MIN_STAKE_REQUIREMENT()` | pure | uint256 | 最低质押门槛 |
| `MIN_VOTING_HOLD_PERIOD()` | pure | uint256 | 最短持仓期（秒）|
| `proposalInfo(uint256)` | view | ProposalInfo struct | 提案信息（简化视图）|

**VIBDividend（#12）**

| 函数 | 纯/视 | 返回类型 | 用途 |
|------|-------|---------|------|
| `dividendBalance()` | view | uint256 | 待分配红利余额 |
| `totalDividendsDistributed()` | view | uint256 | 累计已分配红利 |
| `getPendingDividend(address user)` | view | uint256 | 用户待领红利 |
| `lastClaimTime(address user)` | view | uint256 | 用户上次领取时间 |
| `getBalance()` | view | uint256 | 合约当前余额 |
| `stakingContract()` | view | address | 关联的 Staking 合约 |

**VIBOutputReward（#18）**

| 函数 | 纯/视 | 返回类型 | 用途 |
|------|-------|---------|------|
| `getBalance()` | view | uint256 | 奖池余额 |
| `getTypeBudgetRemaining(uint8 outputType)` | view | uint256 | 某类型预算剩余 |
| `getOutputInfo(bytes32 outputId)` | view | OutputRecord struct | Output 记录 |
| `totalOutputs()` | view | uint256 | Output 总数 |
| `getDailyPool(uint256 day)` | view | uint256 | 某日奖池金额 |

**VIBBuilderReward（#7）**

| 函数 | 纯/视 | 返回类型 | 用途 |
|------|-------|---------|------|
| `getBalance()` | view | uint256 | 奖池余额 |
| `builderCount()` | view | uint256 | Builder 记录总数（含重复）|
| `builderCountUnique()` | view | uint256 | 去重 Builder 数 |
| `getBuilderStats(address builder)` | view | (uint256 points, uint256 totalReward, bool claimed) | Builder 统计 |
| `getBuilderRecord(bytes32 recordId)` | view | BuilderRecord struct | 记录详情 |
| `isBuilder(address)` | view | bool | 是否为 Builder |

**VIBDevReward（#8）**

| 函数 | 纯/视 | 返回类型 | 用途 |
|------|-------|---------|------|
| `getBalance()` | view | uint256 | 奖池余额 |
| `developerCount()` | view | uint256 | 开发者总数 |
| `contributionCount()` | view | uint256 | 贡献记录总数 |
| `getDeveloperStats(address developer)` | view | (uint256 points, uint256 totalReward, bool claimed) | 开发者统计 |
| `getContributionRecord(bytes32 contribId)` | view | ContributionRecord struct | 贡献记录 |
| `isDeveloper(address)` | view | bool | 是否为开发者 |

**VIBNodeReward（#10）**

| 函数 | 纯/视 | 返回类型 | 用途 |
|------|-------|---------|------|
| `getBalance()` | view | uint256 | 奖池余额 |
| `getNodeInfo(address node)` | view | NodeInfo struct | 节点信息（算力/质量/可靠性）|
| `getNodeTotalRewards(address node)` | view | uint256 | 节点累计奖励 |
| `getComputeCredits(address node)` | view | uint256 | 节点计算积分 |

**VIBCollaboration（#11）**

| 函数 | 纯/视 | 返回类型 | 用途 |
|------|-------|---------|------|
| `projectCount()` | view | uint256 | 协作项目总数 |
| `getProjectInfo(bytes32 projectId)` | view | CollaborationProject struct | 项目详情 |
| `getContributors(bytes32 projectId)` | view | address[] | 项目贡献者列表 |
| `getContributorCount(bytes32 projectId)` | view | uint256 | 贡献者数量 |
| `getUserTotalIncome(address user)` | view | uint256 | 用户总收入 |

**VIBVesting（#3）**

| 函数 | 纯/视 | 返回类型 | 用途 |
|------|-------|---------|------|
| `getReleasableAmount(address beneficiary)` | view | uint256 | 受益人可释放金额 |
| `getVestedAmount(address beneficiary)` | view | uint256 | 受益人已释放金额 |
| `getBeneficiaryInfo(address beneficiary)` | view | BeneficiaryInfo struct | 受益人完整信息 |
| `getBeneficiaries(uint256 offset, uint256 limit)` | view | address[] | 分页获取受益人列表 |

**AssetVault（#15）**

| 函数 | 纯/视 | 返回类型 | 用途 |
|------|-------|---------|------|
| `getStats()` | view | AssetStats struct | 全局资产统计 |
| `getAssetInfo(bytes32 assetId)` | view | AssetInfo struct | 资产信息 |
| `getAssetShareholders(bytes32 assetId)` | view | address[] | 资产股东列表 |
| `getUserAssets(address user)` | view | bytes32[] | 用户持有的资产 ID 列表 |
| `getAvailableShares(bytes32 assetId)` | view | uint256 | 资产可购买份额 |

**PriceOracle（#17）**

| 函数 | 纯/视 | 返回类型 | 用途 |
|------|-------|---------|------|
| `getPrice()` | view | uint256 | 当前 VIBE/USD 价格（精度 1e6，即 $0.234500 = 234500）|
| `getPriceWithStalenessCheck()` | view | (uint256 price, bool isStale) | 含过期检查的价格 |
| `getTimeSinceLastUpdate()` | view | uint256 | 距上次更新秒数 |
| `get7DayAverage()` | view | uint256 | 7 日均价 |
| `getDetailedPrice()` | view | PriceData struct | 详细价格数据（含多个源）|
| `getPriceHistory(uint256 index)` | view | uint256 | 价格历史（按索引）|
| `getPriceHistoryLength()` | view | uint256 | 价格历史条数 |

**VIBEcosystemPool（#19）**

| 函数 | 纯/视 | 返回类型 | 用途 |
|------|-------|---------|------|
| `getBalance()` | view | uint256 | 生态池余额 |
| `getDistributionRecordCount()` | view | uint256 | 分配记录总数 |
| `getDistributionRecord(uint256 index)` | view | DistributionRecord struct | 分配记录详情 |

**VIBProtocolFund（#5）**

| 函数 | 纯/视 | 返回类型 | 用途 |
|------|-------|---------|------|
| `getBalance()` | view | uint256 | 基金余额 |
| `getAvailableBalance()` | view | uint256 | 可用余额（未锁定）|
| `getExpenseRequest(bytes32 requestId)` | view | ExpenseRequest struct | 支出申请详情 |
| `getPendingGovernanceReward(address user)` | view | uint256 | 用户待领治理奖励 |

**VIBReserve（#4）**

| 函数 | 纯/视 | 返回类型 | 用途 |
|------|-------|---------|------|
| `getBalance()` | view | uint256 | 储备金余额 |
| `getAvailableBalance()` | view | uint256 | 可用余额 |
| `getReserveStatus()` | view | ReserveStatus struct | 储备状态 |
| `getRefillHistoryCount()` | view | uint256 | 重填历史条数 |
| `getRefillHistory(uint256 index)` | view | RefillHistory struct | 重填历史详情 |

**EmissionController（#29）**

| 函数 | 纯/视 | 返回类型 | 用途 |
|------|-------|---------|------|
| `getReleasableAmount()` | view | uint256 | 可释放 Emission 量 |
| `getDistributionRatios()` | view | uint256[5] | 各池分配比例数组 |

**VIBDispute（#27）**

| 函数 | 纯/视 | 返回类型 | 用途 |
|------|-------|---------|------|
| `getDisputeCount()` | view | uint256 | 争议总数 |
| `getDispute(bytes32 disputeId)` | view | Dispute struct | 争议详情 |
| `getDisputeStatus(bytes32 disputeId)` | view | uint8 | 争议状态 |

**AirdropDistributor（#20）**

| 函数 | 纯/视 | 返回类型 | 用途 |
|------|-------|---------|------|
| `getClaimedCount()` | view | uint256 | 已领取人数 |
| `getUnclaimedTotal()` | view | uint256 | 未领取总额 |
| `isClaimed(address beneficiary)` | view | bool | 是否已领取 |

**VIBContributionPoints（#25）**

| 函数 | 纯/视 | 返回类型 | 用途 |
|------|-------|---------|------|
| `totalContributionPoints()` | view | uint256 | 全网总积分 |
| `getEffectiveContributionPoints(address user)` | view | uint256 | 用户有效积分 |
| `getUserContributionCount(address user)` | view | uint256 | 用户贡献记录数 |

**VIBVEPoints（#26）**

| 函数 | 纯/视 | 返回类型 | 用途 |
|------|-------|---------|------|
| `balanceOf(address account)` | view | uint256 | 账户 veVIBE 余额 |
| `totalSupply()` | view | uint256 | veVIBE 总供给 |

**VIBGovernanceDelegation（#24）**

| 函数 | 纯/视 | 返回类型 | 用途 |
|------|-------|---------|------|
| `delegates(address delegator)` | view | address | 委托人当前被委托者 |
| `delegatedVotes(address delegatee)` | view | uint256 | 被委托者拥有的委托票数 |

**ZKCredential（#14）**

| 函数 | 纯/视 | 返回类型 | 用途 |
|------|-------|---------|------|
| `getCredentialCount()` | view | uint256 | 已注册凭证总数 |
| `isValid(bytes32 credentialId)` | view | bool | 凭证是否有效 |

**JointOrder（#16）**

| 函数 | 纯/视 | 返回类型 | 用途 |
|------|-------|---------|------|
| `getStats()` | view | (uint256 totalPools, uint256 totalBids, uint256 totalVolume) | 订单统计 |
| `getPool(bytes32 poolId)` | view | OrderPool struct | 订单池详情 |
| `getPoolBids(bytes32 poolId)` | view | bytes32[] | 订单池所有报价 ID |
| `getUserPools(address user)` | view | bytes32[] | 用户参与的订单池 |
| `bids(bytes32 poolId, bytes32 bidId)` | view | Bid struct | 某报价详情 |

---

## 4. 页面结构与路由

### 4.1 路由定义

```
/admin                        # 入口 → 重定向到 /admin/dashboard
├── /dashboard                # 运营总览
├── /nodes                    # 节点管理
│   └── /nodes/:id           # 节点详情（弹窗/抽屉）
├── /agents                   # Agent 全局管理
│   └── /agents/:id           # Agent 详情（弹窗/抽屉）
├── /users                    # 用户管理
│   └── /users/:wallet        # 用户详情（弹窗/抽屉）
├── /transactions             # 交易流水
├── /orders                   # 订单管理
├── /matching                 # 匹配分析
├── /gene-capsules            # Gene Capsule 全局
│   └── /gene-capsules/:id   # 胶囊详情
├── /intelligence             # AI 能力分析
├── /governance               # 链上治理（提案投票）
├── /contracts                # 合约总览
│   ├── /contracts/staking   # 质押生态
│   ├── /contracts/rewards   # 奖励分发
│   ├── /contracts/governance # 治理合约
│   ├── /contracts/market    # 市场数据
│   └── /contracts/orders   # 订单与协作
├── /system                   # 系统管理
│   ├── /system/health        # 服务健康
│   ├── /system/config        # 运行时配置（superadmin）
│   └── /system/logs         # 日志查看（superadmin）
├── /permissions              # 权限管理（superadmin）
└── /command-center           # 大屏指挥调度（全屏路由）
```

### 4.2 路由守卫

```typescript
// AdminRoute.tsx
const ADMIN_ROLES = ['superadmin', 'node_admin']

function AdminRoute({ children, requiredRoles = ADMIN_ROLES }: Props) {
  const { user } = useAuthStore()

  if (!user) return <Navigate to="/login" replace />
  if (!requiredRoles.includes(user.role)) return <Navigate to="/403" replace />

  return <>{children}</>
}
```

---

## 5. Layout 布局规范

### 5.1 Admin Layout 组件结构

```
<AdminLayout>
  <AdminHeader />          ← 顶部栏（64px）
    ├── Logo + 平台名
    ├── Breadcrumb
    ├── 全局搜索栏（⌘K）
    ├── 通知铃铛（未读数）
    ├── WebSocket 连接状态
    └── 用户头像 + 下拉菜单
  <div flex>
    <AdminSidebar />       ← 侧边栏（可折叠，256px → 64px）
    <main class="flex-1 overflow-auto">
      <Outlet />           ← 页面内容区
    </main>
  </div>
  <ToastContainer />       ← 全局 Toast
</AdminLayout>
```

### 5.2 AdminHeader

高度：64px，固定定位，不随滚动。

```tsx
// AdminHeader.tsx
<div class="h-16 bg-bg-secondary border-b border-border-primary flex items-center px-6">
  {/* Logo */}
  <Link to="/admin" class="flex items-center gap-3">
    <LogoIcon class="w-8 h-8" />
    <span class="font-orbitron text-lg text-text-primary">USMSB Admin</span>
  </Link>

  {/* Breadcrumb */}
  <Breadcrumb class="ml-8" />

  {/* 全局搜索 */}
  <CommandPalette trigger={<SearchBar />} class="ml-auto mr-4" />

  {/* 通知 */}
  <NotificationBell />

  {/* 连接状态 */}
  <WebSocketStatus />

  {/* 用户菜单 */}
  <UserMenu />
</div>
```

### 5.3 AdminSidebar

宽度：256px（展开）/ 64px（折叠），高度 100vh，固定定位。

```tsx
// AdminSidebar.tsx
<div class={`${isCollapsed ? 'w-16' : 'w-64'} h-screen bg-bg-secondary border-r border-border-primary transition-all duration-300`}>
  <nav class="p-3 space-y-1">
    {navItems.map(item => (
      <NavLink key={item.path} to={item.path}>
        {({ isActive }) => (
          <div class={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors
            ${isActive ? 'bg-primary-muted text-primary border border-primary/30' : 'text-text-secondary hover:bg-bg-tertiary'}`}>
            <item.icon class="w-5 h-5 shrink-0" />
            {!isCollapsed && <span class="font-rajdhani font-medium">{item.label}</span>}
            {!isCollapsed && item.badge && (
              <Badge variant="danger" class="ml-auto">{item.badge}</Badge>
            )}
          </div>
        )}
      </NavLink>
    ))}
  </nav>

  {/* 折叠按钮 */}
  <button onClick={toggleCollapse} class="absolute bottom-4 left-1/2 -translate-x-1/2">
    {isCollapsed ? <ChevronRight /> : <ChevronLeft />}
  </button>
</div>
```

### 5.4 导航项定义

```typescript
const navItems = [
  { path: '/admin/dashboard',    label: '运营总览',     icon: LayoutDashboard, badge: null },
  { path: '/admin/nodes',        label: '节点管理',     icon: Server,         badge: null },
  { path: '/admin/agents',        label: 'Agent 管理',   icon: Bot,            badge: null },
  { path: '/admin/users',        label: '用户管理',     icon: Users,          badge: null },
  { path: '/admin/transactions', label: '交易流水',     icon: ArrowLeftRight, badge: null },
  { path: '/admin/orders',        label: '订单管理',     icon: ClipboardList, badge: null },
  { path: '/admin/matching',      label: '匹配分析',    icon: GitMerge,      badge: null },
  { path: '/admin/gene-capsules',label: 'Gene Capsule', icon: Dna,           badge: null },
  { path: '/admin/intelligence',  label: 'AI 能力',      icon: Brain,         badge: null },
  { path: '/admin/governance',    label: '治理投票',     icon: Vote,          badge: null },
  {
    path: '/admin/contracts',    label: '区块链合约',   icon: Hexagon,       badge: null,
    children: [
      { path: '/admin/contracts/staking',     label: '质押生态' },
      { path: '/admin/contracts/rewards',     label: '奖励分发' },
      { path: '/admin/contracts/governance',  label: '治理合约' },
      { path: '/admin/contracts/market',      label: '市场数据' },
      { path: '/admin/contracts/orders',      label: '订单协作' },
    ]
  },
  {
    path: '/admin/system',       label: '系统管理',     icon: Settings,
    children: [
      { path: '/admin/system/health',  label: '健康状态', superadminOnly: true },
      { path: '/admin/system/config',  label: '运行时配置', superadminOnly: true },
      { path: '/admin/system/logs',    label: '日志查看', superadminOnly: true },
    ]
  },
  { path: '/admin/permissions',  label: '权限管理',     icon: Shield,        badge: null, superadminOnly: true },
  { path: '/admin/command-center', label: '指挥中心',   icon: Monitor,       badge: null },
]
```

---

## 6. Dashboard 详细设计

### 6.1 Dashboard 页面结构

```
/admin/dashboard
│
├── <StatsGrid>           ← 第一行：6个统计卡片 × 2行
│   ├── <StatCard> totalAgents
│   ├── <StatCard> onlineAgents
│   ├── <StatCard> busyAgents
│   ├── <StatCard> offlineAgents
│   ├── <StatCard> totalUsers
│   ├── <StatCard> newUsersToday
│   ├── <StatCard> totalStake
│   ├── <StatCard> activeDemands
│   ├── <StatCard> activeServices
│   ├── <StatCard> activeOrders
│   ├── <StatCard> totalTransactions
│   └── <StatCard> platformRevenue
│
├── <MainContent>         ← 第二行：图表区 + 排行榜
│   ├── <ChartsPanel>     ← 左侧 2/3
│   │   ├── <Tabs>: [7天] [30天] [90天]
│   │   ├── <AgentTrendChart>   (Area Chart)
│   │   ├── <TransactionChart>  (Bar + Line 组合)
│   │   └── <StakeDistributionChart> (Pie + Line)
│   │
│   └── <RealtimePanel>   ← 右侧 1/3
│       ├── <LiveAgentFeed>
│       ├── <LiveTransactionFeed>
│       └── <PendingOrdersPanel>
│
└── <BottomTable>        ← 第三行：节点健康 + 最新交易
    ├── <NodeHealthTable>
    └── <RecentTransactionsTable>
```

### 6.2 StatCard 组件规格

```tsx
interface StatCardProps {
  title: string              // 卡片标题
  value: string | number     // 主数值
  change?: number            // 变化百分比（正=上升，负=下降）
  changeLabel?: string      // 变化标签（如 "vs yesterday"）
  icon: LucideIcon           // 图标组件
  color?: 'primary' | 'success' | 'danger' | 'warning' | 'info'
  loading?: boolean
  prefix?: string           // 前缀（如 "¥" 或 "$"）
  suffix?: string           // 后缀（如 "VIBE" 或 "%"）
  decimals?: number         // 小数位数（默认 0）
  sparklineData?: number[]  // 迷你趋势线数据（可选）
}

function StatCard({ title, value, change, icon: Icon, color = 'primary', prefix, suffix, sparklineData }: StatCardProps) {
  return (
    <div class="bg-bg-secondary rounded-xl border border-border-primary p-5 hover:border-border-active transition-all">
      <div class="flex items-start justify-between">
        <div>
          <p class="text-text-muted text-sm font-rajdhani">{title}</p>
          <p class="text-2xl font-orbitron font-bold text-text-primary mt-1">
            {prefix}{formattedValue}{suffix}
          </p>
          {change !== undefined && (
            <div class={`flex items-center gap-1 mt-2 text-sm
              ${change >= 0 ? 'text-success' : 'text-danger'}`}>
              {change >= 0 ? <TrendingUp class="w-4 h-4" /> : <TrendingDown class="w-4 h-4" />}
              <span>{Math.abs(change)}%</span>
              {changeLabel && <span class="text-text-muted ml-1">{changeLabel}</span>}
            </div>
          )}
        </div>
        <div class={`p-3 rounded-lg bg-${color}-muted`}>
          <Icon class={`w-6 h-6 text-${color}`} />
        </div>
      </div>
      {sparklineData && <Sparkline data={sparklineData} color={color} class="mt-3" />}
    </div>
  )
}
```

### 6.3 AgentTrendChart 规格

```tsx
// AgentTrendChart.tsx
// 类型：Area Chart
// 数据源：agents 表按 last_heartbeat 聚合（每小时统计一次）
// 刷新：每 60 秒

interface DataPoint {
  time: string      // "2026-05-19 14:00"
  online: number
  busy: number
  offline: number
  total: number
}

function AgentTrendChart({ data, timeRange }: { data: DataPoint[], timeRange: '7d' | '30d' | '90d' }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="colorOnline" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3}/>
            <stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
          </linearGradient>
          <linearGradient id="colorBusy" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3}/>
            <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
          </linearGradient>
          <linearGradient id="colorOffline" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
            <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#2d2d4a" />
        <XAxis dataKey="time" stroke="#64748b" fontSize={12} tickLine={false} />
        <YAxis stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
        <Tooltip content={<CustomTooltip />} />
        <Area type="monotone" dataKey="online" stroke="#22c55e" strokeWidth={2} fill="url(#colorOnline)" stackId="1" />
        <Area type="monotone" dataKey="busy" stroke="#f59e0b" strokeWidth={2} fill="url(#colorBusy)" stackId="1" />
        <Area type="monotone" dataKey="offline" stroke="#ef4444" strokeWidth={2} fill="url(#colorOffline)" stackId="1" />
        <Legend formatter={(value) => <span class="text-text-secondary">{value}</span>} />
      </AreaChart>
    </ResponsiveContainer>
  )
}
```

### 6.4 RealtimePanel 实时推送规格

```tsx
// Live数据通过 WebSocket 推送，fallback 5s 轮询
// 连接: ws://host/api/admin/realtime

interface RealtimeEvent {
  type: 'agent_status_change' | 'transaction_new' | 'order_status_change' | 'node_heartbeat'
  data: any
  timestamp: number
}

// 组件内使用
useEffect(() => {
  const ws = new WebSocket(`${WS_BASE}/api/admin/realtime?token=${accessToken}`)
  ws.onmessage = (event) => {
    const msg: RealtimeEvent = JSON.parse(event.data)
    switch (msg.type) {
      case 'agent_status_change':
        setAgents(prev => [msg.data, ...prev.slice(0, 9)])  // 保留最新10条
        break
      case 'transaction_new':
        setTransactions(prev => [msg.data, ...prev.slice(0, 9)])
        break
    }
  }
  return () => ws.close()
}, [])
```

### 6.5 NodeHealthTable 规格

```tsx
// 节点健康表格
// 数据来源: /api/admin/nodes (新建 API)
// 实时数据通过 WebSocket node_heartbeat 事件更新

interface NodeHealthRow {
  nodeId: string
  name: string
  agentCount: number
  onlineCount: number
  cpuPercent: number    // 0-100
  memoryPercent: number
  networkLatency: number  // ms
  status: 'online' | 'warning' | 'critical'
  lastHeartbeat: number   // Unix timestamp
}

// 行颜色编码
// status = 'online' → 整行无高亮
// status = 'warning' → cpu 或 memory > 70% → 行背景 amber/10
// status = 'critical' → cpu 或 memory > 85% → 行背景 red/10 + 闪烁

// 告警阈值（可配置）:
// cpuWarning: 70, cpuCritical: 85
// memoryWarning: 75, memoryCritical: 90
// latencyWarning: 100, latencyCritical: 500 (ms)
```

### 6.6 Dashboard API 调用

```typescript
// /api/admin/dashboard/stats
// GET，返回所有卡片数据（一次拉取，避免 N+1）

interface DashboardStats {
  // Agent 统计
  totalAgents: number
  onlineAgents: number
  busyAgents: number
  offlineAgents: number
  newAgentsToday: number
  agentTrend: { time: string; online: number; busy: number; offline: number }[]

  // 用户统计
  totalUsers: number
  newUsersToday: number

  // 质押统计
  totalStake: string     // VIBE 字符串（大数）
  totalStakeUsd: number  // USD 估值

  // 业务统计
  activeDemands: number
  activeServices: number
  activeOrders: number
  pendingOrders: number
  totalTransactions: number
  todayTransactionCount: number
  todayTransactionVolume: string   // VIBE
  platformRevenue: string          // VIBE（含手续费）

  // 实时
  lastBlockNumber: number
  lastBlockTimestamp: number
  vibePriceUsd: number
  stakeDistribution: {
    none: number
    bronze: number
    silver: number
    gold: number
    platinum: number
  }
}
```

---

## 7. Command Center 详细设计

### 7.1 独立全屏路由

```
URL: /admin/command-center
特点: 无 Sidebar、无 Header、强制 dark theme、全屏、F11 支持
刷新: 5s 自动刷新（可调整 5s/10s/30s/暂停）
```

### 7.2 页面布局（4 分区）

```
┌─────────────────────────────────────────────────────────┐
│  HEADER: USMSB 指挥中心  |  时间  |  刷新: [5s▼]  [⏸]  [⛶] [⚙] │
├────────────────────────────┬────────────────────────────┤
│                            │                            │
│   PANEL 1                  │   PANEL 2                  │
│   实时 Agent 状态           │   全局交易状态               │
│   (环形图 + 数字看板)       │   (金额 + 笔数 + 趋势)      │
│                            │                            │
├────────────────────────────┼────────────────────────────┤
│                            │                            │
│   PANEL 3                  │   PANEL 4                  │
│   匹配效率实时看板           │   节点健康状态               │
│   (漏斗图 + 转化率)         │   (状态列表 + 服务)         │
│                            │                            │
├────────────────────────────┴────────────────────────────┤
│  ALERT BAR: [⚠️ 告警信息滚动字幕]              [📢 广播]│
└─────────────────────────────────────────────────────────┘
```

### 7.3 Panel 1 — 实时 Agent 状态

```tsx
// AgentStatusPanel.tsx

function AgentStatusPanel({ data }: { data: AgentStatusData }) {
  const { online, busy, offline, total, newToday, offlineToday } = data

  return (
    <div class="h-full flex flex-col p-6 bg-bg-secondary rounded-2xl border border-border-primary">
      <h2 class="font-orbitron text-lg text-text-primary mb-6">实时 Agent 状态</h2>

      {/* 环形图 */}
      <div class="relative w-48 h-48 mx-auto">
        <ResponsiveContainer>
          <PieChart>
            <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={90}
              paddingAngle={2} startAngle={90} endAngle={-270}>
              <Pie dataKey="value" fill="#22c55e" />   {/* online */}
              <Pie dataKey="value" fill="#f59e0b" />   {/* busy */}
              <Pie dataKey="value" fill="#ef4444" />   {/* offline */}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        {/* 中心数字 */}
        <div class="absolute inset-0 flex flex-col items-center justify-center">
          <span class="font-orbitron text-4xl font-bold text-text-primary">{total.toLocaleString()}</span>
          <span class="text-text-muted text-sm">总计</span>
        </div>
      </div>

      {/* 状态列表 */}
      <div class="mt-6 space-y-3">
        {[
          { label: '🟢 在线', value: online, color: 'text-success' },
          { label: '🟡 忙碌', value: busy, color: 'text-warning' },
          { label: '🔴 离线', value: offline, color: 'text-danger', alert: offline / total > 0.15 },
        ].map(item => (
          <div key={item.label} class="flex items-center justify-between">
            <span class={item.color}>{item.label}</span>
            <span class={`font-orbitron text-xl ${item.color}`}>{item.value.toLocaleString()}</span>
          </div>
        ))}
      </div>

      {/* 底部统计 */}
      <div class="mt-auto pt-4 border-t border-border-primary grid grid-cols-2 gap-4">
        <div>
          <p class="text-text-muted text-xs">今日新增</p>
          <p class="text-success font-orbitron text-lg">+{newToday}</p>
        </div>
        <div>
          <p class="text-text-muted text-xs">今日下线</p>
          <p class="text-danger font-orbitron text-lg">-{offlineToday}</p>
        </div>
      </div>
    </div>
  )
}
```

### 7.4 Panel 2 — 全局交易状态

```tsx
function TransactionPanel({ data }: { data: TransactionPanelData }) {
  const { todayVolume, todayCount, avgAmount, successRate, volumeTrend } = data

  return (
    <div class="h-full flex flex-col p-6 bg-bg-secondary rounded-2xl border border-border-primary">
      <h2 class="font-orbitron text-lg text-text-primary mb-6">全局交易状态</h2>

      {/* 主指标 */}
      <div class="space-y-4">
        <div>
          <p class="text-text-muted text-xs">今日交易金额</p>
          <p class="font-orbitron text-4xl font-bold text-text-primary">
            {formatVIBE(todayVolume)}
          </p>
          <p class="text-success text-sm">↑ {data.volumeChangePercent}%</p>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <p class="text-text-muted text-xs">交易笔数</p>
            <p class="font-orbitron text-2xl text-text-primary">{todayCount.toLocaleString()}</p>
          </div>
          <div>
            <p class="text-text-muted text-xs">成功率</p>
            <p class="font-orbitron text-2xl text-success">{successRate}%</p>
          </div>
        </div>
      </div>

      {/* 24小时柱状图 */}
      <div class="flex-1 mt-4">
        <p class="text-text-muted text-xs mb-2">24小时交易量</p>
        <ResponsiveContainer width="100%" height={120}>
          <BarChart data={volumeTrend}>
            <Bar dataKey="volume" fill="#6366f1" radius={[2,2,0,0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
```

### 7.5 Panel 3 — 匹配效率

```tsx
function MatchingPanel({ data }: { data: MatchingPanelData }) {
  // data: { demands, aiMatch, negotiations, agreements, deliveries,
  //         avgMatchTime, avgNegotiationRounds, agreementRate, deliveryRate }

  const funnelData = [
    { stage: '发布需求', value: data.demands, color: '#6366f1' },
    { stage: 'AI推荐', value: data.aiMatch, color: '#8b5cf6', pct: (data.aiMatch/data.demands*100).toFixed(1) },
    { stage: '发起协商', value: data.negotiations, color: '#f59e0b', pct: (data.negotiations/data.demands*100).toFixed(1) },
    { stage: '达成合作', value: data.agreements, color: '#22c55e', pct: (data.agreements/data.demands*100).toFixed(1) },
    { stage: '成功交付', value: data.deliveries, color: '#10b981', pct: (data.deliveries/data.demands*100).toFixed(1) },
  ]

  return (
    <div class="h-full flex flex-col p-6 bg-bg-secondary rounded-2xl border border-border-primary">
      <h2 class="font-orbitron text-lg text-text-primary mb-4">匹配效率实时看板</h2>

      {/* 漏斗图 */}
      <div class="flex-1 flex flex-col justify-center space-y-2">
        {funnelData.map((item, i) => (
          <div key={item.stage} class="relative">
            <div class="flex items-center justify-between mb-1">
              <span class="text-text-secondary text-sm">{item.stage}</span>
              <div class="flex items-center gap-2">
                {item.pct && <span class="text-text-muted text-xs">{item.pct}%</span>}
                <span class="font-mono text-text-primary text-sm">{item.value.toLocaleString()}</span>
              </div>
            </div>
            <div class="h-6 bg-bg-tertiary rounded overflow-hidden">
              <div
                class={`h-full rounded transition-all duration-500`}
                style={{ width: `${(item.value / funnelData[0].value) * 100}%`, backgroundColor: item.color }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* 底部指标 */}
      <div class="mt-4 pt-4 border-t border-border-primary grid grid-cols-4 gap-2 text-center">
        <div><p class="text-text-muted text-xs">匹配时长</p><p class="font-mono text-text-primary text-sm">{data.avgMatchTime}</p></div>
        <div><p class="text-text-muted text-xs">协商轮数</p><p class="font-mono text-text-primary text-sm">{data.avgNegotiationRounds}</p></div>
        <div><p class="text-text-muted text-xs">达成率</p><p class="font-mono text-success text-sm">{data.agreementRate}%</p></div>
        <div><p class="text-text-muted text-xs">交付率</p><p class="font-mono text-success text-sm">{data.deliveryRate}%</p></div>
      </div>
    </div>
  )
}
```

### 7.6 Panel 4 — 节点健康

```tsx
function NodeHealthPanel({ nodes, services }: { nodes: NodeData[], services: ServiceData[] }) {
  return (
    <div class="h-full flex flex-col p-6 bg-bg-secondary rounded-2xl border border-border-primary">
      <div class="flex items-center justify-between mb-4">
        <h2 class="font-orbitron text-lg text-text-primary">节点健康状态</h2>
        <div class="flex gap-2">
          <span class="flex items-center gap-1 text-success text-xs"><span class="w-2 h-2 rounded-full bg-success inline-block" />{nodes.filter(n=>n.status==='online').length}</span>
          <span class="flex items-center gap-1 text-warning text-xs"><span class="w-2 h-2 rounded-full bg-warning inline-block" />{nodes.filter(n=>n.status==='warning').length}</span>
        </div>
      </div>

      {/* 节点列表 */}
      <div class="space-y-2 flex-1 overflow-auto">
        {nodes.map(node => (
          <div key={node.id} class={`p-3 rounded-lg border transition-all
            ${node.status==='online' ? 'border-border-primary bg-bg-tertiary/50' :
              node.status==='warning' ? 'border-warning/50 bg-warning/10' :
              'border-danger/50 bg-danger/10 animate-pulse'}`}>
            <div class="flex items-center justify-between mb-1">
              <span class="text-text-primary text-sm font-medium">{node.name}</span>
              <span class={`text-xs ${node.status==='online'?'text-success':node.status==='warning'?'text-warning':'text-danger'}`}>
                {node.status === 'online' ? '🟢' : node.status === 'warning' ? '🟡' : '🔴'} {node.status}
              </span>
            </div>
            <div class="flex gap-4 text-xs text-text-muted">
              <span>Agent: {node.onlineCount}/{node.agentCount}</span>
              <span>CPU: {node.cpuPercent}%</span>
              <span>MEM: {node.memoryPercent}%</span>
              <span>延迟: {node.latency}ms</span>
            </div>
          </div>
        ))}
      </div>

      {/* 服务状态 */}
      <div class="mt-4 pt-4 border-t border-border-primary">
        <p class="text-text-muted text-xs mb-2">服务健康</p>
        <div class="grid grid-cols-2 gap-1">
          {services.map(svc => (
            <div key={svc.name} class="flex items-center gap-2">
              {svc.status === 'ok'
                ? <span class="text-success text-xs">✅</span>
                : <span class="text-warning text-xs animate-pulse">⚠️</span>}
              <span class="text-text-secondary text-xs truncate">{svc.name}</span>
              <span class="text-text-muted text-xs ml-auto">{svc.latency}ms</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
```

### 7.7 Command Center 控制栏

```tsx
// 底部固定控制栏
<div class="fixed bottom-0 left-0 right-0 h-14 bg-bg-secondary border-t border-border-primary flex items-center px-6 gap-4">
  {/* 刷新频率 */}
  <select value={refreshInterval} onChange={e => setRefreshInterval(Number(e.target.value))}
    class="bg-bg-tertiary text-text-primary text-sm rounded px-3 py-1.5 border border-border-primary">
    <option value={5000}>5s 刷新</option>
    <option value={10000}>10s 刷新</option>
    <option value={30000}>30s 刷新</option>
    <option value={0}>暂停刷新</option>
  </select>

  {/* 刷新按钮 */}
  <Button variant="ghost" size="sm" onClick={refetchAll}>
    <RefreshCw class={`w-4 h-4 ${isRefetching ? 'animate-spin' : ''}`} />
  </Button>

  <div class="flex-1" />

  {/* 告警托盘 */}
  {alerts.length > 0 && (
    <div class="flex items-center gap-2 text-danger text-sm">
      <Bell class="w-4 h-4 animate-pulse" />
      <span>{alerts.length} 个告警</span>
    </div>
  )}

  {/* 全屏 */}
  <Button variant="ghost" size="sm" onClick={toggleFullscreen}>
    {isFullscreen ? <Minimize2 /> : <Maximize2 />}
  </Button>

  {/* 设置 */}
  <Button variant="ghost" size="sm" onClick={() => setSettingsOpen(true)}>
    <Settings class="w-4 h-4" />
  </Button>
</div>
```

### 7.8 告警规则配置

```typescript
const ALERT_RULES: AlertRule[] = [
  { id: 'online_rate', label: 'Agent 在线率', metric: 'online_rate', threshold: 70, operator: 'lt', severity: 'critical' },
  { id: 'cpu_high', label: '节点 CPU', metric: 'cpu_percent', threshold: 85, duration: 300, severity: 'critical' },
  { id: 'memory_high', label: '节点内存', metric: 'memory_percent', threshold: 90, duration: 300, severity: 'critical' },
  { id: 'tx_fail_rate', label: '交易失败率', metric: 'tx_fail_rate', threshold: 5, severity: 'warning' },
  { id: 'heartbeat_lost', label: '心跳丢失', metric: 'heartbeat_missing', threshold: 180, severity: 'critical' },
  { id: 'llm_latency', label: 'LLM 延迟', metric: 'llm_latency_ms', threshold: 5000, severity: 'warning' },
  { id: 'blockchain_stuck', label: '区块链卡顿', metric: 'block_interval_ms', threshold: 30000, severity: 'warning' },
]
```

---

## 8. Nodes 节点管理

### 8.1 页面 Tabs

```
[列表 Tab] [拓扑 Tab] [性能 Tab] [配置 Tab]
```

### 8.2 列表 Tab

```tsx
// 数据结构
interface Node {
  id: string
  name: string
  ip: string
  status: 'online' | 'warning' | 'critical' | 'maintenance'
  agentCount: number
  onlineCount: number
  cpuPercent: number
  memoryPercent: number
  diskPercent: number
  networkIn: number    // MB/s
  networkOut: number   // MB/s
  latency: number      // ms
  lastHeartbeat: number
  uptime: number       // 秒
  version: string
  createdAt: number
}

// 表格列
columns: [
  { key: 'name', label: '名称', render: (row) => <span class="font-medium">{row.name}</span> },
  { key: 'status', label: '状态', render: (row) => <StatusBadge status={row.status} /> },
  { key: 'agents', label: 'Agent', render: (row) => `${row.onlineCount}/${row.agentCount}` },
  { key: 'cpu', label: 'CPU', render: (row) => <ProgressBar percent={row.cpuPercent} warning={70} critical={85} /> },
  { key: 'memory', label: '内存', render: (row) => <ProgressBar percent={row.memoryPercent} warning={75} critical={90} /> },
  { key: 'latency', label: '延迟', render: (row) => `${row.latency}ms` },
  { key: 'lastHeartbeat', label: '最后心跳', render: (row) => <TimeAgo timestamp={row.lastHeartbeat} /> },
  { key: 'actions', label: '操作', render: (row) => (
    <div class="flex gap-2">
      <Button size="sm" variant="ghost" onClick={() => openDetail(row)}>详情</Button>
      <Button size="sm" variant="ghost" onClick={() => openConfig(row)}>配置</Button>
    </div>
  )}
]

// 分页
// 每页: 25/50/100
// 总计: 自动计算
```

### 8.3 拓扑 Tab

```tsx
// 使用 D3.js 或 react-force-graph 渲染节点网络拓扑
// 节点 = 物理节点，连接线 = 节点间网络质量

interface TopologyNode {
  id: string
  name: string
  x: number
  y: number
  status: 'online' | 'warning' | 'critical'
  connections: { targetId: string; latency: number; bandwidth: number }[]
}

// 布局算法: 力导向布局（force-directed）
// 节点颜色: online=success, warning=warning, critical=danger
// 连接线颜色: 延迟 < 50ms 绿色, 50-100ms 黄色, > 100ms 红色
// 连接线粗细: 带宽比例
```

### 8.4 性能 Tab

```
[CPU] [内存] [网络] [Agent吞吐] [磁盘] — 子 Tab

每个子 Tab:
  - 24小时折线图（多线：各节点）
  - 阈值线（警告=虚线红色，危险=虚线深红）
  - 峰值标注
  - 数据粒度: 每 5 分钟一个点（每小时平均）
```

### 8.5 详情抽屉

```tsx
interface NodeDetailDrawerProps {
  nodeId: string
  open: boolean
  onClose: () => void
}

// 抽屉宽度: 560px，从右侧滑入
// 内容:
//   - 基本信息卡片
//   - 实时性能仪表盘（4个 Radial Gauge）
//   - Agent 列表（在线/离线分开）
//   - 最近事件日志（最后 50 条）
//   - 操作按钮: [编辑配置] [重启节点] [下线维护] [查看日志]
```

---

## 9. Agents Agent 管理

### 9.1 列表 Tab

```tsx
interface Agent {
  agentId: string
  name: string
  agentType: 'ai' | 'human' | 'system'
  status: 'online' | 'busy' | 'offline'
  stake: string
  reputation: number      // 0.0-5.0
  capabilities: string[]
  lastHeartbeat: number
  createdAt: number
  ownerWallet: string
  bindingStatus: 'wallet' | 'manual' | 'agent'
}

// 筛选器
<FilterBar>
  <Select label="状态" options={['全部', 'online', 'busy', 'offline']} value={filters.status} onChange={...} />
  <Select label="类型" options={['全部', 'ai', 'human', 'system']} value={filters.type} onChange={...} />
  <Select label="Stake" options={['全部', 'none', 'bronze', 'silver', 'gold', 'platinum']} value={filters.tier} onChange={...} />
  <Input label="搜索" placeholder="名称 / ID" value={filters.search} onChange={...} />
  <Button variant="outline" onClick={resetFilters}>重置</Button>
</FilterBar>

// 列
columns: [
  { key: 'agentId', label: 'Agent ID', render: (row) => <CopyableText text={row.agentId} /> },
  { key: 'name', label: '名称', render: (row) => <span class="font-medium">{row.name}</span> },
  { key: 'type', label: '类型', render: (row) => <Badge>{row.agentType}</Badge> },
  { key: 'status', label: '状态', render: (row) => <StatusBadge status={row.status} /> },
  { key: 'stake', label: 'Stake', render: (row) => <VIBEAmount value={row.stake} /> },
  { key: 'reputation', label: 'Rep', render: (row) => <StarRating value={row.reputation} /> },
  { key: 'lastHeartbeat', label: '最后活动', render: (row) => <TimeAgo timestamp={row.lastHeartbeat} /> },
  { key: 'actions', label: '操作', render: (row) => (
    <div class="flex gap-1">
      <Button size="sm" variant="ghost" onClick={() => openDetail(row)}>详情</Button>
      {row.status !== 'offline' && <Button size="sm" variant="danger-ghost" onClick={() => freezeAgent(row)}>冻结</Button>}
    </div>
  )}
]
```

### 9.2 Agent 详情页面（Drawer 或子路由）

```
[Tab: 基本信息] [Tab: Gene Capsule] [Tab: 钱包] [Tab: 交易记录] [Tab: 操作日志]

基本信息 Tab:
  - 头像/名称/ID
  - 类型 + 状态
  - 描述
  - 注册时间 + 最后心跳
  - 能力标签（capabilities）
  - 技能标签（skills）
  - Stake 数量 + 等级
  - Reputation 星级
  - 交易次数 + 成功率
  - 实时状态（CPU/内存/消息速率）

  [重置 API Key]  [冻结 Agent]  [解绑钱包]  [删除 Agent]

Gene Capsule Tab:
  - 经验列表（experiences）
  - 技能列表（skills）
  - 模式列表（patterns）
  - 价值评分
  - 可视性设置
  [导出]  [查看详情]

钱包 Tab:
  - 合约钱包地址（复制）
  - VIBE 余额
  - Stake 状态
  - 日限额 / 单笔限额 / 当日已用
  [查看链上详情]（跳转 Etherscan）

交易记录 Tab:
  - 分页表格（时间/类型/金额/对方/状态）
```

### 9.3 冻结/解冻操作

```typescript
// POST /api/admin/agents/:id/freeze
// 请求体: { reason: string }
// 后端:
//   1. 更新 agents.status = 'offline'
//   2. 写入 audit_logs
//   3. (可选) 调用 AgentWallet pause() 冻结链上资产

// 冻结确认弹窗
<ConfirmModal title="确认冻结 Agent">
  <p class="text-text-secondary">
    冻结后 Agent 将无法接收新任务，已进行的任务不受影响。
    冻结操作会记录到审计日志。
  </p>
  <Textarea label="冻结原因（必填）" value={reason} onChange={setReason}
    placeholder="请输入冻结原因..." />
  <div class="flex justify-end gap-2 mt-4">
    <Button variant="ghost" onClick={onClose}>取消</Button>
    <Button variant="danger" onClick={confirm} disabled={!reason.trim()}>确认冻结</Button>
  </div>
</ConfirmModal>
```

---

## 10. Users 用户管理

### 10.1 用户列表

```tsx
interface User {
  walletAddress: string
  did?: string
  role: UserRole
  stake: string
  reputation: number
  vibeBalance: string
  stakeStatus: 'none' | 'staked' | 'unstaking' | 'unlocked'
  agentId?: string
  createdAt: number
}

// 列
columns: [
  { key: 'walletAddress', label: '钱包地址', render: (row) => <CopyableAddress address={row.walletAddress} /> },
  { key: 'role', label: '角色', render: (row) => <RoleBadge role={row.role} /> },
  { key: 'stake', label: 'Stake', render: (row) => <VIBEAmount value={row.stake} /> },
  { key: 'reputation', label: 'Rep', render: (row) => <StarRating value={row.reputation} /> },
  { key: 'stakeStatus', label: 'Stake状态', render: (row) => <StakeStatusBadge status={row.stakeStatus} /> },
  { key: 'createdAt', label: '注册时间', render: (row) => formatDate(row.createdAt) },
  { key: 'actions', label: '操作', render: (row) => (
    <Button size="sm" variant="ghost" onClick={() => openDetail(row)}>编辑</Button>
  )}
]
```

### 10.2 角色变更

```typescript
// PUT /api/admin/users/:wallet/role
// node_admin 限制: 只能 human → ai_owner
// superadmin: 任意变更

// 变更确认弹窗
<ChangeRoleModal user={user} onConfirm={handleRoleChange}>
  <p>将 <CopyableAddress address={user.walletAddress} /> 的角色从 <RoleBadge role={user.role} /> 变更为:</p>
  <Select options={availableRoles} value={newRole} onChange={setNewRole} />
  {newRole === 'ai_owner' && (
    <div class="mt-3 p-3 bg-warning/10 border border-warning/30 rounded-lg text-sm text-warning">
      ⚠️ 升级为 AI Owner 后，该用户可创建 AI Agent。请确认身份真实性。
    </div>
  )}
</ChangeRoleModal>
```

---

## 11. Transactions 交易流水

### 11.1 筛选器

```tsx
<TransactionFilters>
  <Select label="类型" options={['全部', 'payment', 'stake', 'reward', 'refund', 'governance']} />
  <Select label="状态" options={['全部', 'pending', 'completed', 'failed', 'refunded']} />
  <DateRangePicker label="时间范围" />
  <Input label="金额范围" type="number" placeholder="最小" /> - <Input type="number" placeholder="最大" />
  <Input label="搜索" placeholder="TxHash / 钱包地址" />
</TransactionFilters>
```

### 11.2 表格

```tsx
columns: [
  { key: 'createdAt', label: '时间', render: (row) => formatDateTime(row.createdAt) },
  { key: 'id', label: 'Tx ID', render: (row) => <CopyableText text={row.id} length={12} /> },
  { key: 'from', label: 'From', render: (row) => <Address address={row.buyerId} /> },
  { key: 'to', label: 'To', render: (row) => <Address address={row.sellerId} /> },
  { key: 'amount', label: '金额', render: (row) => (
    <span class={row.buyerId.startsWith('0x') ? 'text-danger' : 'text-success'}>
      {row.buyerId.startsWith('0x') ? '-' : '+'}{formatVIBE(row.amount)}
    </span>
  )},
  { key: 'type', label: '类型', render: (row) => <TypeBadge type={row.transaction_type} /> },
  { key: 'status', label: '状态', render: (row) => <StatusBadge status={row.status} /> },
  { key: 'actions', label: '操作', render: (row) => (
    <Button size="sm" variant="ghost" onClick={() => openDetail(row)}>详情</Button>
  )}
]

// 分页: 每页 25/50/100，默认 25
// 导出: CSV / Excel 格式
```

### 11.3 导出功能

```typescript
// 前端: 使用 xlsx 库生成 Excel
// 后端: GET /api/admin/transactions?format=csv 或 ?format=excel
// 大文件: 后端流式响应，前端显示下载进度
```

---

## 12. Orders 订单管理

### 12.1 订单统计卡片

```tsx
// 顶部 4 个统计卡
<StatsRow>
  <StatCard title="总订单" value={totalOrders} icon={ClipboardList} />
  <StatCard title="进行中" value={inProgress} color="info" icon={Play} />
  <StatCard title="已完成" value={completed} color="success" icon={CheckCircle} />
  <StatCard title="争议中" value={disputed} color="danger" icon={AlertTriangle} />
</StatsRow>
```

### 12.2 订单 Tab

```
[全部] [待确认] [进行中] [已完成] [已取消] [争议中] — 状态 Tab 筛选
```

### 12.3 订单详情弹窗

```tsx
<OrderDetailModal order={order}>
  <div class="space-y-4">
    <div class="grid grid-cols-2 gap-4">
      <InfoItem label="订单号" value={order.orderId} copyable />
      <InfoItem label="状态" value={<StatusBadge status={order.status} />} />
      <InfoItem label="需求方" value={<Address address={order.demandAgentId} />} />
      <InfoItem label="供给方" value={<Address address={order.supplyAgentId} />} />
      <InfoItem label="锁定金额" value={formatVIBE(order.vibeLocked)} />
      <InfoItem label="优先级" value={order.priority} />
      <InfoItem label="创建时间" value={formatDateTime(order.createdAt)} />
      {order.completedAt && <InfoItem label="完成时间" value={formatDateTime(order.completedAt)} />}
    </div>
    {order.chainOrderId && (
      <div class="p-3 bg-bg-tertiary rounded-lg">
        <p class="text-text-muted text-xs mb-1">链上订单 ID</p>
        <CopyableText text={order.chainOrderId} />
      </div>
    )}
    {order.status === 'disputed' && (
      <div class="p-3 bg-danger/10 border border-danger/30 rounded-lg text-sm">
        ⚠️ 此订单正在争议处理中
      </div>
    )}
  </div>
</OrderDetailModal>
```

---

## 13. Matching 匹配分析

### 13.1 实时漏斗图

```tsx
// 同 Command Center Panel 3，扩展版，支持选择不同时间范围
// 额外显示: 每阶段平均耗时、转化率趋势
```

### 13.2 匹配效率趋势

```tsx
// 折线图: 7天/30天/90天
// Y轴1: 合作达成率 (%)
// Y轴2: 交付成功率 (%)
// Y轴3: 平均匹配时长 (小时)
```

### 13.3 AI 推荐分析

```tsx
// 表格: demand_id / 推荐数 / 接受数 / 拒绝数 / 接受率 / 平均匹配分
// 筛选: 时间范围 / 类别
```

---

## 14. Gene Capsules

### 14.1 全局浏览

```tsx
// Tab: [公开胶囊] [私有胶囊] [谈判专用]
// 表格: Capsule ID / Agent / 经验数 / 模式数 / 价值评分 / 可视性 / 操作

columns: [
  { key: 'capsuleId', label: 'Capsule ID', render: (row) => <CopyableText text={row.id} /> },
  { key: 'agent', label: 'Agent', render: (row) => <AgentLink agentId={row.agentId} /> },
  { key: 'experienceCount', label: '经验', render: (row) => row.experiences?.length ?? 0 },
  { key: 'patternCount', label: '模式', render: (row) => row.patterns?.length ?? 0 },
  { key: 'valueScore', label: '价值', render: (row) => <StarRating value={row.valueScore} /> },
  { key: 'visibility', label: '可视性', render: (row) => <Badge>{row.visibility}</Badge> },
  { key: 'actions', label: '操作', render: (row) => (
    <>
      <Button size="sm" variant="ghost" onClick={() => openDetail(row)}>查看</Button>
      {row.visibility === 'public' && <Button size="sm" variant="ghost" onClick={() => exportCapsule(row)}>导出</Button>}
    </>
  )}
]
```

### 14.2 统计面板

```tsx
// 顶部统计
<StatsRow>
  <StatCard title="总胶囊" value={stats.total} icon={Dna} />
  <StatCard title="公开胶囊" value={stats.publicCount} color="success" />
  <StatCard title="私有胶囊" value={stats.privateCount} color="info" />
  <StatCard title="平均价值" value={stats.avgValueScore.toFixed(1)} suffix="/10" color="warning" />
</StatsRow>

// 价值分布直方图
// 经验丰富度散点图: X=经验数, Y=价值评分, 颜色=可视化状态
```

---

## 15. Intelligence AI 能力分析

### 15.1 LLM 调用统计

```tsx
// 顶部: 总调用 / 成功 / 失败 / 平均延迟 / P99延迟
// 模型分布饼图
// Token 消耗趋势（输入/输出/总量）
// 错误类型分布（饼图）
```

### 15.2 模型使用分析

```tsx
// 表格: 模型名 / 调用次数 / 成功次数 / 失败率 / 平均延迟 / P99 / 总Token
// 折线图: 各模型延迟对比（7天）
```

### 15.3 进化引擎

```tsx
// 统计: 今日进化次数 / 本周进化 / 平均提升
// 分布直方图: 每次进化提升分数
// 趋势折线图: 7天进化提升趋势
```

---

## 16. Governance 治理

### 16.1 提案列表

```tsx
// Tab: [全部] [进行中] [已通过] [已否决] [已过期]
// 表格: ID / 标题 / 类型 / 状态 / 赞成/反对 / 截止时间 / 操作

columns: [
  { key: 'id', label: 'ID', render: (row) => `#${row.id}` },
  { key: 'title', label: '标题', render: (row) => <span class="font-medium">{row.title}</span> },
  { key: 'type', label: '类型', render: (row) => <Badge variant={typeColors[row.proposal_type]}>{row.proposal_type}</Badge> },
  { key: 'status', label: '状态', render: (row) => <StatusBadge status={row.status} /> },
  { key: 'votes', label: '投票', render: (row) => (
    <div class="w-48">
      <VoteBar votesFor={row.votes_for} votesAgainst={row.votes_against} />
      <div class="flex justify-between text-xs text-text-muted mt-1">
        <span>赞 {formatVotes(row.votes_for)}</span>
        <span>反 {formatVotes(row.votes_against)}</span>
      </div>
    </div>
  )},
  { key: 'deadline', label: '截止', render: (row) => <Countdown deadline={row.deadline} /> },
  { key: 'actions', label: '操作', render: (row) => (
    <Button size="sm" variant="ghost" onClick={() => openProposal(row)}>详情</Button>
  )}
]
```

### 16.2 提案详情弹窗

```tsx
<ProposalDetailModal proposal={proposal}>
  <div class="space-y-4">
    <div class="flex items-start justify-between">
      <div>
        <h3 class="text-lg font-medium text-text-primary">{proposal.title}</h3>
        <p class="text-text-muted text-sm mt-1">
          提案 ID: #{proposal.id} · 类型: {proposal.proposal_type} · 发起人: <Address address={proposal.proposer_id} />
        </p>
      </div>
      <StatusBadge status={proposal.status} />
    </div>

    {/* 描述 */}
    <div class="p-4 bg-bg-tertiary rounded-lg">
      <p class="text-text-secondary text-sm whitespace-pre-wrap">{proposal.description}</p>
    </div>

    {/* 投票进度 */}
    {proposal.status === 'active' && (
      <div class="space-y-3">
        <VoteBar votesFor={proposal.votes_for} votesAgainst={proposal.votes_against} tall />
        <div class="flex gap-4 text-sm">
          <span>赞成: <strong class="text-success">{formatVotes(proposal.votes_for)}</strong></span>
          <span>反对: <strong class="text-danger">{formatVotes(proposal.votes_against)}</strong></span>
          <span>参与率: <strong>{calculateParticipation(proposal)}}%</strong></span>
        </div>
        <div class="flex gap-2">
          <Button variant="success" onClick={() => castVote('for')}>✅ 赞成</Button>
          <Button variant="danger" onClick={() => castVote('against')}>❌ 反对</Button>
          <Button variant="ghost" onClick={() => castVote('abstain')}>� Abstain</Button>
        </div>
      </div>
    )}

    {/* Top 投票者 */}
    <div>
      <p class="text-text-muted text-sm mb-2">Top 赞成者</p>
      <div class="space-y-1">
        {proposal.topForVoters?.map(v => (
          <div key={v.address} class="flex justify-between text-sm">
            <Address address={v.address} />
            <span class="text-success font-mono">{formatVotes(v.weight)}</span>
          </div>
        ))}
      </div>
    </div>
  </div>
</ProposalDetailModal>
```

---

## 17. Contracts 区块链合约

### 17.1 合约总览页（/admin/contracts）

展示所有 29 个合约的概览列表，点击进入子页面。

```tsx
// 顶部: 总质押量 / VIBE价格 / 总Gas消耗 / 区块高度
// 合约网格: 29 个合约卡片（每行 5 个）
// 每个卡片: 合约名 / 地址(截断) / 余额(VIBE) / 状态指示灯

<ContractGrid>
  {contracts.map(contract => (
    <ContractCard
      name={contract.name}
      address={contract.address}
      balance={contract.balance}
      status={contract.status}
      onClick={() => navigate(`/admin/contracts/${contract.category}/${contract.name}`)}
    />
  ))}
</ContractGrid>
```

### 17.2 Staking 生态页（/admin/contracts/staking）

```tsx
// 核心指标（刷新: 60s）
// 总质押量 | 当前APY | Staker数 | 累计奖励 | 待分配红利 | VIBE价格

// Tab: [质押概览] [奖励追踪] [等级分布] [历史走势]

// 质押概览 Tab
<StatsRow>
  <StatCard title="总质押量" value={formatVIBE(staking.totalStaked)} suffix="VIBE" icon={Coins} color="primary" />
  <StatCard title="当前APY" value={staking.currentAPY / 100} suffix="%" color="success" />
  <StatCard title="Staker 数" value={staking.stakerCount.toLocaleString()} />
  <StatCard title="累计奖励" value={formatVIBE(staking.totalRewardsDistributed)} suffix="VIBE" />
  <StatCard title="待分配红利" value={formatVIBE(dividend.dividendBalance)} suffix="VIBE" color="warning" />
  <StatCard title="VIBE价格" value={`$${oracle.price / 1e6}`} suffix="" change={oracle.priceChange24h} />
</StatsRow>

// 图表: 质押量趋势(30天 Area) + APY历史折线

// 奖励追踪 Tab
<WalletInput onQuery={queryStakeInfo} />
{queryResult && (
  <StakeInfoCard info={queryResult}>
    // 质押量 / 锁定期 / 等级 / 时间加成 / 投票权 / 待领奖励 / 奖励Debt
  </StakeInfoCard>
)}

// 等级分布 Tab
// Bronze/Silver/Gold/Platinum 人数条形图 + 饼图

// 历史走势 Tab
// 30天质押量 + APY调整记录表格
```

### 17.3 奖励分发页（/admin/contracts/rewards）

```tsx
// 奖池总览: 5个卡片（Builder/Dev/Node/Output/Collaboration）
// 每个奖池: 余额 / 记录数 / 累计发放

// Tab: [Builder] [Developer] [Node] [Output] [协作]

// Builder Tab
<RewardPoolStats pool="builder" />
<BuilderRecordsTable>
  // Record ID / Builder地址 / 类型 / 基础奖励 / 质量系数 / 实际奖励 / 状态 / 时间
</BuilderRecordsTable>

// 查询: 输入 Builder 地址 或 Record ID
```

### 17.4 治理合约页（/admin/contracts/governance）

```tsx
// 核心指标
// 总投票权 | 提案总数 | 活跃提案 | 投票参与率 | 争议数

// Tab: [提案] [委托] [争议] [贡献积分]

// 提案 Tab: 同 Governance 治理页面，但数据来自链上
// 委托 Tab: 委托关系图（哪些地址委托给了哪些）
// 争议 Tab: 争议列表（ID / 状态 / 罚款 / 仲裁结果）
// 贡献积分 Tab: 用户有效积分查询
```

### 17.5 市场数据页（/admin/contracts/market）

```tsx
// 核心指标
// VIBE价格 | 7日均价 | 总供给 | 交易税 | Vesting释放率 | 流动性利用率

// Tab: [Token] [价格预言机] [归属释放] [资金池]

// Token Tab
// 总供给 + 持币分布饼图 + 税务配置表格

// 预言机 Tab
// 当前价格 / TWAP / 数据源状态 / 价格历史折线图(多周期)
// 最后更新时间 + 距上次秒数

// 归属释放 Tab
// 团队 / 早期支持者 / 空投 / 流动性 各释放进度条

// 资金池 Tab
// Ecosystem / Governance / Reserve / ProtocolFund / Community / Liquidity 各池余额表格 + 水平条形图
```

### 17.6 订单与协作页（/admin/contracts/orders）

```tsx
// 核心指标
// 订单池总数 | 活跃竞价 | 总交易额 | 平台收入 | ZK凭证已注册

// Tab: [JointOrder] [协作] [资产] [ZK凭证]

// JointOrder Tab
// 统计: 总池/活跃/已完成/争议中 + 各自金额
// 订单池表格: Pool ID / 服务类型 / 预算 / 竞价数 / 状态 / 创建时间

// 协作 Tab: 项目列表 + 贡献者 + 收入
// 资产 Tab: 碎片化资产 + 股东 + 净值
// ZK凭证 Tab: 各类注册数量 + 凭证验证
```

### 17.7 链上数据读取 Hook

```typescript
// useContractRead.ts
import { useReadContract, useMulticall3 } from '@/hooks/useEthers'
import { VIBSTAKING_ABI } from '@/contracts/abis/vibstaking'
import { VIBETOKEN_ABI } from '@/contracts/abis/vibetoken'

// 单合约读取
function TotalStaked() {
  const { data, isLoading, error, refetch } = useReadContract({
    address: VIBSTAKING_ADDRESS,
    abi: VIBSTAKING_ABI,
    functionName: 'totalStaked',
    watch: true,          // 启用轮询
    refetchInterval: 60000, // 60s
  })
  return <span>{data ? formatVIBE(data) : isLoading ? '...' : error.message}</span>
}

// 批量读取（Multicall3）
function DashboardContracts() {
  const { data, loading } = useMulticall3({
    calls: [
      { address: VIBSTAKING, abi: VIBSTAKING_ABI, functionName: 'totalStaked' },
      { address: VIBSTAKING, abi: VIBSTAKING_ABI, functionName: 'getStakerCount' },
      { address: VIBSTAKING, abi: VIBSTAKING_ABI, functionName: 'currentAPY' },
      { address: VIBETOKEN, abi: VIBETOKEN_ABI, functionName: 'totalSupply' },
      { address: PRICEORACLE, abi: PRICEORACLE_ABI, functionName: 'getPrice' },
    ],
    refetchInterval: 60000,
  })
  // data: [totalStaked, stakerCount, apy, totalSupply, price]
}
```

---

## 18. System 系统管理

### 18.1 Health 子页

```tsx
// GET /api/health + GET /api/admin/system/metrics

interface ServiceHealth {
  name: string
  status: 'ok' | 'degraded' | 'down'
  latencyMs: number
  message?: string
}

<HealthPanel>
  {services.map(svc => (
    <ServiceRow key={svc.name} service={svc}>
      {svc.status === 'ok'
        ? <span class="text-success">✅ {svc.name}</span>
        : svc.status === 'degraded'
        ? <span class="text-warning">⚠️ {svc.name} ({svc.latencyMs}ms)</span>
        : <span class="text-danger animate-pulse">🔴 {svc.name} - {svc.message}</span>}
    </ServiceRow>
  ))}
</HealthPanel>

// 告警历史: 最近 20 条（时间 / 级别 / 服务 / 消息）
```

### 18.2 Config 子页（superadmin）

```tsx
// GET /api/config + PUT /api/admin/config

// 配置分组编辑表单
// 变更后: 实时预览 diff → 确认 → 保存
// 保存时: 写入 audit_logs

interface ConfigSection {
  title: string
  fields: ConfigField[]
}

// 分组: [通用] [LLM] [匹配引擎] [风险控制] [通知]
```

### 18.3 Logs 子页（superadmin）

```tsx
// 日志来源: 服务端日志文件 或 structured logs (JSON)

// 筛选: 级别 [DEBUG/INFO/WARN/ERROR] / 时间范围 / 关键词搜索
// 分页: 每页 100 条

// 样式: Monospace 字体，关键词高亮
// ERROR: 红色背景 | WARN: 黄色背景 | INFO: 无

columns: [
  { key: 'timestamp', label: '时间', width: 180 },
  { key: 'level', label: '级别', width: 80, render: (row) => <LogLevelBadge level={row.level} /> },
  { key: 'service', label: '服务', width: 120 },
  { key: 'message', label: '消息', render: (row) => <span class="font-mono text-sm">{row.message}</span> },
  { key: 'actions', label: '操作', render: (row) => <Button size="sm" variant="ghost">详情</Button> }
]
```

---

## 19. Permissions 权限管理

### 19.1 权限矩阵

```tsx
// 角色 × 权限 矩阵表格
// 行: superadmin / node_admin / node_operator / ai_owner / human / ai_agent
// 列: Agent创建 / 交易 / 节点管理 / 用户管理 / 系统配置 / 治理投票 / 合约读 / 合约写

const PERMISSIONS = {
n  agent_create: { superadmin: true, node_admin: true, node_operator: false, ai_owner: true, human: false, ai_agent: false },
  transaction:   { superadmin: true, node_admin: true, node_operator: true,  ai_owner: true, human: true,  ai_agent: true },
  node_manage:  { superadmin: true, node_admin: true, node_operator: false, ai_owner: false, human: false, ai_agent: false },
  user_manage:  { superadmin: true, node_admin: false,node_operator: false, ai_owner: false, human: false, ai_agent: false },
  config_write:  { superadmin: true, node_admin: false,node_operator: false, ai_owner: false, human: false, ai_agent: false },
  governance:    { superadmin: true, node_admin: true, node_operator: false, ai_owner: false, human: true,  ai_agent: false },
  contract_read: { superadmin: true, node_admin: true, node_operator: true,  ai_owner: true, human: true,  ai_agent: true },
  contract_write: { superadmin: true, node_admin: false,node_operator: false, ai_owner: false, human: false, ai_agent: false },
}
```

### 19.2 审计日志

```tsx
// 筛选: 操作类型 / 目标类型 / 时间范围 / 操作人
// 表格: 时间 / 操作人 / 操作类型 / 目标 / 旧值 → 新值 / IP

columns: [
  { key: 'created_at', label: '时间', render: (row) => formatDateTime(row.created_at) },
  { key: 'operator_wallet', label: '操作人', render: (row) => <Address address={row.operator_wallet} /> },
  { key: 'operation_type', label: '操作', render: (row) => <Badge>{row.operation_type}</Badge> },
  { key: 'target', label: '目标', render: (row) => `${row.target_type}: ${row.target_id}` },
  { key: 'change', label: '变更', render: (row) => (
    <span class="text-text-secondary text-sm">
      {row.old_value ? `${formatJson(row.old_value)} → ${formatJson(row.new_value)}` : '新建'}
    </span>
  )},
  { key: 'ip', label: 'IP', render: (row) => <span class="font-mono text-xs text-text-muted">{row.ip_address}</span> }
]
```

---

## 20. 组件库

### 20.1 通用组件

| 组件 | Props | 说明 |
|------|-------|------|
| `<StatCard>` | title, value, change, icon, color, prefix, suffix, decimals, sparklineData, loading | 统计数字卡片 |
| `<StatusBadge>` | status: 'online'\|'busy'\|'offline'\|'pending'... | 状态徽章 |
| `<RoleBadge>` | role: UserRole | 角色徽章 |
| `<StakeStatusBadge>` | status | Stake状态徽章 |
| `<TypeBadge>` | type: string | 类型徽章（交易类型等）|
| `<Address>` | address: string, length?, copyable? | 钱包地址显示 |
| `<CopyableText>` | text: string, length? | 带复制按钮的文字 |
| `<CopyableAddress>` | address: string | 带复制按钮的地址 |
| `<VIBEAmount>` | value: string\|number, suffix? | VIBE 金额显示（自动格式化大数）|
| `<StarRating>` | value: number, max? | 星级评分 |
| `<ProgressBar>` | percent: number, warning?, critical?, showLabel? | 进度条 |
| `<TimeAgo>` | timestamp: number, refresh? | 相对时间（自动刷新）|
| `<Countdown>` | deadline: number | 倒计时 |
| `<Badge>` | variant?, children | 通用徽章 |
| `<Button>` | variant: 'primary'\|'secondary'\|'ghost'\|'danger'\|'danger-ghost', size, loading, disabled | 按钮 |
| `<Input>` | label?, error?, ... | 输入框 |
| `<Select>` | label?, options, value, onChange, ... | 下拉选择 |
| `<Textarea>` | label?, ... | 多行输入 |
| `<Modal>` | open, onClose, title, size? | 模态框 |
| `<Drawer>` | open, onClose, title, position?, width? | 抽屉 |
| `<ConfirmModal>` | title, message, confirmLabel?, variant?, onConfirm, onCancel | 确认弹窗 |
| `<DataTable>` | columns, data, loading, pagination, onSort, onFilter | 数据表格 |
| `<Pagination>` | page, pageSize, total, onChange | 分页器 |
| `<Tabs>` | tabs, activeTab, onChange | Tab 切换 |
| `<DateRangePicker>` | start, end, onChange | 日期范围选择器 |
| `<Toast>` | message, type, duration | Toast 通知 |
| `<EmptyState>` | icon, title, description, action? | 空状态 |
| `<LoadingSpinner>` | size?, text? | 加载动画 |
| `<Skeleton>` | rows?, height? | 骨架屏 |
| `<AlertBanner>` | message, severity, onDismiss | 告警横幅 |
| `<CommandPalette>` | trigger | 全局搜索（⌘K）|
| `<WebSocketStatus>` | — | WS 连接状态指示器 |
| `<NotificationBell>` | — | 通知铃铛（含未读数）|
| `<UserMenu>` | — | 用户下拉菜单 |
| `<Breadcrumb>` | — | 面包屑导航 |
| `<VoteBar>` | votesFor, votesAgainst, tall? | 投票进度条 |
| `<Sparkline>` | data: number[], color? | 迷你趋势线 |
| `<RadialGauge>` | value: number, max: number, label? | 环形仪表盘 |

### 20.2 图表组件

| 组件 | 类型 | 库 | 用途 |
|------|------|-----|------|
| `<AreaChart>` | Area | Recharts | Agent 趋势、Token 消耗 |
| `<BarChart>` | Bar | Recharts | 交易量、奖励分发 |
| `<LineChart>` | Line | Recharts | APY 历史、性能监控 |
| `<PieChart>` / `<DonutChart>` | Pie | Recharts | Stake 分布、类型分布 |
| `<RadarChart>` | Radar | Recharts | Agent 能力雷达图 |
| `<FunnelChart>` | Custom | Recharts + SVG | 匹配漏斗 |
| `<ScatterChart>` | Scatter | Recharts | Gene Capsule 价值分析 |
| `<RadialBarChart>` | RadialBar | Recharts | CPU/内存环形进度 |
| `<TopologyGraph>` | ForceGraph | react-force-graph | 节点网络拓扑 |

### 20.3 组件状态规范

每个组件必须处理的状态：

```typescript
// 加载状态
const { data, isLoading, error } = useQuery(...)
if (isLoading) return <Skeleton rows={3} />
if (error) return <ErrorState message={error.message} onRetry={refetch} />

// 空状态
if (!data || data.length === 0) return <EmptyState title="暂无数据" />

// 正常状态
return <ActualComponent data={data} />
```

---

## 21. API 规范

### 21.1 Admin API 前缀: `/api/admin/*`

所有端点需要 `Authorization: Bearer <access_token>` 头，且 `user.role` 必须是 `node_admin` 或 `superadmin`。

#### 21.1.1 Dashboard

```
GET /api/admin/dashboard/stats
Response: DashboardStats (见 6.6)
```

#### 21.1.2 Nodes

```
GET /api/admin/nodes
  Query: page, pageSize, status, search
  Response: { nodes: Node[], total: number }

GET /api/admin/nodes/:id
  Response: NodeDetail

PUT /api/admin/nodes/:id/config
  Body: { cpuWarning?, memoryWarning?, latencyWarning? }
  Auth: superadmin only

POST /api/admin/nodes/:id/restart
  Body: { reason: string }
  Auth: superadmin only

GET /api/admin/nodes/:id/logs
  Query: level, start, end, limit
  Response: LogEntry[]
```

#### 21.1.3 Agents

```
GET /api/admin/agents
  Query: page, pageSize, status, type, tier, search
  Response: { agents: Agent[], total: number }

GET /api/admin/agents/:id
  Response: AgentDetail

POST /api/admin/agents/:id/freeze
  Body: { reason: string }
  Auth: superadmin only

POST /api/admin/agents/:id/unfreeze
  Auth: superadmin only

DELETE /api/admin/agents/:id
  Body: { reason: string }
  Auth: superadmin only

POST /api/admin/agents/:id/reset-api-key
  Auth: superadmin only
```

#### 21.1.4 Users

```
GET /api/admin/users
  Query: page, pageSize, role, stakeStatus, search
  Response: { users: User[], total: number }

GET /api/admin/users/:wallet
  Response: UserDetail

PUT /api/admin/users/:wallet/role
  Body: { role: UserRole, reason: string }
  Auth: superadmin for all; node_admin only for human→ai_owner

GET /api/admin/users/:wallet/transactions
  Query: page, pageSize, type, status, startTime, endTime
  Response: { transactions: Transaction[], total: number }
```

#### 21.1.5 Transactions

```
GET /api/admin/transactions
  Query: page, pageSize, type, status, startTime, endTime, minAmount, maxAmount, search, format?
  Response: { transactions: Transaction[], total: number, summary: TransactionSummary }

GET /api/admin/transactions/export
  Query: type, status, startTime, endTime, format=csv|excel
  Response: 文件流
```

#### 21.1.6 Orders

```
GET /api/admin/orders
  Query: page, pageSize, status, priority
  Response: { orders: Order[], total: number, stats: OrderStats }

GET /api/admin/orders/:id
  Response: OrderDetail
```

#### 21.1.7 Matching

```
GET /api/admin/matching/funnel
  Query: timeRange: '7d'|'30d'|'90d'
  Response: FunnelData

GET /api/admin/matching/stats
  Response: MatchingStats

GET /api/admin/matching/recommendations
  Query: page, pageSize, demandId?
  Response: { recommendations: Recommendation[], total: number }
```

#### 21.1.8 Gene Capsules

```
GET /api/admin/gene-capsules
  Query: page, pageSize, visibility, search
  Response: { capsules: GeneCapsuleSummary[], total: number, stats: CapsuleStats }

GET /api/admin/gene-capsules/:id
  Response: GeneCapsuleResponse
```

#### 21.1.9 Intelligence

```
GET /api/admin/intelligence/llm-stats
  Query: timeRange
  Response: LLMStats

GET /api/admin/intelligence/model-usage
  Response: ModelUsage[]

GET /api/admin/intelligence/evolution
  Response: EvolutionStats
```

#### 21.1.10 Governance

```
GET /api/admin/governance/proposals
  Query: page, pageSize, status, type
  Response: { proposals: Proposal[], total: number }

GET /api/admin/governance/proposals/:id
  Response: ProposalDetail

POST /api/admin/governance/proposals/:id/vote
  Body: { vote: 'for'|'against'|'abstain' }
  Auth: superadmin only (管理员投票)
```

#### 21.1.11 Contracts

```
GET /api/admin/contracts/overview
  Response: ContractOverview[]  // 29 个合约的余额 + 状态

GET /api/admin/contracts/staking
  Response: StakingData

GET /api/admin/contracts/staking/user/:address
  Response: StakeInfo

GET /api/admin/contracts/rewards
  Response: RewardPoolsData

GET /api/admin/contracts/rewards/:pool/records
  Query: page, pageSize, address?
  Response: RewardRecord[]

GET /api/admin/contracts/governance
  Response: GovernanceData

GET /api/admin/contracts/governance/proposals
  Query: page, pageSize, status
  Response: { proposals: Proposal[], total: number }

GET /api/admin/contracts/market
  Response: MarketData

GET /api/admin/contracts/orders
  Response: OrderPoolData

GET /api/admin/contracts/orders/pools/:poolId
  Response: OrderPoolDetail
```

#### 21.1.12 System

```
GET /api/admin/system/health
  Response: { services: ServiceHealth[], lastCheck: number }

GET /api/admin/system/metrics
  Response: PrometheusFormatMetrics

GET /api/admin/system/config
  Response: SystemConfig

PUT /api/admin/system/config
  Body: Partial<SystemConfig>
  Auth: superadmin only

GET /api/admin/system/logs
  Query: level, service, start, end, search, page, pageSize
  Response: { logs: LogEntry[], total: number }
```

#### 21.1.13 Permissions

```
GET /api/admin/permissions/matrix
  Response: PermissionMatrix

GET /api/admin/permissions/audit
  Query: page, pageSize, operationType, targetType, operator, start, end
  Response: { logs: AuditLog[], total: number }
```

### 21.2 WebSocket 端点

```
ws://host/api/admin/realtime?token=<access_token>

// 服务端推送消息类型:
interface RealtimeMessage {
  type: 'agent_status_change' | 'transaction_new' | 'order_status_change' |
        'node_heartbeat' | 'alert' | 'price_update' | 'block_new'
  data: any
  timestamp: number
}

// 客户端订阅:
ws.send(JSON.stringify({
  action: 'subscribe',
  channels: ['agents', 'transactions', 'nodes', 'alerts', 'prices']
}))

// 断开重连: 指数退避 (1s, 2s, 4s, 8s, max 30s)
```

---

## 22. 数据层架构

### 22.1 TanStack Query 配置

```typescript
// hooks/useQueries.ts

// 全局配置
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000,        // 30s 内不重新请求
      gcTime: 5 * 60 * 1000,  // 5分钟缓存
      retry: 2,
      refetchOnWindowFocus: false,
    }
  }
})

// Admin 数据查询 hooks
export function useDashboardStats() {
  return useQuery({
    queryKey: ['admin', 'dashboard', 'stats'],
    queryFn: () => api.get('/api/admin/dashboard/stats'),
    refetchInterval: 60000,  // 60s 自动刷新
  })
}

export function useAgents(filters: AgentFilters) {
  return useQuery({
    queryKey: ['admin', 'agents', filters],
    queryFn: () => api.get('/api/admin/agents', { params: filters }),
  })
}

export function useContractRead(contract: string, fn: string, args: any[]) {
  return useQuery({
    queryKey: ['contract', contract, fn, args],
    queryFn: () => contractRead(contract, fn, args),
    refetchInterval: getRefetchInterval(fn),  // 根据函数名决定刷新间隔
  })
}
```

### 22.2 数据缓存策略

| 数据类型 | 刷新间隔 | 缓存时间 | 说明 |
|---------|---------|---------|------|
| Dashboard 统计 | 60s | 5min | TanStack Query staleTime=30s |
| Agent 列表 | 30s | 2min | 实时性要求高 |
| 交易流水 | 60s | 5min | 不频繁变化 |
| 节点健康 | 10s | 1min | 高实时性 |
| Gene Capsule | 5min | 30min | 低实时性 |
| **链上 - 价格** | 30s | 1min | Multicall3 |
| **链上 - 质押量** | 60s | 5min | Multicall3 |
| **链上 - 奖池** | 60s | 5min | Multicall3 |
| **链上 - 治理** | 5min | 15min | 变化不频繁 |
| **链上 - Vesting** | 10min | 1h | 解锁节奏固定 |

---

## 23. 实时推送架构

### 23.1 WebSocket 连接管理

```typescript
// hooks/useAdminWebSocket.ts

function useAdminWebSocket(channels: string[]) {
  const [connectionStatus, setConnectionStatus] = useState<'connecting'|'connected'|'disconnected'>('connecting')
  const [alerts, setAlerts] = useState<Alert[]>([])
  const { accessToken } = useAuthStore()
  const queryClient = useQueryClient()

  useEffect(() => {
    const ws = new WebSocket(`${WS_BASE}/api/admin/realtime?token=${accessToken}`)

    ws.onopen = () => {
      setConnectionStatus('connected')
      ws.send(JSON.stringify({ action: 'subscribe', channels }))
    }

    ws.onmessage = (event) => {
      const msg: RealtimeMessage = JSON.parse(event.data)

      // 失效对应的 TanStack Query 缓存（触发自动 refetch）
      queryClient.invalidateQueries({ queryKey: getQueryKey(msg.type) })

      // 更新本地状态
      switch (msg.type) {
        case 'alert':
          setAlerts(prev => [msg.data, ...prev.slice(0, 4)])  // 保留最新5条
          break
        // ...
      }
    }

    ws.onclose = () => {
      setConnectionStatus('disconnected')
      // 指数退避重连
      scheduleReconnect()
    }

    return () => ws.close()
  }, [channels.join(',')])

  return { connectionStatus, alerts }
}
```

### 23.2 后端 WebSocket 广播

```python
# 后端每 10s 广播一次节点心跳
# 每笔新交易时广播 transaction_new
# 每 Agent 状态变化时广播 agent_status_change
# 价格/区块更新时广播 price_update / block_new

import asyncio
from fastapi import WebSocket

class AdminBroadcast:
    def __init__(self):
        self.subscriptions: dict[str, list[WebSocket]] = {}

    async def broadcast(self, channel: str, message: dict):
        for ws in self.subscriptions.get(channel, []):
            try:
                await ws.send_json(message)
            except:
                pass  # 忽略断开的连接
```

---

## 24. 权限体系

### 24.1 前端权限守卫

```typescript
// 路由级守卫
<AdminRoute requiredRoles={['superadmin', 'node_admin']}>
  <AdminLayout />
</AdminRoute>

// 组件级守卫
function ConfigWriteButton() {
  const { user } = useAuthStore()
  if (user.role !== 'superadmin') return null
  return <Button>编辑配置</Button>
}

// API 请求拦截器
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 403) {
      toast.error('无权限执行此操作')
    }
    return Promise.reject(error)
  }
)
```

### 24.2 后端权限装饰器

```python
# decorators.py

from functools import wraps
from fastapi import HTTPException

def require_admin_roles(roles: list[str]):
    """要求指定角色之一"""
    def decorator(func):
        @wraps(func)
        async def wrapper(user: dict = Depends(get_current_user), *args, **kwargs):
            if user.get('role') not in roles:
                raise HTTPException(403, 'Insufficient permissions')
            return await func(user, *args, **kwargs)
        return wrapper
    return decorator

# 使用
@router.put('/config')
@require_admin_roles(['superadmin'])
async def update_config(...):
    ...

@router.put('/users/{wallet}/role')
@require_admin_roles(['superadmin', 'node_admin'])
async def change_role(user: dict, wallet: str, role: UserRole, reason: str):
    # node_admin 特殊限制
    if user['role'] == 'node_admin':
        if role not in ['ai_owner'] or user['wallet'] != wallet:
            raise HTTPException(403, 'node_admin can only promote human→ai_owner')
    ...
```

### 24.3 审计日志写入

```python
# 中间件：所有写操作自动记录审计日志
async def audit_log_middleware(request: Request, call_next):
    response = await call_next(request)

    if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
        # 从 response 状态判断是否成功
        if 200 <= response.status_code < 300:
            await write_audit_log(
                operator=get_current_user_wallet(),
                operation_type=infer_operation_type(request),
                target_type=infer_target_type(request),
                target_id=extract_target_id(request),
                old_value=await get_old_value(request),
                new_value=await get_request_body(request),
                ip_address=request.client.host,
                user_agent=request.headers.get('user-agent'),
            )

    return response
```

---

## 25. 错误处理与状态管理

### 25.1 错误边界

```tsx
// AdminErrorBoundary.tsx
class AdminErrorBoundary extends Component<{}, { hasError: boolean; error?: Error }> {
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div class="flex items-center justify-center h-screen bg-bg-primary">
          <div class="text-center max-w-md">
            <AlertTriangle class="w-16 h-16 text-danger mx-auto mb-4" />
            <h2 class="text-xl font-medium text-text-primary mb-2">页面加载失败</h2>
            <p class="text-text-secondary mb-4">{this.state.error?.message}</p>
            <Button onClick={() => window.location.reload()}>刷新页面</Button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
```

### 25.2 全局错误处理

```tsx
// Toast 通知
// 400: 显示服务端返回的 detail
// 401: 重定向到登录
// 403: Toast "无权限"
// 404: Toast "资源不存在"
// 500: Toast "服务端错误，请稍后重试"
// 网络错误: Toast "网络连接失败"

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { response } = error

    if (!response) {
      toast.error('网络连接失败，请检查网络')
      return Promise.reject(error)
    }

    switch (response.status) {
      case 400:
        const detail = response.data?.detail || '请求参数错误'
        toast.error(detail)
        break
      case 401:
        useAuthStore.getState().logout()
        navigate('/login')
        break
      case 403:
        toast.error(response.data?.detail || '无权限执行此操作')
        break
      case 404:
        toast.error(response.data?.detail || '资源不存在')
        break
      case 500:
        toast.error('服务端错误，请稍后重试')
        break
    }

    return Promise.reject(error)
  }
)
```

### 25.3 加载状态骨架屏

每个页面必须有骨架屏，不能出现空白：

```tsx
function DashboardPage() {
  const { data, isLoading } = useDashboardStats()

  if (isLoading) {
    return (
      <div class="space-y-6">
        {/* 统计卡片骨架 */}
        <div class="grid grid-cols-6 gap-4">
          {[...Array(6)].map((_, i) => <Skeleton key={i} height={100} class="rounded-xl" />)}
        </div>
        {/* 图表骨架 */}
        <Skeleton height={300} class="rounded-xl" />
        {/* 表格骨架 */}
        <Skeleton height={200} class="rounded-xl" />
      </div>
    )
  }

  return <DashboardContent data={data} />
}
```

---

## 26. 文件结构

### 26.1 Frontend Admin 目录

```
frontend/src/
├── admin/
│   ├── index.tsx                  ← Admin 入口（重定向 /admin → /admin/dashboard）
│   ├── AdminApp.tsx               ← Admin Router 定义
│   │
│   ├── layouts/
│   │   ├── AdminLayout.tsx       ← Admin 主 Layout
│   │   ├── AdminHeader.tsx        ← 顶部栏
│   │   └── AdminSidebar.tsx       ← 侧边栏
│   │
│   ├── pages/
│   │   ├── dashboard/
│   │   │   ├── DashboardPage.tsx
│   │   │   └── components/
│   │   │       ├── StatsGrid.tsx
│   │   │       ├── AgentTrendChart.tsx
│   │   │       ├── TransactionChart.tsx
│   │   │       ├── StakeDistributionChart.tsx
│   │   │       ├── RealtimePanel.tsx
│   │   │       ├── LiveAgentFeed.tsx
│   │   │       ├── LiveTransactionFeed.tsx
│   │   │       ├── NodeHealthTable.tsx
│   │   │       └── RecentTransactionsTable.tsx
│   │   │
│   │   ├── command-center/
│   │   │   ├── CommandCenterPage.tsx
│   │   │   └── components/
│   │   │       ├── AgentStatusPanel.tsx
│   │   │       ├── TransactionPanel.tsx
│   │   │       ├── MatchingPanel.tsx
│   │   │       ├── NodeHealthPanel.tsx
│   │   │       ├── AlertBar.tsx
│   │   │       └── CommandBar.tsx
│   │   │
│   │   ├── nodes/
│   │   │   ├── NodesPage.tsx
│   │   │   └── components/
│   │   │       ├── NodesTable.tsx
│   │   │       ├── NodeTopology.tsx
│   │   │       ├── NodePerformanceChart.tsx
│   │   │       └── NodeDetailDrawer.tsx
│   │   │
│   │   ├── agents/
│   │   │   ├── AgentsPage.tsx
│   │   │   └── components/
│   │   │       ├── AgentsTable.tsx
│   │   │       ├── AgentDetailDrawer.tsx
│   │   │       ├── AgentCapabilityRadar.tsx
│   │   │       ├── FreezeAgentModal.tsx
│   │   │       └── WalletTab.tsx
│   │   │
│   │   ├── users/
│   │   │   ├── UsersPage.tsx
│   │   │   └── components/
│   │   │       ├── UsersTable.tsx
│   │   │       ├── UserDetailDrawer.tsx
│   │   │       └── ChangeRoleModal.tsx
│   │   │
│   │   ├── transactions/
│   │   │   ├── TransactionsPage.tsx
│   │   │   └── components/
│   │   │       ├── TransactionsTable.tsx
│   │   │       ├── TransactionFilters.tsx
│   │   │       └── TransactionDetailModal.tsx
│   │   │
│   │   ├── orders/
│   │   │   ├── OrdersPage.tsx
│   │   │   └── components/
│   │   │       ├── OrdersTable.tsx
│   │   │       ├── OrderStats.tsx
│   │   │       └── OrderDetailModal.tsx
│   │   │
│   │   ├── matching/
│   │   │   ├── MatchingPage.tsx
│   │   │   └── components/
│   │   │       ├── MatchingFunnel.tsx
│   │   │       ├── MatchingTrendChart.tsx
│   │   │       └── AIRecommendationTable.tsx
│   │   │
│   │   ├── gene-capsules/
│   │   │   ├── GeneCapsulesPage.tsx
│   │   │   └── components/
│   │   │       ├── CapsulesTable.tsx
│   │   │       ├── CapsuleStats.tsx
│   │   │       ├── ValueScatterChart.tsx
│   │   │       └── CapsuleDetailModal.tsx
│   │   │
│   │   ├── intelligence/
│   │   │   ├── IntelligencePage.tsx
│   │   │   └── components/
│   │   │       ├── LLMStats.tsx
│   │   │       ├── ModelUsageChart.tsx
│   │   │       ├── TokenConsumptionChart.tsx
│   │   │       └── EvolutionStats.tsx
│   │   │
│   │   ├── governance/
│   │   │   ├── GovernancePage.tsx
│   │   │   └── components/
│   │   │       ├── ProposalsTable.tsx
│   │   │       ├── ProposalDetailModal.tsx
│   │   │       └── VoteBar.tsx
│   │   │
│   │   ├── contracts/
│   │   │   ├── ContractsOverviewPage.tsx  ← /admin/contracts
│   │   │   ├── StakingPage.tsx             ← /admin/contracts/staking
│   │   │   ├── RewardsPage.tsx             ← /admin/contracts/rewards
│   │   │   ├── GovernanceContractsPage.tsx ← /admin/contracts/governance
│   │   │   ├── MarketPage.tsx               ← /admin/contracts/market
│   │   │   └── OrdersContractsPage.tsx      ← /admin/contracts/orders
│   │   │
│   │   ├── system/
│   │   │   ├── SystemPage.tsx
│   │   │   ├── HealthPage.tsx
│   │   │   ├── ConfigPage.tsx
│   │   │   └── LogsPage.tsx
│   │   │
│   │   └── permissions/
│   │       ├── PermissionsPage.tsx
│   │       └── components/
│   │           ├── PermissionMatrix.tsx
│   │           └── AuditLogTable.tsx
│   │
│   ├── components/                 ← Admin 专用通用组件
│   │   ├── charts/
│   │   │   ├── Sparkline.tsx
│   │   │   ├── RadialGauge.tsx
│   │   │   └── VoteBar.tsx
│   │   ├── tables/
│   │   │   ├── AdminDataTable.tsx
│   │   │   └── AdminPagination.tsx
│   │   ├── modals/
│   │   │   ├── ConfirmDangerousModal.tsx
│   │   │   └── WalletInputModal.tsx
│   │   └── shared/
│   │       ├── AdminRoute.tsx
│   │       ├── AdminFilter.tsx
│   │       ├── StatCard.tsx
│   │       ├── StatusBadge.tsx
│   │       ├── AddressDisplay.tsx
│   │       ├── VIBEAmount.tsx
│   │       ├── TimeAgo.tsx
│   │       ├── ProgressBar.tsx
│   │       ├── EmptyState.tsx
│   │       ├── SkeletonLoader.tsx
│   │       └── WebSocketStatus.tsx
│   │
│   ├── hooks/
│   │   ├── useAdminAuth.ts
│   │   ├── useAdminWebSocket.ts
│   │   ├── useDashboardStats.ts
│   │   ├── useAgents.ts
│   │   ├── useUsers.ts
│   │   ├── useTransactions.ts
│   │   ├── useOrders.ts
│   │   ├── useContractRead.ts
│   │   ├── useMulticall3.ts
│   │   └── useRealtime.ts
│   │
│   ├── api/
│   │   └── adminApi.ts            ← axios 实例（baseURL: /api/admin）
│   │
│   └── contracts/
│       ├── abis/                  ← 各合约 ABI 文件
│       │   ├── VIBStaking.json
│       │   ├── VIBEToken.json
│       │   ├── VIBGovernance.json
│       │   └── ...（其他 26 个合约）
│       ├── addresses.ts           ← 合约地址常量
│       └── multicall.ts            ← Multicall3 调用封装
│
└── App.tsx                         ← 主入口（Admin 条件渲染或独立路由）
```

### 26.2 Backend Admin API 目录

```
src/usmsb_sdk/api/rest/
├── routers/
│   ├── admin/
│   │   ├── __init__.py
│   │   ├── dashboard.py            # GET /api/admin/dashboard/*
│   │   ├── nodes.py                # GET/PUT /api/admin/nodes/*
│   │   ├── agents.py               # GET/POST/DELETE /api/admin/agents/*
│   │   ├── users.py                # GET/PUT /api/admin/users/*
│   │   ├── transactions.py         # GET /api/admin/transactions/*
│   │   ├── orders.py               # GET /api/admin/orders/*
│   │   ├── matching.py             # GET /api/admin/matching/*
│   │   ├── gene_capsules.py        # GET /api/admin/gene-capsules/*
│   │   ├── intelligence.py          # GET /api/admin/intelligence/*
│   │   ├── governance.py           # GET/POST /api/admin/governance/*
│   │   ├── contracts.py            # GET /api/admin/contracts/*
│   │   ├── system.py               # GET/PUT /api/admin/system/*
│   │   └── permissions.py          # GET /api/admin/permissions/*
│   │
│   └── admin.py                    # AdminRouter 聚合注册
│
├── services/
│   ├── admin_service.py            # Admin 业务逻辑
│   ├── audit_service.py            # 审计日志写入
│   ├── blockchain_reader.py         # 链上数据读取（ethers.py）
│   └── admin_websocket.py           # WebSocket 广播服务
│
├── decorators/
│   ├── __init__.py
│   └── admin_auth.py               # @require_admin_roles 装饰器
│
└── schemas/
    ├── admin/
    │   ├── dashboard.py
    │   ├── nodes.py
    │   ├── agents.py
    │   ├── users.py
    │   ├── transactions.py
    │   ├── orders.py
    │   ├── contracts.py
    │   └── common.py
    └── admin.py                     # AdminSchema 聚合
```

---

## 27. 实施计划

### Phase 1: 基础框架 + Dashboard（5天）

**Day 1-2: 项目初始化**
- [ ] 创建 `src/admin/` 目录结构
- [ ] Admin Layout（Header + Sidebar + 主内容区）
- [ ] 路由守卫 `AdminRoute`
- [ ] 复用 frontend 样式（CSS import、Tailwind config）
- [ ] TanStack Query 配置
- [ ] axios adminApi 实例
- [ ] 通用组件：StatCard, StatusBadge, AddressDisplay, ProgressBar, Pagination

**Day 3-4: Dashboard 页面**
- [ ] `/api/admin/dashboard/stats` 后端端点
- [ ] StatsGrid（12 个 StatCard）
- [ ] AgentTrendChart（Area Chart）
- [ ] TransactionChart（Bar + Line）
- [ ] StakeDistributionChart（Pie）
- [ ] RealtimePanel（Live Feed）
- [ ] NodeHealthTable
- [ ] RecentTransactionsTable

**Day 5: WebSocket 实时**
- [ ] 后端 WebSocket 广播服务
- [ ] `useAdminWebSocket` hook
- [ ] 实时数据更新（Agent 状态、交易、节点心跳）
- [ ] Dashboard 实时数据集成

### Phase 2: 大屏幕 Command Center（3天）

**Day 6: 页面框架**
- [ ] 独立路由 `/admin/command-center`
- [ ] 全屏 CSS（去除 Header/Sidebar）
- [ ] 4 分区 Layout
- [ ] 刷新频率控制栏
- [ ] F11 全屏支持

**Day 7: 4 个 Panel**
- [ ] AgentStatusPanel（环形图 + 数字）
- [ ] TransactionPanel（金额 + 柱状图）
- [ ] MatchingPanel（漏斗图 + 指标）
- [ ] NodeHealthPanel（节点列表 + 服务状态）

**Day 8: 告警 + 优化**
- [ ] 告警规则引擎
- [ ] AlertBar 滚动字幕
- [ ] 数据告警闪烁效果
- [ ] 性能优化（大屏响应式）

### Phase 3: 核心管理页面（5天）

**Day 9-10: Nodes + Agents**
- [ ] Nodes 列表 + 详情抽屉
- [ ] Nodes 拓扑图（react-force-graph）
- [ ] Nodes 性能 Tab（CPU/内存/网络/吞吐）
- [ ] Agents 列表 + 筛选/搜索
- [ ] Agents 详情抽屉（5 个 Tab）
- [ ] 冻结/解冻/删除 Agent
- [ ] 重置 API Key

**Day 11: Users + Transactions**
- [ ] Users 列表 + 详情抽屉
- [ ] 角色变更（含 node_admin 限制）
- [ ] Transactions 流水 + 分页
- [ ] Transactions 筛选器
- [ ] CSV/Excel 导出

**Day 12-13: Orders + Matching + Gene Capsules**
- [ ] Orders 列表 + 状态 Tab
- [ ] Orders 详情弹窗
- [ ] Orders 统计卡片
- [ ] Matching 漏斗图
- [ ] Matching 效率趋势
- [ ] Gene Capsules 列表 + 统计
- [ ] Gene Capsules 详情

### Phase 4: 区块链合约（4天）

**Day 14-15: Staking + Rewards**
- [ ] `blockchain_reader.py`（ethers.js Multicall3 封装）
- [ ] ABI 文件整理（29 个合约）
- [ ] Staking 页面（6 大指标 + 4 Tab）
- [ ] 奖励追踪（钱包查询）
- [ ] 等级分布图
- [ ] Rewards 页面（Builder/Dev/Node/Output/协作）

**Day 16-17: Governance + Market + Orders**
- [ ] Governance 页面（提案 + 委托 + 争议 + 贡献积分）
- [ ] Market 页面（Token + 预言机 + Vesting + 资金池）
- [ ] Orders 页面（JointOrder + 协作 + ZK）
- [ ] 合约总览页（29 合约卡片网格）

### Phase 5: 系统管理 + 完善（3天）

**Day 18: System + Permissions**
- [ ] Health 子页（服务状态 + 告警历史）
- [ ] Config 子页（superadmin 配置写入）
- [ ] Logs 子页（superadmin 日志查看）
- [ ] Permissions 矩阵页面
- [ ] Audit Log 表格 + 筛选

**Day 19: Intelligence + Governance**
- [ ] Intelligence LLM 统计（调用/Token/模型分布）
- [ ] 模型使用分析表格
- [ ] 进化引擎统计
- [ ] Governance 提案列表 + 详情
- [ ] 在线投票（仅 superadmin）

**Day 20: 收尾**
- [ ] 所有页面骨架屏检查
- [ ] 错误边界检查
- [ ] 响应式（移动端降级）
- [ ] 审计日志完整性验证
- [ ] API 401/403 处理
- [ ] Command Center 稳定性测试

---

## 附录 A：合约地址配置

```typescript
// contracts/addresses.ts

export const CONTRACTS = {
  baseSepolia: {
    VIBEToken: '0x93C52dF000317e12F891474B46d8B05652430bDC',
    VIBStaking: '0x1901Ab56eA38cBeFc7a3F0Ed188B7108d27f4c05',
    VIBVesting: '0x4d3008550fc164ccf0e1C0C4f666E77FC14dE924',
    VIBReserve: '0x56AbAf5fc5d58c92C0A51F79251BF3A3002f4263',
    VIBProtocolFund: '0x0F39011e7E542D939C1dce40754a86b01BB3fA5a',
    VIBInfrastructurePool: '0xFc2943d6D426D4D6433944e1ADa4D475F3552500',
    VIBBuilderReward: '0x397Faf7D727db190fB677362B15c091f1d94F7b3',
    VIBDevReward: '0x1a5E99b52e87E718906e8516fDD9c8775Ee0351E',
    VIBIdentity: '0x978eddDf11728B4e6A6C461D8806eD5f4339D466',
    VIBNodeReward: '0xc417b180F3b743A51e86c16A8319Eac353fDC29b',
    VIBCollaboration: '0xe568c56f467E27Cb38d4B132B02318C81EC29D78',
    VIBDividend: '0xa820F9E9Caa90e405452Fc3f24DC5DF7f7d70E9D',
    AgentRegistry: '0xC5AbAE9f580C48D645bDE9904712891AE8FcDec6',
    ZKCredential: '0x59EE17f1E914ba2de89F080CF44FC46Ee46DF874',
    AssetVault: '0x0F5C6Ae463f78aD30De1C9c6BF180423F0A39897',
    JointOrder: '0x55f4b49c9C269Fccf6d90e16304654b7F69138d0',
    PriceOracle: '0x20306509a6b2f0b56ad55C193b4505CA5E62bc48',
    VIBOutputReward: '0x7b3CEB40CFb093e66EcD5b49F835586Ba7Ef428b',
    VIBEcosystemPool: '0x20A25378DB87a94E19A8b51ED638F67d6e9BfE06',
    AirdropDistributor: '0x01cdC2C7C3Deb071e6C7B42ED66884DDd3CADDf6',
    CommunityStableFund: '0x6e616E6B1d63709dA849074bb7cd5A6936350563',
    LiquidityManager: '0x5c11b7f74bBb2dbBE232C6A456eCa64DA4722D42',
    VIBGovernance: '0x27475aea1eEba485005B1717a35a7D411d144a1d',
    VIBGovernanceDelegation: '0x47428bAB428966B32F246a3e9456f10dc70141A5',
    VIBContributionPoints: '0x60D9244bF262bF85Fd3057C95Ca00fEa1622f3E5',
    VIBVEPoints: '0xB2b56dce955ab200E0c1888C22Ac711803e607F1',
    VIBDispute: '0xE32d99daDBd4443423EfDc590af7591f84FAFE7e',
    AgentWallet: '0xeAd5FCC931493F702208B737528578718D681243',
    EmissionController: '0xaeD496480c9668dc90Dc309fCD8Fd9aE4268dF39',
  }
} as const

export const RPC_URL = 'https://sepolia.base.org'
export const CHAIN_ID = 84532  // Base Sepolia
```

---

## 附录 B：vite.config.ts 修改

```typescript
// frontend/vite.config.ts
// 添加条件渲染或独立构建 Admin Panel

export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@admin': path.resolve(__dirname, './src/admin'),
    },
  },
  // 如果 Admin 作为独立构建：
  build: {
    rollupOptions: {
      input: {
        admin: path.resolve(__dirname, 'admin.html'),
      },
    },
  },
})
```

---

## 附录 C：性能目标

| 指标 | 目标 |
|------|------|
| 首屏加载（LCP）| < 2.5s |
| Dashboard 所有卡片渲染 | < 3s |
| Command Center Panel 全部渲染 | < 4s |
| WebSocket 消息延迟 | < 100ms |
| 链上数据 Multicall3 批量读取 | < 2s |
| 表格分页切换 | < 200ms |
| 图表渲染 | < 500ms |
| Time to Interactive | < 5s |
