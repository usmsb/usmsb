# -*- coding: utf-8 -*-
"""
L4: Self-Conscious Agent - 自我意识层

L4 = L3 + 自模型 + 元认知 + 他人心智 + 情感架构

核心突破：
1. SelfModel: 知道自己是谁
2. Metacognition: 知道自己在想什么
3. TheoryOfMind: 知道他人怎么想
4. EmotionalArchitecture: 有情绪反应
"""

from usmsb_sdk.l4.self_model import (
    Identity,
    IdentityVersion,
    CapabilityRecord,
    CapabilityProfile,
    Belief,
    BeliefGraph,
    Desire,
    DesireEngine,
    SelfModel,
)

from usmsb_sdk.l4.metacognition import (
    ReasoningQuality,
    ReasoningStep,
    ReasoningTrace,
    LearningStrategy,
    LearningStrategyRegistry,
    Metacognition,
)

from usmsb_sdk.l4.theory_of_mind import (
    Interaction,
    InferredCapability,
    InferredBelief,
    OtherAgentModel,
    DeceptionAssessment,
    IntentionPrediction,
    TheoryOfMind,
)

from usmsb_sdk.l4.emotional_architecture import (
    EmotionType,
    Emotion,
    MoodState,
    EmotionModel,
    EmotionalArchitecture,
)

from usmsb_sdk.l4.l4_agent import (
    SelfReflection,
    L4SelfConsciousAgent,
)

__all__ = [
    # SelfModel
    "Identity",
    "IdentityVersion",
    "CapabilityRecord",
    "CapabilityProfile",
    "Belief",
    "BeliefGraph",
    "Desire",
    "DesireEngine",
    "SelfModel",
    # Metacognition
    "ReasoningQuality",
    "ReasoningStep",
    "ReasoningTrace",
    "LearningStrategy",
    "LearningStrategyRegistry",
    "Metacognition",
    # TheoryOfMind
    "Interaction",
    "InferredCapability",
    "InferredBelief",
    "OtherAgentModel",
    "DeceptionAssessment",
    "IntentionPrediction",
    "TheoryOfMind",
    # EmotionalArchitecture
    "EmotionType",
    "Emotion",
    "MoodState",
    "EmotionModel",
    "EmotionalArchitecture",
    # L4 Agent
    "SelfReflection",
    "L4SelfConsciousAgent",
]
