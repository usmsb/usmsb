# 推理引擎

> 多引擎推理系统

---

## 1. 概述

推理引擎为 Agent 提供多种推理能力，包括逻辑推理、因果推理、常识推理等。

---

## 2. 模块结构

```
reasoning/
├── base.py            # 基类
├── interfaces.py     # 接口
├── chain_manager.py   # 链管理
├── knowledge_integration.py  # 知识集成
├── uncertainty.py    # 不确定性
└── engines/          # 推理引擎
    ├── meta.py       # 元推理
    ├── commonsense.py # 常识推理
    ├── temporal.py   # 时间推理
    ├── spatial.py    # 空间推理
    ├── analogical.py # 类比推理
    ├── causal.py     # 因果推理
    └── logical.py    # 逻辑推理
```

---

## 3. 推理引擎

| 引擎 | 状态 | 功能 |
|------|------|------|
| 元推理 | ✅ | 推理策略选择 |
| 常识推理 | ✅ | 常识知识推理 |
| 时间推理 | ✅ | 时间关系推理 |
| 空间推理 | ✅ | 空间关系推理 |
| 类比推理 | ✅ | 类比思维 |
| 因果推理 | ✅ | 因果关系分析 |
| 逻辑推理 | ✅ | 逻辑推演 |

---

## 4. 相关文档

- [Meta Agent设计](./meta_agent_design.md) - 超级Agent系统设计
