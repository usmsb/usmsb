# -*- coding: utf-8 -*-
"""
Harness Architecture - MAS 工程基础设施

基于《OpenClaw之后，聊聊多智能体系统Harness Engineering架构设计思考》

四层架构：
1. 知识供给层 - 参数化/非参数化/经验知识
2. 执行编排层 - Orchestrator/Workflow/Policy
3. 风险门控层 - 硬性/软性/动态规则
4. 治理运营层 - 经验沉淀飞轮

使用方式：
```python
from usmsb_sdk.harness import MASOrchestrator, PolicyRuntime, KnowledgeLayer

# 创建 Harness
harness = MASOrchestrator()

# 执行任务
result = await harness.execute(user_intent="帮我分析销售数据")
```
"""

from usmsb_sdk.harness.knowledge_layer import (
    KnowledgeLayer,
    ParametricKnowledge,
    NonParametricKnowledge,
    ExperienceKnowledge,
)

from usmsb_sdk.harness.policy_runtime import (
    PolicyRuntime,
    HardRule,
    SoftRule,
    DynamicRule,
    RuleType,
)

from usmsb_sdk.harness.execution_orchestrator import (
    ExecutionOrchestrator,
    TopologyType,
    AgentRole,
    TaskDecomposition,
)

from usmsb_sdk.harness.governance_layer import (
    GovernanceLayer,
    TrajectoryRecord,
    ExperienceRepository,
)

from usmsb_sdk.harness.execution_engine import (
    ExecutionEngine,
    ExecutionContext,
    ExecutionResult,
    ExecutionStatus,
    EvaluationEngine,
)

__all__ = [
    # Knowledge Layer
    "KnowledgeLayer",
    "ParametricKnowledge",
    "NonParametricKnowledge",
    "ExperienceKnowledge",
    # Policy Runtime
    "PolicyRuntime",
    "HardRule",
    "SoftRule",
    "DynamicRule",
    "RuleType",
    # Execution Orchestrator
    "ExecutionOrchestrator",
    "TopologyType",
    "AgentRole",
    "TaskDecomposition",
    # Governance Layer
    "GovernanceLayer",
    "TrajectoryRecord",
    "ExperienceRepository",
]
