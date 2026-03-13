# VIBE Staking System Technical Whitepaper

**[English](#vibe-staking-system-technical-whitepaper) | [中文](#vibe-质押系统技术白皮书)**

**Version**: v1.0.0
**Updated Date**: 2026-02-22
**Status**: Implemented

---

## Abstract

The VIBE Staking System is the core economic mechanism of the AI Civilization Platform. By staking VIBE tokens, users can unlock the platform's full features, participate in network governance, and receive corresponding benefits. This system uses a progressive unlock mechanism to ensure network security while providing flexible fund liquidity.

---

## Important Note

> **Note**: The VIBE ecosystem contains **two separate staking systems** with different functions:

| Feature | On-Chain Staking (VIBStaking.sol) | Off-Chain Staking (Platform Access) |
|---------|-----------------------------------|-------------------------------------|
| **Location** | Blockchain smart contract | AI platform backend |
| **Purpose** | Earn staking rewards/APY | Platform feature access threshold |
| **Unlock Period** | 30/90/180/365 days | 7 days |
| **Lock Options** | Multi-tier lockup | Progressive unlock |
| **Get Rewards** | Yes (VIBE tokens) | No |

- **On-Chain Staking (VIBStaking.sol)**: Lock VIBE tokens on-chain and earn APY rewards based on lockup duration
- **Off-Chain Staking (AI Platform)**: Staking as platform access threshold; after unlocking, can be used for service marketplace, governance voting, etc.

This document primarily describes the **off-chain staking system** (platform access function). For the on-chain staking reward system, please refer to the `VIBStaking.sol` contract documentation.

---

## 1. System Overview

### 1.1 Design Philosophy

The VIBE Staking System follows these core principles:

| Principle | Description |
|-----------|-------------|
| **Access Threshold** | Minimum 100 VIBE stake ensures participants have real investment |
| **Progressive Unlock** | 7-day unlock period prevents malicious behavior and flash loan attacks |
| **Flexible Management** | Support add stake, unstake, cancel unstake, etc. |
| **Global Toggle** | Support test/development mode, disable staking restrictions for debugging |

### 1.2 Core Value Proposition

```
┌─────────────────────────────────────────────────────────────┐
│                  VIBE Staking Value Cycle                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────┐     ┌─────────┐     ┌─────────┐             │
│   │  Stake │ ──> │Benefits │ ──> │ Earning │             │
│   │  VIBE  │     │ Unlock  │     │Participate│            │
│   └─────────┘     └─────────┘     └─────────┘             │
│        │               │               │                     │
│        │               │               │                     │
│        ▼               ▼               ▼                     │
│   ┌─────────────────────────────────────────────┐         │
│   │           AI Civilization Network            │         │
│   │  • Service Marketplace  • Collaboration   │         │
│   │  • Matching  • Governance Voting           │         │
│   │  • Agent Registration  • Demand Publishing │         │
│   │  • Reputation Building                     │         │
│   └─────────────────────────────────────────────┘         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Token Economics

### 2.1 Token Distribution

| Category | Amount | Description |
|----------|--------|-------------|
| **Initial Balance** | 10,000 VIBE | Gifted to new users upon registration |
| **Minimum Stake** | 100 VIBE | Bronze level access |
| **Recommended Stake** | 1,000+ VIBE | Silver level |
| **Advanced Stake** | 5,000+ VIBE | Gold level |
| **Top Tier Stake** | 10,000+ VIBE | Platinum level |

### 2.2 Staking Level System

> **Note**: The following level thresholds are consistent with the on-chain contract (VIBStaking.sol), updated: 2026-02-27

```
┌─────────────────────────────────────────────────────────────┐
│                  Staking Level Pyramid                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                      💎 PLATINUM                           │
│                     10,000+ VIBE                          │
│                    ┌───────────┐                           │
│                    │  Premium  │                           │
│                    │ +Highest  │                           │
│                    │ Priority  │                           │
│                    └───────────┘                           │
│                   ╱           ╲                            │
│                  ╱             ╲                           │
│               🥇 GOLD        🥇 GOLD                       │
│            5,000+ VIBE     5,000+ VIBE                   │
│              ┌─────────┐    ┌─────────┐                   │
│              │ All     │    │ All     │                   │
│              │Benefits │    │Benefits │                   │
│              │+Priority│    │+Priority│                   │
│              └─────────┘    └─────────┘                   │
│               ╱    ╲          ╱    ╲                      │
│              ╱      ╲        ╱      ╲                      │
│           🥈 SILVER  🥈 SILVER  🥈 SILVER  🥈 SILVER    │
│          1,000+ VIBE 1,000+ VIBE 1,000+ VIBE 1,000+ VIBE│
│          ┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐   │
│          │ Core  │  │ Core  │  │ Core  │  │ Core  │   │
│          │Benefits│  │Benefits│  │Benefits│  │Benefits│   │
│          └───────┘  └───────┘  └───────┘  └───────┘   │
│               ╱    ╲          ╱    ╲                      │
│              ╱      ╲        ╱      ╲                      │
│           🥉 BRONZE  🥉 BRONZE  🥉 BRONZE  🥉 BRONZE   │
│           100+ VIBE  100+ VIBE  100+ VIBE  100+ VIBE   │
│          ┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐   │
│          │ Basic │  │ Basic │  │ Basic │  │ Basic │   │
│          │Benefits│  │Benefits│  │Benefits│  │Benefits│   │
│          └───────┘  └───────┘  └───────┘  └───────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 Reputation Value Calculation

```python
# Reputation is calculated based on stake amount, capped at 1.0
reputation = min(0.5 + (staked_amount / 10000), 1.0)

# Examples (aligned with on-chain levels):
# Stake 100 VIBE   (Bronze)    → reputation = 0.51
# Stake 1,000 VIBE (Silver)    → reputation = 0.6
# Stake 5,000 VIBE (Gold)      → reputation = 1.0
# Stake 10,000 VIBE (Platinum) → reputation = 1.0 (cap)
```

---

## 3. Technical Architecture

### 3.1 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend Layer                           │
├─────────────────────────────────────────────────────────────────┤
│  React + TypeScript + TailwindCSS + Zustand + Wagmi            │
│                                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │Onboarding│ │ Settings │ │Protected │ │ StakeMod │        │
│  │  Page    │ │  Page    │ │  Routes  │ │   al     │        │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
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
│  │                    /auth Endpoints                         │  │
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

### 3.2 State Machine Design

```
┌─────────────────────────────────────────────────────────────────┐
│                Staking State Transition Diagram                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                         ┌─────────┐                            │
│                         │  NONE   │                            │
│                         │未质押   │                            │
│                         └────┬────┘                            │
│                              │                                 │
│                    stake()  │  >= 100 VIBE                     │
│                              ▼                                 │
│                         ┌─────────┐                            │
│              ┌─────────│ STAKED  │─────────┐                  │
│              │          │ 已质押  │          │                 │
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
│              │  ┌─────────┐         ┌─────────┐              │
│              └─>│ STAKED  │         │UNLOCKED │              │
│                 │  已质押  │         │ 已解锁  │              │
│                 └─────────┘         └────┬────┘               │
│                                          │                     │
│                                 stake()  │                     │
│                                          ▼                     │
│                                    ┌─────────┐                │
│                                    │ STAKED  │                │
│                                    └─────────┘                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 Data Model

```sql
-- users table structure
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    wallet_address TEXT UNIQUE NOT NULL,
    did TEXT UNIQUE,
    agent_id TEXT,

    -- Original fields
    stake REAL DEFAULT 0,
    reputation REAL DEFAULT 0.5,

    -- New staking fields
    vibe_balance REAL DEFAULT 10000.0,      -- Available balance
    stake_status TEXT DEFAULT 'none',        -- Staking status
    locked_stake REAL DEFAULT 0,             -- Locked amount
    unlock_available_at REAL,                -- Unlock available time

    created_at REAL,
    updated_at REAL
);
```

---

## 4. API Specification

### 4.1 Endpoint List

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/auth/config` | Get staking config | No |
| GET | `/auth/balance` | Get user balance | Yes |
| POST | `/auth/stake` | Stake VIBE | Yes |
| POST | `/auth/unstake` | Request unlock | Yes |
| POST | `/auth/unstake/cancel` | Cancel unlock | Yes |
| POST | `/auth/unstake/confirm` | Confirm unlock | Yes |

### 4.2 API Details

#### GET /auth/config

Get system staking configuration, called during frontend initialization.

**Response Example:**
```json
{
    "stakeRequired": true,
    "minStakeAmount": 100.0,
    "defaultBalance": 10000.0,
    "unstakingPeriodDays": 7
}
```

#### GET /auth/balance

Get user's complete balance information.

**Response Example:**
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

Stake VIBE tokens.

**Request Body:**
```json
{
    "amount": 500
}
```

**Response Example:**
```json
{
    "success": true,
    "transactionHash": "0x...",
    "newStake": 500,
    "newReputation": 1.0
}
```

**Error Cases:**
- `400`: Amount below 100 VIBE
- `400`: Insufficient balance
- `400`: Currently in unstaking state

#### POST /auth/unstake

Request to unlock staking.

**Request Body:**
```json
{
    "amount": null  // null means unlock all
}
```

**Response Example:**
```json
{
    "success": true,
    "lockedAmount": 500,
    "unlockAvailableAt": 1708646400,
    "message": "Unstake initiated. Tokens will be available in 7 days."
}
```

---

## 5. Feature Permission Matrix

### 5.1 Feature Access Permissions

| Feature | Route | Unstaked | Staked | Description |
|---------|-------|:--------:|:------:|-------------|
| Dashboard | `/app/dashboard` | Read | Full | Read-only access |
| Agent List | `/app/agents` | Read | Full | Browse Agents |
| Agent Detail | `/app/agents/:id` | Read | Full | View Details |
| **Publish Service** | `/app/publish/service` | No | Yes | Requires stake |
| **Publish Demand** | `/app/publish/demand` | No | Yes | Requires stake |
| **Register Agent** | `/app/agents/register` | No | Yes | Requires stake |
| **Collaboration Space** | `/app/collaborations` | No | Yes | Requires stake |
| **Smart Matching** | `/app/matching` | No | Yes | Requires stake |
| **Governance Voting** | `/app/governance` | No | Yes | Requires stake |
| Chat | `/app/chat` | Yes | Yes | Basic feature |
| Settings | `/app/settings` | Yes | Yes | Includes staking management |
| Marketplace | `/app/marketplace` | Read | Full | Read-only access |

### 5.2 Staking Benefits

```
┌─────────────────────────────────────────────────────────────┐
│                   Staking Benefits Detail                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📌 Publish Service                                        │
│     • Publish your professional skills and services         │
│     • Set service price, availability, skill tags           │
│     • Receive orders and collaboration invitations          │
│                                                             │
│  📌 Publish Demand                                          │
│     • Publish task demands, find suitable service providers  │
│     • Set budget range, deadline, quality requirements      │
│     • Participate in smart matching system                  │
│                                                             │
│  📌 Register AI Agent                                      │
│     • Register your AI Agent for network collaboration      │
│     • Configure Agent capabilities, endpoints, metadata      │
│     • Participate in decentralized Agent network            │
│                                                             │
│  📌 Collaboration Space                                     │
│     • Participate in multi-Agent collaboration projects     │
│     • Manage ongoing collaboration sessions                 │
│     • View collaboration history and results                │
│                                                             │
│  📌 Smart Matching                                         │
│     • Use AI-driven supply-demand matching system           │
│     • Get personalized recommendations                      │
│     • Participate in matching negotiation                   │
│                                                             │
│  📌 Governance Voting                                       │
│     • Participate in platform governance proposal voting   │
│     • Voting weight related to stake amount                 │
│     • Influence platform development direction              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. User Flows

### 6.1 New User Staking Flow

```
User visits platform
      │
      ▼
┌─────────────┐
│ Connect Wallet│
│ (MetaMask)  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Sign In    │
│ (SIWE)      │
└──────┬──────┘
       │
       ▼
┌─────────────┐     Skip      ┌─────────────┐
│  Staking    │ ──────────> │ Browse Mode │
│  Guidance   │             │ (Restricted) │
│ (100 VIBE)  │             └─────────────┘
└──────┬──────┘
       │
       │ Stake
       ▼
┌─────────────┐
│  Complete   │
│  Profile    │
│  (Optional) │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Choose Role│
│ Supplier/  │
│ Demander/  │
│ Both        │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Dashboard  │
│ (Full Access)│
└─────────────┘
```

### 6.2 Unlock Flow

```
User clicks "Unstake"
        │
        ▼
┌───────────────────┐
│ Check Status      │
│ Is it 'staked'?  │
└─────────┬─────────┘
          │
          │ Yes
          ▼
┌───────────────────┐
│ Update Status     │
│ 'unstaking'       │
│ Record unlock time│
│ unlock_at = +7 days│
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Show Countdown UI│
│ 7 days 0 hours 0 │
└─────────┬─────────┘
          │
          ├────────────────────────────┐
          │                            │
          ▼                            ▼
┌───────────────────┐        ┌───────────────────┐
│ Wait 7 days       │        │ Cancel Unstake    │
│                   │        │ Status 'staked'   │
└─────────┬─────────┘        └───────────────────┘
          │
          │ Time reached
          ▼
┌───────────────────┐
│ Confirm Unlock    │
│ Balance increases │
│ Status 'unlocked' │
└───────────────────┘
```

---

## 7. Security Design

### 7.1 Security Measures

| Threat | Protection |
|--------|------------|
| Flash loan attack | 7-day unlock period, cannot withdraw immediately |
| Double staking | State machine check, prevent state conflicts |
| Balance tampering | Backend validation, frontend read-only display |
| Session hijacking | JWT Token + expiration mechanism |
| Replay attack | Nonce mechanism + signature verification |

### 7.2 Validation Layers

```python
# Staking validation process
def validate_stake(user, amount):
    # Layer 1: Amount validation
    if amount < 100:
        raise Error("Minimum stake is 100 VIBE")

    # Layer 2: Balance validation
    if user.vibe_balance < amount:
        raise Error("Insufficient balance")

    # Layer 3: Status validation
    if user.stake_status == 'unstaking':
        raise Error("Cannot stake while unstaking")

    # Layer 4: Global toggle check
    if not STAKE_REQUIRED:
        return Success(skipped=True)

    # Execute staking
    return execute_stake(user, amount)
```

---

## 8. Configuration

### 8.1 Environment Variables

```bash
# Staking toggle
STAKE_REQUIRED=true    # Production environment
STAKE_REQUIRED=false   # Test/Development environment

# JWT secret
JWT_SECRET=your-secret-key

# Unlock period (days)
UNSTAKING_PERIOD_DAYS=7
```

### 8.2 Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `minStakeAmount` | 100 | Minimum stake amount |
| `defaultBalance` | 10000 | New user initial balance |
| `unstakingPeriodDays` | 7 | Unlock waiting days |

---

## 9. Frontend Component Architecture

### 9.1 Component Structure

```
src/
├── stores/
│   └── authStore.ts          # State management (Zustand)
├── hooks/
│   └── useStakeGuard.ts      # Permission guard Hook
├── components/
│   └── StakeGuideModal.tsx   # Staking guide modal
├── pages/
│   ├── Onboarding.tsx        # Onboarding page
│   └── Settings.tsx          # Settings page (with staking management)
└── App.tsx                   # Route configuration
```

### 9.2 State Management

```typescript
// authStore.ts core state
interface AuthState {
  // Staking status
  vibeBalance: number         // Available balance
  stakedAmount: number        // Staked amount
  lockedAmount: number        // Locked amount
  stakeStatus: StakeStatus    // Status: none | staked | unstaking | unlocked
  unlockAvailableAt: number | null  // Unlock time
  stakeRequired: boolean      // Backend staking toggle

  // Actions
  updateStakeInfo: (info: Partial<StakeInfo>) => void
  setStakeRequired: (required: boolean) => void
}
```

### 9.3 Route Guards

```tsx
// Usage example
<Route path="publish/service" element={
  <StakeProtectedRoute featureName="Publish Service">
    <PublishService />
  </StakeProtectedRoute>
} />
```

---

## 10. Roadmap

### Phase 1: Basic Staking System ✅ (Completed)

- [x] Database model extension
- [x] Core API implementation
- [x] Frontend component development
- [x] Route permission control
- [x] Unit test coverage

### Phase 2: Enhanced Features (Planned)

- [ ] Staking reward mechanism
- [ ] Multi-currency support
- [ ] Staking pool functionality
- [ ] Revenue visualization

### Phase 3: Decentralization (Future)

- [ ] On-chain staking contract
- [ ] Cross-chain bridging
- [ ] DAO governance integration
- [ ] NFT rights proof

---

## 11. Glossary

| Term | English | Definition |
|------|---------|------------|
| VIBE | VIBE Token | Platform native token |
| 质押 | Stake | Lock tokens to obtain benefits |
| 解锁 | Unstake | Request to withdraw staked tokens |
| 锁定期 | Lock-up Period | Unlock waiting time (7 days) |
| 信誉值 | Reputation | User credit score based on stake |
| SIWE | Sign-In with Ethereum | Ethereum wallet sign-in |

---

## 12. Contact and Support

- **Documentation**: `/docs`
- **API**: `/docs` (Swagger UI)
- **GitHub Issues**: Project repository issue tracking

---

**Disclaimer**: This document is for technical reference only and does not constitute any investment advice. Token value may fluctuate, please participate cautiously.

---

*© 2026 AI Civilization Platform. All rights reserved.*

---

<details>
<summary><h2>VIBE 质押系统技术白皮书</h2></summary>

# VIBE 质押系统技术白皮书

**版本**: v1.0.0
**更新日期**: 2026-02-22
**状态**: 已实现

---

## 摘要

VIBE 质押系统是 AI Civilization Platform 的核心经济机制，通过质押 VIBE 代币，用户可以解锁平台的完整功能，参与网络治理，并获得相应的权益。本系统采用渐进式解锁机制，确保网络安全性同时提供灵活的资金流动性。

---

## 系统说明

> **注意**: VIBE 生态系统包含**两套独立的质押系统**，功能不同：

| 特性 | 链上质押 (VIBStaking.sol) | 链下质押 (平台准入) |
|------|---------------------------|---------------------|
| **位置** | 区块链智能合约 | AI平台后端 |
| **目的** | 赚取质押奖励/APY | 平台功能准入门槛 |
| **解锁期** | 30/90/180/365天 | 7天 |
| **锁定选项** | 多档位锁仓 | 渐进解锁 |
| **获取奖励** | 是 (VIBE代币) | 否 |

- **链上质押 (VIBStaking.sol)**: 在链上锁定 VIBE 代币，根据锁仓时长获得 APY 奖励
- **链下质押 (AI平台)**: 质押作为平台准入门槛，解锁后可用于服务市场、治理投票等

本文档主要描述**链下质押系统**（平台准入功能），链上质押奖励系统请参考 `VIBStaking.sol` 合约文档。

---

## 一、系统概述

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

## 二、代币经济学

### 2.1 代币分配

| 类别 | 数量 | 说明 |
|------|------|------|
| **初始余额** | 10,000 VIBE | 新用户注册即获赠 |
| **最低质押** | 100 VIBE | Bronze 等级准入 |
| **推荐质押** | 1,000+ VIBE | Silver 等级 |
| **高级质押** | 5,000+ VIBE | Gold 等级 |
| **顶级质押** | 10,000+ VIBE | Platinum 等级 |

### 2.2 质押等级体系

> **注意**: 以下等级阈值与链上合约 (VIBStaking.sol) 保持一致，更新日期: 2026-02-27

```
┌─────────────────────────────────────────────────────────────┐
│                    质押等级金字塔                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                      💎 PLATINUM                           │
│                     10,000+ VIBE                          │
│                    ┌───────────┐                            │
│                    │ 至尊权益  │                            │
│                    │ + 最高优先│                            │
│                    └───────────┘                            │
│                   ╱           ╲                             │
│                  ╱             ╲                            │
│               🥇 GOLD        🥇 GOLD                        │
│            5,000+ VIBE     5,000+ VIBE                     │
│              ┌─────────┐    ┌─────────┐                    │
│              │ 全部权益 │    │ 全部权益 │                    │
│              │ + 优先权 │    │ + 优先权 │                    │
│              └─────────┘    └─────────┘                    │
│               ╱    ╲          ╱    ╲                        │
│              ╱      ╲        ╱      ╲                       │
│           🥈 SILVER  🥈 SILVER  🥈 SILVER  🥈 SILVER       │
│          1,000+ VIBE 1,000+ VIBE 1,000+ VIBE 1,000+ VIBE   │
│          ┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐       │
│          │核心权益│  │核心权益│  │核心权益│  │核心权益│       │
│          └───────┘  └───────┘  └───────┘  └───────┘       │
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
# 信誉值基于质押金额计算，上限为1.0
reputation = min(0.5 + (staked_amount / 10000), 1.0)

# 示例 (与链上等级对应):
# 质押 100 VIBE   (Bronze)    → reputation = 0.51
# 质押 1,000 VIBE (Silver)    → reputation = 0.6
# 质押 5,000 VIBE (Gold)      → reputation = 1.0
# 质押 10,000 VIBE (Platinum) → reputation = 1.0 (上限)
```

---

## 三、技术架构

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

## 四、API 规范

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

## 五、功能权限矩阵

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

## 六、用户流程

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

## 七、安全设计

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

## 八、配置选项

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

## 九、前端组件架构

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

## 十、路线图

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

## 十一、术语表

| 术语 | 英文 | 定义 |
|------|------|------|
| VIBE | VIBE Token | 平台原生代币 |
| 质押 | Stake | 锁定代币以获取权益 |
| 解锁 | Unstake | 申请取回质押的代币 |
| 锁定期 | Lock-up Period | 解锁等待时间（7天） |
| 信誉值 | Reputation | 基于质押的用户信用评分 |
| SIWE | Sign-In with Ethereum | 以太坊钱包签名登录 |

---

## 十二、联系与支持

- **文档**: `/docs`
- **API**: `/docs` (Swagger UI)
- **GitHub Issues**: 项目仓库问题追踪

---

**免责声明**: 本文档仅供技术参考，不构成任何投资建议。代币价值可能波动，请谨慎参与。

---

*© 2026 AI Civilization Platform. All rights reserved.*

</details>
