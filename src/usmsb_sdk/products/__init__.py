# -*- coding: utf-8 -*-
"""USMSB 产品。

v3.0：超级个体大管家走 ButlerPea（基于 harness 的 PEA）。
团队版（TeamLeader 等）仍为早期 stub，安全导入；后续会迁到「多 PEA over A2A」。
"""

# v3.0 受支持实现
from usmsb_sdk.products.super_individual import ButlerPea, ButlerProfile
from usmsb_sdk.products.team import LLMTaskDecomposer, TeamLeaderPea

# 旧 stub 安全导入：任一断裂不连累整个 products 包
try:  # pragma: no cover - legacy, deprecated
    from usmsb_sdk.products.super_individual import (
        ButlerAgent,
        ButlerConfig,
        EveningSummary,
        MorningBriefing,
        UserMemory,
    )
except Exception:  # noqa: BLE001
    UserMemory = MorningBriefing = EveningSummary = ButlerAgent = ButlerConfig = None  # type: ignore

try:  # pragma: no cover - legacy, deprecated
    from usmsb_sdk.products.team import (
        AllocationResult,
        Decision,
        Department,
        TaskAllocation,
        TeamContext,
        TeamLeader,
        TeamMember,
        TeamMemory,
        TeamTask,
        WeeklyGoal,
        WeeklyPlan,
        WeeklyPlanning,
    )
except Exception:  # noqa: BLE001
    TeamLeader = TeamMember = TeamTask = Department = TaskAllocation = None  # type: ignore
    AllocationResult = TeamMemory = TeamContext = Decision = None  # type: ignore
    WeeklyPlanning = WeeklyGoal = WeeklyPlan = None  # type: ignore

__all__ = [
    # v3.0 supported
    "ButlerPea",
    "ButlerProfile",
    "TeamLeaderPea",
    "LLMTaskDecomposer",
    # legacy super individual (deprecated)
    "UserMemory",
    "MorningBriefing",
    "EveningSummary",
    "ButlerAgent",
    "ButlerConfig",
    # legacy team (deprecated)
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
