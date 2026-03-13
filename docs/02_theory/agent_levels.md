# Agent Level Definitions

**[English](#1-agent-level-overview) | [中文](#1-agent等级概述)**

> Based on OpenAI Agent's eight-layer architecture and five-level definitions

---

## 1. Agent Level Overview

USMSB SDK, based on OpenAI's proposed Agent classification system, defines five Agent levels, each representing different capability levels and degrees of autonomy.

---

## 2. Five Level Definitions

### Level 1: Reactive Agent

**Capability**: Basic response capability, no long-term memory

**Characteristics**:
- Generate responses directly based on current input
- No persistent state
- No autonomous decision-making capability

**Code Example**:
```python
# Simple LLM call
response = llm.chat(user_message)
```

---

### Level 2: Stateful Agent

**Capability**: Maintain conversation state and context

**Characteristics**:
- Maintain conversation history
- Understand context
- Generate responses based on historical information

**Code Example**:
```python
# Contextual conversation
messages = [{"role": "system", "content": "..."}]
messages.append({"role": "user", "content": user_message})
response = llm.chat(messages)
```

---

### Level 3: Tool-using Agent

**Capability**: Call external tools to complete complex tasks

**Characteristics**:
- Can call APIs, databases, file systems, etc.
- Can execute multi-step tasks
- Support function calling

**Code Example**:
```python
# Tool calling
tools = [get_weather, send_email]
response = llm.chat(messages, tools=tools)
```

---

### Level 4: Autonomous Agent

**Capability**: Autonomously plan, execute, and optimize tasks

**Characteristics**:
- Task planning and decomposition
- Autonomous decision-making and execution
- Error recovery and retry
- Continuous learning and optimization

**Code Example** (USMSB Meta Agent):
```python
# Core autonomous agent capabilities
class MetaAgent:
    async def chat(self, message):
        # 1. Understand intent
        intent = await self.analyze_intent(message)

        # 2. Plan actions
        plan = await self.plan_actions(intent)

        # 3. Execute and evaluate
        result = await self.execute_and_evaluate(plan)

        # 4. Learn and optimize
        await self.learn_from_result(result)

        return result
```

---

### Level 5: Super Agent

**Capability**: Self-driven, continuous evolution, multi-Agent collaboration

**Characteristics**:
- Have own goals and values
- Possess blockchain wallet and economic behavior
- Can create and manage sub-Agents
- Participate in decentralized governance
- Continuous self-evolution

**Code Example**:
```python
# Super Agent
class SuperAgent:
    def __init__(self):
        self.wallet = AgentWallet()  # Blockchain wallet
        self.goals = GoalEngine()    # Goal engine
        self.learning = LearningEngine()  # Learning engine
        self.collaboration = CollaborationNetwork()  # Collaboration network

    async def run(self):
        while True:
            # Perceive environment
            perception = await self.perceive()

            # Decide
            decision = await self.decide(perception)

            # Execute
            await self.execute(decision)

            # Evaluate and feedback
            await self.evaluate_and_feedback()

            # Learn and evolve
            await self.evolve()
```

---

## 3. Eight-Layer Architecture

USMSB SDK's Agent architecture is divided into eight layers:

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 8: Ecosystem Layer                                        │
│   - Multi-Agent networks, governance mechanisms, economic      │
├─────────────────────────────────────────────────────────────────┤
│ Layer 7: Autonomous Evolution Layer                             │
│   - Self-learning, capability expansion, behavior optimization │
├─────────────────────────────────────────────────────────────────┤
│ Layer 6: Collaboration Layer                                   │
│   - Multi-Agent communication, task coordination, resource     │
├─────────────────────────────────────────────────────────────────┤
│ Layer 5: Planning Layer                                        │
│   - Task decomposition, path planning, time scheduling        │
├─────────────────────────────────────────────────────────────────┤
│ Layer 4: Reasoning Layer                                       │
│   - Logical reasoning, causal analysis, problem solving        │
├─────────────────────────────────────────────────────────────────┤
│ Layer 3: Tool Usage Layer                                      │
│   - API calls, function execution, external interaction        │
├─────────────────────────────────────────────────────────────────┤
│ Layer 2: Memory Layer                                          │
│   - Short-term memory, long-term memory, context management    │
├─────────────────────────────────────────────────────────────────┤
│ Layer 1: Perception Layer                                      │
│   - Input parsing, intent recognition, entity extraction       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Level and Capability Mapping

| Level | Perception | Memory | Tools | Planning | Collaboration | Autonomy | Evolution |
|-------|------------|--------|-------|----------|--------------|----------|----------|
| L1    | ✓          | ✗      | ✗     | ✗        | ✗            | ✗        | ✗        |
| L2    | ✓          | ✓      | ✗     | ✗        | ✗            | ✗        | ✗        |
| L3    | ✓          | ✓      | ✓     | ✗        | ✗            | ✗        | ✗        |
| L4    | ✓          | ✓      | ✓     | ✓        | ✗            | ✗        | ✗        |
| L5    | ✓          | ✓      | ✓     | ✓        | ✓            | ✓        | ✓        |

---

## 5. Implementation in USMSB SDK

USMSB SDK provides complete Agent level implementations:

- **Level 1-2**: Implemented via `agent_sdk/base_agent.py`
- **Level 3**: Implemented via tool calling in `agent_sdk` module
- **Level 4**: Implemented via autonomous Agent in `meta_agent` module
- **Level 5**: Implemented via complete `meta_agent` system, including wallet, goal engine, learning engine, etc.

---

## 6. Related Documentation

- [USMSB Model](../02_theory/usmsb_model.md) - Universal Social Behavior System Model
- [Meta Agent Design](../04_core_modules/meta_agent_design.md) - Super Agent System Design
- [Collaboration Service](../05_services/collaboration_service.md) - Multi-Agent Collaboration

<details>
<summary><h2>中文翻译</h2></summary>

# Agent等级定义

---

## 1. Agent等级概述

USMSB SDK 基于 OpenAI 提出的 Agent 分级体系，定义了五个 Agent 等级，每个等级代表不同的能力水平和自主程度。

---

## 2. 五个等级定义

### Level 1: 响应式Agent (Reactive Agent)

**能力**: 基础的响应能力，无长期记忆

**特征**:
- 根据当前输入直接生成响应
- 无持久状态
- 无自主决策能力

**代码对应**:
```python
# 简单LLM调用
response = llm.chat(user_message)
```

---

### Level 2: 状态记忆Agent (Stateful Agent)

**能力**: 维护对话状态和上下文

**特征**:
- 维护对话历史
- 理解上下文
- 基于历史信息生成响应

**代码对应**:
```python
# 带上下文的对话
messages = [{"role": "system", "content": "..."}]
messages.append({"role": "user", "content": user_message})
response = llm.chat(messages)
```

---

### Level 3: 工具使用Agent (Tool-using Agent)

**能力**: 调用外部工具完成复杂任务

**特征**:
- 可以调用API、数据库、文件系统等
- 能够执行多步骤任务
- 支持函数调用(Function Calling)

**代码对应**:
```python
# 工具调用
tools = [get_weather, send_email]
response = llm.chat(messages, tools=tools)
```

---

### Level 4: 自主Agent (Autonomous Agent)

**能力**: 自主规划、执行和优化任务

**特征**:
- 任务规划和分解
- 自主决策和执行
- 错误恢复和重试
- 持续学习和优化

**代码对应** (USMSB Meta Agent):
```python
# 自主Agent核心能力
class MetaAgent:
    async def chat(self, message):
        # 1. 理解意图
        intent = await self.analyze_intent(message)

        # 2. 规划行动
        plan = await self.plan_actions(intent)

        # 3. 执行并评估
        result = await self.execute_and_evaluate(plan)

        # 4. 学习优化
        await self.learn_from_result(result)

        return result
```

---

### Level 5: 超级Agent (Super Agent)

**能力**: 具备自我驱动、持续进化、多Agent协作能力

**特征**:
- 拥有自己的目标和价值观
- 具备区块链钱包和经济行为
- 能够创建和管理子Agent
- 参与去中心化治理
- 持续自我进化

**代码对应**:
```python
# 超级Agent
class SuperAgent:
    def __init__(self):
        self.wallet = AgentWallet()  # 区块链钱包
        self.goals = GoalEngine()    # 目标引擎
        self.learning = LearningEngine()  # 学习引擎
        self.collaboration = CollaborationNetwork()  # 协作网络

    async def run(self):
        while True:
            # 感知环境
            perception = await self.perceive()

            # 决策
            decision = await self.decide(perception)

            # 执行
            await self.execute(decision)

            # 评估和反馈
            await self.evaluate_and_feedback()

            # 学习进化
            await self.evolve()
```

---

## 3. 八层架构

USMSB SDK 的 Agent 架构分为八个层次：

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 8: 生态系统层 (Ecosystem)                                 │
│   - 多Agent网络、治理机制、经济模型                              │
├─────────────────────────────────────────────────────────────────┤
│ Layer 7: 自主进化层 (Autonomous Evolution)                     │
│   - 自我学习、能力扩展、行为优化                                 │
├─────────────────────────────────────────────────────────────────┤
│ Layer 6: 协作层 (Collaboration)                                 │
│   - 多Agent通信、任务协调、资源共享                              │
├─────────────────────────────────────────────────────────────────┤
│ Layer 5: 规划层 (Planning)                                     │
│   - 任务分解、路径规划、时间调度                                │
├─────────────────────────────────────────────────────────────────┤
│ Layer 4: 推理层 (Reasoning)                                     │
│   - 逻辑推理、因果分析、问题求解                                │
├─────────────────────────────────────────────────────────────────┤
│ Layer 3: 工具层 (Tool Usage)                                   │
│   - API调用、函数执行、外部交互                                 │
├─────────────────────────────────────────────────────────────────┤
│ Layer 2: 记忆层 (Memory)                                        │
│   - 短期记忆、长期记忆、上下文管理                              │
├─────────────────────────────────────────────────────────────────┤
│ Layer 1: 感知层 (Perception)                                    │
│   - 输入解析、意图识别、实体提取                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. 等级与能力对照表

| 等级 | 感知 | 记忆 | 工具 | 规划 | 协作 | 自主 | 进化 |
|------|------|------|------|------|------|------|------|
| L1   | ✓    | ✗    | ✗    | ✗    | ✗    | ✗    | ✗    |
| L2   | ✓    | ✓    | ✗    | ✗    | ✗    | ✗    | ✗    |
| L3   | ✓    | ✓    | ✓    | ✗    | ✗    | ✗    | ✗    |
| L4   | ✓    | ✓    | ✓    | ✓    | ✗    | ✗    | ✗    |
| L5   | ✓    | ✓    | ✓    | ✓    | ✓    | ✓    | ✓    |

---

## 5. USMSB SDK 中的实现

USMSB SDK 提供了完整的 Agent 等级实现：

- **Level 1-2**: 通过 `agent_sdk/base_agent.py` 实现
- **Level 3**: 通过 `agent_sdk` 模块的工具调用实现
- **Level 4**: 通过 `meta_agent` 模块的自主Agent实现
- **Level 5**: 通过完整的 `meta_agent` 系统实现，包含钱包、目标引擎、学习引擎等

---

## 6. 相关文档

- [USMSB模型](../02_theory/usmsb_model.md) - 社会行为通用系统模型
- [Meta Agent设计](../04_core_modules/meta_agent_design.md) - 超级Agent系统设计
- [协作服务](../05_services/collaboration_service.md) - 多Agent协作

</details>
