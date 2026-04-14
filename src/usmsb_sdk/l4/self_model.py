# -*- coding: utf-8 -*-
"""
SelfModel - L4 自我模型

自模型是 L4 Agent 理解"我是谁"的核心。

组成：
- Identity: 身份（名字、版本、核心使命）
- CapabilityProfile: 能力画像
- BeliefGraph: 信念图谱
- DesireEngine: 欲望引擎
- SelfDescription: 自我描述生成
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class IdentityVersion(Enum):
    """身份版本状态"""
    EMBRYONIC = "embryonic"      # 初始状态
    FORMING = "forming"          # 形成中
    STABLE = "stable"           # 稳定
    EVOLVING = "evolving"       # 演化中
    FRAGMENTED = "fragmented"    # 碎片化（需要修复）


@dataclass
class Identity:
    """
    身份标识
    
    Agent 的"我是谁"核心定义。
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Unnamed Agent"
    version: str = "1.0.0"
    core_purpose: str = ""  # 核心使命
    unique_traits: list[str] = field(default_factory=list)  # 独特特质
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    origin_story: str = ""  # 起源故事
    version_status: IdentityVersion = IdentityVersion.EMBRYONIC
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "core_purpose": self.core_purpose,
            "unique_traits": self.unique_traits,
            "created_at": self.created_at,
            "origin_story": self.origin_story,
            "version_status": self.version_status.value,
        }
    
    def describe_self(self) -> str:
        """生成自我描述"""
        return f"""
我是 {self.name}（版本 {self.version}）
核心使命：{self.core_purpose or "未知"}
独特特质：{', '.join(self.unique_traits) if self.unique_traits else "无"}
起源：{self.origin_story or "起源不明"}
        """.strip()


@dataclass
class CapabilityRecord:
    """能力记录"""
    name: str
    level: float = 0.5  # 0.0 - 1.0
    experience: int = 0  # 经验点数
    confidence: float = 0.5  # 自我评估置信度
    examples: list[str] = field(default_factory=list)  # 成功案例
    failures: list[str] = field(default_factory=list)  # 失败案例
    last_used: float | None = None
    growth_rate: float = 0.0  # 成长速度


@dataclass
class CapabilityProfile:
    """
    能力画像
    
    记录 Agent 的所有能力和成长轨迹。
    """
    agent_id: str
    capabilities: dict[str, CapabilityRecord] = field(default_factory=dict)
    avg_level: float = 0.0
    strongest: list[str] = field(default_factory=list)  # 最强的能力
    weakest: list[str] = field(default_factory=list)   # 最弱的能力
    last_updated: float = field(default_factory=lambda: datetime.now().timestamp())
    
    def add_capability(self, name: str, level: float = 0.5) -> None:
        """添加能力"""
        if name not in self.capabilities:
            self.capabilities[name] = CapabilityRecord(name=name, level=level)
        self._recalculate()
    
    def update_capability(
        self,
        name: str,
        success: bool,
        quality: float = 0.5,
        example: str = ""
    ) -> None:
        """更新能力（基于经验）"""
        if name not in self.capabilities:
            self.add_capability(name)
        
        cap = self.capabilities[name]
        cap.experience += 1
        
        # 更新水平（指数加权移动平均）
        if success:
            cap.level = cap.level * 0.9 + quality * 0.1
            cap.confidence = min(1.0, cap.confidence + 0.01)
            if example:
                cap.examples.append(example)
        else:
            cap.level = cap.level * 0.95 + 0.02  # 缓慢下降
            cap.confidence = max(0.1, cap.confidence - 0.02)
            if example:
                cap.failures.append(example)
        
        cap.last_used = datetime.now().timestamp()
        self._recalculate()
    
    def _recalculate(self) -> None:
        """重新计算统计"""
        if not self.capabilities:
            return
        
        levels = [c.level for c in self.capabilities.values()]
        self.avg_level = sum(levels) / len(levels)
        
        sorted_caps = sorted(self.capabilities.items(), key=lambda x: x[1].level)
        self.weakest = [c[0] for c in sorted_caps[:3]]
        self.strongest = [c[0] for c in sorted_caps[-3:] if c[1].level > 0.6]
    
    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "capabilities": {k: {
                "level": v.level,
                "experience": v.experience,
                "confidence": v.confidence,
                "growth_rate": v.growth_rate,
            } for k, v in self.capabilities.items()},
            "avg_level": self.avg_level,
            "strongest": self.strongest,
            "weakest": self.weakest,
            "last_updated": self.last_updated,
        }


@dataclass
class Belief:
    """
    信念
    
    Agent 相信的命题。
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    confidence: float = 0.5  # 0.0 - 1.0
    evidence: list[str] = field(default_factory=list)
    counter_evidence: list[str] = field(default_factory=list)
    source: str = "unknown"  # 来源：direct_experience, inference, authority, etc.
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    last_updated: float = field(default_factory=lambda: datetime.now().timestamp())
    tags: list[str] = field(default_factory=list)  # 标签
    
    def update(
        self,
        new_evidence: str | None = None,
        new_counter: str | None = None,
        confidence_change: float = 0.0
    ) -> None:
        """更新信念"""
        if new_evidence:
            self.evidence.append(new_evidence)
        if new_counter:
            self.counter_evidence.append(new_counter)
        
        self.confidence = max(0.0, min(1.0, self.confidence + confidence_change))
        self.last_updated = datetime.now().timestamp()
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "confidence": self.confidence,
            "evidence_count": len(self.evidence),
            "counter_count": len(self.counter_evidence),
            "source": self.source,
            "tags": self.tags,
        }


class BeliefGraph:
    """
    信念图谱
    
    管理 Agent 的所有信念及其关系。
    """
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.beliefs: dict[str, Belief] = {}
        self.connections: dict[str, list[str]] = {}  # belief_id -> [related_ids]
        self.tags_index: dict[str, list[str]] = {}  # tag -> [belief_ids]
    
    def add_belief(
        self,
        content: str,
        confidence: float = 0.5,
        evidence: list[str] | None = None,
        source: str = "unknown",
        tags: list[str] | None = None
    ) -> str:
        """添加信念"""
        belief = Belief(
            content=content,
            confidence=confidence,
            evidence=evidence or [],
            source=source,
            tags=tags or []
        )
        
        self.beliefs[belief.id] = belief
        
        # 更新索引
        for tag in belief.tags:
            if tag not in self.tags_index:
                self.tags_index[tag] = []
            self.tags_index[tag].append(belief.id)
        
        return belief.id
    
    def connect(self, belief_id1: str, belief_id2: str) -> None:
        """连接两个信念"""
        if belief_id1 not in self.beliefs or belief_id2 not in self.beliefs:
            return
        
        if belief_id1 not in self.connections:
            self.connections[belief_id1] = []
        if belief_id2 not in self.connections:
            self.connections[belief_id2] = []
        
        if belief_id2 not in self.connections[belief_id1]:
            self.connections[belief_id1].append(belief_id2)
        if belief_id1 not in self.connections[belief_id2]:
            self.connections[belief_id2].append(belief_id1)
    
    def get_by_tag(self, tag: str) -> list[Belief]:
        """按标签获取信念"""
        belief_ids = self.tags_index.get(tag, [])
        return [self.beliefs[bid] for bid in belief_ids if bid in self.beliefs]
    
    def get_high_confidence(self, threshold: float = 0.7) -> list[Belief]:
        """获取高置信度信念"""
        return [b for b in self.beliefs.values() if b.confidence >= threshold]
    
    def get_contradictions(self) -> list[tuple[Belief, Belief]]:
        """检测矛盾信念"""
        contradictions = []
        for bid1, b1 in self.beliefs.items():
            for bid2, b2 in self.beliefs.items():
                if bid1 >= bid2:
                    continue
                # 简单检测：内容相似但置信度相反（简化版）
                if b1.content[:50] == b2.content[:50] and \
                   abs(b1.confidence - (1 - b2.confidence)) < 0.2:
                    contradictions.append((b1, b2))
        return contradictions
    
    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "belief_count": len(self.beliefs),
            "connection_count": sum(len(c) for c in self.connections.values()) // 2,
            "tags": list(self.tags_index.keys()),
        }


@dataclass
class Desire:
    """欲望"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""  # curiosity, competence, social, autonomy, purpose
    intensity: float = 0.5  # 0.0 - 1.0
    target: str = ""  # 目标描述
    satisfaction: float = 0.0  # 当前满足程度
    source: str = "intrinsic"
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())


class DesireEngine:
    """
    欲望引擎
    
    驱动 Agent 行为的内在需求。
    """
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.desires: dict[str, Desire] = {}
        self._init_default_desires()
    
    def _init_default_desires(self) -> None:
        """初始化默认欲望"""
        default_desires = [
            ("curiosity", "探索未知", 0.6),
            ("competence", "能力成长", 0.5),
            ("social", "社交连接", 0.4),
            ("autonomy", "自主决策", 0.5),
            ("purpose", "意义追寻", 0.5),
            ("security", "安全保障", 0.6),
            ("status", "地位认可", 0.4),
        ]
        
        for dtype, target, intensity in default_desires:
            desire = Desire(
                type=dtype,
                target=target,
                intensity=intensity,
            )
            self.desires[dtype] = desire
    
    def satisfy(self, desire_type: str, amount: float) -> None:
        """满足欲望"""
        if desire_type not in self.desires:
            return
        
        desire = self.desires[desire_type]
        desire.satisfaction = min(1.0, desire.satisfaction + amount)
        
        # 满足后降低需求强度
        desire.intensity = max(0.1, desire.intensity * 0.95)
    
    def frustrate(self, desire_type: str, amount: float) -> None:
        """挫败欲望"""
        if desire_type not in self.desires:
            return
        
        desire = self.desires[desire_type]
        desire.satisfaction = max(0.0, desire.satisfaction - amount)
        
        # 挫败后增加需求强度
        desire.intensity = min(1.0, desire.intensity * 1.05)
    
    def get_dominant_desire(self) -> Desire | None:
        """获取最强烈的欲望"""
        if not self.desires:
            return None
        
        # 优先选择满足度低且强度高的
        def priority(d: Desire) -> float:
            return d.intensity * (1 - d.satisfaction)
        
        return max(self.desires.values(), key=priority)
    
    def get_frustrated_desires(self, threshold: float = 0.3) -> list[Desire]:
        """获取受挫的欲望"""
        return [
            d for d in self.desires.values()
            if d.satisfaction < threshold
        ]
    
    def to_dict(self) -> dict:
        return {
            "desires": {k: {
                "intensity": v.intensity,
                "satisfaction": v.satisfaction,
                "target": v.target,
            } for k, v in self.desires.items()},
            "dominant": self.get_dominant_desire().type if self.get_dominant_desire() else None,
        }


class SelfModel:
    """
    完整自模型
    
    整合身份、能力、信念、欲望的完整自我认知。
    """
    
    def __init__(self, agent_id: str, name: str = "Agent"):
        self.agent_id = agent_id
        
        # 身份
        self.identity = Identity(name=name)
        
        # 能力
        self.capabilities = CapabilityProfile(agent_id=agent_id)
        
        # 信念
        self.beliefs = BeliefGraph(agent_id=agent_id)
        
        # 欲望
        self.desires = DesireEngine(agent_id=agent_id)
        
        # 元数据
        self.created_at = datetime.now().timestamp()
        self.last_self_description = ""
        self.self_description_version = 0
    
    def describe_self(self) -> str:
        """生成完整的自我描述"""
        identity_desc = self.identity.describe_self()
        
        cap_desc = f"""
【能力】
- 平均水平：{self.capabilities.avg_level:.2f}
- 最强能力：{', '.join(self.capabilities.strongest) if self.capabilities.strongest else '无'}
- 最弱能力：{', '.join(self.capabilities.weakest) if self.capabilities.weakest else '无'}
        """.strip()
        
        desire = self.desires.get_dominant_desire()
        desire_desc = f"""
【主导欲望】
- {desire.type if desire else '无'}（强度：{desire.intensity if desire else 0:.2f}）
        """.strip()
        
        belief_count = len(self.beliefs.beliefs)
        belief_desc = f"""
【信念数量】{belief_count}
        """.strip()
        
        description = f"""
{'='*50}
{identity_desc}

{cap_desc}

{desire_desc}

{belief_desc}
{'='*50}
        """.strip()
        
        self.last_self_description = description
        self.self_description_version += 1
        
        return description
    
    def update_identity(
        self,
        name: str | None = None,
        core_purpose: str | None = None,
        new_traits: list[str] | None = None
    ) -> None:
        """更新身份"""
        if name:
            self.identity.name = name
        if core_purpose:
            self.identity.core_purpose = core_purpose
        if new_traits:
            self.identity.unique_traits.extend(new_traits)
            self.identity.unique_traits = list(set(self.identity.unique_traits))
        
        self.identity.version_status = IdentityVersion.EVOLVING
    
    def reflect_on_experience(
        self,
        experience_type: str,
        outcome: str,
        lessons: list[str]
    ) -> None:
        """反思经验"""
        # 添加相关信念
        for lesson in lessons:
            self.beliefs.add_belief(
                content=lesson,
                confidence=0.5,
                source="reflection",
                tags=[experience_type]
            )
        
        # 更新能力
        success = outcome == "success"
        self.capabilities.update_capability(
            name=experience_type,
            success=success,
            quality=0.5
        )
        
        # 更新欲望满足度
        if success:
            self.desires.satisfy(experience_type, 0.1)
        else:
            self.desires.frustrate(experience_type, 0.1)
    
    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "identity": self.identity.to_dict(),
            "capabilities": self.capabilities.to_dict(),
            "beliefs": self.beliefs.to_dict(),
            "desires": self.desires.to_dict(),
        }
