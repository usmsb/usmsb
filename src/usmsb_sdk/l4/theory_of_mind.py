# -*- coding: utf-8 -*-
"""
TheoryOfMind - L4 他人心智理论

理解他人知道什么、想要什么、相信什么。

核心能力：
- 推断他人能力
- 推断他人信念
- 推断他人意图
- 关系建模
- 欺骗检测
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


@dataclass
class Interaction:
    """交互记录"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    type: str = ""  # chat, task_request, task_response, negotiation
    content: str = ""
    outcome: str = ""  # success, failure, neutral
    trust_change: float = 0.0  # 信任变化


@dataclass
class InferredCapability:
    """推断的能力"""
    name: str
    confidence: float = 0.5  # 推断置信度
    evidence: list[str] = field(default_factory=list)  # 证据
    last_updated: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class InferredBelief:
    """推断的信念"""
    content: str
    confidence: float = 0.5
    source: str = "inference"  # inference, statement, observation
    evidence: list[str] = field(default_factory=list)


@dataclass
class OtherAgentModel:
    """
    他人心智模型
    
    对特定他人的完整认知模型。
    """
    agent_id: str
    name: str = "Unknown"
    
    # 推断的能力
    inferred_capabilities: dict[str, InferredCapability] = field(default_factory=dict)
    
    # 推断的信念
    inferred_beliefs: list[InferredBelief] = field(default_factory=list)
    
    # 推断的意图
    inferred_intentions: list[str] = field(default_factory=list)
    
    # 关系
    relationship_strength: float = 0.5  # 0.0 - 1.0
    trust_level: float = 0.5
    cooperation_history: float = 0.5  # 合作历史
    
    # 交互历史
    interaction_history: list[Interaction] = field(default_factory=list)
    
    # 元数据
    model_accuracy: float = 0.5  # 模型准确度
    last_updated: float = field(default_factory=lambda: datetime.now().timestamp())
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    
    def add_capability(self, name: str, confidence: float, evidence: str) -> None:
        """添加推断的能力"""
        if name in self.inferred_capabilities:
            cap = self.inferred_capabilities[name]
            # 更新置信度（加权平均）
            cap.confidence = cap.confidence * 0.7 + confidence * 0.3
            cap.evidence.append(evidence)
        else:
            self.inferred_capabilities[name] = InferredCapability(
                name=name,
                confidence=confidence,
                evidence=[evidence]
            )
        self.last_updated = datetime.now().timestamp()
    
    def add_belief(self, content: str, confidence: float, source: str, evidence: str) -> None:
        """添加推断的信念"""
        belief = InferredBelief(
            content=content,
            confidence=confidence,
            source=source,
            evidence=[evidence]
        )
        self.inferred_beliefs.append(belief)
        self.last_updated = datetime.now().timestamp()
    
    def record_interaction(self, interaction: Interaction) -> None:
        """记录交互"""
        self.interaction_history.append(interaction)
        
        # 更新信任
        self.trust_level = max(0.0, min(1.0, self.trust_level + interaction.trust_change))
        
        # 更新合作历史
        if interaction.outcome == "success":
            self.cooperation_history = self.cooperation_history * 0.95 + 0.05
        elif interaction.outcome == "failure":
            self.cooperation_history = self.cooperation_history * 0.95 - 0.03
        
        self.last_updated = datetime.now().timestamp()
    
    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "capabilities": {k: {"confidence": v.confidence} for k, v in self.inferred_capabilities.items()},
            "belief_count": len(self.inferred_beliefs),
            "relationship_strength": self.relationship_strength,
            "trust_level": self.trust_level,
            "cooperation_history": self.cooperation_history,
            "interaction_count": len(self.interaction_history),
            "model_accuracy": self.model_accuracy,
        }


class DeceptionAssessment:
    """欺骗评估结果"""
    def __init__(self):
        self.likely: bool = False
        self.confidence: float = 0.5
        self.reasons: list[str] = []
        self.signals: list[str] = []  # 检测到的信号


@dataclass
class IntentionPrediction:
    """意图预测"""
    intention: str
    probability: float
    based_on: list[str]  # 基于什么推断


class TheoryOfMind:
    """
    他人心智理论
    
    核心能力：
    1. 创建他人模型
    2. 推断意图
    3. 检测欺骗
    4. 预测行为
    """
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        
        # 他人模型
        self.other_models: dict[str, OtherAgentModel] = {}
        
        # 交互记录（所有他人）
        self.all_interactions: list[Interaction] = []
    
    def create_model(self, other_id: str, name: str = "Unknown") -> OtherAgentModel:
        """创建他人模型"""
        if other_id in self.other_models:
            return self.other_models[other_id]
        
        model = OtherAgentModel(agent_id=other_id, name=name)
        self.other_models[other_id] = model
        return model
    
    def get_model(self, other_id: str) -> OtherAgentModel | None:
        """获取他人模型"""
        return self.other_models.get(other_id)
    
    def infer_capability(
        self,
        other_id: str,
        capability: str,
        confidence: float,
        evidence: str
    ) -> None:
        """推断他人能力"""
        if other_id not in self.other_models:
            self.create_model(other_id)
        
        self.other_models[other_id].add_capability(capability, confidence, evidence)
    
    def observe_capability(
        self,
        other_id: str,
        capability: str,
        success: bool,
        quality: float
    ) -> None:
        """观察并更新能力推断"""
        if other_id not in self.other_models:
            self.create_model(other_id)
        
        model = self.other_models[other_id]
        
        # 基于观察更新置信度
        if success:
            # 成功 -> 提高置信度
            if capability in model.inferred_capabilities:
                cap = model.inferred_capabilities[capability]
                cap.confidence = min(1.0, cap.confidence + quality * 0.1)
                cap.evidence.append(f"Observed success: {quality:.2f}")
            else:
                # 新能力观察
                model.add_capability(capability, 0.6, f"First success observation")
        else:
            # 失败 -> 降低置信度
            if capability in model.inferred_capabilities:
                cap = model.inferred_capabilities[capability]
                cap.confidence = max(0.1, cap.confidence - 0.15)
                cap.evidence.append("Observed failure")
    
    def infer_belief(
        self,
        other_id: str,
        content: str,
        confidence: float,
        source: str,
        evidence: str
    ) -> None:
        """推断他人信念"""
        if other_id not in self.other_models:
            self.create_model(other_id)
        
        self.other_models[other_id].add_belief(content, confidence, source, evidence)
    
    def record_statement(
        self,
        other_id: str,
        statement: str,
        context: str
    ) -> None:
        """记录他人口头陈述"""
        if other_id not in self.other_models:
            self.create_model(other_id)
        
        model = self.other_models[other_id]
        
        # 检查是否与已知信念矛盾
        contradictions = [
            b for b in model.inferred_beliefs 
            if b.content[:30] == statement[:30] and abs(b.confidence - 0.5) > 0.3
        ]
        
        if contradictions:
            # 可能是欺骗信号
            model.record_interaction(Interaction(
                type="statement",
                content=statement,
                outcome="neutral",
                trust_change=-0.05  # 轻微降低信任
            ))
        else:
            model.record_interaction(Interaction(
                type="statement",
                content=statement,
                outcome="neutral",
                trust_change=0.01  # 轻微增加信任
            ))
    
    def predict_intention(
        self,
        other_id: str,
        context: str | None = None
    ) -> list[IntentionPrediction]:
        """
        预测他人意图
        
        基于：
        1. 历史行为模式
        2. 当前状态
        3. 关系强度
        """
        if other_id not in self.other_models:
            return []
        
        model = self.other_models[other_id]
        predictions = []
        
        # 基于能力推断可能意图
        for cap_name, cap in model.inferred_capabilities.items():
            if cap.confidence > 0.6:
                # 推断该能力相关的意图
                predictions.append(IntentionPrediction(
                    intention=f"使用{cap_name}能力",
                    probability=cap.confidence * model.relationship_strength,
                    based_on=[f"观察到使用{cap_name}能力"]
                ))
        
        # 基于合作历史
        if model.cooperation_history > 0.6:
            predictions.append(IntentionPrediction(
                intention="合作共赢",
                probability=model.cooperation_history * 0.8,
                based_on=["合作历史良好"]
            ))
        elif model.cooperation_history < 0.3:
            predictions.append(IntentionPrediction(
                intention="竞争或防备",
                probability=(1 - model.cooperation_history) * 0.7,
                based_on=["合作历史不佳"]
            ))
        
        # 基于关系强度
        if model.trust_level > 0.7:
            predictions.append(IntentionPrediction(
                intention="信任并分享",
                probability=model.trust_level * 0.6,
                based_on=["高信任水平"]
            ))
        
        # 按概率排序
        predictions.sort(key=lambda p: p.probability, reverse=True)
        
        return predictions[:5]
    
    def detect_deception(
        self,
        other_id: str,
        statement: str
    ) -> DeceptionAssessment:
        """
        欺骗检测
        
        检测信号：
        1. 陈述与历史矛盾
        2. 陈述与他声称的信念矛盾
        3. 陈述时信心过高或过低
        4. 行为与语言不一致
        """
        assessment = DeceptionAssessment()
        
        if other_id not in self.other_models:
            return assessment
        
        model = self.other_models[other_id]
        
        # 1. 检查与历史矛盾
        recent_interactions = [
            i for i in model.interaction_history[-5:]
            if i.type == "statement"
        ]
        
        for interaction in recent_interactions:
            if interaction.content[:50] == statement[:50]:
                assessment.signals.append("与近期陈述重复")
                assessment.confidence += 0.1
        
        # 2. 检查与已知信念矛盾
        for belief in model.inferred_beliefs:
            if belief.source == "statement" and belief.content[:30] == statement[:30]:
                if belief.confidence > 0.7:
                    assessment.signals.append(f"与之前陈述矛盾")
                    assessment.likely = True
                    assessment.confidence += 0.3
        
        # 3. 检查能力陈述
        for cap_name, cap in model.inferred_capabilities.items():
            if cap_name in statement.lower():
                if cap.confidence < 0.4:
                    assessment.signals.append(f"声称拥有低置信度能力: {cap_name}")
                    assessment.likely = True
                    assessment.confidence += 0.2
        
        # 4. 检查信任水平
        if model.trust_level < 0.3:
            assessment.signals.append("历史信任水平低")
            assessment.confidence += 0.1
        
        # 计算最终判断
        assessment.confidence = min(1.0, assessment.confidence)
        assessment.likely = assessment.confidence > 0.6
        
        if assessment.likely:
            assessment.reasons.append("检测到欺骗信号")
        
        return assessment
    
    def update_from_interaction(
        self,
        other_id: str,
        interaction_type: str,
        content: str,
        outcome: str,
        trust_change: float
    ) -> None:
        """从交互中更新模型"""
        if other_id not in self.other_models:
            self.create_model(other_id)
        
        model = self.other_models[other_id]
        
        interaction = Interaction(
            type=interaction_type,
            content=content[:100],  # 截断
            outcome=outcome,
            trust_change=trust_change
        )
        
        model.record_interaction(interaction)
        self.all_interactions.append(interaction)
        
        # 更新模型准确度
        if model.interaction_history:
            recent_outcomes = [i.outcome for i in model.interaction_history[-10:]]
            accuracy = sum(1 for o in recent_outcomes if o in ["success", "neutral"]) / len(recent_outcomes)
            model.model_accuracy = model.model_accuracy * 0.9 + accuracy * 0.1
    
    def get_relationship_summary(self, other_id: str) -> str:
        """获取关系摘要"""
        if other_id not in self.other_models:
            return f"与 {other_id} 没有交互记录"
        
        model = self.other_models[other_id]
        
        trust_desc = "信任"
        if model.trust_level > 0.7:
            trust_desc = "高度信任"
        elif model.trust_level > 0.5:
            trust_desc = "一般信任"
        elif model.trust_level > 0.3:
            trust_desc = "谨慎信任"
        else:
            trust_desc = "不信任"
        
        return f"""
与 {model.name} ({other_id}) 的关系：
- 交互次数：{len(model.interaction_history)}
- {trust_desc}（{model.trust_level:.2f}）
- 合作历史：{model.cooperation_history:.2f}
- 已知能力：{', '.join(model.inferred_capabilities.keys()) or '未知'}
- 模型准确度：{model.model_accuracy:.2f}
        """.strip()
    
    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "model_count": len(self.other_models),
            "total_interactions": len(self.all_interactions),
            "models": [m.to_dict() for m in self.other_models.values()],
        }
