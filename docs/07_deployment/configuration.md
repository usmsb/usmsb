# Configuration Guide

<div style="background: #f0f0f0; padding: 10px; border-radius: 5px; margin: 10px 0;">

**Language / 语言:** <a href="#chinese-translation">English</a> | <a href="#chinese-translation">中文</a>

*Click the link above to jump to the Chinese translation section below.*

</div>

**[English](#1-configuration-file) | [中文](#1-配置文件)**

---

## 1. Configuration File

Default configuration file: `config.yaml`

---

## 2. Configuration Options

### 2.1 API Configuration

```yaml
api:
  base_url: "https://api.usmsb.com"
  api_key: "your_api_key"
  timeout: 30
```

### 2.2 LLM Configuration

```yaml
llm:
  provider: "openai"  # openai, anthropic, glm, minimax
  api_key: "your_key"
  model: "gpt-4"
  temperature: 0.7
```

### 2.3 Database Configuration

```yaml
database:
  type: "sqlite"  # sqlite, postgres
  path: "./data/usmsb.db"
```

### 2.4 Logging Configuration

```yaml
logging:
  level: "INFO"
  format: "json"
  output: "file"
```

<a id="chinese-translation"></a>

<details id="chinese-translation">
<summary><h2>中文翻译 (Click to expand / 点击展开)</h2></summary>

# 配置说明

---

## 1. 配置文件

默认配置文件: `config.yaml`

---

## 2. 配置项

### 2.1 API 配置

```yaml
api:
  base_url: "https://api.usmsb.com"
  api_key: "your_api_key"
  timeout: 30
```

### 2.2 LLM 配置

```yaml
llm:
  provider: "openai"  # openai, anthropic, glm, minimax
  api_key: "your_key"
  model: "gpt-4"
  temperature: 0.7
```

### 2.3 数据库配置

```yaml
database:
  type: "sqlite"  # sqlite, postgres
  path: "./data/usmsb.db"
```

### 2.4 日志配置

```yaml
logging:
  level: "INFO"
  format: "json"
  output: "file"
```

</details>
