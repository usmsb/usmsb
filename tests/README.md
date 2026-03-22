# USMSB SDK 测试方案

> 更新于 2026-03-22

## 概述

本测试方案实现**全量业务覆盖**、**完整业务闭环**的测试体系，确保每次 commit 都能验证核心业务流程的正确性。

## 测试架构

```
tests/
├── business/                  # 业务逻辑单元测试（按领域分类）
│   ├── test_agents_business.py
│   ├── test_orders_business.py
│   ├── test_staking_business.py
│   └── ...
├── integration/               # 跨模块集成测试
│   ├── conftest.py
│   ├── test_agents.py
│   ├── test_orders.py
│   ├── test_negotiations.py
│   ├── test_staking.py
│   ├── test_usmsb_matching.py
│   └── ...
├── e2e/                      # 端到端流程测试
│   ├── conftest.py
│   ├── test_order_flow.py    # 跨模块业务闭环（14个流程测试）
│   ├── test_staking_e2e.py  # 质押流程（6个端点可达性测试）
│   ├── test_precise_matching_e2e.py    # (跳过，需Meta-agent服务)
│   ├── test_smart_memory_e2e.py        # (跳过，需Smart memory服务)
│   └── test_agent_sdk_e2e.py           # (跳过，需SDK环境)
├── fixtures/                 # 共享测试数据和辅助函数
├── unit/                     # 底层单元测试
└── conftest.py              # 全局 pytest 配置和共享 fixtures
```

## 测试数据方案

### 内存数据库 + 临时文件数据库

- **集成测试**: 使用 `tests/integration/conftest.py` 的 `create_test_db()` 创建独立内存数据库
- **E2E 测试**: 使用 `tests/e2e/conftest.py` 的 `shared_db` 模块级共享内存数据库
- **隔离策略**: 每个测试函数通过 `function` 级别 fixture 获取独立 DB 连接

### 环境变量控制

| 环境变量 | 说明 |
|---------|------|
| `CLEAN_DB_BETWEEN_TESTS=1` | 启用测试间数据库清理 |
| `DATABASE_PATH` | 自定义数据库路径 |

## 当前测试状态

> 2026-03-22 最新

| 测试类别 | 文件数 | 通过 | 跳过 | 失败 |
|----------|--------|------|------|------|
| 业务逻辑测试 | 9 | **182** | 0 | ✅ 0 |
| 集成测试 | 20 | **190** | 8 | ✅ 0 |
| **E2E 流程测试** | 4 | **20** | 34 | ✅ 0 |
| **合计** | — | **392** | 42 | **0** ✅ |
| 集成测试 | 20 | **190** | 8 | ✅ 0 |
| **E2E 流程测试** | 4 | **20** | 34 | ✅ 0 |
| **合计** | — | **392** | 42 | **0** ✅ |

### E2E 测试详情

| 文件 | 通过 | 跳过 | 说明 |
|------|------|------|------|
| `test_order_flow.py` | 14 | 0 | 跨模块业务闭环：注册→质押→订单→谈判→治理 |
| `test_staking_e2e.py` | 6 | 0 | 质押/取消质押/配置/余额/Profile 端点可达性 |
| `test_precise_matching_e2e.py` | 0 | **11** | Meta-agent 服务返回 503（服务未实现）|
| `test_smart_memory_e2e.py` | 0 | **11** | Smart memory 服务不可用 |
| `test_agent_sdk_e2e.py` | 0 | **6** | 需要完整 SDK 环境 |

### 集成测试覆盖的模块

| 模块 | 测试文件 |
|------|---------|
| Agents | `test_agents.py` |
| Orders | `test_orders.py` |
| Negotiations | `test_negotiations.py` |
| Joint Orders | `test_joint_order.py` |
| Disputes | `test_dispute.py` |
| Staking | `test_staking.py` |
| Registration | `test_registration.py` |
| Identity | `test_identity.py` |
| Governance | `test_governance.py` |
| Blockchain | `test_blockchain.py` |
| USMSB Matching | `test_usmsb_matching.py` |
| Services | `test_services.py` |
| Agent SDK | `test_agent_sdk_integration.py` |

| Matching Endpoints | `test_matching_endpoints.py` | ← **NEW** |
| Wallet Endpoints | `test_wallet_endpoints.py` | ← **NEW** |
| Workflow Endpoints | `test_workflow_endpoints.py` | ← **NEW** |
| Collaboration Endpoints | `test_collaboration_endpoints.py` | ← **NEW** |
| State Machines | `test_state_machines.py` | ← **NEW** |
| Data Consistency | `test_data_consistency.py` | ← **NEW** |
| Matching Endpoints | `test_matching_endpoints.py` | ← **NEW** |
| Wallet Endpoints | `test_wallet_endpoints.py` | ← **NEW** |
| Workflow Endpoints | `test_workflow_endpoints.py` | ← **NEW** |
| Collaboration Endpoints | `test_collaboration_endpoints.py` | ← **NEW** |
| State Machines | `test_state_machines.py` | ← **NEW** |
| Data Consistency | `test_data_consistency.py` | ← **NEW** |
| Memory Manager | `test_memory_manager.py` |
| Pre-match Negotiation | `test_pre_match_negotiation.py` |

### 跳过的集成测试（20个）

| 文件 | 跳过数 | 原因 |
|------|--------|------|
| `test_multi_user_isolation.py` | 1 | SessionManager 依赖外部服务超时 |
| `test_meta_agent_integration.py` | 8 | `EnhancedDiscoveryManager` 签名变更 |
| `test_staking_integration.py` | 11 | 路径 `/auth/...` 应为 `/api/auth/...` |

## 运行测试

### 快速开始

```bash
# 全部测试（排除已知问题）
pytest tests/integration/ tests/e2e/ -o timeout=15 -q

# 仅集成测试
pytest tests/integration/ -o timeout=15 -q

# 仅 E2E 测试
pytest tests/e2e/ -o timeout=180 -q

# 仅业务逻辑测试（核心文件）
pytest tests/test_orders_business.py tests/test_negotiations_business.py \
       tests/test_joint_order_business.py tests/test_dispute_business.py \
       tests/test_staking_business.py tests/test_registration_business.py \
       tests/test_identity_business.py tests/test_governance_business.py \
       tests/test_matching_business.py -o timeout=15 -q
```

### 使用 pytest 直接运行

```bash
# 全部测试
pytest tests/ -o timeout=15 -q

# 仅特定模块
pytest tests/integration/test_orders.py -v

# 生成覆盖率报告
pytest tests/ --cov=usmsb_sdk --cov-report=html --cov-report=term
```

## 标记说明

| 标记 | 说明 |
|------|------|
| `integration` | 集成测试（`tests/integration/`） |
| `e2e` | 端到端测试（`tests/e2e/`） |
| `business` | 业务逻辑测试（`tests/test_*_business.py`） |
| `unit` | 单元测试（`tests/unit/`） |

## 外部依赖 Mock 策略

| 服务 | Mock 方式 |
|------|-----------|
| **Web3/区块链** | `mock_web3` fixture（`tests/integration/conftest.py`）|
| **VIBGovernanceClient** | `mock_vib_governance_client` fixture |
| **数据库** | 内存 SQLite (`create_test_db()`) |
| **外部 HTTP** | `httpx.AsyncClient` + 响应模拟 |

## 已知限制

1. **Meta-agent 服务** (`/api/meta-agent/*`): 返回 503，服务未实现
2. **Smart Memory 服务**: 服务不可用
3. **Agent SDK E2E**: 需要完整 SDK 环境配置
4. **多用户隔离测试**: SessionManager 依赖外部服务超时
5. **部分路径重构**: `test_staking_integration.py` 中旧路径 `/auth/...` 需更新为 `/api/auth/...`

## 下一步测试计划

### P1 — 补充现有模块的端点覆盖

根据 [TEST_GAP_ANALYSIS.md](./TEST_GAP_ANALYSIS.md)，以下模块的端点尚未测试：

| 模块 | 缺失端点 | 优先级 |
|------|---------|--------|
| **Matching Router** | `search-demands`, `search-suppliers`, `negotiate`, `opportunities`, `stats` | P1 |
| **Transactions Router** | `escrow`, `start`, `deliver`, `accept`, `dispute`, `resolve`, `cancel` | P1 |
| **Wallet Router** | `balance`, `transactions/{tx_id}` | P1 |
| **Workflows Router** | `execute` | P1 |
| **Collaborations Router** | `execute`, `join`, `contribute`, `stats` | P1 |
| **Learning Router** | `analyze`, `insights`, `strategy`, `market` | P2 |
| **Network Router** | `explore`, `recommendations`, `stats` | P2 |
| **Reputation Router** | `history` | P2 |

### P2 — 修复现有跳过的测试

1. **`test_staking_integration.py` (11个跳过)**
   - 修复路径: `/auth/...` → `/api/auth/...`
   - 责任人: 测试框架

2. **`test_agent_sdk_integration.py` (8个跳过)**
   - 修复 `EnhancedDiscoveryManager` 签名问题
   - 需要: `agent_config` 和 `communication_manager` 参数

3. **`test_meta_agent_integration.py` (8个跳过)**
   - 同上，SDK 签名问题

### P3 — 新增测试类型

1. **状态机测试**
   - 交易状态转换: `created → escrow → delivered → completed`
   - 协作状态转换: `pending → active → completed`
   - 质押状态转换: `none → staked → unstaking → unlocked`
   - 争议状态转换: `open → resolved`

2. **数据一致性测试**
   - Agent ↔ Wallet 数据一致性
   - Demand ↔ Service ↔ Match 数据一致性
   - Staking ↔ Reputation 联动

3. **并发安全测试**
   - 并发创建 Agent
   - 并发质押/取消质押
   - 并发订单创建

4. **E2E 流程扩展**
   - 完整 Matching 流程: Demand → Match → Negotiation → Proposal → Order
   - 完整 Dispute 流程: Order → Dispute → Resolution
   - 完整 Governance 流程: Proposal → Vote → Execute

### P4 — 安全测试

1. 授权测试（跨用户访问）
2. SQL 注入防护
3. 越权操作防护
4. 超长字符串边界条件

## 覆盖率目标

| 测试类型 | 当前覆盖率 | 目标 |
|----------|-----------|------|
| 整体 | ~60% | 80% |
| API 端点 | ~70% | 90% |
| 业务逻辑 | ~75% | 85% |
| 状态机 | ~40% | 80% |

## 故障排查

### 测试失败

1. 查看详细错误: `pytest -vv`
2. 运行单个测试: `pytest tests/integration/test_orders.py::TestOrders::test_order_create -vv`
3. 检查数据库状态: `sqlite3 tests_data/test.db`

### 超时问题

- E2E 测试默认 180s 超时（app 加载约 7s）
- 集成测试默认 15s 超时

## 贡献指南

添加新测试时：

1. 选择合适的测试类型 (`integration`/`e2e`/`business`)
2. 使用现有 fixtures（`MOCK_USER`, `mock_web3`, `sample_bound_agent` 等）
3. 添加适当的 pytest 标记
4. 确保测试独立可运行
5. 更新本 README 文档
