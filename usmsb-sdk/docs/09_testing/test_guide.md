# 测试指南

> USMSB SDK 测试指南

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
