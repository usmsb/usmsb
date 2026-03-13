# 创意经济平台技术设计文档

> 基于USMSB、IAP与雅典娜计划的Z世代创意人群品牌方案
> 
> 版本：1.0.0 | 日期：2025-02-23

## 文档目录

| 章节 | 文件 | 内容 |
|------|------|------|
| 第1章 | [01_overview.md](./01_overview.md) | 项目概述与愿景 |
| 第2章 | [02_architecture.md](./02_architecture.md) | 系统架构设计 |
| 第3章 | [03_joint_order.md](./03_joint_order.md) | 联合订单系统设计 |
| 第4章 | [04_asset_fractionalization.md](./04_asset_fractionalization.md) | 资产碎片化NFT设计 |
| 第5章 | [05_zk_credential.md](./05_zk_credential.md) | zk-信用通行证设计 |
| 第6章 | [06_smart_contracts.md](./06_smart_contracts.md) | 智能合约详细设计 |
| 第7章 | [07_offchain_services.md](./07_offchain_services.md) | 链下服务设计 |
| 第8章 | [08_trust_scenarios.md](./08_trust_scenarios.md) | 平台信任场景全景 |
| 第9章 | [09_implementation_roadmap.md](./09_implementation_roadmap.md) | 实施路线图 |

## 核心设计决策

### 链上 vs 链下分工原则

| 功能类型 | 链上实现 | 链下实现 | 原因 |
|----------|----------|----------|------|
| **联合订单** | 资金托管、状态管理、结算执行 | 需求聚合、竞价评估 | 托管必须链上确保安全 |
| **资产碎片化** | NFT铸造、碎片发行、收益分发 | 估值计算、碎片定价 | 所有权必须链上透明 |
| **zk信用通行证** | 证明验证、凭证签发 | 证明生成、数据聚合 | 验证需公开，生成需隐私 |

### Gas费策略

- **用户全额支付**：基础操作
- **平台补贴**：复杂操作部分补贴
- **分摊机制**：联合订单按比例分摊

### 上链方式选择

系统提供两种上链方式，由用户和Agent自动选择：
1. **最小化上链**：只托管结算，复杂逻辑链下（低Gas）
2. **完整上链**：完整逻辑在链上执行（高安全）

---

## 快速开始

### 智能合约目录

```
contracts/
├── src/
│   ├── JointOrder.sol       # 联合订单合约
│   ├── AssetVault.sol       # 资产碎片化合约
│   ├── ZKCredential.sol     # zk信用通行证合约
│   ├── VIBToken.sol         # 代币合约 (已有)
│   ├── VIBStaking.sol       # 质押合约 (已有)
│   ├── VIBIdentity.sol      # 身份合约 (已有)
│   └── VIBGovernance.sol    # 治理合约 (已有)
```

### 链下服务目录

```
src/usmsb_sdk/services/
├── joint_order_service.py       # 联合订单服务
├── asset_fractionalization_service.py  # 资产碎片化服务
├── zk_credential_service.py     # zk证明服务
├── dynamic_pricing_service.py   # 动态定价服务 (已有)
└── reputation_service.py        # 信誉服务 (已有)
```

### 测试目录

```
tests/
├── contracts/                   # 智能合约测试
│   ├── test_joint_order.py
│   ├── test_asset_vault.py
│   └── test_zk_credential.py
├── integration/                 # 集成测试
│   └── test_full_flow.py
└── e2e/                         # 端到端测试
    └── test_user_journey.py
```

---

## 核心概念速查

### ISA (智能服务体)

```
ISA = 去中心化节点 + Meta Agent + 人类运营者

┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  P2PNode     │    │  Meta Agent  │    │   人类运营者  │
│ (去中心化节点)│    │  (AI智能体)   │    │  (决策/监督)  │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────┐
│                    ISA 服务能力                      │
├─────────────────────────────────────────────────────┤
│ • 服务注册与发现        • 智能决策与执行            │
│ • 协议治理参与          • 本地服务托管              │
│ • 信誉与质押管理        • 异常处理与人工介入        │
└─────────────────────────────────────────────────────┘
```

### 联合订单流程

```
Phase 1: 需求聚合
  C端用户发布需求 → AI代理匹配相似需求 → 形成需求池

Phase 2: 反向竞价
  发布竞价请求 → 服务商提交报价 → 系统评估选择

Phase 3: 合约执行
  智能合约托管资金 → 服务商交付 → 用户确认 → 分批放款
```

### zk-信用通行证核心原则

```
证明属性，不暴露具体值
证明历史，不暴露具体交易
证明资格，不暴露原因
```

---

## 联系与贡献

- 技术负责人：AI Civilization Platform Team
- 文档维护：自动生成
- 最后更新：2025-02-23
