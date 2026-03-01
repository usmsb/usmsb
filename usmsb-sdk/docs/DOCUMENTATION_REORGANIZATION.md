# 文档整理说明

> 本文档记录了本次文档整理的过程和结果

---

## 整理概述

### 1. 完成的操作

1. **移动根目录文档**: 将根目录的5个md文件移动到 `usmsb-sdk/docs/`
2. **创建新文档结构**: 按照软件工程流程创建了新的文档目录结构
3. **补充核心文档**: 创建了概述、理论、架构、核心模块、服务层、API、开发指南等文档
4. **标记实现状态**: 在文档中标注了功能模块的实现状态（已实现/规划中）

### 2. 文档结构

```
docs/
├── README.md                    # 文档索引
├── 01_overview/                 # 概述
│   ├── platform-overview.md
│   └── vision.md
├── 02_theory/                  # 理论
│   ├── usmsb_model.md
│   └── agent_levels.md
├── 03_architecture/            # 架构
│   ├── system_architecture.md
│   ├── protocol_architecture.md
│   └── component_design.md
├── 04_core_modules/            # 核心模块
│   ├── meta_agent_design.md
│   ├── agent_sdk.md
│   ├── skill_system.md
│   ├── memory_system.md
│   ├── reasoning_engine.md
│   └── autonomous_evolution.md
├── 05_services/                # 服务层
│   └── README.md
├── 06_api/                    # API
│   ├── rest_api.md
│   ├── websocket_api.md
│   └── python_sdk.md
├── 07_deployment/              # 部署
│   ├── deployment_guide.md
│   ├── configuration.md
│   └── monitoring.md
├── 08_development/            # 开发
│   ├── quickstart.md
│   └── examples.md
├── 09_testing/                # 测试
│   └── test_guide.md
└── 10_changelog/              # 变更日志
    └── CHANGELOG.md
```

### 3. 过时文档（需要整合/废弃）

以下文档已过时或被新文档取代：

| 原文档 | 状态 | 说明 |
|--------|------|------|
| `info_extractor_design.md` | ⚠️ 过时 | 被 v4 取代 |
| `info_extractor_design_v2.md` | ⚠️ 过时 | 被 v4 取代 |
| `info_extractor_design_v3.md` | ⚠️ 过时 | 被 v4 取代 |
| `info_extractor_design_v4.md` | ⚠️ 需要整合 | 应整合到核心模块文档 |
| `autonomous_evolution_design.md` | ⚠️ 过时 | 被 v2 取代 |
| `meta_agent_chat_method_review.md` | ⚠️ 过时 | 被 v2 取代 |

### 4. 未实现功能（标记为规划中）

| 功能 | 状态 |
|------|------|
| 目标引擎 | 🔄 规划中 |
| 自主学习 | 🔄 规划中 |
| 涌现行为 | 🔄 规划中 |

---

## 后续工作

1. 继续整合过时的文档
2. 完善 frontend/public/docs/ 中的文档
3. 添加更多示例代码
4. 完善API文档
