"""
SkillRouter - Skill 调用路由

将 Skill 调用路由到内部实现或 SDK 实现，
集成 StrategyRouter 的经验库，实现自我进化。
"""

import json
import logging
import os
import random
import sqlite3
import time
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Any

from ...l2.agent import L2Agent
from ...l3.purpose_generator import PurposeGenerator
from ...l4.l4_agent import L4Agent
from ...l5.l5_collective import L5Collective
from ...meta_agent.goals.engine import GoalEngine
from ..loaders.loader import create_skill_loader
from ..types import SkillCall, SkillInstance, SkillTier

logger = logging.getLogger(__name__)


# 策略选择的 LLM Prompt
SKILL_STRATEGY_PROMPT = """
任务类型：{task_type}
Skill tier：{tier}
输入长度：{input_len} 字符
历史 internal 质量：{internal_quality:.2f}
历史 sdk 质量：{sdk_quality:.2f}

判断应该使用哪种策略：
- internal: 使用 MetaAgent 内部已有实现
- sdk: 使用 SDK 的标准 L2/L3/L4/L5 实现
- both: 两者都运行，评估后选最优

决策规则：
- L2: 优先 sdk
- L3: 如果历史 internal 质量 > sdk 质量 + 0.1，选 internal；否则 sdk
- L4: 优先 sdk
- L5: 优先 sdk

返回 JSON：{{"strategy": "internal|sdk|both", "reasoning": "..."}}
"""


class StrategyExperienceDB:
    """策略经验数据库（与 StrategyRouter 共用同一 DB）"""

    def __init__(self, db_path: str = "data/strategy_experience.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS skill_strategy_experience (
                id TEXT PRIMARY KEY,
                skill_id TEXT NOT NULL,
                tier TEXT NOT NULL,
                scenario TEXT NOT NULL,
                strategy TEXT NOT NULL,
                quality_score REAL NOT NULL,
                execution_time REAL NOT NULL,
                selected INTEGER NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_skill_tier
            ON skill_strategy_experience(skill_id, tier)
        """)
        conn.commit()
        conn.close()

    def record(self, skill_id: str, tier: str, scenario: str,
               strategy: str, quality_score: float,
               execution_time: float, selected: bool):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO skill_strategy_experience VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            str(uuid.uuid4()), skill_id, tier, scenario, strategy,
            quality_score, execution_time, int(selected), datetime.now().isoformat()
        ])
        conn.commit()
        conn.close()

    def get_avg_quality(self, skill_id: str, tier: str, strategy: str) -> float:
        conn = sqlite3.connect(self.db_path)
        row = conn.execute("""
            SELECT AVG(quality_score), COUNT(*) FROM skill_strategy_experience
            WHERE skill_id = ? AND tier = ? AND strategy = ?
        """, [skill_id, tier, strategy]).fetchone()
        conn.close()
        if row and row[1] >= 3:
            return row[0] or 0.5
        return 0.5  # 数据不足时默认中立


class SkillRouter:
    """
    Skill 路由层。

    职责：
    1. 根据 Skill tier 选择加载器
    2. 查询历史经验，选择最优策略
    3. 执行调用
    4. 记录经验到 DB
    """

    def __init__(self, registry=None, experience_db_path: str = "data/strategy_experience.db"):
        self.registry = registry
        self._loaders: dict[str, Any] = {}
        self._experience_db = StrategyExperienceDB(experience_db_path)

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

        skill_id = instance.metadata.skill_id
        tier = instance.metadata.tier.value

        try:
            # Step 1: 获取或创建 loader
            loader = self._loaders.get(skill_id)
            if loader is None:
                loader = create_skill_loader(instance.metadata)
                await loader.load(instance.config)
                self._loaders[skill_id] = loader

            # Step 2: 基于历史经验选择策略
            strategy = self._choose_strategy(skill_id, tier, input_data)
            strategy_used = strategy

            # Step 3: 执行
            internal_out = None
            sdk_out = None

            if strategy == "internal" and loader.supports_internal():
                internal_out = await loader.call(input_data)
                output_data = internal_out
            elif strategy == "sdk" and loader.supports_sdk():
                sdk_out = await loader.call(input_data)
                output_data = sdk_out
            elif strategy == "both":
                # 并行执行
                if loader.supports_internal():
                    try:
                        internal_out = await loader.call(input_data)
                    except NotImplementedError:
                        internal_out = None
                if loader.supports_sdk():
                    sdk_out = await loader.call(input_data)

                # 评估选优
                if internal_out and sdk_out:
                    winner, quality = self._evaluate_results(internal_out, sdk_out)
                    output_data = winner
                    strategy_used = winner
                    quality_score = quality
                elif sdk_out:
                    output_data = sdk_out
                    strategy_used = "sdk"
                elif internal_out:
                    output_data = internal_out
                    strategy_used = "internal"
                else:
                    raise RuntimeError("No strategy available")
            else:
                # Fallback
                if loader.supports_sdk():
                    output_data = await loader.call(input_data)
                    strategy_used = "sdk"
                elif loader.supports_internal():
                    output_data = await loader.call(input_data)
                    strategy_used = "internal"

            if not quality_score:
                quality_score = self._score_result(output_data)

            elapsed = time.time() - start_time

        except Exception as e:
            elapsed = time.time() - start_time
            error = str(e)
            logger.error(f"[SkillRouter] Skill call failed: {e}")
            quality_score = 0.0

        # Step 4: 记录经验
        scenario = self._classify_scenario(input_data)
        self._experience_db.record(
            skill_id=skill_id,
            tier=tier,
            scenario=scenario,
            strategy=strategy_used,
            quality_score=quality_score,
            execution_time=elapsed,
            selected=True,
        )

        # Step 5: 更新 registry
        if self.registry and quality_score > 0:
            self.registry.update_last_used(skill_id, quality_score)

        return SkillCall(
            call_id=call_id,
            skill_id=skill_id,
            agent_id=agent_id,
            input_data=input_data,
            output_data=output_data,
            error=error,
            quality_score=quality_score,
            strategy_used=strategy_used,
            execution_time=elapsed,
        )

    def _choose_strategy(self, skill_id: str, tier: str, input_data: dict) -> str:
        """
        基于历史经验选择策略。
        """
        internal_quality = self._experience_db.get_avg_quality(skill_id, tier, "internal")
        sdk_quality = self._experience_db.get_avg_quality(skill_id, tier, "sdk")

        task_text = str(input_data)[:100]

        if tier == "l2":
            return "sdk"
        elif tier == "l3":
            # L3: 参考历史质量
            if internal_quality > sdk_quality + 0.1:
                return "internal"
            elif sdk_quality > internal_quality + 0.1:
                return "sdk"
            else:
                # 随机探索 5%
                return "internal" if random.random() < 0.05 else "sdk"
        elif tier == "l4":
            return "sdk"
        elif tier == "l5":
            return "sdk"
        return "sdk"

    def _classify_scenario(self, input_data: dict) -> str:
        """简单场景分类"""
        text = str(input_data).lower()
        if any(k in text for k in ["goal", "purpose", "target", "目标", "计划"]):
            return "PLAN"
        elif any(k in text for k in ["reflect", "feel", "emotion", "反思", "情感"]):
            return "COG"
        elif any(k in text for k in ["collaborate", "team", "多个", "协作"]):
            return "COLLAB"
        return "INFO"

    def _evaluate_results(self, a: Any, b: Any) -> tuple[str, float]:
        """评估两个结果，选更优"""
        sa = self._score_result(a)
        sb = self._score_result(b)
        if sa > sb:
            return "internal", sa
        elif sb > sa:
            return "sdk", sb
        return "sdk", sb

    def _score_result(self, result: Any) -> float:
        """简单质量评分"""
        if result is None:
            return 0.0
        if isinstance(result, dict):
            if result.get("error"):
                return 0.1
            return 0.7
        if isinstance(result, str):
            return 0.6 if len(result) > 20 else 0.3
        return 0.5
