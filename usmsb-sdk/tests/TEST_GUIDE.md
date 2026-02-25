# 精准匹配系统测试指南

本文档描述了如何运行 Meta Agent 精准匹配系统的测试。

---

## 测试结构

```
tests/
├── unit/                           # 单元测试
│   ├── test_meta_agent_service.py
│   ├── test_meta_agent_service_extended.py
│   ├── test_enhanced_discovery.py
│   └── test_pre_match_negotiation.py
├── integration/                    # 集成测试
│   └── test_meta_agent_integration.py
├── e2e/                            # 端到端测试
│   └── test_precise_matching_e2e.py
└── run_tests.py                   # 测试运行脚本
```

---

## 快速开始

### 运行所有测试

```bash
cd usmsb-sdk
python tests/run_tests.py
```

### 运行特定类型的测试

```bash
# 单元测试
python tests/run_tests.py --type unit

# 集成测试
python tests/run_tests.py --type integration

# E2E 测试
python tests/run_tests.py --type e2e
```

### 详细输出

```bash
python tests/run_tests.py --verbose
```

### 生成覆盖率报告

```bash
python tests/run_tests.py --coverage
```

---

## 单元测试

### 测试内容

1. **数据类测试**
   - ConversationMessage
   - MetaAgentConversation
   - AgentProfile
   - AgentRecommendation
   - Opportunity

2. **服务类测试**
   - MetaAgentService 初始化
   - 对话管理
   - 能力画像提取
   - 推荐系统
   - 咨询服务
   - 展示接收

3. **边缘情况测试**
   - 空消息
   - 超长消息
   - 特殊字符
   - 并发对话

### 运行单元测试

```bash
# 使用 pytest 直接运行
pytest tests/unit/ -v

# 使用测试脚本
python tests/run_tests.py --type unit
```

---

## 集成测试

### 测试内容

1. **MetaAgent + GeneCapsule 集成**
   - 基因胶囊服务调用
   - 经验发现集成

2. **MetaAgent + PreMatchNegotiation 集成**
   - 预匹配谈判流程
   - 谈判通知集成

3. **增强发现系统集成**
   - 多维度搜索
   - 语义匹配
   - 批量对比

4. **WebSocket 通知集成**
   - 订阅管理
   - 通知发送

### 运行集成测试

```bash
pytest tests/integration/ -v
```

---

## E2E 测试

### 前置条件

E2E 测试需要运行中的服务器：

```bash
# 启动服务器
cd usmsb-sdk
python -m usmsb_sdk.api.rest.main
```

或设置环境变量：

```bash
export E2E_BASE_URL=http://your-server:8000
```

### 测试内容

1. **完整面试流程**
   - 发起对话 → 消息交互 → 画像提取

2. **展示到推荐流程**
   - 分享展示 → 发起推荐 → 验证结果

3. **咨询流程**
   - 发起咨询 → 验证响应

4. **机会通知流程**
   - 创建画像 → 发送通知 → 验证结果

5. **基因胶囊匹配流程**
   - 添加经验 → 匹配请求 → 验证结果

6. **错误处理**
   - 无效对话类型
   - 缺少 agent_id
   - 不存在的对话
   - 空消息

7. **性能测试**
   - 并发请求
   - 响应时间

### 运行 E2E 测试

```bash
# 确保服务器运行
python tests/run_tests.py --type e2e

# 或直接使用 pytest
pytest tests/e2e/ -v --tb=short
```

---

## 测试覆盖率

### 生成覆盖率报告

```bash
# 终端输出
pytest --cov=usmsb_sdk --cov-report=term-missing

# HTML 报告
pytest --cov=usmsb_sdk --cov-report=html
open htmlcov/index.html
```

### 使用测试脚本

```bash
python tests/run_tests.py --coverage --html
```

---

## CI/CD 集成

### GitHub Actions 示例

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-asyncio pytest-cov
      - name: Run unit tests
        run: python tests/run_tests.py --type unit --coverage
      - name: Run integration tests
        run: python tests/run_tests.py --type integration
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## 测试最佳实践

### 1. 测试命名规范

```python
# 测试方法命名: test_<被测方法>_<场景>_<预期结果>
def test_initiate_conversation_with_valid_params_returns_conversation():
    pass

def test_process_message_with_empty_content_returns_error():
    pass
```

### 2. 使用 Fixtures

```python
@pytest.fixture
def meta_agent_service():
    """Create a MetaAgentService instance"""
    service = MetaAgentService(...)
    return service
```

### 3. 异步测试

```python
@pytest.mark.asyncio
async def test_async_operation():
    result = await async_function()
    assert result is not None
```

### 4. Mock 外部依赖

```python
@patch('usmsb_sdk.platform.external.meta_agent.services.meta_agent_service.MetaAgentService')
def test_with_mock(mock_service):
    mock_service.return_value = ...
```

---

## 常见问题

### Q: E2E 测试失败，提示连接超时

A: 确保服务器正在运行，或设置正确的 `E2E_BASE_URL` 环境变量。

### Q: 测试运行很慢

A: 使用 `--type unit` 只运行单元测试，跳过 E2E 测试。

### Q: 覆盖率报告不完整

A: 确保安装了 `pytest-cov`：`pip install pytest-cov`

---

## 测试报告位置

- 单元测试报告: `tests/reports/unit/`
- 集成测试报告: `tests/reports/integration/`
- E2E 测试报告: `tests/reports/e2e/`
- 覆盖率报告: `htmlcov/`

---

*最后更新: 2026-02-25*
