# SDK组件详细映射表

本文档将智能交通管理场景的每个需求点映射到USMSB SDK的具体组件、类和方法。

---

## 1. 核心元素映射

### 1.1 主体 (Subject/Agent)

| 场景实体 | SDK组件 | 文件位置 | 创建方式 |
|---------|--------|---------|---------|
| CTMC-Agent | `Agent` | `core/elements.py` | `Agent(id, name, type=AgentType.AI_AGENT, capabilities, goals, resources)` |
| Vehicle-Agent | `Agent` | `core/elements.py` | `Agent(id, name, type=AgentType.AI_AGENT, capabilities, goals)` |
| Emergency-Agent | `Agent` | `core/elements.py` | `Agent(id, name, type=AgentType.AI_AGENT, capabilities, goals)` |
| Citizen-Agent | `Agent` | `core/elements.py` | `Agent(id, name, type=AgentType.HUMAN_AGENT, capabilities, goals)` |

**关键方法:**
```python
# Agent 类核心方法
agent.add_goal(goal)           # 添加目标
agent.add_resource(resource)   # 添加资源
agent.add_rule(rule)          # 添加规则
agent.get_active_goals()      # 获取活动目标
agent.get_highest_priority_goal()  # 获取最高优先级目标
agent.update_state(new_state) # 更新状态
```

### 1.2 目标 (Goal)

| 目标类型 | SDK组件 | 文件位置 | 示例 |
|---------|--------|---------|------|
| 保障安全 | `Goal` | `core/elements.py` | `Goal(id="goal_safety", name="保障安全", priority=1.0, status=GoalStatus.ACTIVE)` |
| 恢复效率 | `Goal` | `core/elements.py` | `Goal(id="goal_efficiency", priority=0.8)` |
| 保障救援 | `Goal` | `core/elements.py` | `Goal(id="goal_rescue", priority=0.95)` |
| 信息发布 | `Goal` | `core/elements.py` | `Goal(id="goal_info", priority=0.6)` |

**关键方法:**
```python
# Goal 类核心方法
goal.update_progress(0.5)      # 更新进度
goal.mark_completed()          # 标记完成
goal.add_sub_goal(sub_goal)    # 添加子目标
```

### 1.3 资源 (Resource)

| 资源类型 | SDK组件 | 文件位置 | 示例 |
|---------|--------|---------|------|
| 道路 | `Resource` | `core/elements.py` | `Resource(id, name="主干道A", type=ResourceType.INFRASTRUCTURE)` |
| 信号灯 | `Resource` | `core/elements.py` | `Resource(id, name="交叉口X", type=ResourceType.CONTROL)` |
| 计算资源 | `Resource` | `core/elements.py` | `Resource(id, name="计算资源", type=ResourceType.COMPUTATIONAL)` |
| 通信带宽 | `Resource` | `core/elements.py` | `Resource(id, name="带宽", type=ResourceType.INFORMATION)` |

### 1.4 规则 (Rule)

| 规则类型 | SDK组件 | 文件位置 | 示例 |
|---------|--------|---------|------|
| 紧急优先 | `Rule` | `core/elements.py` | `Rule(id, name="紧急优先", rule_type="priority", conditions, actions)` |
| 信号遵守 | `Rule` | `core/elements.py` | `Rule(id, name="信号遵守", rule_type="constraint")` |
| 通行限制 | `Rule` | `core/elements.py` | `Rule(id, name="通行限制", rule_type="constraint")` |

### 1.5 信息 (Information)

| 信息类型 | SDK组件 | 文件位置 | 示例 |
|---------|--------|---------|------|
| 静态地图 | `Information` | `core/elements.py` | `Information(id, title="地图数据", info_type="static")` |
| 实时流量 | `Information` | `core/elements.py` | `Information(id, title="实时流量", info_type="dynamic")` |
| 事故报告 | `Information` | `core/elements.py` | `Information(id, title="事故报告", info_type="event")` |
| 民众反馈 | `Information` | `core/elements.py` | `Information(id, title="民众反馈", info_type="social")` |

### 1.6 风险 (Risk)

| 风险类型 | SDK组件 | 文件位置 | 示例 |
|---------|--------|---------|------|
| 拥堵扩散 | `Risk` | `core/elements.py` | `Risk(id, name="拥堵扩散", probability=0.85, impact=0.8)` |
| 二次事故 | `Risk` | `core/elements.py` | `Risk(id, name="二次事故", probability=0.45, impact=0.95)` |
| 救援延误 | `Risk` | `core/elements.py` | `Risk(id, name="救援延误", probability=0.6, impact=0.9)` |

### 1.7 环境 (Environment)

| 环境类型 | SDK组件 | 文件位置 | 示例 |
|---------|--------|---------|------|
| 交通路网 | `Environment` | `core/elements.py` | `Environment(id, name="城市交通网", type=EnvironmentType.URBAN)` |

---

## 2. 通用行动接口映射

### 2.1 感知 (Perceive)

| 场景需求 | SDK接口 | 文件位置 | 方法 |
|---------|--------|---------|------|
| 多源数据融合 | `LLMPerceptionService` | `core/universal_actions.py` | `perceive(agent, environment, inputs)` |
| 传感器数据处理 | `LLMPerceptionService` | `core/universal_actions.py` | `_process_sensor_data(raw_data)` |
| Agent报告处理 | `LLMPerceptionService` | `core/universal_actions.py` | `_process_agent_reports(reports)` |
| 态势感知 | `LLMPerceptionService` | `core/universal_actions.py` | `_build_situation_awareness(context)` |

**使用示例:**
```python
from usmsb_sdk.core.universal_actions import LLMPerceptionService

perception = LLMPerceptionService(llm_adapter)
result = await perception.perceive(
    agent=ctmc_agent,
    environment=traffic_environment,
    inputs={
        "sensor_data": [camera_data, loop_data],
        "agent_reports": vehicle_reports
    },
    perception_type="multi_source_fusion"
)
```

### 2.2 决策 (Decide)

| 场景需求 | SDK接口 | 文件位置 | 方法 |
|---------|--------|---------|------|
| 多策略生成 | `LLMDecisionService` | `core/universal_actions.py` | `decide(agent, context, decision_type)` |
| 策略评估 | `DecisionSupportService` | `services/decision_support_service.py` | `analyze_decision(options, context)` |
| 方案推荐 | `DecisionSupportService` | `services/decision_support_service.py` | `recommend(options, context, criteria)` |
| 方案比较 | `DecisionSupportService` | `services/decision_support_service.py` | `compare_options(options, context)` |

**使用示例:**
```python
from usmsb_sdk.services.decision_support_service import (
    DecisionSupportService, DecisionOption, DecisionContext
)

decision_support = DecisionSupportService(llm_adapter)
recommendation = await decision_support.recommend(
    options=[
        DecisionOption(id="opt_1", name="优先救援", ...),
        DecisionOption(id="opt_2", name="均衡方案", ...),
    ],
    context=DecisionContext(
        agent=ctmc_agent,
        goals=ctmc_agent.get_active_goals(),
        risks=ctmc_agent.risks,
        ...
    )
)
```

### 2.3 执行 (Execute)

| 场景需求 | SDK接口 | 文件位置 | 方法 |
|---------|--------|---------|------|
| 行动执行 | `LLMExecutionService` | `core/universal_actions.py` | `execute(action, agent, environment)` |
| 批量执行 | `LLMExecutionService` | `core/universal_actions.py` | `execute_batch(actions, agent)` |
| 执行回滚 | `LLMExecutionService` | `core/universal_actions.py` | `rollback(action_id)` |

### 2.4 交互 (Interact)

| 场景需求 | SDK接口 | 文件位置 | 方法 |
|---------|--------|---------|------|
| Agent间通信 | `LLMInteractionService` | `core/universal_actions.py` | `send_message(sender, receiver, message)` |
| 广播消息 | `LLMInteractionService` | `core/universal_actions.py` | `broadcast(sender, topic, message)` |
| 协议通信 | `AgentCommunication` | `core/communication/agent_communication.py` | `send_protocol_message()` |

**使用示例:**
```python
from usmsb_sdk.core.communication.agent_communication import (
    AgentCommunication, Message, MessageType
)

comm = AgentCommunication(agent_id=ctmc_agent.id)
await comm.send_message(
    receiver_id=ambulance_agent.id,
    message=Message(
        type=MessageType.TASK_ASSIGNMENT,
        content={"mission": "rescue", "location": accident_location}
    )
)
```

### 2.5 学习 (Learn)

| 场景需求 | SDK接口 | 文件位置 | 方法 |
|---------|--------|---------|------|
| 经验提取 | `LLMLearningService` | `core/universal_actions.py` | `learn(experience, feedback)` |
| 模式识别 | `LLMLearningService` | `core/universal_actions.py` | `_identify_patterns(experience)` |
| 参数优化 | `LLMLearningService` | `core/universal_actions.py` | `_optimize_parameters(learnings)` |

### 2.6 风险管理 (Risk Management)

| 场景需求 | SDK接口 | 文件位置 | 方法 |
|---------|--------|---------|------|
| 风险识别 | `LLMRiskManagementService` | `core/universal_actions.py` | `identify_risks(context, agent)` |
| 风险评估 | `LLMRiskManagementService` | `core/universal_actions.py` | `assess_risk(risk_id)` |
| 缓解策略 | `LLMRiskManagementService` | `core/universal_actions.py` | `mitigate_risk(risk_id, strategy)` |

---

## 3. 核心逻辑引擎映射

### 3.1 目标-行动-结果循环 (GAO)

| 场景阶段 | SDK引擎 | 文件位置 | 方法 |
|---------|--------|---------|------|
| 目标驱动行为 | `GoalActionOutcomeEngine` | `core/logic/core_engines.py` | `run_cycle(agent)` |
| 行动选择 | `GoalActionOutcomeEngine` | `core/logic/core_engines.py` | `select_action(agent, goal)` |
| 结果评估 | `GoalActionOutcomeEngine` | `core/logic/core_engines.py` | `evaluate_outcome(action, result)` |

**使用示例:**
```python
from usmsb_sdk.core.logic.core_engines import GoalActionOutcomeEngine

gao_engine = GoalActionOutcomeEngine(agent=ctmc_agent)
result = await gao_engine.run_cycle()
# result: {action_taken, outcome, goal_progress, next_action}
```

### 3.2 资源-转化-价值链 (RTV)

| 场景阶段 | SDK引擎 | 文件位置 | 方法 |
|---------|--------|---------|------|
| 资源分配 | `ResourceTransformationValueEngine` | `core/logic/core_engines.py` | `allocate_resources(agent, requirements)` |
| 价值评估 | `ResourceTransformationValueEngine` | `core/logic/core_engines.py` | `evaluate_value(transformation)` |
| 效率优化 | `ResourceTransformationValueEngine` | `core/logic/core_engines.py` | `optimize_allocation(resources, constraints)` |

### 3.3 信息-决策-控制循环 (IDC)

| 场景阶段 | SDK引擎 | 文件位置 | 方法 |
|---------|--------|---------|------|
| 信息处理 | `InformationDecisionControlEngine` | `core/logic/core_engines.py` | `process(raw_information)` |
| 决策生成 | `InformationDecisionControlEngine` | `core/logic/core_engines.py` | `generate_decision(processed_info)` |
| 控制指令 | `InformationDecisionControlEngine` | `core/logic/core_engines.py` | `generate_control_signals(decision)` |

### 3.4 系统-环境交互 (SE)

| 场景阶段 | SDK引擎 | 文件位置 | 方法 |
|---------|--------|---------|------|
| 环境状态更新 | `SystemEnvironmentEngine` | `core/logic/core_engines.py` | `update_state(changes)` |
| 环境约束检查 | `SystemEnvironmentEngine` | `core/logic/core_engines.py` | `check_constraints(action)` |
| 环境响应 | `SystemEnvironmentEngine` | `core/logic/core_engines.py` | `get_environment_response(action)` |

### 3.5 涌现与自组织 (ESO)

| 场景阶段 | SDK引擎 | 文件位置 | 方法 |
|---------|--------|---------|------|
| 模式检测 | `EmergenceSelfOrganizationEngine` | `core/logic/core_engines.py` | `detect_patterns(state_history)` |
| 涌现预测 | `EmergenceSelfOrganizationEngine` | `core/logic/core_engines.py` | `predict_emergence(current_state)` |
| 自组织协调 | `EmergenceSelfOrganizationEngine` | `core/logic/core_engines.py` | `coordinate_self_organization(agents)` |

### 3.6 适应与演化 (AE)

| 场景阶段 | SDK引擎 | 文件位置 | 方法 |
|---------|--------|---------|------|
| 适应调整 | `AdaptationEvolutionEngine` | `core/logic/core_engines.py` | `adapt(agent, learnings)` |
| 演化更新 | `AdaptationEvolutionEngine` | `core/logic/core_engines.py` | `evolve(agent, evolution_data)` |
| 能力提升 | `AdaptationEvolutionEngine` | `core/logic/core_engines.py` | `enhance_capabilities(agent, improvements)` |

---

## 4. 应用服务映射

### 4.1 行为预测服务

| 场景需求 | SDK服务 | 文件位置 | 方法 |
|---------|--------|---------|------|
| Agent行为预测 | `BehaviorPredictionService` | `services/behavior_prediction_service.py` | `predict_agent_behavior(agent, environment)` |
| 系统演化预测 | `BehaviorPredictionService` | `services/behavior_prediction_service.py` | `predict_system_evolution(agents, environment)` |
| 交互结果预测 | `BehaviorPredictionService` | `services/behavior_prediction_service.py` | `predict_interaction_outcome(agent1, agent2)` |

### 4.2 系统仿真服务

| 场景需求 | SDK服务 | 文件位置 | 方法 |
|---------|--------|---------|------|
| 创建仿真 | `SystemSimulationService` | `services/system_simulation_service.py` | `create_simulation(agents, environment, config)` |
| 运行仿真 | `SystemSimulationService` | `services/system_simulation_service.py` | `run_simulation(simulation_id)` |
| Monte Carlo | `SystemSimulationService` | `services/system_simulation_service.py` | `run_monte_carlo(agents, environment, num_runs)` |
| 分步执行 | `SystemSimulationService` | `services/system_simulation_service.py` | `step_simulation(simulation_id, num_steps)` |

**使用示例:**
```python
from usmsb_sdk.services.system_simulation_service import (
    SystemSimulationService, SimulationConfig, SimulationType
)

simulation = SystemSimulationService(llm_adapter)
sim_id = await simulation.create_simulation(
    agents=[ctmc_agent, ambulance_agent] + vehicle_agents,
    environment=traffic_environment,
    config=SimulationConfig(
        simulation_type=SimulationType.AGENT_BASED,
        max_steps=3600
    )
)
result = await simulation.run_simulation(sim_id)
```

---

## 5. 事件与监控映射

### 5.1 事件总线

| 场景需求 | SDK组件 | 文件位置 | 方法 |
|---------|--------|---------|------|
| 事件发布 | `EventBus` | `logging_monitoring/event_bus.py` | `emit(event_type, source, data)` |
| 事件订阅 | `EventBus` | `logging_monitoring/event_bus.py` | `subscribe(event_pattern, handler)` |
| 事件历史 | `EventBus` | `logging_monitoring/event_bus.py` | `get_event_history(event_type, limit)` |

**使用示例:**
```python
from usmsb_sdk.logging_monitoring import EventBus, EventType

event_bus = EventBus()
await event_bus.start()

# 订阅事故事件
event_bus.subscribe(
    "traffic.accident.detected",
    handle_accident,
    is_async=True
)

# 发布事件
await event_bus.emit(
    event_type="traffic.accident.detected",
    source="sensor_cam_001",
    data={"location": accident_location, "severity": "high"}
)
```

### 5.2 指标收集

| 场景需求 | SDK组件 | 文件位置 | 方法 |
|---------|--------|---------|------|
| 计数器 | `Counter` | `logging_monitoring/metrics.py` | `increment(amount)` |
| 仪表盘 | `Gauge` | `logging_monitoring/metrics.py` | `set(value)` |
| 直方图 | `Histogram` | `logging_monitoring/metrics.py` | `observe(value)` |
| 计时器 | `Timer` | `logging_monitoring/metrics.py` | `start()`, `stop()` |

**使用示例:**
```python
from usmsb_sdk.logging_monitoring import get_metrics_registry

registry = get_metrics_registry()

# 定义指标
accident_count = registry.counter("traffic.accident.count")
avg_delay = registry.gauge("traffic.average_delay")
response_time = registry.histogram("emergency.response_time")
decision_latency = registry.timer("decision.latency")

# 使用指标
accident_count.increment()
avg_delay.set(45.5)
response_time.observe(420)
label = decision_latency.start()
# ... 执行决策 ...
decision_latency.stop(label)
```

### 5.3 结构化日志

| 场景需求 | SDK组件 | 文件位置 | 方法 |
|---------|--------|---------|------|
| JSON日志 | `StructuredLogger` | `logging_monitoring/logger.py` | `info(message, **kwargs)` |
| 关联ID | `set_correlation_id()` | `logging_monitoring/logger.py` | `set_correlation_id(id)` |
| 上下文日志 | `LoggingContext` | `logging_monitoring/logger.py` | `with LoggingContext(...):` |

---

## 6. 数据持久化映射

### 6.1 数据模型

| 场景实体 | SDK模型 | 文件位置 | 字段 |
|---------|--------|---------|------|
| Agent | `AgentModel` | `data_management/models.py` | id, name, type, state, capabilities, goals |
| Goal | `GoalModel` | `data_management/models.py` | id, agent_id, name, priority, status, progress |
| Resource | `ResourceModel` | `data_management/models.py` | id, name, type, quantity, environment_id |
| Risk | `RiskModel` | `data_management/models.py` | id, name, probability, impact, risk_level |
| 仿真结果 | `SimulationResultModel` | `data_management/models.py` | id, simulation_id, status, metrics |
| 事件日志 | `EventLogModel` | `data_management/models.py` | id, event_type, source, data, timestamp |

### 6.2 Repository访问

| 场景操作 | SDK Repository | 文件位置 | 方法 |
|---------|---------------|---------|------|
| Agent CRUD | `AgentRepository` | `data_management/repositories.py` | `get_by_id()`, `create()`, `update()` |
| Goal CRUD | `GoalRepository` | `data_management/repositories.py` | `get_active_goals()`, `update_progress()` |
| 事件查询 | `EventLogRepository` | `data_management/repositories.py` | `get_recent()`, `get_by_type()` |
| 指标查询 | `MetricsRepository` | `data_management/repositories.py` | `get_time_series()`, `get_latest()` |

**使用示例:**
```python
from usmsb_sdk.data_management import RepositoryFactory, init_db

# 初始化数据库
await init_db("sqlite+aiosqlite:///./traffic.db")

# 使用Repository
factory = RepositoryFactory(session)
agent_repo = factory.agents
goal_repo = factory.goals

# 创建Agent
agent_model = AgentModel(
    id=ctmc_agent.id,
    name=ctmc_agent.name,
    type=ctmc_agent.type.value
)
await agent_repo.create(agent_model)

# 查询活动目标
active_goals = await goal_repo.get_active_goals(agent_id=ctmc_agent.id)
```

---

## 7. 知识库映射

### 7.1 向量数据库

| 场景需求 | SDK组件 | 文件位置 | 方法 |
|---------|--------|---------|------|
| 文档存储 | `VectorDBAdapter` | `intelligence_adapters/knowledge_base/adapters.py` | `store(documents)` |
| 相似搜索 | `VectorDBAdapter` | `intelligence_adapters/knowledge_base/adapters.py` | `search(query, top_k)` |
| RAG查询 | `VectorDBAdapter` | `intelligence_adapters/knowledge_base/adapters.py` | `query_with_rag(query, llm_adapter)` |

**使用示例:**
```python
from usmsb_sdk.intelligence_adapters.knowledge_base.adapters import (
    VectorDBAdapter, VectorDBType
)

# 初始化向量数据库
kb = VectorDBAdapter(
    db_type=VectorDBType.CHROMA,
    collection_name="traffic_cases"
)

# 存储案例
await kb.store([{
    "id": "case_001",
    "content": "高峰期主干道三车追尾事故处理...",
    "metadata": {"type": "accident", "severity": "high"}
}])

# RAG查询
result = await kb.query_with_rag(
    query="如何快速疏导高峰期交通事故造成的拥堵?",
    llm_adapter=llm_adapter,
    top_k=5
)
```

---

## 8. 完整依赖图

```
智能交通管理系统
│
├── core/elements.py
│   ├── Agent (CTMC-Agent, Vehicle-Agent, Emergency-Agent, Citizen-Agent)
│   ├── Goal (安全、效率、救援、信息)
│   ├── Resource (道路、信号灯、计算、通信)
│   ├── Rule (紧急优先、信号遵守)
│   ├── Information (静态、动态、社交)
│   ├── Risk (拥堵扩散、二次事故、救援延误)
│   └── Environment (城市交通网络)
│
├── core/universal_actions.py
│   ├── LLMPerceptionService (多源感知融合)
│   ├── LLMDecisionService (策略决策)
│   ├── LLMExecutionService (行动执行)
│   ├── LLMInteractionService (Agent通信)
│   ├── LLMLearningService (经验学习)
│   └── LLMRiskManagementService (风险管理)
│
├── core/logic/core_engines.py
│   ├── GoalActionOutcomeEngine (目标驱动循环)
│   ├── ResourceTransformationValueEngine (资源价值链)
│   ├── InformationDecisionControlEngine (信息决策控制)
│   ├── SystemEnvironmentEngine (环境交互)
│   ├── EmergenceSelfOrganizationEngine (涌现检测)
│   └── AdaptationEvolutionEngine (适应演化)
│
├── services/
│   ├── behavior_prediction_service.py (行为预测)
│   ├── decision_support_service.py (决策支持)
│   └── system_simulation_service.py (系统仿真)
│
├── core/communication/
│   └── agent_communication.py (Agent通信协议)
│
├── logging_monitoring/
│   ├── event_bus.py (事件驱动)
│   ├── metrics.py (指标收集)
│   └── logger.py (结构化日志)
│
├── data_management/
│   ├── models.py (数据模型)
│   └── repositories.py (数据访问)
│
└── intelligence_adapters/
    ├── llm/ (LLM适配器)
    └── knowledge_base/adapters.py (知识库)
```

---

## 9. 结论

USMSB SDK 提供了完整的组件支持智能交通管理场景的实现:

- ✅ **9大核心元素** - 完整支持Agent、Goal、Resource、Risk等实体建模
- ✅ **9大通用行动接口** - 感知、决策、执行、交互、学习、风险管理等
- ✅ **6大核心逻辑引擎** - 目标驱动、资源转化、信息处理、环境交互、涌现检测、适应演化
- ✅ **应用服务层** - 行为预测、决策支持、系统仿真
- ✅ **通信与协作** - Agent通信协议、事件总线
- ✅ **监控与日志** - 指标收集、结构化日志
- ✅ **数据持久化** - Repository模式、SQLAlchemy模型
- ✅ **知识管理** - 向量数据库、RAG支持

**SDK完全满足场景需求，可以直接进行代码实现。**
