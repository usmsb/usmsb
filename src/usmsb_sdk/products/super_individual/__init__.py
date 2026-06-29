# -*- coding: utf-8 -*-
"""超级个体产品。

v3.0：ButlerPea（基于 v3.0 harness 的大管家 PEA）是受支持的实现。
旧 ButlerAgent / MorningBriefing / EveningSummary 为早期 stub（且 butler 导入链已断裂），
此处安全导入（坏了不连累整个包），保留仅为向后兼容，标记 deprecated。
"""

from usmsb_sdk.products.super_individual.butler_pea import ButlerPea, ButlerProfile

# 旧 stub 安全导入：butler.ButlerAgent 依赖断裂的 l3_orchestrator → 失败时降级为 None
try:  # pragma: no cover - legacy, deprecated
    from usmsb_sdk.products.super_individual.user_memory import UserMemory
    from usmsb_sdk.products.super_individual.morning_briefing import MorningBriefing
    from usmsb_sdk.products.super_individual.evening_summary import EveningSummary
    from usmsb_sdk.products.super_individual.butler import ButlerAgent, ButlerConfig
except Exception:  # noqa: BLE001
    UserMemory = MorningBriefing = EveningSummary = ButlerAgent = ButlerConfig = None  # type: ignore

__all__ = [
    "ButlerPea",
    "ButlerProfile",
    # legacy (deprecated)
    "UserMemory",
    "MorningBriefing",
    "EveningSummary",
    "ButlerAgent",
    "ButlerConfig",
]
