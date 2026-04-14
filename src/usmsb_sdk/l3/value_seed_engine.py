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
