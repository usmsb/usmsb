# Test Guide

<div style="background: #f0f0f0; padding: 10px; border-radius: 5px; margin: 10px 0;">

**Language / 语言:** <a href="#chinese-translation">English</a> | <a href="#chinese-translation">中文</a>

*Click the link above to jump to the Chinese translation section below.*

</div>

---

<a id="chinese-translation"></a>

<details id="chinese-translation">
<summary><h2>中文翻译 (Click to expand / 点击展开)</h2></summary>

# 测试指南

---

## 1. 运行测试

```bash
# Install test dependencies
pip install -e ".[test]"

# Run all tests
pytest

# Run specific test
pytest tests/test_agent.py
```

---

## 2. Test Structure

```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
└── e2e/          # End-to-end tests
```

---

## 3. Writing Tests

```python
import pytest
from usmsb_sdk import USMSBClient

@pytest.mark.asyncio
async def test_chat():
    client = USMSBClient(api_key="test_key")
    response = await client.chat.send(message="Hello")
    assert response.content is not None
```



---

## 1. 运行测试

```bash
# 安装测试依赖
pip install -e ".[test]"

# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_agent.py
```

---

## 2. 测试结构

```
tests/
├── unit/           # 单元测试
├── integration/    # 集成测试
└── e2e/          # 端到端测试
```

---

## 3. 编写测试

```python
import pytest
from usmsb_sdk import USMSBClient

@pytest.mark.asyncio
async def test_chat():
    client = USMSBClient(api_key="test_key")
    response = await client.chat.send(message="Hello")
    assert response.content is not None
```

</details>
