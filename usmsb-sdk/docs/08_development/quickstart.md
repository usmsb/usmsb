# 快速开始

> USMSB SDK 快速入门指南

---

## 1. 安装

```bash
# 克隆项目
git clone https://github.com/usmsb-sdk/usmsb-sdk.git
cd usmsb-sdk

# 安装依赖
pip install -e .
```

---

## 2. 配置

创建配置文件 `config.yaml`:

```yaml
api:
  base_url: "https://api.usmsb.com"
  api_key: "your_api_key"

llm:
  provider: "openai"
  api_key: "your_openai_key"

database:
  type: "sqlite"
  path: "./data/usmsb.db"
```

---

## 3. 运行示例

```python
import asyncio
from usmsb_sdk import USMSBClient

async def main():
    client = USMSBClient(api_key="your_api_key")
    
    # 对话
    response = await client.chat.send(
        message="Hello!"
    )
    print(response)

asyncio.run(main())
```

---

## 4. 下一步

- [Python SDK](../06_api/python_sdk.md) - 详细SDK用法
- [示例代码](./examples.md) - 更多示例
- [REST API](../06_api/rest_api.md) - API参考
