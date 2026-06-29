# -*- coding: utf-8 -*-
"""团队产品。

v3.0：团队 = 多 PEA over A2A —— TeamLeaderPea（LLM 拆解→能力发现组队→联合订单 Shapley 分账）。
旧 TeamLeader/TaskAllocation 等为早期内存 dict-CRUD stub，安全导入，标记 deprecated。
"""

from usmsb_sdk.products.team.team_leader_pea import LLMTaskDecomposer, TeamLeaderPea

# 旧 stub 安全导入：任一断裂不连累整个包
try:  # pragma: no cover - legacy, deprecated
    from usmsb_sdk.products.team.team_leader import (
        Department,
        TeamLeader,
        TeamMember,
        TeamTask,
    )
    from usmsb_sdk.products.team.task_allocation import AllocationResult, TaskAllocation
    from usmsb_sdk.products.team.team_memory import Decision, TeamContext, TeamMemory
    from usmsb_sdk.products.team.weekly_planning import WeeklyGoal, WeeklyPlan, WeeklyPlanning
except Exception:  # noqa: BLE001
    TeamLeader = TeamMember = TeamTask = Department = None  # type: ignore
    TaskAllocation = AllocationResult = TeamMemory = TeamContext = Decision = None  # type: ignore
    WeeklyPlanning = WeeklyGoal = WeeklyPlan = None  # type: ignore

__all__ = [
    # v3.0 supported
    "TeamLeaderPea",
    "LLMTaskDecomposer",
    # legacy (deprecated)
    "TeamLeader",
    "TeamMember",
    "TeamTask",
    "Department",
    "TaskAllocation",
    "AllocationResult",
    "TeamMemory",
    "TeamContext",
    "Decision",
    "WeeklyPlanning",
    "WeeklyGoal",
    "WeeklyPlan",
]
