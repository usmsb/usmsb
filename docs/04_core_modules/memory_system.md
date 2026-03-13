# 记忆系统

> 智能记忆与上下文管理

---

## 1. 概述

记忆系统为 Agent 提供智能上下文管理和长期记忆能力。

---

## 2. 模块结构

```
platform/external/meta_agent/
├── memory/
│   └── memory_manager.py    # 记忆管理
└── agi_core/
    └── memory.py            # 核心记忆
```

---

## 3. 功能

| 功能 | 状态 | 说明 |
|------|------|------|
| 短期记忆 | ✅ | 对话上下文 |
| 长期记忆 | ✅ | 向量存储 |
| 记忆检索 | ✅ | 语义搜索 |
| 记忆更新 | ✅ | 自动更新 |

---

## 4. 相关文档

- [Meta Agent设计](./meta_agent_design.md) - 超级Agent系统设计
