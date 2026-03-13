# Monitoring & Operations

> USMSB SDK Monitoring and Operations

<div style="background: #f0f0f0; padding: 10px; border-radius: 5px; margin: 10px 0;">

**Language / 语言:** <a href="#chinese-translation">English</a> | <a href="#chinese-translation">中文</a>

*Click the link above to jump to the Chinese translation section below.*

</div>

---

<a id="chinese-translation"></a>

<details id="chinese-translation">
<summary><h2>中文翻译 (Click to expand / 点击展开)</h2></summary>

# 监控运维

> USMSB SDK 监控与运维

---

## 1. 监控指标

### 1.1 System Metrics

- CPU Usage
- Memory Usage
- Disk I/O
- Network Traffic

### 1.2 Business Metrics

- API Request Volume
- Response Time
- Agent Online Count
- Matching Success Rate

---

## 2. Logging

### 2.1 Log Levels

- DEBUG: Debug Information
- INFO: General Information
- WARNING: Warning
- ERROR: Error
- CRITICAL: Critical Error

### 2.2 Log Format

```json
{
  "timestamp": "2026-02-26T10:00:00Z",
  "level": "INFO",
  "message": "Agent registered",
  "agent_id": "agent_123"
}
```

---

## 3. Alerts

Configure alert rules:

```yaml
alerts:
  - name: "high_cpu"
    condition: "cpu > 80"
    duration: "5m"
    action: "notify"
```



> USMSB SDK 监控与运维

---

## 1. 监控指标

### 1.1 系统指标

- CPU 使用率
- 内存使用
- 磁盘 I/O
- 网络流量

### 1.2 业务指标

- API 请求量
- 响应时间
- Agent 在线数
- 匹配成功率

---

## 2. 日志

### 2.1 日志级别

- DEBUG: 调试信息
- INFO: 一般信息
- WARNING: 警告
- ERROR: 错误
- CRITICAL: 严重错误

### 2.2 日志格式

```json
{
  "timestamp": "2026-02-26T10:00:00Z",
  "level": "INFO",
  "message": "Agent registered",
  "agent_id": "agent_123"
}
```

---

## 3. 告警

配置告警规则:

```yaml
alerts:
  - name: "high_cpu"
    condition: "cpu > 80"
    duration: "5m"
    action: "notify"
```

</details>
