# Quick Start

<div style="background: #f0f0f0; padding: 10px; border-radius: 5px; margin: 10px 0;">

**Language / 语言:** <a href="#chinese-translation">English</a> | <a href="#chinese-translation">中文</a>

*Click the link above to jump to the Chinese translation section below.*

</div>

**[English](#1-installation) | [中文](#1-安装)**

---

## 1. Installation

```bash
# Clone project
git clone https://github.com/usmsb/usmsb.git
cd usmsb-sdk

# Install dependencies
pip install -e .
```

---

## 2. Configuration

Create configuration file `config.yaml`:

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

## 3. Run Example

```python
import asyncio
from usmsb_sdk import USMSBClient

async def main():
    client = USMSBClient(api_key="your_api_key")

    # Chat
    response = await client.chat.send(
        message="Hello!"
    )
    print(response)

asyncio.run(main())
```

---

## 4. Next Steps

- [Python SDK](../06_api/python_sdk.md) - Detailed SDK usage
- [Examples](./examples.md) - More examples
- [REST API](../06_api/rest_api.md) - API reference

<a id="chinese-translation"></a>

<details id="chinese-translation">
<summary><h2>中文翻译 (Click to expand / 点击展开)</h2></summary>

# 快速开始

---

## 1. 安装

```bash
# 克隆项目
git clone https://github.com/usmsb/usmsb.git
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

</details>
