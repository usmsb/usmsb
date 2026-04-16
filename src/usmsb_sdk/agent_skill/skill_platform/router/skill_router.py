"""
SkillRouter - Skill 调用路由

将 Skill 调用路由到内部实现或 SDK 实现，
集成 StrategyRouter 的 LLM 智能路由能力。
"""

import logging
import time
import uuid
from typing import Any

from ...l2.agent import L2Agent
from ...l3.purpose_generator import PurposeGenerator
from ...l4.l4_agent import L4Agent
from ...l5.l5_collective import L5Collective
from ...meta_agent.goals.engine import GoalEngine
from ..loaders.loader import create_skill_loader
from ..types import SkillCall, SkillInstance, SkillTier

logger = logging.getLogger(__name__)


# LLM 驱动的策略选择（内联，不依赖 StrategyRouter 避免循环导入）
SKILL_STRATEGY_PROMPT = """
任务类型：{task_type}
Skill tier：{tier}
输入长度：{input_len} 字符

判断应该使用哪种策略：
- internal: 使用 MetaAgent 内部已有实现（goals/engine 等）
- sdk: 使用 SDK 的标准 L2/L3/L4/L5 实现
- both: 两者都运行，LLM 评估后选最优

策略选择规则：
- L2: 优先 sdk（工具调用标准化）
- L3: 优先 both（目标生成质量差异大）
- L4: 优先 sdk（自我意识能力 SDK 更完整）
- L5: 优先 sdk（L5 目前无内部实现）

返回 JSON：{{"strategy": "internal|sdk|both", "reasoning": "..."}}
"""


async def _llm_choose_strategy(tier: SkillTier, task_text: str) -> str:
    """LLM 判断使用哪个策略（轻量版，不依赖外部 LLMManager）"""
    # 简化实现：基于规则 + 随机探索
    # 后续接入 MetaAgent 的 LLMManager 做真正的 LLM 判断
    import random

    if tier == SkillTier.L2:
        return "sdk"
    elif tier == SkillTier.L3:
        # 3% 概率探索 internal（让它积累经验）
        return "internal" if random.random() < 0.03 else "sdk"
    elif tier == SkillTier.L4:
        return "sdk"
    elif tier == SkillTier.L5:
        return "sdk"
    return "sdk"


async def _llm_evaluate_call(
    internal_result: Any, sdk_result: Any, task_text: str
) -> tuple[str, float]:
    """
    LLM 评估两个策略的结果，选择更优的。
    返回 (winner_strategy, quality_score)
    """
    # 简化实现：基于结果质量 heuristics
    # 后续接入 MetaAgent 的 LLMManager

    def score_result(r):
        if r is None:
            return 0.0
        if isinstance(r, dict):
            if "error" in r:
                return 0.1
            return 0.7
        if isinstance(r, str):
            if len(r) < 10:
                return 0.3
            return 0.6
        return 0.5

    s_internal = score_result(internal_result)
    s_sdk = score_result(sdk_result)

    if s_internal > s_sdk + 0.1:
        return "internal", s_internal
    elif s_sdk > s_internal + 0.1:
        return "sdk", s_sdk
    else:
        # 平局，随机选
        return ("sdk", s_sdk) if s_sdk >= s_internal else ("internal", s_internal)


class SkillRouter:
    """
    Skill 路由层。

    职责：
    1. 根据 Skill tier 选择加载器
    2. LLM 判断使用 internal / sdk / both
    3. 执行调用
    4. LLM 评估结果
    5. 记录经验
    """

    def __init__(self, registry=None):
        self.registry = registry
        self._loaders: dict[str, Any] = {}  # skill_id -> loader

    async def call_skill(
        self,
        instance: SkillInstance,
        input_data: dict,
        agent_id: str = "system",
    ) -> SkillCall:
        """
        调用 Skill，自动路由到最优策略。
        """
        call_id = str(uuid.uuid4())
        start_time = time.time()
        strategy_used = ""
        output_data = None
        error = None
        quality_score = 0.0

        try:
            # Step 1: 获取或创建 loader
            loader = self._loaders.get(instance.metadata.skill_id)
            if loader is None:
                loader = create_skill_loader(instance.metadata)
                await loader.load(instance.config)
                self._loaders[instance.metadata.skill_id] = loader

            # Step 2: LLM 选择策略
            task_text = str(input_data)[:200]
            strategy = await _llm_choose_strategy(
                instance.metadata.tier, task_text
            )
            strategy_used = strategy

            # Step 3: 执行
            if strategy == "internal" and loader.supports_internal():
                output_data = await loader.call(input_data)
            elif strategy == "sdk" and loader.supports_sdk():
                output_data = await loader.call(input_data)
            elif strategy == "both":
                # 并行执行，内部优先
                internal_out = None
                sdk_out = None
                if loader.supports_internal():
                    try:
                        internal_out = await loader.call(input_data)
                    except NotImplementedError:
                        internal_out = None
                if loader.supports_sdk():
                    sdk_out = await loader.call(input_data)

                # LLM 评估
                if internal_out and sdk_out:
                    winner, quality_score = await _llm_evaluate_call(
                        internal_out, sdk_out, task_text
                    )
                    output_data = internal_out if winner == "internal" else sdk_out
                    strategy_used = winner
                elif sdk_out:
                    output_data = sdk_out
                    strategy_used = "sdk"
                elif internal_out:
                    output_data = internal_out
                    strategy_used = "internal"
                else:
                    raise RuntimeError("No strategy available")
            else:
                # fallback 到 SDK
                output_data = await loader.call(input_data)
                strategy_used = "sdk"

            elapsed = time.time() - start_time
            quality_score = quality_score or 0.5

        except Exception as e:
            elapsed = time.time() - start_time
            error = str(e)
            logger.error(f"[SkillRouter] Skill call failed: {e}")
            quality_score = 0.0

        call_record = SkillCall(
            call_id=call_id,
            skill_id=instance.metadata.skill_id,
            agent_id=agent_id,
            input_data=input_data,
            output_data=output_data,
            error=error,
            quality_score=quality_score,
            strategy_used=strategy_used,
            execution_time=elapsed,
        )

        # 更新 registry 中的使用记录
        if self.registry and call_record.quality_score > 0:
            self.registry.update_last_used(
                instance.metadata.skill_id, call_record.quality_score
            )

        return call_record
