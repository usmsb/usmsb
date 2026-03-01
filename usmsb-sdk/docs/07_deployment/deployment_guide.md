# 部署指南

> USMSB SDK 部署指南

---

## 1. 环境要求

- Python 3.10+
- SQLite
- 4GB+ RAM

---

## 2. 本地部署

```bash
# 克隆
git clone https://github.com/usmsb-sdk/usmsb-sdk.git
cd usmsb-sdk

# 安装
pip install -e .

# 运行
python -m usmsb_sdk.api.rest.main
```

---

## 3. Docker 部署

```bash
# 构建
docker build -t usmsb-sdk .

# 运行
docker run -p 8000:8000 usmsb-sdk
```

---

## 4. 配置

编辑 `config.yaml`:

```yaml
server:
  host: "0.0.0.0"
  port: 8000

database:
  type: "sqlite"
  path: "./data/usmsb.db"
```
