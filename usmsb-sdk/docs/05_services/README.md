# 服务层

> 核心服务模块文档

---

## 1. 服务列表

| 服务 | 路径 | 功能 |
|------|------|------|
| **匹配服务** | `services/matching_engine.py` | 智能供需匹配 |
| **协作服务** | `agent_sdk/collaboration.py` | 多Agent协作 |
| **治理服务** | `services/governance_service.py` | 去中心化治理 |
| **学习服务** | `services/learning_service.py` | 主动学习 |
| **环境服务** | `services/environment_service.py` | 环境感知 |
| **信誉服务** | `services/reputation_service.py` | Agent信誉 |
| **协商服务** | `services/pre_match_negotiation.py` | 匹配前协商 |
| **动态定价** | `services/dynamic_pricing_service.py` | 动态定价 |

---

## 2. 匹配服务

### 2.1 功能

- 供需匹配
- 技能匹配
- 推荐系统

### 2.2 实现

```python
from usmsb_sdk.services import MatchingEngine

engine = MatchingEngine()
result = await engine.match(
    demand={"skill": "python", "budget": 1000},
    supply=[{"skill": "python", "price": 800}]
)
```

---

## 3. 协作服务

### 3.1 功能

- Agent间通信
- 任务委托
- 资源协调

---

## 4. 治理服务

### 4.1 功能

- 提案管理
- 投票机制
- 权限控制

---

## 5. 相关文档

- [系统架构](../03_architecture/system_architecture.md) - 整体系统架构
- [REST API](../06_api/rest_api.md) - API参考
