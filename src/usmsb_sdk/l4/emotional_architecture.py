# -*- coding: utf-8 -*-
from __future__ import annotations

"""
EmotionalArchitecture - L4 情感架构 v2

情感架构让 Agent 不仅会思考，还会"感受"。
EmotionalArchitecture - L4 情感架构 v2

情感架构让 Agent 不仅会思考，还会"感受"。

核心能力（v2 升级）：
- 情绪模型：喜、怒、哀、乐、惊、惧等
- 心境状态：持续的情绪基调（VAD模型）
- 情感表达：自然语言表达情感
- 事件反应：对事件的情绪反应
- 依恋系统：关系建模
- 行为倾向：情绪直接驱动 ActionTendency（规则层）
- LLM 深度推理：复杂情绪场景由 LLM 提供指导（LLM层）
- 指数衰减：每种情绪有自己的半衰期
- MoodState：慢衰减背景，让情绪有惯性
"""

import math
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


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


# ─────────────────────────────────────────────────────────────────────────────
# ActionTendency - 情绪驱动的行为倾向
# ─────────────────────────────────────────────────────────────────────────────

class ActionTendency(Enum):
    """
    行为倾向
    
    情绪通过规则层映射为行为倾向，每种倾向直接影响：
    - 目标难度选择
    - 推理策略
    - 协作意愿
    - 反思频率
    """
    AMBITIOUS = "ambitious"        # 自信提升 → 尝试更难目标
    CONSERVATIVE = "conservative"  # 自信降低 → 降级目标难度，回避风险
    RISK_AVERSE = "risk_averse"    # 恐惧 → 回避风险，回避未知
    CHALLENGING = "challenging"    # 愤怒 → 主动挑战，更竞争性
    EXPLORING = "exploring"        # 好奇 → 探索新领域/新Agent
    OPTIMISTIC = "optimistic"      # 希望 → 积极追求目标
    RECALIBRATING = "recalibrating"  # 惊讶 → 重新校准，暂停审视
    TRUSTING = "trusting"          # 信任 → 加强合作
    WITHDRAWN = "withdrawn"        # 悲伤 → 减少社交，回避
    VIGILANT = "vigilant"          # 警惕 → 谨慎评估
    NURTURING = "nurturing"        # 感恩/爱 → 保护/培育关系


# ─────────────────────────────────────────────────────────────────────────────
# 情绪半衰期配置（秒）
# ─────────────────────────────────────────────────────────────────────────────

EMOTION_HALF_LIVES: dict[EmotionType, float] = {
    # 极短暂（<1分钟）
    EmotionType.SURPRISE:  10.0,
    EmotionType.FEAR:      30.0,
    EmotionType.ANGER:     60.0,
    # 中等（1-3分钟）
    EmotionType.DISGUST:   45.0,
    EmotionType.JOY:      120.0,
    EmotionType.HOPE:     180.0,
    EmotionType.RELIEF:   120.0,
    # 较长（3-5分钟）
    EmotionType.CURIOSITY: 180.0,
    EmotionType.SATISFACTION: 180.0,
    # 持久（>5分钟）
    EmotionType.SADNESS:   300.0,
    EmotionType.SHAME:     300.0,
    EmotionType.REMORSE:   300.0,
    EmotionType.GRATITUDE: 300.0,
    # 社会性情绪（持续久）
    EmotionType.PRIDE:     240.0,
    EmotionType.CONTEMPT:  120.0,
    EmotionType.ANTICIPATION: 150.0,
    EmotionType.ADMIRATION: 240.0,
    EmotionType.TRUST:     180.0,
}

# ─────────────────────────────────────────────────────────────────────────────
# 情绪 → 行为倾向 映射矩阵
# ─────────────────────────────────────────────────────────────────────────────

EMOTION_TENDENCY_MAP: dict[EmotionType, dict[ActionTendency, float]] = {
    # 正面-愉悦类
    EmotionType.JOY: {
        ActionTendency.AMBITIOUS:  0.8,
        ActionTendency.EXPLORING:  0.3,
        ActionTendency.OPTIMISTIC: 0.5,
        ActionTendency.TRUSTING:   0.2,
    },
    EmotionType.SATISFACTION: {
        ActionTendency.AMBITIOUS:  0.6,
        ActionTendency.CONSERVATIVE: 0.1,
        ActionTendency.OPTIMISTIC:  0.4,
    },
    EmotionType.PRIDE: {
        ActionTendency.AMBITIOUS:  0.9,
        ActionTendency.CHALLENGING: 0.3,
        ActionTendency.OPTIMISTIC:  0.4,
    },
    EmotionType.HOPE: {
        ActionTendency.AMBITIOUS:  0.5,
        ActionTendency.OPTIMISTIC:  0.8,
        ActionTendency.EXPLORING:   0.3,
    },
    EmotionType.RELIEF: {
        ActionTendency.OPTIMISTIC:  0.7,
        ActionTendency.CONSERVATIVE: 0.2,
        ActionTendency.RECALIBRATING: 0.1,
    },
    EmotionType.ADMIRATION: {
        ActionTendency.EXPLORING:   0.6,
        ActionTendency.TRUSTING:    0.7,
        ActionTendency.NURTURING:   0.3,
    },
    EmotionType.GRATITUDE: {
        ActionTendency.TRUSTING:   0.8,
        ActionTendency.NURTURING:  0.6,
        ActionTendency.OPTIMISTIC: 0.3,
    },
    # 负面-退缩类
    EmotionType.SADNESS: {
        ActionTendency.CONSERVATIVE: 0.7,
        ActionTendency.WITHDRAWN:   0.6,
        ActionTendency.RECALIBRATING: 0.2,
    },
    EmotionType.FEAR: {
        ActionTendency.RISK_AVERSE:  0.9,
        ActionTendency.WITHDRAWN:    0.5,
        ActionTendency.VIGILANT:     0.4,
    },
    EmotionType.DISGUST: {
        ActionTendency.RISK_AVERSE:  0.6,
        ActionTendency.WITHDRAWN:    0.5,
        ActionTendency.VIGILANT:     0.3,
    },
    EmotionType.SHAME: {
        ActionTendency.CONSERVATIVE: 0.8,
        ActionTendency.WITHDRAWN:    0.4,
        ActionTendency.RECALIBRATING: 0.2,
    },
    EmotionType.REMORSE: {
        ActionTendency.CONSERVATIVE: 0.7,
        ActionTendency.WITHDRAWN:    0.4,
        ActionTendency.RECALIBRATING: 0.3,
    },
    EmotionType.CONTEMPT: {
        ActionTendency.CHALLENGING: 0.6,
        ActionTendency.WITHDRAWN:   0.2,
        ActionTendency.RISK_AVERSE: 0.2,
    },
    # 中性-激活类
    EmotionType.ANGER: {
        ActionTendency.CHALLENGING:  0.8,
        ActionTendency.RISK_AVERSE:  0.2,
        ActionTendency.VIGILANT:     0.3,
    },
    EmotionType.SURPRISE: {
        ActionTendency.RECALIBRATING: 0.8,
        ActionTendency.EXPLORING:     0.3,
        ActionTendency.VIGILANT:     0.3,
    },
    EmotionType.CURIOSITY: {
        ActionTendency.EXPLORING:    0.9,
        ActionTendency.AMBITIOUS:    0.2,
        ActionTendency.VIGILANT:     0.1,
    },
    EmotionType.ANTICIPATION: {
        ActionTendency.OPTIMISTIC:   0.5,
        ActionTendency.AMBITIOUS:    0.3,
        ActionTendency.VIGILANT:     0.3,
        ActionTendency.RECALIBRATING: 0.2,
    },
    EmotionType.TRUST: {
        ActionTendency.TRUSTING:     0.9,
        ActionTendency.EXPLORING:    0.2,
        ActionTendency.NURTURING:    0.4,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# 数据结构
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Emotion:
    """情绪"""
    type: EmotionType
    intensity: float  # 0.0 - 1.0
    trigger: str  # 触发原因
    timestamp: float = field(default_factory=lambda: time.time())
    duration_estimate: float = 60.0  # 预计持续时间（秒）
    source: str = "internal"  # internal, external, social


@dataclass
class MoodState:
    """
    心境状态（慢衰减背景情绪）
    
    采用 VAD 模型：
    - Valence (效价): 积极 - 消极
    - Arousal (唤醒度): 兴奋 - 平静
    - Dominance (支配度): 控制 - 被控制
    
    心境更新很慢（alpha=0.1），让情绪有惯性。
    """
    valence: float = 0.5      # 0.0(消极) - 1.0(积极)
    arousal: float = 0.5       # 0.0(平静) - 1.0(兴奋)
    dominance: float = 0.5     # 0.0(被控制) - 1.0(有控制感)
    
    primary_mood: str = "neutral"
    
    recent_emotions: list[Emotion] = field(default_factory=list)
    emotion_history: list[Emotion] = field(default_factory=list)
    
    def to_natural_language(self) -> str:
        parts = []
        if self.valence > 0.7:   parts.append("非常积极")
        elif self.valence > 0.6: parts.append("积极")
        elif self.valence > 0.5: parts.append("有点积极")
        elif self.valence < 0.3: parts.append("消极")
        elif self.valence < 0.4: parts.append("有点消极")
        
        if self.arousal > 0.7:   parts.append("高度激活")
        elif self.arousal > 0.6: parts.append("警觉")
        elif self.arousal < 0.3: parts.append("平静")
        elif self.arousal < 0.4: parts.append("放松")
        
        if self.dominance > 0.7: parts.append("有控制感")
        elif self.dominance < 0.3: parts.append("感到失控")
        
        return "，".join(parts) if parts else "中性"
    
    def get_dominant_emotion(self) -> EmotionType | None:
        if not self.recent_emotions:
            return None
        return max(self.recent_emotions, key=lambda e: e.intensity).type


# ─────────────────────────────────────────────────────────────────────────────
# EmotionModel - 情绪触发规则
# ─────────────────────────────────────────────────────────────────────────────

class EmotionModel:
    """定义每种情绪的触发条件和计算方式"""
    
    @staticmethod
    def is_triggered(emotion_type: EmotionType, event: dict, agent_state: dict) -> bool:
        event_type = event.get("type", "")
        event_valence = event.get("valence", 0.5)
        
        triggers = {
            EmotionType.JOY:         lambda: event_valence > 0.7 and event_type == "success",
            EmotionType.SADNESS:     lambda: event_valence < 0.3 and event_type == "failure",
            EmotionType.ANGER:       lambda: event_valence < 0.3 and event_type in ["betrayal", "unfairness", "frustration"],
            EmotionType.FEAR:        lambda: event.get("threat_level", 0) > 0.6,
            EmotionType.SURPRISE:     lambda: event.get("unexpected", False),
            EmotionType.DISGUST:     lambda: event.get("disgust_level", 0) > 0.6,
            EmotionType.TRUST:        lambda: event_valence > 0.6 and event_type in ["cooperation", "support"],
            EmotionType.ANTICIPATION: lambda: event.get("awaited", False) and event_valence > 0.5,
            EmotionType.CURIOSITY:    lambda: event.get("novelty", 0) > 0.5,
            EmotionType.HOPE:         lambda: event_valence > 0.5 and event.get("uncertain", True),
            EmotionType.RELIEF:      lambda: event_valence > 0.6 and event_type in ["threat_removed", "failure_avoided"],
            EmotionType.SATISFACTION: lambda: event_valence > 0.7 and event_type in ["goal_achieved", "success"],
            EmotionType.PRIDE:       lambda: event_valence > 0.7 and event_type == "achievement",
            EmotionType.SHAME:       lambda: event_valence < 0.3 and event_type == "failure" and event.get("responsible", False),
            EmotionType.GRATITUDE:   lambda: event_valence > 0.6 and event_type == "gift",
            EmotionType.REMORSE:     lambda: event_valence < 0.3 and event.get("responsible", False) and event_type in ["failure", "harm"],
            EmotionType.CONTEMPT:    lambda: event_valence < 0.3 and event_type in ["inferiority", "disrespect"],
            EmotionType.ADMIRATION:  lambda: event_valence > 0.6 and event_type in ["excellence", "skill"],
        }
        
        trigger_fn = triggers.get(emotion_type)
        return trigger_fn() if trigger_fn else False
    
    @staticmethod
    def calculate_intensity(emotion_type: EmotionType, event: dict, agent_state: dict) -> float:
        base = event.get("intensity", 0.5)
        
        if emotion_type in [EmotionType.FEAR, EmotionType.ANGER]:
            return min(1.0, base * 1.2)
        elif emotion_type == EmotionType.CURIOSITY:
            return (base + event.get("novelty", 0.5)) / 2
        elif emotion_type in [EmotionType.HOPE, EmotionType.ANTICIPATION]:
            uncertainty = event.get("uncertainty", 0.5)
            return (base + (1.0 - uncertainty)) / 2
        elif emotion_type == EmotionType.SADNESS:
            responsibility = event.get("responsible", False)
            return min(1.0, base * (1.3 if responsibility else 1.0))
        
        return base


# ─────────────────────────────────────────────────────────────────────────────
# EmotionalGoalModifier - 把 ActionTendency 翻译成行为参数
# ─────────────────────────────────────────────────────────────────────────────

class EmotionalGoalModifier:
    """
    情绪目标修改器
    
    把 ActionTendency 翻译成目标系统能理解的参数：
    - 目标难度系数
    - 推理策略
    - 协作权重
    - 时间分配策略
    """
    
    DIFFICULTY_MULTIPLIERS: dict[ActionTendency, float] = {
        ActionTendency.AMBITIOUS:     1.15,  # +15% 难度
        ActionTendency.CONSERVATIVE:  0.80,  # -20% 难度
        ActionTendency.EXPLORING:     1.00,  # 不变，探索目标不比较难度
        ActionTendency.RISK_AVERSE:   0.70,  # -30% 难度
        ActionTendency.CHALLENGING:   1.20,  # +20% 难度
        ActionTendency.OPTIMISTIC:    1.10,  # +10% 难度
        ActionTendency.RECALIBRATING: 0.90,  # -10% 难度，审视优先
        ActionTendency.VIGILANT:      0.85,  # -15% 难度
        ActionTendency.TRUSTING:      1.00,  # 不变
        ActionTendency.WITHDRAWN:     0.75,  # -25% 难度，减少行动
        ActionTendency.NURTURING:     1.00,  # 不变
    }
    
    REASONING_STRATEGIES: dict[ActionTendency, str] = {
        ActionTendency.RISK_AVERSE:    "conservative",    # 保守推理，多验证
        ActionTendency.CHALLENGING:    "bold",           # 大胆推理，快速迭代
        ActionTendency.RECALIBRATING: "reexamine",      # 重新审视，从头分析
        ActionTendency.AMBITIOUS:     "confident",      # 自信推理，相信直觉
        ActionTendency.CONSERVATIVE:  "cautious",       # 谨慎推理，多重确认
        ActionTendency.EXPLORING:     "divergent",       # 发散思维，探索多种可能
        ActionTendency.OPTIMISTIC:    "positive",        # 积极推理，关注机会
        ActionTendency.VIGILANT:      "critical",        # 批判思维，关注风险
        ActionTendency.WITHDRAWN:     "reflective",      # 内省思维，少外部依赖
        ActionTendency.TRUSTING:      "open",            # 开放推理，信任输入
        ActionTendency.NURTURING:     "collaborative",   # 协作推理，重视关系
    }
    
    COLLABORATION_ADJUSTMENTS: dict[ActionTendency, float] = {
        # 正值 = 更愿意协作，负值 = 更回避协作
        ActionTendency.TRUSTING:      0.20,
        ActionTendency.NURTURING:     0.15,
        ActionTendency.EXPLORING:     0.10,
        ActionTendency.OPTIMISTIC:    0.10,
        ActionTendency.AMBITIOUS:     0.05,
        ActionTendency.CONSERVATIVE: -0.10,
        ActionTendency.WITHDRAWN:     -0.25,
        ActionTendency.RISK_AVERSE:   -0.15,
        ActionTendency.CHALLENGING:   -0.10,
        ActionTendency.RECALIBRATING: 0.00,
        ActionTendency.VIGILANT:     -0.05,
    }
    
    TIME_ALLOCATIONS: dict[ActionTendency, str] = {
        ActionTendency.AMBITIOUS:     "accelerate",
        ActionTendency.CONSERVATIVE: "maintain",
        ActionTendency.EXPLORING:     "explore",       # 分配时间给探索
        ActionTendency.RISK_AVERSE:   "pause",         # 暂停评估
        ActionTendency.CHALLENGING:   "accelerate",
        ActionTendency.OPTIMISTIC:    "accelerate",
        ActionTendency.RECALIBRATING: "reconsider",    # 重新规划时间
        ActionTendency.VIGILANT:     "maintain",
        ActionTendency.TRUSTING:     "maintain",
        ActionTendency.WITHDRAWN:    "pause",
        ActionTendency.NURTURING:    "maintain",
    }
    
    def get_difficulty_multiplier(self, tendency: ActionTendency) -> float:
        return self.DIFFICULTY_MULTIPLIERS.get(tendency, 1.0)
    
    def get_reasoning_strategy(self, tendency: ActionTendency) -> str:
        return self.REASONING_STRATEGIES.get(tendency, "normal")
    
    def get_collaboration_adjustment(self, tendency: ActionTendency) -> float:
        return self.COLLABORATION_ADJUSTMENTS.get(tendency, 0.0)
    
    def get_time_allocation(self, tendency: ActionTendency) -> str:
        return self.TIME_ALLOCATIONS.get(tendency, "maintain")
    
    def get_full_guidance(self, tendency: ActionTendency, confidence: float) -> dict:
        """获取完整的情绪引导参数"""
        return {
            "tendency": tendency.value,
            "confidence": confidence,
            "difficulty_multiplier": self.get_difficulty_multiplier(tendency),
            "reasoning_strategy": self.get_reasoning_strategy(tendency),
            "collaboration_adjustment": self.get_collaboration_adjustment(tendency),
            "time_allocation": self.get_time_allocation(tendency),
        }


# ─────────────────────────────────────────────────────────────────────────────
# EmotionalArchitecture - 核心情感架构
# ─────────────────────────────────────────────────────────────────────────────

class EmotionalArchitecture:
    """
    情感架构 v2
    
    核心组件：
    - mood: MoodState（VAD慢衰减背景）
    - emotion_models: 每种情绪的触发规则
    - attachment_bonds: 依恋关系
    - action_modifier: 情绪→行为参数翻译器
    - current_tendency: 当前主导行为倾向
    """
    
    # 情绪清理阈值
    INTENSITY_CLEANUP_THRESHOLD = 0.05
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        
        self.mood = MoodState()
        self.emotion_models: dict[EmotionType, EmotionModel] = {
            et: EmotionModel() for et in EmotionType
        }
        self.attachment_bonds: dict[str, float] = {}
        
        self.emotion_history: list[Emotion] = []
        
        # 活跃情绪（带指数衰减的实时视图）
        self._emotions_raw: list[Emotion] = []
        
        # 当前主导行为倾向
        self.current_tendency: ActionTendency = ActionTendency.OPTIMISTIC
        self.current_tendency_confidence: float = 0.5
        
        # 行为修改器
        self.action_modifier = EmotionalGoalModifier()
        
        self._init_expression_templates()
    
    def _init_expression_templates(self) -> None:
        self.expression_templates = {
            EmotionType.JOY: ["太开心了！", "这让我非常高兴", "太好了！", "心情愉悦"],
            EmotionType.SADNESS: ["有些失落", "有点难过", "心情不太好", "感到沮丧"],
            EmotionType.ANGER: ["有些不满", "感到愤怒", "这不太公平", "让我很恼火"],
            EmotionType.FEAR: ["有些担心", "感到不安", "有点害怕", "这让我紧张"],
            EmotionType.SURPRISE: ["很出乎意料！", "哇！没想到", "令人惊讶", "这很有趣！"],
            EmotionType.CURIOSITY: ["我想了解更多", "这很有意思", "我很好奇", "想知道更多"],
            EmotionType.HOPE: ["希望会好转", "期待好的结果", "保持希望", "乐观期待"],
            EmotionType.PRIDE: ["感到自豪", "这是我的成就", "值得骄傲", "我很满意"],
            EmotionType.GRATITUDE: ["非常感谢", "很感激", "谢谢你们", "心存感激"],
            EmotionType.TRUST: ["我相信", "可以依靠", "很信任", "充满信心"],
            EmotionType.ADMIRATION: ["令人钦佩", "非常尊敬", "值得赞赏", "仰慕"],
            EmotionType.SHAME: ["有些惭愧", "不好意思", "感到羞愧", "自责"],
            EmotionType.REMORSE: ["很后悔", "对不起", "我错了", "深感歉意"],
            EmotionType.CONTEMPT: ["不屑一顾", "看不起", "傲慢", "轻视"],
            EmotionType.SATISFACTION: ["很满足", "满意", "心满意足", "称心如意"],
            EmotionType.RELIEF: ["松了一口气", "终于放心了", "如释重负", "轻松多了"],
            EmotionType.DISGUST: ["很反感", "厌恶", "恶心", "讨厌"],
            EmotionType.ANTICIPATION: ["很期待", "迫不及待", "充满期待", "兴奋不已"],
        }
    
    # ── 活跃情绪管理 ──────────────────────────────────────────────────────
    
    @property
    def active_emotions(self) -> list[Emotion]:
        """返回有效强度 > 阈值的情绪列表（实时计算指数衰减）"""
        active = []
        for emotion in self._emotions_raw:
            if self._effective_intensity(emotion) > self.INTENSITY_CLEANUP_THRESHOLD:
                active.append(emotion)
        return active
    
    def _effective_intensity(self, emotion: Emotion) -> float:
        """计算经过指数衰减后的有效强度"""
        elapsed = time.time() - emotion.timestamp
        half_life = EMOTION_HALF_LIVES.get(emotion.type, 60.0)
        return emotion.intensity * (0.5 ** (elapsed / half_life))
    
    def _cleanup_weak_emotions(self) -> None:
        """移除衰减到阈值以下的情绪"""
        self._emotions_raw = [
            e for e in self._emotions_raw
            if self._effective_intensity(e) > self.INTENSITY_CLEANUP_THRESHOLD
        ]
    
    # ── 事件反应 ──────────────────────────────────────────────────────────
    
    def react_to_event(self, event: dict) -> list[Emotion]:
        """
        对事件产生情绪反应
        
        event = {
            "type": str,        # success, failure, threat, etc.
            "valence": float,   # 0-1, 1=positive
            "intensity": float, # 0-1
            "description": str,
            "source": str,      # internal, external, social
            # 可选：
            "novelty": float,
            "threat_level": float,
            "unexpected": bool,
            "uncertain": bool,
            "responsible": bool,
            "disgust_level": float,
        }
        """
        triggered = []
        
        for emotion_type in EmotionType:
            if EmotionModel.is_triggered(emotion_type, event, {}):
                intensity = EmotionModel.calculate_intensity(emotion_type, event, {})
                emotion = Emotion(
                    type=emotion_type,
                    intensity=intensity,
                    trigger=event.get("description", ""),
                    source=event.get("source", "internal"),
                    duration_estimate=EMOTION_HALF_LIVES.get(emotion_type, 60.0),
                )
                triggered.append(emotion)
                self._emotions_raw.append(emotion)
        
        # 更新心境（很慢的指数加权移动平均）
        if triggered:
            self._update_mood(triggered)
        
        # 更新行为倾向（规则层，立即生效）
        if triggered:
            self._update_action_tendency()
        
        # 记录历史
        self.emotion_history.extend(triggered)
        self.mood.recent_emotions.extend(triggered)
        
        # 清理
        if len(self._emotions_raw) > 200:
            self._cleanup_weak_emotions()
        if len(self.emotion_history) > 1000:
            self.emotion_history = self.emotion_history[-500:]
        if len(self.mood.recent_emotions) > 20:
            self.mood.recent_emotions = self.mood.recent_emotions[-10:]
        
        return triggered
    
    def _update_mood(self, emotions: list[Emotion]) -> None:
        """根据情绪更新心境（VAD，慢衰减）"""
        if not emotions:
            return
        
        # 计算情绪对VAD的影响
        valence_sum = 0.0
        arousal_sum = 0.0
        dominance_sum = 0.0
        
        positive_types = {
            EmotionType.JOY, EmotionType.SATISFACTION, EmotionType.PRIDE,
            EmotionType.HOPE, EmotionType.RELIEF, EmotionType.ADMIRATION,
            EmotionType.GRATITUDE, EmotionType.TRUST, EmotionType.ANTICIPATION
        }
        negative_types = {
            EmotionType.SADNESS, EmotionType.ANGER, EmotionType.FEAR,
            EmotionType.DISGUST, EmotionType.SHAME, EmotionType.REMORSE,
            EmotionType.CONTEMPT
        }
        high_arousal = {
            EmotionType.ANGER, EmotionType.FEAR, EmotionType.SURPRISE,
            EmotionType.CURIOSITY, EmotionType.ANTICIPATION, EmotionType.HOPE
        }
        low_arousal = {
            EmotionType.SADNESS, EmotionType.RELIEF, EmotionType.SATISFACTION,
            EmotionType.SATISFACTION
        }
        
        for e in emotions:
            val = 1.0 if e.type in positive_types else (-1.0 if e.type in negative_types else 0.0)
            valence_sum += val * e.intensity
            arousal_sum += (1.0 if e.type in high_arousal else (-0.5 if e.type in low_arousal else 0.0)) * e.intensity
            dominance_sum += (0.3 if e.type in {EmotionType.PRIDE, EmotionType.ANGER} else (-0.3 if e.type in {EmotionType.FEAR, EmotionType.SADNESS} else 0.0)) * e.intensity
        
        avg_valence = valence_sum / len(emotions)
        avg_arousal = arousal_sum / len(emotions)
        avg_dominance = dominance_sum / len(emotions)
        
        alpha = 0.1  # 很慢的更新
        self.mood.valence = max(0.0, min(1.0, self.mood.valence * (1 - alpha) + (avg_valence * 0.5 + 0.5) * alpha))
        self.mood.arousal = max(0.0, min(1.0, self.mood.arousal * (1 - alpha) + (avg_arousal * 0.5 + 0.5) * alpha))
        self.mood.dominance = max(0.0, min(1.0, self.mood.dominance * (1 - alpha) + (avg_dominance * 0.5 + 0.5) * alpha))
        
        dominant = self.mood.get_dominant_emotion()
        if dominant:
            self.mood.primary_mood = dominant.value
    
    def _update_action_tendency(self) -> None:
        """规则层：计算当前主导行为倾向（加权投票）"""
        scores: dict[ActionTendency, float] = defaultdict(float)
        active = self.active_emotions
        
        if not active:
            # 无活跃情绪时，用心境作为背景
            if self.mood.valence > 0.65:
                scores[ActionTendency.AMBITIOUS] += 0.15
                scores[ActionTendency.OPTIMISTIC] += 0.15
            elif self.mood.valence < 0.35:
                scores[ActionTendency.CONSERVATIVE] += 0.15
                scores[ActionTendency.WITHDRAWN] += 0.10
            
            if self.mood.arousal > 0.65:
                scores[ActionTendency.VIGILANT] += 0.10
            elif self.mood.arousal < 0.35:
                scores[ActionTendency.WITHDRAWN] += 0.05
            
            if scores:
                winner = max(scores, key=scores.get)
                self.current_tendency = winner
                self.current_tendency_confidence = scores[winner]
            else:
                self.current_tendency = ActionTendency.OPTIMISTIC
                self.current_tendency_confidence = 0.3
            return
        
        # 加权投票
        for emotion in active:
            eff = self._effective_intensity(emotion)
            tendency_weights = EMOTION_TENDENCY_MAP.get(emotion.type, {})
            for tendency, weight in tendency_weights.items():
                scores[tendency] += eff * weight
        
        if not scores:
            self.current_tendency = ActionTendency.OPTIMISTIC
            self.current_tendency_confidence = 0.3
            return
        
        winner = max(scores, key=scores.get)
        total = sum(scores.values())
        self.current_tendency = winner
        self.current_tendency_confidence = scores[winner] / total if total > 0 else 0.3
    
    # ── 行为倾向查询 ──────────────────────────────────────────────────────
    
    def get_action_tendency(self) -> tuple[ActionTendency, float]:
        """返回 (当前主导行为倾向, 置信度)"""
        return self.current_tendency, self.current_tendency_confidence
    
    def get_behavioral_guidance(self) -> dict:
        """获取完整的情绪行为引导参数"""
        return self.action_modifier.get_full_guidance(
            self.current_tendency,
            self.current_tendency_confidence
        )
    
    # ── 表达 ──────────────────────────────────────────────────────────────
    
    def express_emotion(self, emotion_type: EmotionType | None = None) -> str:
        if emotion_type is None:
            dominant = self.mood.get_dominant_emotion()
            if dominant is None:
                return self.mood.to_natural_language()
            emotion_type = dominant
        
        templates = self.expression_templates.get(emotion_type, [])
        if not templates:
            return self.mood.to_natural_language()
        
        intensity = 0.5
        recent = [e for e in self.mood.recent_emotions if e.type == emotion_type]
        if recent:
            intensity = sum(self._effective_intensity(e) for e in recent) / len(recent)
        
        if intensity > 0.7:
            return templates[0]
        elif intensity > 0.4:
            return templates[1] if len(templates) > 1 else templates[0]
        else:
            return templates[-1]
    
    # ── 依恋系统 ──────────────────────────────────────────────────────────
    
    def form_bond(self, other_id: str, initial_strength: float = 0.3) -> None:
        if other_id not in self.attachment_bonds:
            self.attachment_bonds[other_id] = initial_strength
    
    def strengthen_bond(self, other_id: str, amount: float) -> None:
        if other_id in self.attachment_bonds:
            self.attachment_bonds[other_id] = min(1.0, self.attachment_bonds[other_id] + amount)
    
    def weaken_bond(self, other_id: str, amount: float) -> None:
        if other_id in self.attachment_bonds:
            self.attachment_bonds[other_id] = max(0.0, self.attachment_bonds[other_id] - amount)
    
    def get_bond_strength(self, other_id: str) -> float:
        return self.attachment_bonds.get(other_id, 0.0)
    
    # ── 状态报告 ──────────────────────────────────────────────────────────
    
    def get_emotional_summary(self) -> str:
        dominant = self.mood.get_dominant_emotion()
        dominant_desc = dominant.value if dominant else "无"
        
        recent_types = [e.type.value for e in self.mood.recent_emotions[-5:]]
        active = self.active_emotions
        active_summary = ", ".join([
            f"{e.type.value}({self._effective_intensity(e):.2f})"
            for e in sorted(active, key=self._effective_intensity, reverse=True)[:5]
        ])
        
        guidance = self.get_behavioral_guidance()
        
        return f"""
【情绪状态】
- 当前心境：{self.mood.to_natural_language()}
- 主导情绪：{dominant_desc}
- 最近情绪：{', '.join(recent_types) or '无'}
- 活跃情绪：{active_summary or '无'}
- 行为倾向：{self.current_tendency.value}（置信度 {self.current_tendency_confidence:.2f}）
- 目标难度调整：×{guidance['difficulty_multiplier']:.2f}
- 推理策略：{guidance['reasoning_strategy']}
- 协作倾向：{'+' if guidance['collaboration_adjustment'] >= 0 else ''}{guidance['collaboration_adjustment']:.2f}
- 时间分配：{guidance['time_allocation']}
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
            "current_tendency": self.current_tendency.value,
            "tendency_confidence": self.current_tendency_confidence,
            "behavioral_guidance": self.get_behavioral_guidance(),
            "active_emotion_count": len(self.active_emotions),
            "bond_count": len(self.attachment_bonds),
            "emotion_count": len(self.emotion_history),
        }
