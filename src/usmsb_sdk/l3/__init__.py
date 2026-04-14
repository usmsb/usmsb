"""
USMSB L3 - 目的内生 Agent 模块

L3 = 目的内生 Agent（Intrinsic Purpose Agent）

核心模块：
- PurposeGenerator: 目标生成器（L3 核心突破口）
- IntrinsicMotivationEngine: 内在动机引擎
- NeedDetector: 需求检测器
- GoalPersistence: 目标持久化（Gene Capsule 集成）

L3 硅基生命判断标准：
- 工具：goal = user_input (外部赋予)
- 硅基生命：goal = self.generate_goal() (自己生成)

使用方式：
```python
from usmsb_sdk.l3 import PurposeGenerator, IntrinsicMotivationEngine, NeedDetector

# 创建组件
motivation = IntrinsicMotivationEngine()
detector = NeedDetector()
generator = PurposeGenerator(
    agent_id="agent_001",
    intrinsic_motivation=motivation,
    need_detector=detector
)

# 生成目标
purpose = generator.generate_purpose()
if purpose:
    goal = generator.purpose_to_goal(purpose)
    print(f"生成了目标: {goal.name}")
```

或使用完整集成：
```python
from usmsb_sdk.l3 import PurposeGenerator, GoalPersistence

persistence = GoalPersistence(agent_id="agent_001")
generator = PurposeGenerator(
    agent_id="agent_001",
    goal_persistence=persistence
)

# 重启后恢复目标
goals = generator.recover_goals_from_persistence()
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
]
