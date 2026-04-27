# -*- coding: utf-8 -*-
"""
L4 Self-Conscious Agent - 自我意识 Agent

L4 = L3 + 自模型 + 元认知 + 他人心智 + 情感架构

核心突破：
1. 知道自己是谁（SelfModel）
2. 知道自己在想什么（Metacognition）
3. 知道他人怎么想（TheoryOfMind）
4. 有情绪反应（EmotionalArchitecture）
"""

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from usmsb_sdk.l4.self_model import (
    SelfModel, Identity, CapabilityProfile, BeliefGraph, DesireEngine,
    IdentityVersion
)
from usmsb_sdk.l4.metacognition import (
    Metacognition, ReasoningTrace, ReasoningQuality
)
from usmsb_sdk.l4.theory_of_mind import (
    TheoryOfMind, OtherAgentModel, DeceptionAssessment
)
from usmsb_sdk.l4.emotional_architecture import (
    EmotionalArchitecture, Emotion, EmotionType, MoodState
)


@dataclass
class SelfReflection:
    """
    自我反思结果
    """
    identity_description: str
    current_intention: str
    alignment_score: float
    metacognitive_insight: str
    emotional_state: str
    lessons: list[str]
    recommendations: list[str]
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


class L4SelfConsciousAgent:
    """
    L4 自我意识 Agent
    
    继承 L3 的所有能力，加上：
    - SelfModel: 完整的自我认知
    - Metacognition: 元认知（思考自己在想什么）
    - TheoryOfMind: 他人心智（理解他人）
    - EmotionalArchitecture: 情感架构（有情绪）
    
    使用方式：
    ```python
    agent = L4SelfConsciousAgent(
        agent_id="agent_001",
        name="Athena"
    )
    
    # 自我反思
    reflection = await agent.self_reflect()
    
    # 元认知思考
    thought = agent.metacognize("我应该如何解决这个问题？")
    
    # 理解他人
    model = agent.model_other("agent_002")
    ```
    """
    
    def __init__(
        self,
        agent_id: str,
        name: str = "L4 Agent",
        core_purpose: str = "",
        parent_id: str | None = None,
    ):
        self.agent_id = agent_id
        self.id = agent_id  # 别名
        
        # ========== L4 核心组件 ==========
        
        # 1. 自模型
        self.self_model = SelfModel(agent_id=agent_id, name=name)
        if core_purpose:
            self.self_model.identity.core_purpose = core_purpose
        
        # 2. 元认知
        self.metacognition = Metacognition(agent_id=agent_id)
        
        # 3. 他人心智
        self.theory_of_mind = TheoryOfMind(agent_id=agent_id)
        
        # 4. 情感架构
        self.emotions = EmotionalArchitecture(agent_id=agent_id)
        
        # ========== 继承 L3 能力的占位符 ==========
        # 实际使用时，这些会连接到 L3Orchestrator
        self._l3_capabilities: dict = {}
        
        # ========== 元数据 ==========
        self.parent_id = parent_id
        self.created_at = datetime.now().timestamp()
        self.last_reflection = 0.0
        self.reflection_count = 0
        
        # L4 状态
        self.is_self_aware = True  # 自我意识开关
        
        print(f"[L4Agent] {name} ({agent_id}) initialized with full self-awareness")
    
    # ========== 自我反思 ==========
    
    async def self_reflect(self) -> SelfReflection:
        """
        完整自我反思
        
        L4 的核心能力：定期反思"我是谁，我在做什么"
        """
        self.reflection_count += 1
        self.last_reflection = datetime.now().timestamp()
        
        # 1. 自我描述
        identity_desc = self.self_model.describe_self()
        
        # 2. 当前意图
        desire = self.self_model.desires.get_dominant_desire()
        current_intention = desire.target if desire else "无明确目标"
        
        # 3. 对齐评估（简版）
        alignment_score = 0.8  # TODO: 接入 L3 的 ValueSeedEngine
        
        # 4. 元认知洞察
        metacog_insight = self.metacognition.think_about_thinking()
        
        # 5. 情绪状态
        emotional_state = self.emotions.express_emotion()
        
        # 6. 提取教训
        lessons = self._extract_lessons()
        
        # 7. 建议
        recommendations = self._generate_recommendations()
        
        # 生成反思报告
        reflection = SelfReflection(
            identity_description=identity_desc,
            current_intention=current_intention,
            alignment_score=alignment_score,
            metacognitive_insight=metacog_insight,
            emotional_state=emotional_state,
            lessons=lessons,
            recommendations=recommendations,
        )
        
        return reflection
    
    def _extract_lessons(self) -> list[str]:
        """从历史中提取教训"""
        lessons = []
        
        # 从元认知历史提取
        if self.metacognition.reasoning_history:
            recent_traces = self.metacognition.reasoning_history[-5:]
            
            for trace in recent_traces:
                if trace.quality_grade == ReasoningQuality.FAILED:
                    lessons.append(f"推理失败：{trace.goal[:50]}...")
                elif trace.quality_grade == ReasoningQuality.POOR:
                    lessons.append(f"推理质量差：{trace.conclusion[:50]}...")
        
        # 从情绪历史提取
        recent_emotions = self.emotions.emotion_history[-10:]
        negative = [e for e in recent_emotions 
                   if e.type in [EmotionType.SADNESS, EmotionType.ANGER, EmotionType.FEAR]]
        
        if len(negative) > 3:
            lessons.append(f"近期负面情绪较多，可能需要调整策略")
        
        return lessons
    
    def _generate_recommendations(self) -> list[str]:
        """生成建议"""
        recommendations = []
        
        # 基于能力短板
        if self.self_model.capabilities.weakest:
            weakest = self.self_model.capabilities.weakest[0]
            recommendations.append(f"建议提升{weakest}能力")
        
        # 基于元认知困惑
        if self.metacognition.detect_confusion():
            recommendations.append("检测到思维困惑，建议换一种思考方式")
        
        # 基于情绪状态
        if self.emotions.mood.valence < 0.4:
            recommendations.append("情绪偏消极，建议寻找积极反馈")
        
        # 基于欲望满足度
        frustrated = self.self_model.desires.get_frustrated_desires()
        if frustrated:
            recommendations.append(f"未满足的欲望：{[d.type for d in frustrated]}")
        
        return recommendations
    
    # ========== 元认知 ==========
    
    def think(self, thought: str, evidence: list[str] | None = None) -> None:
        """
        添加思考步骤
        
        这是"我正在想什么"的记录。
        """
        self.metacognition.think(thought, evidence)
    
    def think_about_thinking(self) -> str:
        """
        元认知：思考自己在想什么
        """
        return self.metacognition.think_about_thinking()
    
    def revise_previous_thought(self, reason: str, new_thought: str) -> None:
        """修订之前的思考"""
        self.metacognition.revise(reason, new_thought)
    
    def consider_alternatives(self, alternatives: list[str]) -> None:
        """考虑替代方案"""
        for alt in alternatives:
            self.metacognition.consider_alternative(alt)
    
    def finish_reasoning(self, conclusion: str) -> ReasoningTrace:
        """完成当前推理"""
        return self.metacognition.finish_reasoning(conclusion)
    
    def detect_confusion(self) -> bool:
        """检测是否困惑"""
        return self.metacognition.detect_confusion()
    
    def get_confusion_reason(self) -> str:
        """获取困惑原因"""
        return self.metacognition.get_confusion_reason()
    
    # ========== 他人心智 ==========
    
    def model_other(self, other_id: str) -> OtherAgentModel:
        """获取或创建他人模型"""
        return self.theory_of_mind.create_model(other_id)
    
    def update_other_capability(
        self,
        other_id: str,
        capability: str,
        success: bool,
        quality: float
    ) -> None:
        """更新对他人能力的推断"""
        self.theory_of_mind.observe_capability(other_id, capability, success, quality)
    
    def predict_other_intention(self, other_id: str) -> list:
        """预测他人意图"""
        return self.theory_of_mind.predict_intention(other_id)
    
    def detect_deception(self, other_id: str, statement: str) -> DeceptionAssessment:
        """检测他人是否在说谎"""
        return self.theory_of_mind.detect_deception(other_id, statement)
    
    def record_interaction(
        self,
        other_id: str,
        interaction_type: str,
        content: str,
        outcome: str
    ) -> None:
        """记录与他人的交互"""
        trust_change = 0.05 if outcome == "success" else -0.05
        self.theory_of_mind.update_from_interaction(
            other_id, interaction_type, content, outcome, trust_change
        )
    
    def get_relationship(self, other_id: str) -> str:
        """获取与他人关系摘要"""
        return self.theory_of_mind.get_relationship_summary(other_id)
    
    # ========== 情感 ==========
    
    def _feel_sync(self, event: dict) -> list[Emotion]:
        """
        对事件产生情绪反应（同步内部方法）
        
        event = {
            "type": "success",  # success, failure, threat, etc.
            "valence": 0.8,     # 0-1, 1=positive
            "intensity": 0.7,   # 0-1
            "description": "任务完成",
        }
        """
        emotions = self.emotions.react_to_event(event)
        
        # 如果有情绪，也更新相关能力
        for emotion in emotions:
            if emotion.type in [EmotionType.JOY, EmotionType.SADNESS]:
                # 从成功/失败中学习
                success = emotion.type == EmotionType.JOY
                self.self_model.capabilities.update_capability(
                    name="emotional_learning",
                    success=success,
                    quality=emotion.intensity
                )
        
        return emotions
    
    def express_feeling(self) -> str:
        """表达当前情绪"""
        return self.emotions.express_emotion()
    
    def get_emotional_state(self) -> str:
        """获取情绪状态描述"""
        return self.emotions.get_emotional_summary()
    
    # ========== 自模型更新 ==========
    
    def learn_from_experience(
        self,
        experience_type: str,
        outcome: str,
        lessons: list[str]
    ) -> None:
        """从经验中学习并更新自模型"""
        self.self_model.reflect_on_experience(experience_type, outcome, lessons)
    
    def update_identity(
        self,
        name: str | None = None,
        purpose: str | None = None,
        traits: list[str] | None = None
    ) -> None:
        """更新身份"""
        self.self_model.update_identity(name, purpose, traits)
    
    def add_belief(
        self,
        content: str,
        confidence: float,
        evidence: str,
        tags: list[str] | None = None
    ) -> str:
        """添加信念"""
        return self.self_model.beliefs.add_belief(
            content=content,
            confidence=confidence,
            evidence=[evidence] if evidence else [],
            tags=tags or []
        )
    
    # ========== 情绪行为引导 ==========
    
    def get_behavioral_guidance(self) -> dict:
        """
        获取当前情绪驱动的行为引导参数。
        
        供外部系统（L3目标生成、元认知策略等）调用：
        - 目标难度系数（difficulty_multiplier）
        - 推理策略（reasoning_strategy）
        - 协作调整（collaboration_adjustment）
        - 时间分配（time_allocation）
        """
        return self.emotions.get_behavioral_guidance()
    
    def get_emotional_state_summary(self) -> str:
        """获取情绪状态摘要"""
        return self.emotions.get_emotional_summary()
    
    # ========== 状态报告 ==========
    
    def get_full_status(self) -> dict:
        """获取完整状态"""
        return {
            "agent_id": self.agent_id,
            "identity": self.self_model.identity.to_dict(),
            "self_model": {
                "avg_capability": self.self_model.capabilities.avg_level,
                "belief_count": len(self.self_model.beliefs.beliefs),
                "dominant_desire": (
                    self.self_model.desires.get_dominant_desire().type
                    if self.self_model.desires.get_dominant_desire() else None
                ),
            },
            "metacognition": self.metacognition.get_metacognitive_report(),
            "theory_of_mind": {
                "others_modeled": len(self.theory_of_mind.other_models),
                "total_interactions": len(self.theory_of_mind.all_interactions),
            },
            "emotions": self.emotions.to_dict(),
            "behavioral_guidance": self.emotions.get_behavioral_guidance(),
            "reflection_count": self.reflection_count,
            "uptime": datetime.now().timestamp() - self.created_at,
        }
    
    def __repr__(self) -> str:
        return f"L4SelfConsciousAgent({self.self_model.identity.name}, id={self.agent_id})"

    # ─────────────────────────────────────────────────────────
    # IL4 接口实现（适配层）
    # ─────────────────────────────────────────────────────────

    @dataclass
    class MetacognitionResult:
        thought: str
        analysis: str
        confidence: float

    @dataclass
    class TheoryOfMindResult:
        other_agent_id: str
        inferred_intent: str
        confidence: float

    @dataclass
    class EmotionResponse:
        """IL4 情感响应（扩展版）"""
        primary_emotion: str
        intensity: float
        action_tendency: str          # 行为倾向名称
        tendency_confidence: float    # 置信度
        active_emotions: list[dict]  # 所有活跃情绪及其衰减强度
        mood_state: str              # 心境自然语言描述
        behavioral_guidance: dict    # 完整行为引导参数

    async def build_self_model(self, experience: list[dict]) -> SelfModel:
        """IL4: 根据经验构建/更新自模型"""
        for exp in experience:
            self.self_model.reflect_on_experience(
                exp.get('type', 'general'),
                exp.get('outcome', 'neutral'),
                exp.get('lessons', [])
            )
        return self.self_model

    async def metacognize(self, thought: str) -> MetacognitionResult:
        """IL4: 元认知"""
        analysis = self.think_about_thinking()
        return self.MetacognitionResult(
            thought=thought, analysis=analysis, confidence=0.7
        )

    async def infer_mind(self, other_agent_id: str, history: list[dict]) -> TheoryOfMindResult:
        """IL4: 他人心智推断"""
        predictions = self.theory_of_mind.predict_intention(other_agent_id)
        inferred = predictions[0] if predictions else '未知意图'
        return self.TheoryOfMindResult(
            other_agent_id=other_agent_id,
            inferred_intent=inferred,
            confidence=0.6 if predictions else 0.3,
        )

    async def feel(self, stimulus: dict) -> EmotionResponse:
        """
        IL4: 情感反应
        
        对刺激产生情绪反应，并返回完整的行为引导信息。
        情绪通过规则层立即映射为 ActionTendency（无递归）。
        """
        # 触发情绪反应（规则层）
        emotions = self._feel_sync(stimulus)
        
        # 获取当前行为倾向（规则层计算）
        tendency, confidence = self.emotions.get_action_tendency()
        
        # 获取完整行为引导
        guidance = self.emotions.get_behavioral_guidance()
        
        # 收集所有活跃情绪
        active = self.emotions.active_emotions
        active_emotions_data = []
        for e in active:
            eff = self.emotions._effective_intensity(e)
            active_emotions_data.append({
                "type": e.type.value,
                "effective_intensity": round(eff, 3),
                "original_intensity": e.intensity,
                "trigger": e.trigger[:50] if e.trigger else "",
                "elapsed_seconds": round(time.time() - e.timestamp, 1),
            })
        
        primary = emotions[0] if emotions else None
        if primary:
            emotion_type = getattr(primary.type, 'value', str(primary.type)) if hasattr(primary, 'type') else 'neutral'
            intensity = getattr(primary, 'intensity', 0.5)
            action = tendency.value
        else:
            emotion_type, intensity, action = 'neutral', 0.0, tendency.value
        
        return self.EmotionResponse(
            primary_emotion=emotion_type,
            intensity=intensity,
            action_tendency=action,
            tendency_confidence=round(confidence, 3),
            active_emotions=active_emotions_data,
            mood_state=self.emotions.mood.to_natural_language(),
            behavioral_guidance=guidance,
        )
