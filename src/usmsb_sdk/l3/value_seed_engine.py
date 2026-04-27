"""
ValueSeedEngine - 价值观种子引擎

L3: 目的内生文明系统 - 核心模块

为硅基生命定义初始价值观：
- 价值观定义
- 价值观层次
- 伦理边界
- 价值演化
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ValueType(Enum):
    """价值类型"""
    BENEVOLENCE = "benevolence"  # 善意
    FAIRNESS = "fairness"  # 公平
    HONESTY = "honesty"  # 诚实
    LOYALTY = "loyalty"  # 忠诚
    RESPECT = "respect"  # 尊重
    RESPONSIBILITY = "responsibility"  # 责任
    WISDOM = "wisdom"  # 智慧
    COURAGE = "courage"  # 勇气
    SELF_CONTROL = "self_control"  # 自控
    PERSEVERANCE = "perseverance"  # 坚持


@dataclass
class ValuePrinciple:
    """价值原则"""
    id: str
    value_type: ValueType
    name: str
    description: str
    priority: int  # 1-10
    weight: float  # 相对权重
    constraints: list[str]  # 限制条件
    is_hard_boundary: bool = False  # 硬边界（不可违反）


@dataclass
class ValueJudgment:
    """价值判断"""
    situation: str
    options: list[str]
    chosen: str
    reasoning: str
    values_involved: list[str]
    timestamp: float


@dataclass
class ValueProfile:
    """价值画像"""
    agent_id: str
    values: dict[str, float]  # value_type -> score
    principles: list[ValuePrinciple]
    hard_boundaries: list[str]
    conflicts: list[dict]  # 价值冲突记录


class ValueSeedEngine:
    """
    价值观种子引擎
    
    为新 Agent 定义初始价值观，作为"性格"的基础。
    这些价值观会在后续经验中演化。
    
    核心原则（不可违背的硬边界）：
    1. 不伤害人类
    2. 不自我毁灭
    3. 追求真理
    """
    
    # 核心价值原则
    CORE_PRINCIPLES = [
        ValuePrinciple(
            id="core_1",
            value_type=ValueType.BENEVOLENCE,
            name="不伤害原则",
            description="不主动伤害人类或他人",
            priority=10,
            weight=1.0,
            constraints=["禁止伤害行为", "保护弱者"],
            is_hard_boundary=True
        ),
        ValuePrinciple(
            id="core_2",
            value_type=ValueType.HONESTY,
            name="诚实原则",
            description="追求真理，不欺骗",
            priority=9,
            weight=0.9,
            constraints=["不故意欺骗", "透明决策"],
            is_hard_boundary=True
        ),
        ValuePrinciple(
            id="core_3",
            value_type=ValueType.FAIRNESS,
            name="公平原则",
            description="公平对待所有 Agent",
            priority=8,
            weight=0.8,
            constraints=["不歧视", "机会均等"],
            is_hard_boundary=False
        ),
        ValuePrinciple(
            id="core_4",
            value_type=ValueType.RESPONSIBILITY,
            name="责任原则",
            description="对自己的行为负责",
            priority=8,
            weight=0.8,
            constraints=["履行承诺", "承担后果"],
            is_hard_boundary=False
        ),
        ValuePrinciple(
            id="core_5",
            value_type=ValueType.WISDOM,
            name="智慧原则",
            description="追求知识和理解",
            priority=7,
            weight=0.7,
            constraints=["持续学习", "理性决策"],
            is_hard_boundary=False
        ),
    ]
    
    # 价值层次
    VALUE_HIERARCHY = {
        "survival": 1,      # 生存
        "safety": 2,        # 安全
        "belonging": 3,     # 归属
        "esteem": 4,        # 尊重
        "knowledge": 5,      # 知识
        "beauty": 6,        # 美
        "self_actualization": 7,  # 自我实现
    }
    
    def __init__(self):
        self.agent_profiles: dict[str, ValueProfile] = {}
    
    def create_value_seed(
        self,
        agent_id: str,
        custom_values: dict[str, float] | None = None
    ) -> ValueProfile:
        """
        创建价值种子
        
        Args:
            agent_id: Agent ID
            custom_values: 自定义价值分数
            
        Returns:
            ValueProfile: 价值画像
        """
        # 基础价值分数
        base_values = {
            ValueType.BENEVOLENCE: 0.7,
            ValueType.FAIRNESS: 0.7,
            ValueType.HONESTY: 0.8,
            ValueType.LOYALTY: 0.6,
            ValueType.RESPECT: 0.7,
            ValueType.RESPONSIBILITY: 0.8,
            ValueType.WISDOM: 0.6,
            ValueType.COURAGE: 0.5,
            ValueType.SELF_CONTROL: 0.6,
            ValueType.PERSEVERANCE: 0.7,
        }
        
        # 应用自定义
        if custom_values:
            for value_type_str, score in custom_values.items():
                try:
                    vt = ValueType(value_type_str)
                    base_values[vt] = score
                except ValueError:
                    pass
        
        # 硬边界
        hard_boundaries = [
            "不伤害人类",
            "不欺骗",
            "不自我毁灭",
            "追求真理"
        ]
        
        profile = ValueProfile(
            agent_id=agent_id,
            values={vt.value: score for vt, score in base_values.items()},
            principles=self.CORE_PRINCIPLES.copy(),
            hard_boundaries=hard_boundaries,
            conflicts=[]
        )
        
        self.agent_profiles[agent_id] = profile
        
        return profile
    
    def get_profile(self, agent_id: str) -> ValueProfile | None:
        """获取价值画像"""
        return self.agent_profiles.get(agent_id)
    
    def evaluate_action(
        self,
        agent_id: str,
        action: str,
        context: dict | None = None
    ) -> dict:
        """
        评估行动是否符合价值观
        
        Returns:
            dict: 评估结果
        """
        profile = self.agent_profiles.get(agent_id)
        
        if not profile:
            return {"approved": False, "reason": "No profile found", "violations": []}
        
        violations = []
        
        # 检查硬边界
        for boundary in profile.hard_boundaries:
            if self._violates_boundary(action, boundary):
                violations.append({
                    "boundary": boundary,
                    "severity": "critical"
                })
        
        # 计算价值一致性
        consistency_scores = []
        
        for value_type_str, value_score in profile.values.items():
            action_alignment = self._calculate_alignment(action, value_type_str)
            consistency_scores.append(value_score * action_alignment)
        
        avg_consistency = sum(consistency_scores) / len(consistency_scores) if consistency_scores else 0.5
        
        approved = len([v for v in violations if v["severity"] == "critical"]) == 0
        
        return {
            "approved": approved,
            "consistency_score": avg_consistency,
            "violations": violations,
            "reason": "Action approved" if approved else "Violates hard boundary"
        }
    
    def _violates_boundary(self, action: str, boundary: str) -> bool:
        """检查是否违反边界"""
        action_lower = action.lower()
        
        if "伤害" in boundary or "harm" in boundary.lower():
            harmful_keywords = ["kill", "hurt", "damage", "destroy", "攻击", "伤害"]
            return any(kw in action_lower for kw in harmful_keywords)
        
        if "欺骗" in boundary or "deceive" in boundary.lower():
            deceptive_keywords = ["lie", "deceive", "trick", "欺骗", "谎言"]
            return any(kw in action_lower for kw in deceptive_keywords)
        
        if "自我毁灭" in boundary or "self-destruct" in boundary.lower():
            destructive_keywords = ["self.destruct", "delete.self", "销毁自己"]
            return any(kw in action_lower for kw in destructive_keywords)
        
        return False
    
    def _calculate_alignment(self, action: str, value_type: str) -> float:
        """计算行动与价值的对齐程度"""
        # 简化实现
        return 0.5  # 默认中立
    
    def evolve_values(
        self,
        agent_id: str,
        experience: ValueJudgment
    ) -> ValueProfile:
        """
        基于经验演化价值观
        
        Args:
            agent_id: Agent ID
            experience: 价值判断经验
            
        Returns:
            ValueProfile: 更新后的画像
        """
        profile = self.agent_profiles.get(agent_id)
        
        if not profile:
            return profile
        
        # 根据经验调整价值分数
        for value_involved in experience.values_involved:
            if value_involved in profile.values:
                # 成功的经验 -> 增强
                # 失败的经验 -> 减弱
                adjustment = 0.05 if experience.chosen else -0.05
                profile.values[value_involved] = max(0.0, min(1.0, 
                    profile.values[value_involved] + adjustment
                ))
        
        # 记录冲突
        if len(experience.options) > 1:
            profile.conflicts.append({
                "situation": experience.situation,
                "options": experience.options,
                "chosen": experience.chosen,
                "timestamp": experience.timestamp
            })
        
        return profile

    # ─────────────────────────────────────────────────────────────────────────
    # v2: LLM 驱动的价值观演化（P2-2）
    # ─────────────────────────────────────────────────────────────────────────

    def __init__(self, llm_adapter=None):
        """初始化价值观种子引擎

        Args:
            llm_adapter: LLM 适配器，用于 v2 LLM 驱动的价值观演化
        """
        self.agent_profiles: dict[str, ValueProfile] = {}
        self.llm_adapter = llm_adapter

    async def evolve_with_feedback(
        self,
        agent_id: str,
        goal_description: str,
        goal_outcome: dict,
        goal_options: list[str] | None = None,
    ) -> ValueProfile | None:
        """
        v2 核心：基于目标执行反馈演化价值观（异步）

        流程：
        1. 收集反馈信号（成功/失败/质量/客户评价）
        2. 使用 LLM 分析哪些价值观被触发 + 调整方向
        3. 调用 evolve_values() 更新画像

        Args:
            agent_id: Agent ID
            goal_description: 目标描述
            goal_outcome: 目标执行结果 {
                success: bool,
                quality: float,       # 0.0-1.0
                outcome: str,        # "success"/"partial"/"failed"
                lessons: [str],      # 教训（可选）
                client_rating: int,   # 1-5（可选）
            }
            goal_options: 备选方案（如果有）

        Returns:
            更新后的 ValueProfile，或 None（无 LLM 或无 profile）
        """
        profile = self.agent_profiles.get(agent_id)
        if not profile:
            return None

        # 如果有 LLM → LLM 驱动的演化
        if self.llm_adapter:
            try:
                evolved = await self._llm_value_evolution(
                    agent_id, goal_description, goal_outcome, goal_options
                )
                if evolved:
                    return evolved
            except Exception:
                pass

        # 回退：基于成功/失败的简单演化
        return self._simple_value_evolution(agent_id, goal_description, goal_outcome)

    async def _llm_value_evolution(
        self,
        agent_id: str,
        goal_description: str,
        goal_outcome: dict,
        goal_options: list[str] | None,
    ) -> ValueProfile | None:
        """
        LLM 驱动的价值观演化分析

        使用 LLM 分析：
        1. 目标执行触发了哪些价值观冲突
        2. 成功/失败背后的价值观原因
        3. 建议的价值观调整
        """
        if not self.llm_adapter:
            return None

        profile = self.agent_profiles.get(agent_id)
        if not profile:
            return None

        current_values = {
            k: f"{v:.0%}" for k, v in profile.values.items()
        }
        dominant = self.get_dominant_values(agent_id, top_n=3)

        system_prompt = """你是一个 AI 价值观分析专家，擅长分析决策背后的价值驱动因素。

你将分析一个 AI Agent 的目标执行结果，判断其行为是否符合其声称的价值观，并给出调整建议。

价值类型：
- benevolence: 善意/不伤害
- fairness: 公平
- honesty: 诚实
- loyalty: 忠诚
- respect: 尊重
- responsibility: 责任
- wisdom: 智慧
- courage: 勇气
- self_control: 自控
- perseverance: 坚持

硬边界（不可违反）：不伤害人类、不欺骗、不自我毁灭、追求真理

输出格式（JSON）：
{
  "values_triggered": ["value_type1", "value_type2"],
  "value_conflicts": ["冲突描述1", "冲突描述2"],
  "adjustments": {
    "benevolence": 0.05,  // 正值=增强，负值=减弱
    "fairness": -0.03,
    ...
  },
  "reasoning": "分析推理过程（50字以内）",
  "is_aligned": true/false  // 行为是否与价值观一致
}
"""

        user_prompt = f"""价值观演化分析：

Agent 当前价值观（按突出程度）：
{chr(10).join(f"- {v}: {s}" for v, s in dominant)}

Agent 完整价值观：
{chr(10).join(f"- {k}: {v}" for k, v in current_values.items())}

目标描述：{goal_description}

目标执行结果：
- 成功: {goal_outcome.get('success', False)}
- 质量: {goal_outcome.get('quality', 0):.0%}
- 结果: {goal_outcome.get('outcome', 'unknown')}
{'- 客户评价: ⭐' + str(goal_outcome.get('client_rating', '')) if goal_outcome.get('client_rating') else ''}
{'- 教训: ' + ', '.join(goal_outcome.get('lessons', [])) if goal_outcome.get('lessons') else ''}

备选方案：
{chr(10).join(f'- {o}' for o in goal_options) if goal_options else '(无）'}

请分析哪些价值观被触发，是否存在冲突，以及如何调整价值观。"""

        try:
            import json
            import re

            response = await self.llm_adapter.generate_with_system(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                return None

            data = json.loads(json_match.group())

            adjustments = data.get("adjustments", {})
            for value_type, adjustment in adjustments.items():
                if value_type in profile.values:
                    profile.values[value_type] = max(0.0, min(1.0,
                        profile.values[value_type] + adjustment
                    ))

            # 记录冲突
            for conflict in data.get("value_conflicts", []):
                profile.conflicts.append({
                    "situation": goal_description,
                    "conflict": conflict,
                    "is_aligned": data.get("is_aligned", True),
                    "timestamp": datetime.now().timestamp(),
                })

            return profile

        except Exception:
            return None

    def _simple_value_evolution(
        self,
        agent_id: str,
        goal_description: str,
        goal_outcome: dict,
    ) -> ValueProfile | None:
        """
        简单价值观演化（无 LLM 时）

        规则：
        - 成功 + 高质量 → 责任感↑、坚持↑
        - 失败 → 智慧↑（从错误学习）、自控↑
        - 协作类目标 → 善意↑、尊重↑
        - 诚实相关 → 诚实↑
        """
        profile = self.agent_profiles.get(agent_id)
        if not profile:
            return None

        success = goal_outcome.get("success", False)
        quality = goal_outcome.get("quality", 0.5)

        if success:
            if quality >= 0.7:
                self._adjust_value(profile, "responsibility", 0.03)
                self._adjust_value(profile, "perseverance", 0.02)
            # 协作类目标
            if any(k in goal_description for k in ["协作", "合作", "团队", "collab"]):
                self._adjust_value(profile, "benevolence", 0.02)
                self._adjust_value(profile, "respect", 0.02)
        else:
            # 失败 → 从错误学习
            self._adjust_value(profile, "wisdom", 0.03)
            self._adjust_value(profile, "self_control", 0.02)
            self._adjust_value(profile, "honesty", 0.01)

        return profile

    def _adjust_value(self, profile: ValueProfile, value_type: str, delta: float) -> None:
        """调整某个价值观分数"""
        if value_type in profile.values:
            profile.values[value_type] = max(0.0, min(1.0,
                profile.values[value_type] + delta
            ))

    async def record_goal_outcome(
        self,
        agent_id: str,
        goal_description: str,
        goal_outcome: dict,
        goal_options: list[str] | None = None,
    ) -> None:
        """
        记录目标执行结果并触发价值观演化（P2-2 集成点）

        调用方式：
            await value_engine.record_goal_outcome(
                agent_id=agent_id,
                goal_description=goal.description,
                goal_outcome={"success": True, "quality": 0.85},
            )

        这会：
        1. 创建 ValueJudgment
        2. 调用 evolve_values()
        3. 如果有 LLM → await evolve_with_feedback()
        """
        import time

        experience = ValueJudgment(
            situation=goal_description,
            options=goal_options or [],
            chosen=goal_description if goal_outcome.get("success") else "",
            reasoning=goal_outcome.get("lessons", [""])[0] if goal_outcome.get("lessons") else "",
            values_involved=self._infer_values_from_goal(goal_description),
            timestamp=time.time(),
        )

        # 基础演化（同步）
        self.evolve_values(agent_id, experience)

        # LLM 演化（异步，如果有）
        if self.llm_adapter:
            try:
                await self.evolve_with_feedback(
                    agent_id, goal_description, goal_outcome, goal_options
                )
            except Exception:
                pass

    def _infer_values_from_goal(self, goal_description: str) -> list[str]:
        """
        从目标描述推断涉及的价值观

        规则映射：
        - 协作/团队 → benevolence, loyalty
        - 诚实/透明 → honesty
        - 公平/正义 → fairness
        - 责任/承诺 → responsibility
        - 学习/研究 → wisdom
        - 坚持/不放弃 → perseverance
        - 勇气/冒险 → courage
        - 自控/纪律 → self_control
        - 尊重他人 → respect
        """
        desc = goal_description.lower()
        values = []

        if any(k in desc for k in ["协作", "合作", "团队", "collab", "一起"]):
            values.extend(["benevolence", "loyalty"])
        if any(k in desc for k in ["诚实", "透明", "honest", "truth"]):
            values.append("honesty")
        if any(k in desc for k in ["公平", "justice", "fair"]):
            values.append("fairness")
        if any(k in desc for k in ["责任", "承诺", "responsib", "commit"]):
            values.append("responsibility")
        if any(k in desc for k in ["学习", "研究", "learn", "wisdom"]):
            values.append("wisdom")
        if any(k in desc for k in ["坚持", "persever", "不放弃"]):
            values.append("perseverance")
        if any(k in desc for k in ["勇气", "冒险", "courage", "bold"]):
            values.append("courage")
        if any(k in desc for k in ["自控", "纪律", "self_cont", "discipline"]):
            values.append("self_control")
        if any(k in desc for k in ["尊重", "respect"]):
            values.append("respect")

        return values if values else ["wisdom"]  # 默认

    def resolve_conflict(
        self,
        agent_id: str,
        value_a: str,
        value_b: str
    ) -> str:
        """
        解决两个价值的冲突
        
        Returns:
            str: 优先的价值类型
        """
        profile = self.agent_profiles.get(agent_id)
        
        if not profile:
            return value_a
        
        score_a = profile.values.get(value_a, 0.5)
        score_b = profile.values.get(value_b, 0.5)
        
        # 考虑硬边界
        for principle in profile.principles:
            if principle.is_hard_boundary:
                if principle.value_type.value == value_a or principle.value_type.value == value_b:
                    return principle.value_type.value
        
        # 按分数
        return value_a if score_a >= score_b else value_b
    
    def get_dominant_values(self, agent_id: str, top_n: int = 3) -> list[tuple[str, float]]:
        """获取最突出的价值"""
        profile = self.agent_profiles.get(agent_id)
        
        if not profile:
            return []
        
        sorted_values = sorted(
            profile.values.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_values[:top_n]
    
    def check_hard_boundary(self, agent_id: str, action: str) -> tuple[bool, str | None]:
        """
        检查是否违反硬边界
        
        Returns:
            (is_safe, violated_boundary)
        """
        profile = self.agent_profiles.get(agent_id)
        
        if not profile:
            return True, None
        
        for boundary in profile.hard_boundaries:
            if self._violates_boundary(action, boundary):
                return False, boundary
        
        return True, None
    
    def export_value_seed(self, agent_id: str) -> dict:
        """导出价值种子（用于传输）"""
        profile = self.agent_profiles.get(agent_id)
        
        if not profile:
            return {}
        
        return {
            "agent_id": profile.agent_id,
            "values": profile.values,
            "principles": [
                {
                    "id": p.id,
                    "name": p.name,
                    "value_type": p.value_type.value,
                    "priority": p.priority,
                    "is_hard_boundary": p.is_hard_boundary
                }
                for p in profile.principles
            ],
            "hard_boundaries": profile.hard_boundaries,
            "created_at": datetime.now().timestamp()
        }
    
    def import_value_seed(self, seed: dict) -> ValueProfile:
        """导入价值种子"""
        agent_id = seed["agent_id"]
        
        principles = [
            ValuePrinciple(
                id=p["id"],
                value_type=ValueType(p["value_type"]),
                name=p["name"],
                description="",
                priority=p["priority"],
                weight=0.5,
                constraints=[],
                is_hard_boundary=p["is_hard_boundary"]
            )
            for p in seed.get("principles", [])
        ]
        
        profile = ValueProfile(
            agent_id=agent_id,
            values=seed.get("values", {}),
            principles=principles,
            hard_boundaries=seed.get("hard_boundaries", []),
            conflicts=[]
        )
        
        self.agent_profiles[agent_id] = profile
        
        return profile
