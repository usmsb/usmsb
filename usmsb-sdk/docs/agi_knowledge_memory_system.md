# AGI知识库与记忆系统设计文档

> 版本: 2.0
> 日期: 2026-02-23
> 基于USMSB模型设计

---

## 一、系统架构总览

### 1.1 整合后的文件夹结构

```
meta_agent/
├── agi_core/                      # 核心集成层（本地+专业版）
│   ├── __init__.py                # 统一导出
│   ├── memory.py                  # 多层记忆系统（本地）
│   ├── knowledge_graph.py         # 动态知识图谱（本地）
│   └── integration.py             # 集成系统（调用专业版）
│
├── evolution_v2/                  # 专业进化系统
│   ├── models.py                  # 数据模型
│   ├── meta_learner.py            # 元学习器
│   ├── capability_assessor.py     # 能力评估器
│   ├── knowledge_solidifier.py    # 知识固化器
│   ├── curiosity_engine.py        # 好奇心引擎
│   ├── self_optimizer.py          # 自我优化器
│   ├── goal_generator.py          # 目标生成器
│   ├── engine.py                  # 主引擎
│   └── ARCHITECTURE.md            # 架构文档
│
└── [其他组件...]

usmsb_sdk/
└── reasoning/                     # 专业推理系统
    ├── interfaces.py              # 接口定义
    ├── base.py                    # 基类
    ├── engines/                   # 推理引擎
    │   ├── logical.py             # 演绎/归纳/溯因
    │   ├── causal.py              # 因果推理
    │   ├── analogical.py          # 类比推理
    │   ├── spatial.py             # 空间推理
    │   ├── temporal.py            # 时间推理
    │   ├── commonsense.py         # 常识推理
    │   └── meta.py                # 元推理
    ├── uncertainty.py             # 不确定性管理
    ├── chain_manager.py           # 推理链管理
    └── knowledge_integration.py   # 知识图谱集成
```

### 1.2 组件关系图

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           AGI Core System                                        │
│                    (integration.py - 统一接口)                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                         本地组件 (agi_core/)                               │  │
│  │                                                                            │  │
│  │   ┌─────────────────────┐       ┌─────────────────────┐                   │  │
│  │   │   AGIMemorySystem   │       │ DynamicKnowledgeGraph│                   │  │
│  │   │   (memory.py)       │       │ (knowledge_graph.py) │                   │  │
│  │   │                     │       │                       │                   │  │
│  │   │ • 工作记忆 (7项)    │       │ • 实体节点            │                   │  │
│  │   │ • 情景记忆 (2000条) │       │ • 关系边              │                   │  │
│  │   │ • 语义记忆 (10000条)│       │ • 因果链              │                   │  │
│  │   │ • 永久记忆 (无限)   │       │ • USMSB索引           │                   │  │
│  │   │ • 重要性评估        │       │ • 时序演化            │                   │  │
│  │   │ • 遗忘曲线          │       │                       │                   │  │
│  │   └─────────────────────┘       └─────────────────────┘                   │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                       │                                          │
│                                       ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                         专业版组件                                         │  │
│  │                                                                            │  │
│  │   ┌─────────────────────────────┐  ┌─────────────────────────────┐        │  │
│  │   │   SelfEvolutionEngine       │  │   ReasoningChainManager     │        │  │
│  │   │   (evolution_v2/engine.py)  │  │   (reasoning/)              │        │  │
│  │   │                             │  │                             │        │  │
│  │   │ • 元学习器 MetaLearner      │  │ • DeductiveEngine 演绎     │        │  │
│  │   │ • 能力评估 CapabilityAssessor│  │ • InductiveEngine 归纳     │        │  │
│  │   │ • 知识固化 KnowledgeSolidifier│  │ • AbductiveEngine 溯因     │        │  │
│  │   │ • 好奇心 CuriosityEngine   │  │ • CausalEngine 因果        │        │  │
│  │   │ • 自我优化 SelfOptimizer   │  │ • AnalogicalEngine 类比    │        │  │
│  │   │ • 目标生成 GoalGenerator   │  │ • 不确定性管理              │        │  │
│  │   └─────────────────────────────┘  └─────────────────────────────┘        │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、核心组件详解

### 2.1 多层记忆系统 (memory.py)

| 层级 | 容量 | 持续时间 | 特点 |
|------|------|----------|------|
| 工作记忆 | 7±2项 | 秒-分钟 | 当前处理的信息 |
| 情景记忆 | 2000条 | 小时-天 | 个人经历和事件 |
| 语义记忆 | 10000条 | 长期 | 事实和概念知识 |
| 永久记忆 | 无限 | 永不丢失 | 关键重要信息 |

**核心特性：**
- 重要性评估算法（频率+情感+实用性+新近度）
- Ebbinghaus遗忘曲线
- 自动记忆巩固
- 永久记忆永不丢失

### 2.2 动态知识图谱 (knowledge_graph.py)

**节点属性：**
- USMSB九大要素映射
- 置信度和重要性评分
- 访问统计

**关系类型：**
- IS_A, HAS_A, CAUSES, USES, RELATES
- USMSB要素关系

### 2.3 专业进化系统 (evolution_v2/)

**核心组件：**
| 组件 | 功能 |
|------|------|
| MetaLearner | 学习如何学习，8种学习策略 |
| CapabilityAssessor | 15种核心能力评估 |
| KnowledgeSolidifier | 知识固化（临时→永久） |
| CuriosityEngine | 好奇心驱动探索 |
| SelfOptimizer | 自我优化参数和策略 |
| GoalGenerator | 自主生成学习目标 |

**进化阶段：**
```
EXPLORATION → ACQUISITION → CONSOLIDATION → OPTIMIZATION → MASTERY
```

### 2.4 专业推理系统 (reasoning/)

**推理引擎：**
| 引擎 | 类型 | 用途 |
|------|------|------|
| DeductiveEngine | 演绎 | 从一般到特殊 |
| InductiveEngine | 归纳 | 从特殊到一般 |
| AbductiveEngine | 溯因 | 最佳解释 |
| CausalEngine | 因果 | 原因-结果 |
| AnalogicalEngine | 类比 | 相似性映射 |

---

## 三、使用方式

### 3.1 基本使用

```python
from usmsb_sdk.platform.external.meta_agent.agi_core import AGICoreSystem, AGICoreConfig

# 初始化
config = AGICoreConfig(
    memory_db="data/agi_memory.db",
    knowledge_db="data/agi_knowledge.db",
    enable_evolution=True,
    enable_inference=True
)
system = AGICoreSystem(config, llm_manager=llm, data_dir="data")

# 初始化系统
await system.init()

# 处理输入（自动记忆+学习）
result = await system.process_input(
    content="用户的重要偏好",
    user_id="user_001",
    usmsb_element="agent"
)

# 智能召回
recall = await system.smart_recall(
    query="用户之前的偏好是什么？",
    user_id="user_001"
)

# 构建上下文
context = await system.build_context(
    query="帮助用户做决策",
    user_id="user_001"
)
```

### 3.2 自主学习

```python
# 执行自主学习
learning_result = await system.autonomous_learning()

# 自我反思
reflection = await system.self_reflect()

# 获取系统状态
stats = system.get_system_stats()
```

### 3.3 添加USMSB知识

```python
# 添加目标知识
await system.add_usmsb_knowledge(
    element="goal",
    content="提升用户体验"
)

# 添加风险知识
await system.add_usmsb_knowledge(
    element="risk",
    content="数据泄露风险"
)
```

---

## 四、文件清单

### 4.1 本地组件 (agi_core/)

```
C:\Users\1\Documents\vibecode\usmsb-sdk\src\usmsb_sdk\platform\external\meta_agent\agi_core\
├── __init__.py           # 统一导出接口
├── memory.py             # 多层记忆系统
├── knowledge_graph.py    # 动态知识图谱
└── integration.py        # 集成系统（核心）
```

### 4.2 专业进化系统 (evolution_v2/)

```
C:\Users\1\Documents\vibecode\usmsb-sdk\src\usmsb_sdk\platform\external\meta_agent\evolution_v2\
├── __init__.py
├── models.py             # 数据模型
├── meta_learner.py       # 元学习器
├── capability_assessor.py # 能力评估
├── knowledge_solidifier.py # 知识固化
├── curiosity_engine.py   # 好奇心引擎
├── self_optimizer.py     # 自我优化
├── goal_generator.py     # 目标生成
├── engine.py             # 主引擎
└── ARCHITECTURE.md       # 架构文档
```

### 4.3 专业推理系统 (reasoning/)

```
C:\Users\1\Documents\vibecode\usmsb-sdk\src\usmsb_sdk\reasoning\
├── __init__.py
├── interfaces.py         # 接口定义
├── base.py               # 基类
├── engines/              # 推理引擎目录
│   └── [多种推理引擎]
├── uncertainty.py        # 不确定性管理
├── chain_manager.py      # 推理链管理
└── knowledge_integration.py # 知识集成
```

---

## 五、核心问题解决方案

| 问题 | 解决方案 | 实现位置 |
|------|----------|----------|
| **遗忘问题** | 永久记忆+重要性评估+遗忘曲线 | `agi_core/memory.py` |
| **不够智能** | 5种推理引擎+知识图谱 | `reasoning/` |
| **上下文限制** | 智能召回+重要性排序 | `agi_core/integration.py` |
| **缺乏进化** | 元学习+好奇心驱动+知识固化 | `evolution_v2/` |

---

*文档版本: 2.0*
*最后更新: 2026-02-23*
