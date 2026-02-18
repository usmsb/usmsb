# USMSB 交通管理场景 - 详细序列流程

## 1. 系统初始化序列

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           系统启动阶段                                        │
└──────────────────────────────────────────────────────────────────────────────┘

Actor: System

Step 1: 创建环境 (Environment)
────────────────────────────────
Environment environment = Environment(
    id="env_city_traffic_001",
    name="城市交通网络",
    type=EnvironmentType.URBAN,
    state={
        "total_roads": 1500,
        "total_intersections": 450,
        "active_signals": 380
    },
    constraints={
        "max_speed": 60,  # km/h
        "emergency_priority": True
    }
)

Step 2: 创建资源 (Resource)
────────────────────────────────
# 道路资源
road_resources = [
    Resource(id="road_main_001", name="主干道A", type=ResourceType.INFRASTRUCTURE,
             quantity=1, attributes={"lanes": 4, "length": 5000}),
    Resource(id="road_secondary_001", name="次干道B", type=ResourceType.INFRASTRUCTURE,
             quantity=1, attributes={"lanes": 2, "length": 3000}),
    # ... 更多道路
]

# 信号灯资源
signal_resources = [
    Resource(id="signal_001", name="交叉口X信号灯", type=ResourceType.CONTROL,
             quantity=1, attributes={"phases": 4, "current_phase": 1}),
    # ... 更多信号灯
]

Step 3: 创建规则 (Rule)
────────────────────────────────
traffic_rules = [
    Rule(
        id="rule_emergency_priority",
        name="紧急车辆优先通行",
        description="紧急车辆享有最高通行优先级",
        rule_type="priority",
        conditions={"vehicle_type": "emergency"},
        actions={"right_of_way": True, "signal_preemption": True}
    ),
    Rule(
        id="rule_signal_compliance",
        name="信号灯遵守",
        description="所有车辆必须遵守信号灯指示",
        rule_type="constraint",
        conditions={"signal_state": "red"},
        actions={"must_stop": True}
    ),
    # ... 更多规则
]

Step 4: 创建 CTMC-Agent
────────────────────────────────
ctmc_agent = Agent(
    id="agent_ctmc_001",
    name="城市交通管理中心",
    type=AgentType.AI_AGENT,
    capabilities=[
        "global_perception",
        "multi_objective_decision",
        "signal_control",
        "route_optimization",
        "risk_assessment",
        "agent_coordination"
    ],
    goals=[
        Goal(id="goal_safety", name="保障安全", priority=1.0),
        Goal(id="goal_efficiency", name="提升效率", priority=0.8),
        Goal(id="goal_rescue", name="保障救援", priority=0.95)
    ],
    resources=[
        Resource(id="res_compute", name="计算资源", quantity=100),
        Resource(id="res_comm", name="通信带宽", quantity=1000)
    ],
    rules=traffic_rules
)

Step 5: 创建 Vehicle-Agent 池
────────────────────────────────
vehicle_agents = []
for i in range(1000):
    agent = Agent(
        id=f"agent_vehicle_{i:04d}",
        name=f"车辆{i}",
        type=AgentType.AI_AGENT,
        capabilities=["route_planning", "communication", "driving"],
        goals=[Goal(id=f"goal_dest_{i}", name="到达目的地", priority=0.9)],
        resources=[Resource(id=f"res_fuel_{i}", name="燃油", quantity=random.uniform(20, 100))]
    )
    vehicle_agents.append(agent)

Step 6: 创建 Emergency-Agent
────────────────────────────────
ambulance_agent = Agent(
    id="agent_ambulance_001",
    name="救护车001",
    type=AgentType.AI_AGENT,
    capabilities=["emergency_response", "route_optimization", "priority_communication"],
    goals=[Goal(id="goal_rescue", name="救援伤员", priority=1.0)],
    resources=[Resource(id="res_fuel", name="燃油", quantity=80)]
)

police_agent = Agent(
    id="agent_police_001",
    name="警车001",
    type=AgentType.AI_AGENT,
    capabilities=["emergency_response", "route_optimization", "priority_communication"],
    goals=[Goal(id="goal_scene", name="处理事故现场", priority=1.0)]
)

Step 7: 初始化逻辑引擎
────────────────────────────────
registry = LogicEngineRegistry()

# 注册所有核心引擎
registry.register(GoalActionOutcomeEngine(ctmc_agent))
registry.register(ResourceTransformationValueEngine())
registry.register(InformationDecisionControlEngine())
registry.register(SystemEnvironmentEngine(environment))
registry.register(EmergenceSelfOrganizationEngine())
registry.register(AdaptationEvolutionEngine())

Step 8: 初始化服务
────────────────────────────────
# LLM适配器 (使用GLM-5或OpenAI)
llm_adapter = GLMAdapter(api_key=config.ZHIPU_API_KEY)

# 通用行动服务
perception_service = LLMPerceptionService(llm_adapter)
decision_service = LLMDecisionService(llm_adapter)
execution_service = LLMExecutionService(llm_adapter)
interaction_service = LLMInteractionService(llm_adapter)
learning_service = LLMLearningService(llm_adapter)
risk_service = LLMRiskManagementService(llm_adapter)

# 应用服务
decision_support = DecisionSupportService(llm_adapter)
simulation = SystemSimulationService(llm_adapter)

# 事件总线
event_bus = EventBus()
await event_bus.start()

Step 9: 注册事件处理器
────────────────────────────────
event_bus.subscribe(
    "traffic.accident.detected",
    ctmc_agent.handle_accident_detected,
    is_async=True,
    priority=10
)

event_bus.subscribe(
    "agent.emergency.dispatch",
    ambulance_agent.handle_dispatch,
    is_async=True
)

# ... 更多订阅
```

---

## 2. 事故检测与感知序列

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    Phase 1: 感知 (Perceive)                                   │
│                    时间: T+0s (事故发生)                                      │
└──────────────────────────────────────────────────────────────────────────────┘

Actor: Sensors, Vehicle-Agent, CTMC-Agent

Step 1: 传感器检测异常
────────────────────────────────
# 摄像头检测到异常停车
camera_data = {
    "sensor_id": "cam_main_050",
    "timestamp": now(),
    "detections": [
        {"type": "vehicle_stopped", "location": "lane_1", "confidence": 0.95},
        {"type": "vehicle_stopped", "location": "lane_2", "confidence": 0.92},
        {"type": "collision", "confidence": 0.88}
    ]
}

# 地磁线圈检测流量骤降
loop_data = {
    "sensor_id": "loop_main_050",
    "timestamp": now(),
    "flow_before": 1200,  # vehicles/hour
    "flow_after": 200,
    "speed_before": 45,   # km/h
    "speed_after": 5
}

Step 2: Vehicle-Agent 发送事故报告
────────────────────────────────
# 事故车辆自动发送报告
accident_vehicle = vehicle_agents[accident_vehicle_index]

await interaction_service.send_message(
    sender=accident_vehicle,
    receiver=ctmc_agent,
    message_type="accident_report",
    content={
        "type": "multi_vehicle_collision",
        "location": {"lat": 31.2304, "lng": 121.4737},
        "severity": "high",
        "blocked_lanes": 2,
        "injuries": True,
        "description": "三车追尾，两条车道堵塞"
    }
)

Step 3: CTMC-Agent 触发感知流程
────────────────────────────────
# 接收到事故报告后触发
async def ctmc_agent.handle_accident_detected(event):
    # 调用感知服务进行信息融合
    perception_result = await perception_service.perceive(
        agent=self,
        environment=environment,
        inputs={
            "sensor_data": [camera_data, loop_data],
            "agent_reports": event.data,
            "historical_context": get_historical_context()
        },
        perception_type="multi_source_fusion"
    )

    # perception_result 结构:
    # {
    #     "accident_snapshot": {
    #         "location": {"lat": 31.2304, "lng": 121.4737},
    #         "severity": "high",
    #         "blocked_lanes": 2,
    #         "vehicles_involved": 3,
    #         "injuries": True,
    #         "estimated_clearance": None
    #     },
    #     "traffic_state": {
    #         "affected_segment": "road_main_001",
    #         "current_flow": 200,
    #         "queue_length": 50,
    #         "congestion_level": 0.85
    #     },
    #     "confidence": 0.92,
    #     "uncertainties": ["exact_injury_count", "clearance_time"]
    # }

    # 发布感知完成事件
    await event_bus.emit(
        event_type="perception.completed",
        source=self.id,
        data=perception_result
    )

Step 4: 信息-决策-控制引擎处理
────────────────────────────────
# IDC引擎处理感知结果
idc_engine = registry.get(InformationDecisionControlEngine)

processed_info = await idc_engine.process(
    raw_information=perception_result,
    context={
        "time": "rush_hour",
        "weather": "clear",
        "day_type": "weekday"
    }
)

# processed_info 包含结构化的决策输入
# {
#     "structured_facts": [...],
#     "derived_insights": [...],
#     "control_signals": [...],
#     "priority_ranking": [...]
# }
```

---

## 3. 目标评估与风险识别序列

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    Phase 2: 目标评估 & 风险识别                                │
│                    时间: T+5s                                                 │
└──────────────────────────────────────────────────────────────────────────────┘

Actor: CTMC-Agent, RiskService

Step 1: 激活相关目标
────────────────────────────────
# 目标管理器激活并排序目标
goal_manager = GoalManager(agent=ctmc_agent)

# 根据场景动态调整优先级
activated_goals = await goal_manager.activate_for_scenario(
    scenario_type="traffic_accident",
    context={
        "severity": "high",
        "injuries": True,
        "location": "main_road"
    }
)

# 结果:
# [
#     Goal(id="goal_safety", priority=1.0, status="active"),
#     Goal(id="goal_rescue", priority=0.98, status="active"),  # 提升优先级
#     Goal(id="goal_efficiency", priority=0.7, status="active"), # 稍降低
#     Goal(id="goal_info", priority=0.6, status="active")
# ]

Step 2: 风险识别
────────────────────────────────
risks = await risk_service.identify_risks(
    context={
        "accident": perception_result["accident_snapshot"],
        "traffic_state": perception_result["traffic_state"],
        "environment": environment.state,
        "time": "rush_hour"
    },
    agent=ctmc_agent
)

# 识别出的风险:
# {
#     "identified_risks": [
#         {
#             "id": "risk_congestion_spread",
#             "name": "拥堵扩散风险",
#             "probability": 0.85,
#             "impact": 0.8,
#             "level": "high",
#             "affected_area": ["segment_1", "segment_2", "segment_3"]
#         },
#         {
#             "id": "risk_secondary_accident",
#             "name": "二次事故风险",
#             "probability": 0.45,
#             "impact": 0.95,
#             "level": "critical",
#             "mitigation": "设置警示标志、减速引导"
#         },
#         {
#             "id": "risk_rescue_delay",
#             "name": "救援延误风险",
#             "probability": 0.6,
#             "impact": 0.9,
#             "level": "high",
#             "current_path_blocked": True
#         }
#     ],
#     "risk_matrix": {...},
#     "mitigation_recommendations": [...]
# }

Step 3: 创建风险实体并添加到Agent
────────────────────────────────
for risk_data in risks["identified_risks"]:
    risk = Risk(
        id=risk_data["id"],
        name=risk_data["name"],
        probability=risk_data["probability"],
        impact=risk_data["impact"],
        description=risk_data.get("mitigation", ""),
        status="identified"
    )
    ctmc_agent.add_risk(risk)
```

---

## 4. 决策生成序列

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    Phase 3: 决策 (Decide)                                     │
│                    时间: T+10s                                                │
└──────────────────────────────────────────────────────────────────────────────┘

Actor: CTMC-Agent, DecisionService, DecisionSupportService

Step 1: 生成决策选项
────────────────────────────────
decision_options = [
    DecisionOption(
        id="option_1",
        name="优先救援方案",
        description="优先保障救援车辆通行，适度牺牲通行效率",
        expected_outcome="救援时间最短，但短期拥堵加剧",
        resource_requirements={"signal_adjustment": 15, "lane_control": 2},
        risk_level=0.3,
        estimated_value=0.85
    ),
    DecisionOption(
        id="option_2",
        name="均衡方案",
        description="平衡救援与疏导，逐步恢复通行",
        expected_outcome="救援和疏导都达到可接受水平",
        resource_requirements={"signal_adjustment": 10, "lane_control": 1},
        risk_level=0.4,
        estimated_value=0.75
    ),
    DecisionOption(
        id="option_3",
        name="快速疏导方案",
        description="最大化分流，快速恢复通行",
        expected_outcome="拥堵消散最快，但救援可能延误",
        resource_requirements={"signal_adjustment": 20, "lane_control": 3},
        risk_level=0.6,
        estimated_value=0.65
    )
]

Step 2: 创建决策上下文
────────────────────────────────
decision_context = DecisionContext(
    agent=ctmc_agent,
    goals=ctmc_agent.get_active_goals(),
    resources=ctmc_agent.resources,
    risks=ctmc_agent.risks,
    rules=ctmc_agent.rules,
    information=[
        Information(id="info_1", content=perception_result),
        Information(id="info_2", content=risks)
    ],
    constraints={
        "time_pressure": "high",
        "resource_available": True,
        "legal_requirements": ["救援优先"]
    },
    preferences={
        "safety_weight": 0.4,
        "efficiency_weight": 0.3,
        "rescue_weight": 0.3
    }
)

Step 3: 多准则决策分析
────────────────────────────────
recommendation = await decision_support.recommend(
    options=decision_options,
    context=decision_context,
    criteria=[
        DecisionCriteria(name="goal_alignment", weight=1.0),
        DecisionCriteria(name="resource_efficiency", weight=0.8, is_cost=True),
        DecisionCriteria(name="risk_level", weight=0.9, is_cost=True),
        DecisionCriteria(name="expected_value", weight=0.7)
    ],
    decision_type=DecisionType.STRATEGIC
)

# recommendation 结构:
# {
#     "recommended_option": option_1,  # 优先救援方案
#     "alternatives": [option_2, option_3],
#     "analysis": {
#         "weighted_scores": {"option_1": 0.82, "option_2": 0.75, "option_3": 0.68},
#         "rankings": [("option_1", 0.82), ("option_2", 0.75), ("option_3", 0.68)],
#         "tradeoffs": [...],
#         "confidence": 0.85
#     },
#     "rationale": "考虑到事故涉及人员伤亡，救援优先级最高...",
#     "implementation_steps": [
#         "1. 立即调度救护车和警车",
#         "2. 调整沿途信号灯为绿波带",
#         "3. 封闭事故车道",
#         "4. 发布绕行建议",
#         "5. 持续监控并调整"
#     ]
# }

Step 4: 生成具体行动序列
────────────────────────────────
# 使用决策服务生成行动序列
actions = await decision_service.decide(
    agent=ctmc_agent,
    context={
        "recommendation": recommendation,
        "current_state": environment.state
    },
    decision_type="multi_step"
)

# actions 结构:
# [
#     Action(id="action_1", type="emergency_dispatch", target="ambulance_001", params={...}),
#     Action(id="action_2", type="signal_adjustment", target="signal_001", params={...}),
#     Action(id="action_3", type="lane_closure", target="road_main_001", params={...}),
#     Action(id="action_4", type="info_broadcast", target="citizens", params={...}),
#     ...
# ]
```

---

## 5. 交互与执行序列

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    Phase 4: 交互与执行 (Interact)                              │
│                    时间: T+15s ~ T+300s                                       │
└──────────────────────────────────────────────────────────────────────────────┘

Actor: CTMC-Agent, Emergency-Agent, Vehicle-Agent, Signal System

Step 1: 执行信号灯调整
────────────────────────────────
signal_action = actions[1]  # signal_adjustment

result = await execution_service.execute(
    action=signal_action,
    agent=ctmc_agent,
    environment=environment
)

# 具体执行:
# 1. 向信号灯控制器发送配时调整指令
# 2. 验证指令执行成功
# 3. 更新环境状态

Step 2: 调度 Emergency-Agent
────────────────────────────────
# 向救护车发送调度指令
dispatch_result = await interaction_service.send_message(
    sender=ctmc_agent,
    receiver=ambulance_agent,
    message_type="emergency_dispatch",
    content={
        "mission_id": "mission_001",
        "type": "medical_rescue",
        "location": perception_result["accident_snapshot"]["location"],
        "priority": "highest",
        "route": await route_optimizer.get_optimal_route(
            origin=ambulance_agent.location,
            destination=perception_result["accident_snapshot"]["location"],
            constraints={"green_wave": True, "avoid_congestion": True}
        ),
        "eta": 420  # seconds
    }
)

# 救护车接收并确认
async def ambulance_agent.handle_dispatch(event):
    # 更新目标
    self.update_goal("goal_rescue", status="executing")

    # 开始移动
    await self.follow_route(event.data["route"])

    # 发送确认
    await interaction_service.send_message(
        sender=self,
        receiver=ctmc_agent,
        message_type="dispatch_accepted",
        content={"eta": event.data["eta"], "status": "en_route"}
    )

Step 3: 发布交通信息
────────────────────────────────
# 向所有受影响的 Vehicle-Agent 发送绕行建议
affected_vehicles = get_vehicles_in_area(affected_area)

for vehicle in affected_vehicles:
    alternate_route = await route_optimizer.get_alternate_route(
        origin=vehicle.location,
        destination=vehicle.destination,
        avoid_segments=["road_main_001"]
    )

    await interaction_service.send_message(
        sender=ctmc_agent,
        receiver=vehicle,
        message_type="reroute_suggestion",
        content={
            "reason": "accident_ahead",
            "alternate_route": alternate_route,
            "delay_saved": alternate_route["time_saved"]
        }
    )

Step 4: 处理 Agent 反馈
────────────────────────────────
# Vehicle-Agent 响应绕行建议
async def vehicle_agent.handle_reroute(event):
    # 评估建议
    if event.data["delay_saved"] > 5 * 60:  # 节省超过5分钟
        self.accept_route(event.data["alternate_route"])
        await interaction_service.send_message(
            sender=self,
            receiver=ctmc_agent,
            message_type="reroute_accepted",
            content={"vehicle_id": self.id}
        )
    else:
        # 继续原路线但减速
        self.adjust_speed(0.5)

Step 5: 创建绿波带
────────────────────────────────
# 为救护车创建绿波带
green_wave_segments = get_route_segments(ambulance_route)

for segment in green_wave_segments:
    signal = get_signal_for_segment(segment)
    await execution_service.execute(
        action=Action(
            type="signal_preemption",
            target=signal.id,
            params={"phase": "green", "duration": 30}
        ),
        agent=ctmc_agent
    )

    # 记录事件
    await event_bus.emit(
        event_type="signal.preemption",
        source=ctmc_agent.id,
        data={"signal_id": signal.id, "reason": "emergency_escort"}
    )
```

---

## 6. 学习与适应序列

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    Phase 5: 学习 (Learn)                                      │
│                    时间: T+30min (事故处理完成)                                │
└──────────────────────────────────────────────────────────────────────────────┘

Actor: CTMC-Agent, LearningService, AdaptationEngine

Step 1: 收集执行数据
────────────────────────────────
execution_history = {
    "incident": perception_result,
    "decisions": [recommendation, actions],
    "executions": execution_logs,
    "agent_responses": agent_feedback,
    "timeline": event_timeline,
    "outcomes": {
        "rescue_time": 420,  # 实际救援时间
        "congestion_duration": 1800,  # 拥堵持续时间
        "secondary_accidents": 0,
        "vehicles_rerouted": 450,
        "citizen_satisfaction": 0.85
    }
}

Step 2: 效果评估
────────────────────────────────
evaluation_result = await evaluation_service.evaluate(
    agent=ctmc_agent,
    execution_history=execution_history,
    goals=ctmc_agent.get_active_goals()
)

# evaluation_result:
# {
#     "goal_achievements": {
#         "goal_safety": {"target": 1.0, "actual": 1.0, "score": 1.0},
#         "goal_rescue": {"target": 480, "actual": 420, "score": 1.14},
#         "goal_efficiency": {"target": 1500, "actual": 1800, "score": 0.83}
#     },
#     "overall_score": 0.92,
#     "success_factors": ["快速响应", "绿波带有效", "信息发布及时"],
#     "improvement_areas": ["拥堵疏导可更快", "部分绕行路线非最优"]
# }

Step 3: 经验学习
────────────────────────────────
lessons = await learning_service.learn(
    experience=execution_history,
    evaluation=evaluation_result,
    context={
        "scenario_type": "traffic_accident",
        "time": "rush_hour",
        "severity": "high"
    }
)

# lessons:
# {
#     "patterns_learned": [
#         {
#             "pattern": "rush_hour_accident_response",
#             "conditions": {"time": "rush_hour", "severity": "high"},
#             "effective_actions": ["immediate_dispatch", "green_wave", "early_reroute"],
#             "effectiveness": 0.92
#         }
#     ],
#     "parameters_adjusted": {
#         "dispatch_delay_threshold": 10,  # 从15降到10秒
#         "reroute_trigger_distance": 2000  # 从1500增加到2000米
#     },
#     "knowledge_updates": {
#         "new_rules": [],
#         "modified_rules": ["emergency_response_protocol"]
#     }
# }

Step 4: 知识库更新
────────────────────────────────
# 更新知识库中的经验
knowledge_base = VectorDBAdapter(...)

await knowledge_base.store(
    documents=[{
        "id": f"case_{incident_id}",
        "content": json.dumps(execution_history),
        "metadata": {
            "type": "incident_case",
            "scenario": "traffic_accident",
            "outcome": "successful",
            "lessons": lessons
        }
    }]
)

Step 5: 模型适应
────────────────────────────────
adaptation_engine = registry.get(AdaptationEvolutionEngine)

await adaptation_engine.adapt(
    agent=ctmc_agent,
    learnings=lessons,
    adaptation_type="incremental"
)

# 更新 Agent 的决策参数和策略
# 例如: 调整信号配时算法的权重、更新风险评估模型等
```

---

## 7. 仿真运行完整流程

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    完整仿真运行                                                │
└──────────────────────────────────────────────────────────────────────────────┘

async def run_traffic_simulation():
    # 初始化
    simulation = SystemSimulationService(llm_adapter)

    # 创建仿真
    sim_id = await simulation.create_simulation(
        agents=[ctmc_agent] + vehicle_agents + [ambulance_agent, police_agent],
        environment=environment,
        config=SimulationConfig(
            simulation_type=SimulationType.AGENT_BASED,
            max_steps=3600,  # 1小时，每步1秒
            snapshot_interval=60,
            stop_conditions=[
                {"type": "goal_achieved", "goal_id": "goal_safety"},
                {"type": "step_count", "max_steps": 7200}
            ]
        )
    )

    # 注册仿真事件处理器
    simulation.register_event_handler(
        EventType.AGENT_ACTION,
        handle_agent_action
    )
    simulation.register_event_handler(
        EventType.AGENT_INTERACTION,
        handle_agent_interaction
    )

    # 在特定步骤注入事故
    async def inject_accident(sim, step_num):
        if step_num == 300:  # 第5分钟发生事故
            await event_bus.emit(
                event_type="traffic.accident.detected",
                source="simulation",
                data=accident_config
            )

    simulation.add_step_callback(inject_accident)

    # 运行仿真
    result = await simulation.run_simulation(sim_id)

    # 分析结果
    print(f"仿真状态: {result.status}")
    print(f"执行步数: {len(result.steps)}")
    print(f"最终指标: {result.metrics}")
    print(f"涌现模式: {result.emergent_patterns}")

    # Agent 统计
    for agent_id, stats in result.agent_stats.items():
        print(f"Agent {agent_id}: {stats}")

    return result

# 运行
result = await run_traffic_simulation()
```

---

## 8. 关键接口调用总结

| 阶段 | SDK 组件 | 关键方法 |
|------|---------|---------|
| 初始化 | Agent, Environment, Resource | `__init__`, `add_goal`, `add_resource` |
| 感知 | LLMPerceptionService | `perceive()` |
| 信息处理 | InformationDecisionControlEngine | `process()` |
| 风险识别 | LLMRiskManagementService | `identify_risks()` |
| 决策 | DecisionSupportService | `recommend()`, `analyze_decision()` |
| 执行 | LLMExecutionService | `execute()` |
| 交互 | LLMInteractionService | `send_message()`, `broadcast()` |
| 学习 | LLMLearningService | `learn()` |
| 适应 | AdaptationEvolutionEngine | `adapt()` |
| 仿真 | SystemSimulationService | `create_simulation()`, `run_simulation()` |
| 事件 | EventBus | `emit()`, `subscribe()` |
| 指标 | MetricsRegistry | `counter()`, `gauge()`, `histogram()` |
| 存储 | RepositoryFactory | `agents`, `goals`, `event_logs` |
