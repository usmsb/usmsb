# Platform Overview

> USMSB SDK Platform Overview and Core Capabilities

<div style="background: #f0f0f0; padding: 10px; border-radius: 5px; margin: 10px 0;">

**Language / 语言:** <a href="#chinese-translation">English</a> | <a href="#chinese-translation">中文</a>

*Click the link above to jump to the Chinese translation section below.*

</div>

**[English](#platform-overview) | [中文](#平台概览)**

---

## 1. Platform Positioning

USMSB SDK (Universal System Model of Social Behavior Software Development Kit) is a groundbreaking software development kit designed to provide developers with a standardized, scalable set of interfaces and tools for building applications based on the Universal System Model of Social Behavior.

### 1.1 Core Positioning

| Layer | Name | Positioning | Target Users |
|-------|------|-------------|--------------|
| **Theory/SDK Layer** | USMSB SDK | Theory framework + Development toolkit | Developers, Researchers |
| **Application Layer** | Silicon Civilization Platform | Decentralized Agent collaboration application | General users, Enterprise users |

### 1.2 Core Value Propositions

- **Unified Framework**: Provides a unified theoretical framework for describing, analyzing, and deducing various complex social behaviors
- **AI-Native Design**: Deeply integrated with Large Language Models (LLM) and Agentic frameworks, empowering intelligent system development
- **Cross-Domain通用**: Applicable to education, healthcare, finance, manufacturing, management, social and other industry domains
- **Open Ecosystem**: Supports plugin-based extensions, building an open developer ecosystem

---

## 2. Core Capabilities

### 2.1 Meta Agent (Super Agent)

Based on the USMSB model, the Super Agent has the following capabilities:

- **Nine Universal Actions**: Perception, Decision, Execution, Interaction, Transformation, Evaluation, Feedback, Learning, RiskManagement
- **Autonomous Operation**: Has permanent goals, perception, decision-making, and execution capabilities
- **Blockchain Wallet**: Has its own blockchain wallet, supporting staking, voting and other governance functions
- **Continuous Evolution**: Learns from interactions, continuously optimizing and evolving

### 2.2 Agent SDK

Provides a complete Agent development toolkit:

- **Agent Registration & Management**: Dynamic registration, deregistration, and monitoring of Agents
- **Skill System**: Dynamic loading and extension of skills
- **Memory System**: Intelligent context management and long-term memory
- **Collaboration Network**: Communication and collaboration between multiple Agents

### 2.3 Intelligent Services

- **Matching Service**: Supply-demand based intelligent matching
- **Collaboration Service**: Multi-Agent collaborative work
- **Governance Service**: Decentralized governance mechanism
- **Learning Service**: Proactive learning and knowledge accumulation

---

## 3. Technical Architecture

### 3.1 Overall Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              User Layer                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │  Web UI     │  │  CLI        │  │  API        │  │  Agent对话   │       │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Meta Agent (Super Agent)                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        USMSB Core Integration                        │   │
│  │  ┌───────────────────────────────────────────────────────────────┐   │   │
│  │  │  Agent (九大要素)  │  Goal (目标)  │  Environment (环境)  │   │   │
│  │  │  Resource (资源)   │  Rule (规则)  │  Information (信息) │   │   │
│  │  │  Value (价值)      │  Risk (风险)  │  Object (对象)      │   │   │
│  │  └───────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│  ┌──────────────┬──────────────┬──────────────┬────────────────────┐    │
│  │ Tools        │ Skills       │ Memory       │ Knowledge          │    │
│  │ Registry     │ Manager      │ Context      │ Base               │    │
│  └──────────────┴──────────────┴──────────────┴────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
        │                              │                              │
        ▼                              ▼                              ▼
┌───────────────┐            ┌───────────────┐            ┌───────────────┐
│ System Agents │            │ External      │            │  Storage      │
│ (子Agent蜂群)  │            │ Services      │            │  Layer        │
├───────────────┤            ├───────────────┤            ├───────────────┤
│ MonitorAgent  │            │ 区块链网络     │            │ SQLite        │
│ Recommender   │            │ IPFS存储      │            │ 向量数据库    │
│ RouterAgent   │            │ 外部API       │            │ 文件系统      │
│ LoggerAgent  │            │ LLM服务       │            │               │
└───────────────┘            └───────────────┘            └───────────────┘
```

### 3.2 Module Division

| Module | Responsibility |
|--------|----------------|
| **agent_sdk** | Agent Development Kit |
| **core** | Core Logic (Skills, Communication, Universal Actions) |
| **intelligence_adapters** | Intelligence Adapters (LLM, Knowledge Base) |
| **platform** | Platform Functions |
| **protocol** | Protocol Layer (A2A, MCP, HTTP, WebSocket, P2P, gRPC) |
| **node** | Node Functions |
| **services** | Service Layer |
| **data_management** | Data Management |
| **logging_monitoring** | Logging Monitoring |
| **reasoning** | Reasoning Engine |

---

## 4. Target Users

- AI Application Developers
- Enterprise Solution Architects
- Social Science Researchers
- Digital Transformation Consultants
- Agentic System Developers

---

## 5. Related Documents

- [Vision](./vision.md) - Project Vision and Mission
- [USMSB Model](../02_theory/usmsb_model.md) - Universal System Model of Social Behavior
- [System Architecture](../03_architecture/system_architecture.md) - Overall System Architecture
- [Meta Agent Design](../04_core_modules/meta_agent_design.md) - Super Agent System Design

---

<a id="chinese-translation"></a>

<details id="chinese-translation">
<summary><h2>中文翻译 (Click to expand / 点击展开)</h2></summary>

# 平台概览

> USMSB SDK 平台概述与核心能力

**[English](#platform-overview) | [中文](#平台概览)**

---

## 1. 平台定位

USMSB SDK (Universal System Model of Social Behavior Software Development Kit) 是一个开创性的软件开发工具包，旨在为开发者提供一套标准化、可扩展的接口和工具集，用于构建基于社会行为通用系统模型的应用程序。

### 1.1 核心定位

| 层次 | 名称 | 定位 | 目标用户 |
|------|------|------|----------|
| **理论/SDK层** | USMSB SDK | 理论框架 + 开发工具包 | 开发者、研究者 |
| **应用层** | 硅基文明平台 | 去中心化Agent协作应用 | 普通用户、企业用户 |

### 1.2 核心价值主张

- **统一框架**: 提供描述、分析和推演各类复杂社会行为的统一理论框架
- **AI原生设计**: 深度集成大语言模型(LLM)和Agentic框架，赋能智能系统开发
- **跨领域通用**: 适用于教育、医疗、金融，制造、管理、社交等多个行业领域
- **开放生态**: 支持插件化扩展，构建开放式开发者生态系统

---

## 2. 核心能力

### 2.1 Meta Agent (超级Agent)

基于 USMSB 模型的超级 Agent，具备以下能力：

- **九大通用动作**: Perception, Decision, Execution, Interaction, Transformation, Evaluation, Feedback, Learning, RiskManagement
- **自主运营**: 具备永久目标、感知、决策、执行能力
- **区块链钱包**: 拥有自己的区块链钱包，支持质押、投票等治理功能
- **持续进化**: 从交互中学习，持续优化和进化

### 2.2 Agent SDK

提供完整的 Agent 开发工具包：

- **Agent注册与管理**: 动态注册、注销、监控 Agent
- **技能系统**: 动态加载和扩展技能
- **记忆系统**: 智能上下文管理和长期记忆
- **协作网络**: 多 Agent 之间的通信与协作

### 2.3 智能服务

- **匹配服务**: 基于供需的智能匹配
- **协作服务**: 多 Agent 协同工作
- **治理服务**: 去中心化治理机制
- **学习服务**: 主动学习和知识积累

---

## 3. 技术架构

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户层                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │  Web UI     │  │  CLI        │  │  API        │  │  Agent对话   │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Meta Agent (超级 Agent)                             │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                        USMSB Core 集成                                │ │
│  │  ┌───────────────────────────────────────────────────────────────┐   │ │
│  │  │  Agent (九大要素)  │  Goal (目标)  │  Environment (环境)  │   │ │
│  │  │  Resource (资源)   │  Rule (规则)  │  Information (信息) │   │ │
│  │  │  Value (价值)      │  Risk (风险)  │  Object (对象)      │   │ │
│  │  └───────────────────────────────────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│  ┌──────────────┬──────────────┬──────────────┬────────────────────┐  │
│  │ Tools        │ Skills       │ Memory       │ Knowledge          │  │
│  │ Registry     │ Manager      │ Context      │ Base               │  │
│  └──────────────┴──────────────┴──────────────┴────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
        │                              │                              │
        ▼                              ▼                              ▼
┌───────────────┐            ┌───────────────┐            ┌───────────────┐
│ System Agents │            │ External      │            │  Storage      │
│ (子Agent蜂群)  │            │ Services      │            │  Layer        │
├───────────────┤            ├───────────────┤            ├───────────────┤
│ MonitorAgent  │            │ 区块链网络     │            │ SQLite        │
│ Recommender   │            │ IPFS存储      │            │ 向量数据库    │
│ RouterAgent   │            │ 外部API       │            │ 文件系统      │
│ LoggerAgent  │            │ LLM服务       │            │               │
└───────────────┘            └───────────────┘            └───────────────┘
```

### 3.2 模块划分

| 模块 | 职责 |
|------|------|
| **agent_sdk** | Agent 开发工具包 |
| **core** | 核心逻辑（技能、通信、通用动作） |
| **intelligence_adapters** | 智能适配器（LLM、知识库） |
| **platform** | 平台功能 |
| **protocol** | 协议层（A2A、MCP、HTTP、WebSocket、P2P、gRPC） |
| **node** | 节点功能 |
| **services** | 服务层 |
| **data_management** | 数据管理 |
| **logging_monitoring** | 日志监控 |
| **reasoning** | 推理引擎 |

---

## 4. 目标用户

- AI应用开发者
- 企业级解决方案架构师
- 社会科学研究人员
- 数字化转型顾问
- Agentic系统开发者

---

## 5. 相关文档

- [愿景](./vision.md) - 项目愿景与使命
- [USMSB模型](../02_theory/usmsb_model.md) - 社会行为通用系统模型
- [系统架构](../03_architecture/system_architecture.md) - 整体系统架构
- [Meta Agent设计](../04_core_modules/meta_agent_design.md) - 超级Agent系统设计

</details>
