# USMSB SDK 测试方案

## 概述

本测试方案旨在实现**全量业务覆盖**、**完整业务闭环**的测试体系，确保每次commit都能验证核心业务流程的正确性。

## 测试架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        E2E 测试 (e2e)                          │
│           完整业务流程闭环 - 端到端验证                          │
├─────────────────────────────────────────────────────────────────┤
│                     Integration Tests (integration)            │
│              跨模块业务逻辑 - API交互验证                        │
├─────────────────────────────────────────────────────────────────┤
│                       Unit Tests (unit)                        │
│               单个API功能 - 快速独立验证                        │
├─────────────────────────────────────────────────────────────────┤
│                         Fixtures                                │
│              测试数据 + 辅助函数 + Mock                         │
└─────────────────────────────────────────────────────────────────┘
```

## 测试数据库方案

### 选用策略: 临时文件数据库 (Session级别)

- **位置**: `tmp_path/tests_data/test_civilization.db`
- **生命周期**: Session级别，整个测试会话共享
- **隔离策略**: 测试间不清理，支持业务闭环测试
- **优点**:
  - 支持测试间数据共享，便于测试完整业务流程
  - 保留现场便于调试失败测试
  - 接近真实生产环境的文件数据库

### 环境变量控制

| 环境变量 | 说明 |
|---------|------|
| `CLEAN_DB_BETWEEN_TESTS=1` | 启用测试间数据库清理 |
| `DATABASE_PATH` | 自定义数据库路径 |

## 业务闭环覆盖

| 闭环 | 测试模块 | 覆盖API |
|------|---------|---------|
| 1 | Agent生命周期 | agents, heartbeat |
| 2 | 认证授权 | auth, agent_auth |
| 3 | 钱包管理 | wallet |
| 4 | 质押Staking | staking |
| 5 | 需求-匹配-协作 | demands, matching, collaborations |
| 6 | 工作流 | workflows |
| 7 | 治理 | governance |
| 8 | 交易 | transactions |
| 9 | 环境管理 | environments |
| 10 | 学习洞察 | learning |
| 11 | 网络探索 | network |
| 12 | 服务管理 | services |
| 13 | 基因胶囊 | gene_capsule |
| 14 | 声誉 | reputation |
| 15 | 匹配前谈判 | pre_match_negotiation |
| 16 | Meta匹配 | meta_agent_matching |
| 17 | 预测 | predictions |
| 18 | 区块链 | blockchain |
| 19 | 注册 | registration |
| 20 | 系统 | system |

## 测试数据

测试使用独立的测试数据 fixtures，定义在 `tests/fixtures/test_data.py` 中：

- `AgentTestData` - Agent测试数据
- `UserTestData` - 用户测试数据
- `WalletTestData` - 钱包测试数据
- `DemandTestData` - 需求测试数据
- `ServiceTestData` - 服务测试数据
- `CollaborationTestData` - 协作测试数据
- `WorkflowTestData` - 工作流测试数据
- `ProposalTestData` - 提案测试数据
- `TransactionTestData` - 交易测试数据

## 运行测试

### 快速开始

```bash
# 全部测试
python run_full_tests.py

# 仅单元测试
python run_full_tests.py --unit

# 仅集成测试
python run_full_tests.py --integration

# 仅E2E测试
python run_full_tests.py --e2e

# CI模式 (每次commit运行)
python run_full_tests.py --ci
```

### 使用pytest直接运行

```bash
# 全部测试
pytest tests/test_business_api_full_coverage.py -v

# 仅特定模块
pytest tests/test_business_api_full_coverage.py -m agent -v

# 仅快速测试
pytest tests/test_business_api_full_coverage.py -m "unit and not slow" -v

# 生成覆盖率报告
pytest tests/test_business_api_full_coverage.py --cov=usmsb_sdk --cov-report=html
```

### 使用Make命令

```bash
# 安装依赖
make install-test

# 运行所有测试
make test

# 运行单元测试
make test-unit

# 运行集成测试
make test-integration

# 运行E2E测试
make test-e2e

# 运行CI测试
make test-ci

# 生成覆盖率报告
make test-coverage
```

## 标记说明

| 标记 | 说明 |
|------|------|
| `unit` | 单元测试 |
| `integration` | 集成测试 |
| `e2e` | 端到端测试 |
| `ci` | CI/CD自动测试 |
| `slow` | 慢速测试 |
| `agent` | Agent模块测试 |
| `auth` | 认证模块测试 |
| `wallet` | 钱包模块测试 |
| `staking` | 质押模块测试 |
| `matching` | 匹配模块测试 |
| `collaboration` | 协作模块测试 |
| `workflow` | 工作流模块测试 |
| `governance` | 治理模块测试 |
| `transaction` | 交易模块测试 |
| `environment` | 环境模块测试 |
| `learning` | 学习模块测试 |
| `network` | 网络模块测试 |
| `blockchain` | 区块链模块测试 |

## CI/CD集成

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt

      - name: Run CI tests
        run: |
          python run_full_tests.py --ci
        env:
          TESTING: true
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ETH_TESTNET_RPC: ${{ secrets.ETH_TESTNET_RPC }}

      - name: Upload coverage
        if: success()
        uses: codecov/codecov-action@v3
```

### 本地Pre-commit Hook

```bash
# 安装pre-commit hook
cp .git/hooks/pre-commit .git/hooks/pre-commit.sample
chmod +x .git/hooks/pre-commit
```

## 覆盖率要求

| 测试类型 | 最低覆盖率 |
|----------|-----------|
| 单元测试 | 70% |
| 集成测试 | 60% |
| E2E测试 | 50% |
| 整体 | 80% |

## 外部依赖

测试使用以下真实外部服务：

1. **LLM服务** - 用于需要AI能力的测试
   - 配置: `OPENAI_API_KEY` 或其他LLM提供商
   - 标记: `requires_llm`

2. **区块链测试网** - 用于区块链交互测试
   - 配置: `ETH_TESTNET_RPC` (如 Sepolia)
   - 标记: `real_blockchain`

## 测试数据隔离

- 使用内存数据库 (`:memory:` 或临时文件)
- 每个测试独立的数据fixtures
- 测试后保留数据库便于调试

## 故障排查

### 测试失败

1. 检查环境变量是否正确配置
2. 查看详细错误信息: `pytest -vv`
3. 运行单个测试: `pytest tests/test_business_api_full_coverage.py::TestAgentLifecycle::test_agent_create -vv`

### 覆盖率不足

1. 查看未覆盖的代码: `htmlcov/index.html`
2. 添加更多边界条件测试
3. 检查异常处理路径

## 贡献指南

添加新测试时：

1. 选择合适的测试类型 (unit/integration/e2e)
2. 使用现有的fixtures创建测试数据
3. 添加适当的pytest标记
4. 确保测试独立可运行
5. 更新本README文档

## 许可证

MIT License
