# Deployment Guide

<div style="background: #f0f0f0; padding: 10px; border-radius: 5px; margin: 10px 0;">

**Language / 语言:** <a href="#chinese-translation">English</a> | <a href="#chinese-translation">中文</a>

*Click the link above to jump to the Chinese translation section below.*

</div>

**[English](#1-environment-requirements) | [中文](#1-环境要求)**

---

## 1. Environment Requirements

- Python 3.10+
- SQLite
- 4GB+ RAM

---

## 2. Local Deployment

```bash
# Clone
git clone https://github.com/usmsb/usmsb.git
cd usmsb-sdk

# Install
pip install -e .

# Run
python -m usmsb_sdk.api.rest.main
```

---

## 3. Docker Deployment

```bash
# Build
docker build -t usmsb-sdk .

# Run
docker run -p 8000:8000 usmsb-sdk
```

---

## 4. Configuration

Edit `config.yaml`:

```yaml
server:
  host: "0.0.0.0"
  port: 8000

database:
  type: "sqlite"
  path: "./data/usmsb.db"
```

<a id="chinese-translation"></a>

<details id="chinese-translation">
<summary><h2>中文翻译 (Click to expand / 点击展开)</h2></summary>

# 部署指南

---

## 1. 环境要求

- Python 3.10+
- SQLite
- 4GB+ RAM

---

## 2. 本地部署

```bash
# 克隆
git clone https://github.com/usmsb/usmsb.git
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

</details>
