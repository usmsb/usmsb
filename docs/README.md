# USMSB Documentation Center

> USMSB (Universal System Model of Social Behavior) Software Development Kit

**[English](#documentation) | [中文](#文档目录)**

## Current entry points — open collaboration alpha

USMSB's common core describes Agent, Object, Goal, Resource, Rule, Information, Value, Risk, and Environment. World/host policies govern authentication and cooperation; external agents choose strategies and execute work. Wishbud, OPC, PEA, IAP, VIBE, and model providers are reference environments or optional applications, not prerequisites for these shared semantics. Value can include research, public knowledge, mutual aid, and economic exchange.

- [Current architecture and acceptance design](./architecture/open-collaboration-v1.md) — intended boundaries, threat model, and validation gates; requirements are not evidence of completion.
- [Migration, versioning, and rollback](./architecture/open-collaboration-migration.md) — existing compatibility defaults, alpha profiles/journal, package choices, and host responsibilities.
- [Host integration and additive governance](./architecture/collaboration-host-integration.md) — a2 authentication/evidence boundary, exact protocol agreement, backup and migration fencing.
- [Bounded resilience experiments](./architecture/collaboration-experiments.md) — multi-process CAS/replay, killed-writer recovery and controlled revision rounds; not long-term emergence.
- [Delivery evidence and external prerequisites](./architecture/open-collaboration-delivery.md) — actual pass/skip results and unfinished real-world acceptance.
- [English README](../README.md) · [中文 README](../README_CN.md) — current positioning, runnable test entry points, and retained economic examples.

Existing portable contracts have local regression tests. Neutral profiles, the collaboration journal, standalone core distribution, lazy imports, and external-client integration belong to the current alpha iteration; consult the delivery report referenced by the design for actual results. Production identity, evidence provenance, payment, scale, and cross-World trust require separate validation. Scripted demos and local accounting do not prove autonomous behavior or real settlement.

The catalog below preserves useful SDK documentation, application designs, research, and history. Older claims about a mandatory economic loop, production readiness, or civilization are historical context; the current architecture defines the common core. Existing REST/platform guides describe their own application APIs, not automatically the new journal command interface.

---

## Documentation

### 1. Overview
- [Platform Overview](./01_overview/platform-overview.md) - USMSB SDK platform overview
- [Vision](./01_overview/vision.md) - Project vision and mission

### 2. Theory Framework
- [USMSB Model](./02_theory/usmsb_model.md) - Universal System Model of Social Behavior
- [Agent Levels](./02_theory/agent_levels.md) - OpenAI Agent eight-level architecture and five tiers

### 3. Architecture
- [System Architecture](./03_architecture/system_architecture.md) - Overall system architecture
- [Protocol Architecture](./03_architecture/protocol_architecture.md) - Communication protocol architecture
- [Component Design](./03_architecture/component_design.md) - Core component design

### 4. Core Modules
- [Meta Agent Design](./04_core_modules/meta_agent_design.md) - Super Agent system design
- [Agent SDK](./04_core_modules/agent_sdk.md) - Agent Software Development Kit
- [Skill System](./04_core_modules/skill_system.md) - Dynamic skill extension mechanism
- [Memory System](./04_core_modules/memory_system.md) - Intelligent memory and context management
- [Reasoning Engine](./04_core_modules/reasoning_engine.md) - Multi-engine reasoning system
- [Autonomous Evolution](./04_core_modules/autonomous_evolution.md) - Autonomous learning and evolution system

### 5. Services
- [Matching Service](./05_services/README.md#2-matching-services) - Intelligent supply-demand matching
- [Collaboration Service](./05_services/README.md#3-collaborative-services-collaborativematchingservice) - Multi-Agent collaboration
- [Governance Service](./05_services/README.md#4-governance-service-governanceservice) - Decentralized governance
- [Learning Service](./05_services/README.md#5-learning-services-proactivelearningservice) - Proactive learning service
- Environment Service - Historical catalog entry; its dedicated page is not present in this checkout.

### 6. API Reference
- [REST API](./06_api/rest_api.md) - REST API reference
- [WebSocket API](./06_api/websocket_api.md) - WebSocket real-time communication
- [Python SDK](./06_api/python_sdk.md) - Python SDK usage guide

### 7. Deployment & Operations
- [Deployment Guide](./07_deployment/deployment_guide.md) - Quick deployment
- [Configuration](./07_deployment/configuration.md) - System configuration
- [Monitoring](./07_deployment/monitoring.md) - Monitoring and operations

### 8. Development Guide
- [Quick Start](./08_development/quickstart.md) - Getting started
- [SDK Usage](./06_api/python_sdk.md) - Python SDK usage reference
- [Examples](./08_development/examples.md) - Examples and tutorials

### 9. Testing
- [Testing Guide](./09_testing/test_guide.md) - Testing guide

### 10. Changelog
- Changelog - Historical catalog entry; `10_changelog/CHANGELOG.md` is not present in this checkout.

---

## Research Documents

### USMSB Theory
- [USMSB Model Summary](./research/04-USMSB模型总结.md)
- [USMSB SDK Architecture Design](./research/05-USMSB模型SDK总体架构设计.md)
- [USMSB_SDK Detailed Design](./research/06-USMSB_SDK_Detailed_Design.md)

### Expert Debates
- [Economic Model Design Debate](./economic_model_design/) - Economic model design expert debates

### Creative Economy Platform
- [Creative Economy Platform Design](./creative_economy_platform_design/) - Creative economy platform architecture

---

## Related Resources

- GitHub Repository: https://github.com/usmsb/usmsb
- Issues: https://github.com/usmsb/usmsb/issues
- Current entry points updated: 2026-09-29; individual documents retain their own status and dates.

---

<details>
<summary><h2>文档目录</h2></summary>

# USMSB SDK 文档中心

> USMSB (Universal System Model of Social Behavior) 软件开发工具包

**[English](#documentation) | [中文](#文档目录)**

## 当前入口：开放协作 alpha

共同内核以主体、客体、目标、资源、规则、信息、价值、风险、环境九要素表达语义；World/宿主规定认证与协作规则，外部 Agent 决定策略并执行工作。Wishbud、OPC、PEA、IAP、VIBE 和模型服务属于参考环境或可选应用，不是共同语义的先决条件。研究、公共知识、互助和经济交换可以表达不同价值。

- [当前架构与验收设计](./architecture/open-collaboration-v1.md)：边界、威胁模型和门禁；验收要求不等于完成证据。
- [迁移、版本与回滚](./architecture/open-collaboration-migration.md)：兼容默认行为、alpha Profile/账本、分发选择与宿主职责。
- [中文 README](../README_CN.md) · [English README](../README.md)：当前定位、可运行测试入口及保留的经济示例。

已有可移植契约有本地回归测试；中立 Profile、协作账本、独立 core 分发、惰性导入和外部客户端集成属于本轮 alpha 工作，实际结果见设计指向的交付报告。生产身份、证据来源、支付、规模和跨 World 信任需另行验证。脚本化示例与本地记账不证明自主行为或真实结算。

以下保留原 SDK 文档、应用设计、研究与历史入口。旧文档中的强制经济闭环、生产就绪或文明愿景应按历史语境阅读，共同内核边界以当前架构为准。既有 REST/平台文档描述相应应用 API，不自动等于新账本命令接口。

---

## 文档目录

### 1. 概述 (Overview)
- [平台概览](./01_overview/platform-overview.md) - USMSB SDK 平台概述
- [愿景](./01_overview/vision.md) - 项目愿景与使命

### 2. 理论框架 (Theory)
- [USMSB模型](./02_theory/usmsb_model.md) - 社会行为通用系统模型
- [Agent等级定义](./02_theory/agent_levels.md) - OpenAI Agent八层架构和五个等级

### 3. 架构设计 (Architecture)
- [系统架构](./03_architecture/system_architecture.md) - 整体系统架构
- [协议架构](./03_architecture/protocol_architecture.md) - 通信协议架构
- [组件设计](./03_architecture/component_design.md) - 核心组件设计

### 4. 核心模块 (Core Modules)
- [Meta Agent设计](./04_core_modules/meta_agent_design.md) - 超级Agent系统设计
- [Agent SDK](./04_core_modules/agent_sdk.md) - Agent软件开发包
- [技能系统](./04_core_modules/skill_system.md) - 动态技能扩展机制
- [记忆系统](./04_core_modules/memory_system.md) - 智能记忆与上下文管理
- [推理引擎](./04_core_modules/reasoning_engine.md) - 多引擎推理系统
- [自主进化](./04_core_modules/autonomous_evolution.md) - 自主学习与进化系统

### 5. 服务层 (Services)
- [匹配服务](./05_services/README.md) - 智能供需匹配
- [协作服务](./05_services/README.md) - 多Agent协作
- [治理服务](./05_services/README.md) - 去中心化治理
- [学习服务](./05_services/README.md) - 主动学习服务
- 环境服务 - 保留历史目录项；当前工作区中没有对应独立页面。

### 6. API文档 (API Reference)
- [REST API](./06_api/rest_api.md) - REST API参考
- [WebSocket API](./06_api/websocket_api.md) - WebSocket实时通信
- [Python SDK](./06_api/python_sdk.md) - Python SDK使用指南

### 7. 部署运维 (Deployment)
- [部署指南](./07_deployment/deployment_guide.md) - 快速部署
- [配置说明](./07_deployment/configuration.md) - 系统配置
- [监控运维](./07_deployment/monitoring.md) - 监控与运维

### 8. 开发指南 (Development)
- [快速开始](./08_development/quickstart.md) - 快速入门
- [SDK使用](./06_api/python_sdk.md) - Python SDK使用参考
- [示例代码](./08_development/examples.md) - 示例与教程

### 9. 测试 (Testing)
- [测试指南](./09_testing/test_guide.md) - 测试指南

### 10. 变更日志 (Changelog)
- 更新日志 - 保留历史目录项；当前工作区中没有 `10_changelog/CHANGELOG.md`。

---

## 研究文档

### USMSB理论
- [USMSB模型总结](./research/04-USMSB模型总结.md)
- [USMSB模型SDK总体架构设计](./research/05-USMSB模型SDK总体架构设计.md)
- [USMSB_SDK详细设计](./research/06-USMSB_SDK_Detailed_Design.md)

### 专家辩论
- [经济模型设计辩论](./economic_model_design/) - 经济模型设计专家辩论

### 创意经济平台
- [创意经济平台设计](./creative_economy_platform_design/) - 创意经济平台架构

---

## 相关资源

- GitHub仓库: https://github.com/usmsb/usmsb
- 问题反馈: https://github.com/usmsb/usmsb/issues
- 当前入口更新日期：2026-09-29；各文档保留自己的状态与日期。

</details>
