# 配置说明

> USMSB SDK 系统配置

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
