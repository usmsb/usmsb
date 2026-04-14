"""
USMSB L3 - 目的内生 Agent 模块

L3 = 目的内生 Agent（Intrinsic Purpose Agent）

核心模块：
- PurposeGenerator: 目标生成器（L3 核心突破口）
- IntrinsicMotivationEngine: 内在动机引擎
- NeedDetector: 需求检测器
- GoalPersistence: 目标持久化（Gene Capsule 集成）
- ValueSelfLoop: 价值自循环模块
- ServiceRegistry: 服务注册与管理
- ValueLedger: 价值账本
- VIBEToken: VIBE Token 管理

L3 硅基生命判断标准：
- 工具：goal = user_input (外部赋予)
- 硅基生命：goal = self.generate_goal() (自己生成)

使用方式：
```python
from usmsb_sdk.l3 import PurposeGenerator, ValueSelfLoop, ServiceType

# 创建组件
generator = PurposeGenerator(agent_id="agent_001")
value_loop = ValueSelfLoop(agent_id="agent_001")

# 生成目标
purpose = generator.generate_purpose()
goal = generator.purpose_to_goal(purpose)

# 执行价值循环
result = value_loop.execute_complete_cycle(
    provider_id="agent_001",
    consumer_id="agent_002",
    service_type=ServiceType.COMPUTATION,
    description="数据处理"
)
```
"""

from .purpose_generator import (
    PurposeGenerator,
    Purpose,
    IntrinsicNeed,
    NeedType,
)
from .intrinsic_motivation import (
    IntrinsicMotivationEngine,
    MotivationSource,
)
from .need_detector import (
    NeedDetector,
    AgentSelfState,
)
from .goal_persistence import (
    GoalPersistence,
    GeneCapsule,
    GeneCapsuleDB,
)
from .vibe_token import (
    VIBEToken,
    VIBEBalance,
)
from .value_ledger import (
    ValueLedger,
    ValueRecord,
    ValueType,
    ValueStatus,
)
from .service_registry import (
    ServiceRegistry,
    Service,
    ServiceType,
    ServiceStatus,
)
from .value_self_loop import (
    ValueSelfLoop,
    ValueCalculationEngine,
    VIBEConversionEngine,
    CircularFlowStats,
)

__all__ = [
    # Purpose Generator
    "PurposeGenerator",
    "Purpose",
    "IntrinsicNeed",
    "NeedType",
    # Intrinsic Motivation
    "IntrinsicMotivationEngine",
    "MotivationSource",
    # Need Detector
    "NeedDetector",
    "AgentSelfState",
    # Goal Persistence
    "GoalPersistence",
    "GeneCapsule",
    "GeneCapsuleDB",
    # VIBE Token
    "VIBEToken",
    "VIBEBalance",
    # Value Ledger
    "ValueLedger",
    "ValueRecord",
    "ValueType",
    "ValueStatus",
    # Service Registry
    "ServiceRegistry",
    "Service",
    "ServiceType",
    "ServiceStatus",
    # Value Self Loop
    "ValueSelfLoop",
    "ValueCalculationEngine",
    "VIBEConversionEngine",
    "CircularFlowStats",
]
