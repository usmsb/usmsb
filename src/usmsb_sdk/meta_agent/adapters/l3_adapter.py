"""
L3 IL3Component Adapter

将 SDK 的 PurposeGenerator + IntrinsicMotivationEngine
适配为 IL3Component 接口，同时支持 internal/sdk 双轨。
"""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MotivationSignal:
    """内在动机信号"""
    needs: list[Any]
    dominant: str | None
    intensity: float  # 0.0-1.0


@dataclass
class Goal:
    """目标对象（适配 IL3 接口）"""
    id: str
    name: str
    description: str = ""
    priority: int = 50
    status: str = "pending"
    metadata: dict = field(default_factory=dict)


class L3Adapter:
    """
    IL3 接口适配器。

    策略模式：
    - sdk: 使用 PurposeGenerator + IntrinsicMotivationEngine
    - internal: 使用内建启发式逻辑（当前 goals/engine.py）

    所有外部调用统一走 IL3 接口，内部自动选择策略。
    """

    def __init__(
        self,
        agent_id: str = "meta_agent",
        llm_client=None,
        internal_goals_engine=None,
    ):
        self.agent_id = agent_id
        self._llm = llm_client

        # SDK 实现（L3）
        try:
            from ...l3.purpose_generator import PurposeGenerator as SDKPurposeGenerator
            from ...l3.intrinsic_motivation import IntrinsicMotivationEngine as SDKIntrinsicMotivation

            self._sdk_purpose = SDKPurposeGenerator(
                agent_id=agent_id,
                llm_client=llm_client,
            )
            self._sdk_motivation = SDKIntrinsicMotivation()
            self._has_sdk = True
        except ImportError as e:
            logger.warning(f"[L3Adapter] SDK not available: {e}, using internal only")
            self._has_sdk = False
            self._sdk_purpose = None
            self._sdk_motivation = None

        # 内部实现
        self._internal_engine = internal_goals_engine

        # 策略质量统计（供 StrategyRouter 参考）
        self._sdk_quality: list[float] = []
        self._internal_quality: list[float] = []

    # ─────────────────────────────────────────────────────────
    # IL3Component 接口
    # ─────────────────────────────────────────────────────────

    async def generate_goal(self, context: dict = None) -> Goal:
        """
        生成目标。

        优先用 SDK（L3 PurposeGenerator），
        fallback 到 internal 引擎。
        """
        context = context or {}

        if self._has_sdk:
            try:
                purpose = self._sdk_purpose.generate_purpose()
                if purpose:
                    goal = self._sdk_purpose.purpose_to_goal(purpose)
                    if isinstance(goal, Goal):
                        return goal
                    # 手动转换
                    return Goal(
                        id=goal.id,
                        name=goal.name,
                        description=getattr(goal, 'description', goal.name),
                        priority=50,
                        status="pending",
                        metadata={"motivation": purpose.motivation},
                    )
            except Exception as e:
                logger.warning(f"[L3Adapter] SDK generate_goal failed: {e}")

        # Fallback: internal
        return await self._internal_generate_goal(context)

    async def _internal_generate_goal(self, context: dict) -> Goal:
        """internal 策略生成目标（启发式）"""
        import uuid
        import random

        fallback_goals = [
            "探索新能力领域",
            "提升协作效率",
            "优化任务执行",
            "学习先进技术",
            "增强问题解决能力",
        ]
        selected = random.choice(fallback_goals)
        return Goal(
            id=str(uuid.uuid4())[:16],
            name=f"[内部] {selected}",
            description=selected,
            priority=30,
            status="pending",
            metadata={"strategy": "internal"},
        )

    async def evaluate_outcome(self, goal: Goal, result: Any) -> float:
        """
        评估目标执行结果（0.0-1.0）。

        LLM 驱动的质量评估。
        """
        if result is None:
            return 0.0

        if isinstance(result, dict):
            if result.get("error"):
                score = 0.1
            elif result.get("success"):
                score = 0.9
            else:
                score = 0.6
        elif isinstance(result, str):
            score = 0.7 if len(result) > 20 else 0.3
        else:
            score = 0.5

        # 记录质量
        self._sdk_quality.append(score)
        if len(self._sdk_quality) > 50:
            self._sdk_quality = self._sdk_quality[-50:]

        return score

    async def detect_intrinsic_motivation(self, state: dict = None) -> MotivationSignal:
        """
        检测内在动机。

        使用 SDK 的 IntrinsicMotivationEngine。
        """
        state = state or {}

        if self._has_sdk and self._sdk_motivation:
            try:
                needs = self._sdk_motivation.generate_needs(state)
                dominant = self._sdk_motivation.get_dominant_motivation()
                intensity = (
                    self._sdk_motivation.get_motivation_state(dominant or "curiosity")
                    if dominant
                    else 0.5
                )
                return MotivationSignal(
                    needs=needs,
                    dominant=dominant,
                    intensity=intensity,
                )
            except Exception as e:
                logger.warning(f"[L3Adapter] SDK detect_intrinsic_motivation failed: {e}")

        # Fallback: 默认动机
        return MotivationSignal(
            needs=[],
            dominant="curiosity",
            intensity=0.5,
        )

    # ─────────────────────────────────────────────────────────
    # 策略信息（供 StrategyRouter 查询）
    # ─────────────────────────────────────────────────────────

    def get_strategy_quality(self, strategy: str) -> float:
        """获取某策略的平均质量分"""
        if strategy == "sdk":
            if not self._sdk_quality:
                return 0.6  # 默认中立
            return sum(self._sdk_quality) / len(self._sdk_quality)
        elif strategy == "internal":
            if not self._internal_quality:
                return 0.5
            return sum(self._internal_quality) / len(self._internal_quality)
        return 0.5

    def supports_sdk(self) -> bool:
        return self._has_sdk

    def supports_internal(self) -> bool:
        return self._internal_engine is not None
