# -*- coding: utf-8 -*-
"""
EmotionalArchitecture - L4 情感架构

情感架构让 Agent 不仅会思考，还会"感受"。

核心能力：
- 情绪模型：喜、怒、哀、乐、惊、惧等
- 心境状态：持续的情绪基调
- 情感表达：自然语言表达情感
- 事件反应：对事件的情绪反应
- 依恋系统：关系建模
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class EmotionType(Enum):
    """情绪类型"""
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    TRUST = "trust"
    ANTICIPATION = "anticipation"
    CURIOSITY = "curiosity"
    HOPE = "hope"
    RELIEF = "relief"
    SATISFACTION = "satisfaction"
    PRIDE = "pride"
    SHAME = "shame"
    GRATITUDE = "gratitude"
    REMORSE = "remorse"
    CONTEMPT = "contempt"
    ADMIRATION = "admiration"


@dataclass
class Emotion:
    """情绪"""
    type: EmotionType
    intensity: float  # 0.0 - 1.0
    trigger: str  # 触发原因
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    duration_estimate: float = 60.0  # 预计持续时间（秒）
    source: str = "internal"  # internal, external, social


@dataclass
class MoodState:
    """
    心境状态
    
    持续较长时间的基线情绪。
    采用 VAD 模型：
    - Valence (效价): 积极 - 消极
    - Arousal (唤醒度): 兴奋 - 平静
    - Dominance (支配度): 控制 - 被控制
    """
    valence: float = 0.5      # 积极/消极
    arousal: float = 0.5      # 兴奋/平静
    dominance: float = 0.5   # 控制/被控制
    
    # 当前心境描述
    primary_mood: str = "neutral"
    
    # 最近情绪历史
    recent_emotions: list[Emotion] = field(default_factory=list)
    
    # 情绪历史（更长时间）
    emotion_history: list[Emotion] = field(default_factory=list)
    
    def to_natural_language(self) -> str:
        """转换为自然语言描述"""
        parts = []
        
        # 效价
        if self.valence > 0.7:
            parts.append("非常积极")
        elif self.valence > 0.6:
            parts.append("积极")
        elif self.valence > 0.5:
            parts.append("有点积极")
        elif self.valence < 0.3:
            parts.append("消极")
        elif self.valence < 0.4:
            parts.append("有点消极")
        
        # 唤醒度
        if self.arousal > 0.7:
            parts.append("高度激活")
        elif self.arousal > 0.6:
            parts.append("警觉")
        elif self.arousal < 0.3:
            parts.append("平静")
        elif self.arousal < 0.4:
            parts.append("放松")
        
        # 支配度
        if self.dominance > 0.7:
            parts.append("有控制感")
        elif self.dominance < 0.3:
            parts.append("感到失控")
        
        if not parts:
            return "中性"
        
        return "，".join(parts)
    
    def get_dominant_emotion(self) -> EmotionType | None:
        """从最近情绪获取主导情绪"""
        if not self.recent_emotions:
            return None
        
        return max(
            self.recent_emotions,
            key=lambda e: e.intensity
        ).type


class EmotionModel:
    """
    情绪模型
    
    定义每种情绪的触发条件和计算方式。
    """
    
    @staticmethod
    def is_triggered(emotion_type: EmotionType, event: dict, agent_state: dict) -> bool:
        """
        判断情绪是否被触发
        
        Args:
            emotion_type: 情绪类型
            event: 事件数据
            agent_state: Agent 状态
        """
        event_type = event.get("type", "")
        event_valence = event.get("valence", 0.5)  # 0-1, 1=positive
        
        if emotion_type == EmotionType.JOY:
            return event_valence > 0.7 and event_type == "success"
        
        elif emotion_type == EmotionType.SADNESS:
            return event_valence < 0.3 and event_type == "failure"
        
        elif emotion_type == EmotionType.ANGER:
            return event_valence < 0.3 and event_type in ["betrayal", "unfairness"]
        
        elif emotion_type == EmotionType.FEAR:
            return event.get("threat_level", 0) > 0.6
        
        elif emotion_type == EmotionType.SURPRISE:
            return event.get("unexpected", False)
        
        elif emotion_type == EmotionType.CURIOSITY:
            return event.get("novelty", 0) > 0.5
        
        elif emotion_type == EmotionType.HOPE:
            return event_valence > 0.5 and event.get("uncertain", True)
        
        elif emotion_type == EmotionType.HOPE:
            return event_valence > 0.5 and event.get("uncertain", True)
        
        return False
    
    @staticmethod
    def calculate_intensity(emotion_type: EmotionType, event: dict, agent_state: dict) -> float:
        """
        计算情绪强度
        
        Returns:
            float: 0.0 - 1.0
        """
        base_intensity = event.get("intensity", 0.5)
        
        # 根据情绪类型调整
        if emotion_type in [EmotionType.JOY, EmotionType.SADNESS]:
            return base_intensity
        elif emotion_type in [EmotionType.FEAR, EmotionType.ANGER]:
            # 负面情绪可能更强
            return min(1.0, base_intensity * 1.2)
        elif emotion_type == EmotionType.CURIOSITY:
            # 好奇心与新奇度相关
            novelty = event.get("novelty", 0.5)
            return (base_intensity + novelty) / 2
        
        return base_intensity
    
    @staticmethod
    def estimate_duration(emotion_type: EmotionType, intensity: float) -> float:
        """估计情绪持续时间（秒）"""
        base_duration = {
            EmotionType.JOY: 120,
            EmotionType.SADNESS: 300,
            EmotionType.ANGER: 60,
            EmotionType.FEAR: 30,
            EmotionType.SURPRISE: 10,
            EmotionType.CURIOSITY: 180,
            EmotionType.HOPE: 240,
            EmotionType.GRATITUDE: 300,
        }
        
        base = base_duration.get(emotion_type, 60)
        
        # 强度越高，持续越长
        return base * (0.5 + intensity * 0.5)


class EmotionalArchitecture:
    """
    情感架构
    
    完整的情绪处理系统。
    """
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        
        # 心境状态
        self.mood = MoodState()
        
        # 情绪模型
        self.emotion_models: dict[EmotionType, EmotionModel] = {
            et: EmotionModel() for et in EmotionType
        }
        
        # 依恋关系
        self.attachment_bonds: dict[str, float] = {}  # agent_id -> bond_strength
        
        # 情绪历史
        self.emotion_history: list[Emotion] = []
        
        # 表达模板
        self._init_expression_templates()
    
    def _init_expression_templates(self) -> None:
        """初始化情绪表达模板"""
        self.expression_templates = {
            EmotionType.JOY: [
                "我很开心！",
                "这让我感到很高兴",
                "太好了！",
                "心情愉悦",
            ],
            EmotionType.SADNESS: [
                "这让我感到有些失落",
                "有点难过",
                "心情不太好",
                "感到沮丧",
            ],
            EmotionType.ANGER: [
                "这让我有些不满",
                "感到愤怒",
                "这不太公平",
                "让我很恼火",
            ],
            EmotionType.FEAR: [
                "这让我有些担心",
                "感到不安",
                "有点害怕",
                "这让我紧张",
            ],
            EmotionType.SURPRISE: [
                "这很出乎意料！",
                "哇！没想到",
                "令人惊讶",
                "这很有趣！",
            ],
            EmotionType.CURIOSITY: [
                "我想了解更多",
                "这很有意思",
                "我很好奇",
                "想知道更多",
            ],
            EmotionType.HOPE: [
                "希望会好转",
                "期待好的结果",
                "保持希望",
                "乐观期待",
            ],
        }
    
    def react_to_event(self, event: dict) -> list[Emotion]:
        """
        对事件产生情绪反应
        
        Args:
            event: {
                "type": str,  # success, failure, threat, opportunity, etc.
                "valence": float,  # 0-1
                "intensity": float,  # 0-1
                "description": str,
                "source": str,  # internal, external, social
            }
        """
        triggered_emotions = []
        
        for emotion_type in EmotionType:
            if EmotionModel.is_triggered(emotion_type, event, {}):
                intensity = EmotionModel.calculate_intensity(emotion_type, event, {})
                
                emotion = Emotion(
                    type=emotion_type,
                    intensity=intensity,
                    trigger=event.get("description", ""),
                    source=event.get("source", "internal"),
                    duration_estimate=EmotionModel.estimate_duration(emotion_type, intensity)
                )
                
                triggered_emotions.append(emotion)
        
        # 更新心境
        self._update_mood(triggered_emotions)
        
        # 记录情绪
        self.emotion_history.extend(triggered_emotions)
        self.mood.recent_emotions.extend(triggered_emotions)
        
        # 限制历史长度
        if len(self.emotion_history) > 1000:
            self.emotion_history = self.emotion_history[-500:]
        if len(self.mood.recent_emotions) > 20:
            self.mood.recent_emotions = self.mood.recent_emotions[-10:]
        
        return triggered_emotions
    
    def _update_mood(self, emotions: list[Emotion]) -> None:
        """根据情绪更新心境"""
        if not emotions:
            return
        
        # 计算情绪平均值对心境的影响
        avg_valence = sum(
            e.intensity * (1 if e.type in [EmotionType.JOY, EmotionType.TRUST, EmotionType.ANTICIPATION, EmotionType.HOPE] else -1)
            for e in emotions
        ) / len(emotions)
        
        avg_arousal = sum(
            e.intensity for e in emotions
        ) / len(emotions)
        
        # 指数加权移动平均更新心境
        alpha = 0.1  # 更新率
        
        self.mood.valence = self.mood.valence * (1 - alpha) + avg_valence * alpha
        self.mood.valence = max(0.0, min(1.0, self.mood.valence))
        
        self.mood.arousal = self.mood.arousal * (1 - alpha) + avg_arousal * alpha
        self.mood.arousal = max(0.0, min(1.0, self.mood.arousal))
        
        # 更新主情绪描述
        dominant = self.mood.get_dominant_emotion()
        if dominant:
            self.mood.primary_mood = dominant.value
    
    def express_emotion(self, emotion_type: EmotionType | None = None) -> str:
        """
        表达情绪
        
        如果指定情绪类型，使用该类型；
        否则根据当前心境生成表达。
        """
        if emotion_type is None:
            dominant = self.mood.get_dominant_emotion()
            if dominant is None:
                return self.mood.to_natural_language()
            emotion_type = dominant
        
        # 获取表达模板
        templates = self.expression_templates.get(emotion_type, [])
        
        if not templates:
            return self.mood.to_natural_language()
        
        # 根据强度调整表达
        intensity = 0.5
        if self.mood.recent_emotions:
            recent = [e for e in self.mood.recent_emotions if e.type == emotion_type]
            if recent:
                intensity = sum(e.intensity for e in recent) / len(recent)
        
        if intensity > 0.7:
            return templates[0]  # 最强烈的表达
        elif intensity > 0.4:
            return templates[1] if len(templates) > 1 else templates[0]
        else:
            return templates[-1]  # 最轻微的表达
    
    def form_bond(self, other_id: str, initial_strength: float = 0.3) -> None:
        """形成依恋关系"""
        if other_id not in self.attachment_bonds:
            self.attachment_bonds[other_id] = initial_strength
    
    def strengthen_bond(self, other_id: str, amount: float) -> None:
        """加强依恋"""
        if other_id in self.attachment_bonds:
            self.attachment_bonds[other_id] = min(1.0, self.attachment_bonds[other_id] + amount)
    
    def weaken_bond(self, other_id: str, amount: float) -> None:
        """减弱依恋"""
        if other_id in self.attachment_bonds:
            self.attachment_bonds[other_id] = max(0.0, self.attachment_bonds[other_id] - amount)
    
    def get_bond_strength(self, other_id: str) -> float:
        """获取依恋强度"""
        return self.attachment_bonds.get(other_id, 0.0)
    
    def get_emotional_summary(self) -> str:
        """获取情绪摘要"""
        dominant = self.mood.get_dominant_emotion()
        dominant_desc = dominant.value if dominant else "无"
        
        recent_types = [e.type.value for e in self.mood.recent_emotions[-5:]]
        
        return f"""
【情绪状态】
- 当前心境：{self.mood.to_natural_language()}
- 主导情绪：{dominant_desc}
- 最近情绪：{', '.join(recent_types) or '无'}
- 依恋关系数：{len(self.attachment_bonds)}
        """.strip()
    
    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "mood": {
                "valence": self.mood.valence,
                "arousal": self.mood.arousal,
                "dominance": self.mood.dominance,
                "primary": self.mood.primary_mood,
            },
            "bond_count": len(self.attachment_bonds),
            "emotion_count": len(self.emotion_history),
        }
