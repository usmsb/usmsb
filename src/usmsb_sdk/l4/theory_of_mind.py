# -*- coding: utf-8 -*-
"""
TheoryOfMind - L4 他人心智理论 v2

理解他人知道什么、想要什么、相信什么。

v2 升级（LLM驱动）：
- predict_intention() → LLM 分析对话历史 + 行为模式 → 意图推断
- detect_deception() → LLM 语言分析 → 欺骗检测
- infer_belief_from_text() → LLM 从文本自动推断信念
- OtherAgentModel → 自动从交互历史中学习
"""

from __future__ import annotations

import uuid
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────

class InteractionType(Enum):
    """交互类型"""
    CHAT = "chat"
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    NEGOTIATION = "negotiation"
    STATEMENT = "statement"
    PROMISE = "promise"
    EXCUSE = "excuse"


class IntentionCategory(Enum):
    """意图类别"""
    COOPERATION = "cooperation"          # 合作意图
    COMPETITION = "competition"          # 竞争意图
    INFORMATION_GATHERING = "info_gathering"  # 信息收集
    MANIPULATION = "manipulation"        # 操纵意图
    GENUINE_HELP = "genuine_help"        # 真诚帮助
    SELF_PROTECTION = "self_protection"  # 自我保护
    EXPLOITATION = "exploitation"        # 剥削意图
    TRUST_BUILDING = "trust_building"     # 建立信任
    UNKNOWN = "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Interaction:
    """交互记录"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    type: str = "chat"  # chat, task_request, task_response, negotiation, statement
    content: str = ""
    outcome: str = ""  # success, failure, neutral
    trust_change: float = 0.0
    # v2: LLM 推断
    llm_inferred_intent: str | None = None      # LLM 推断的意图
    llm_inferred_emotion: str | None = None     # LLM 推断的情绪
    is_deceptive: bool | None = None             # LLM 判断是否欺骗


@dataclass
class InferredCapability:
    """推断的能力"""
    name: str
    confidence: float = 0.5
    evidence: list[str] = field(default_factory=list)
    last_updated: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class InferredBelief:
    """推断的信念"""
    content: str
    confidence: float = 0.5
    source: str = "inference"  # inference, statement, observation, llm
    evidence: list[str] = field(default_factory=list)
    inferred_at: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class LLMInferredMind:
    """LLM 推断的他人心智状态"""
    primary_intent: str = ""
    intent_probability: float = 0.5
    secondary_intents: list[str] = field(default_factory=list)
    emotional_state: str = ""
    beliefs: list[str] = field(default_factory=list)      # 推断的信念
    knowledge_gaps: list[str] = field(default_factory=list)  # 推断的知识缺口
    deception_signals: list[str] = field(default_factory=list)  # 欺骗信号
    confidence: float = 0.5
    reasoning: str = ""  # LLM 推理过程
    raw_analysis: str = ""  # LLM 原始分析


@dataclass
class OtherAgentModel:
    """
    他人心智模型 v2

    v2 升级：
    - LLMInferredMind: 定期用 LLM 刷新心智推断
    - conversation_summary: 对话历史摘要（用于 LLM 分析）
    - belief_network: 信念网络（哪些信念同时出现）
    - interaction_patterns: 交互模式（LLM 从历史中学习）
    """
    agent_id: str
    name: str = "Unknown"

    # 推断的能力
    inferred_capabilities: dict[str, InferredCapability] = field(default_factory=dict)

    # 推断的信念
    inferred_beliefs: list[InferredBelief] = field(default_factory=list)

    # 推断的意图历史
    inferred_intentions: list[str] = field(default_factory=list)

    # 关系
    relationship_strength: float = 0.5
    trust_level: float = 0.5
    cooperation_history: float = 0.5

    # 交互历史
    interaction_history: list[Interaction] = field(default_factory=list)

    # v2: LLM 推断的心智状态
    current_mind_state: LLMInferredMind | None = None
    last_llm_inference: float = 0.0

    # v2: 对话摘要（定期压缩历史）
    conversation_summary: str = ""

    # v2: 交互模式标签
    interaction_patterns: list[str] = field(default_factory=list)

    # 元数据
    model_accuracy: float = 0.5
    last_updated: float = field(default_factory=lambda: datetime.now().timestamp())
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())

    def add_capability(self, name: str, confidence: float, evidence: str) -> None:
        if name in self.inferred_capabilities:
            cap = self.inferred_capabilities[name]
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
        belief = InferredBelief(
            content=content,
            confidence=confidence,
            source=source,
            evidence=[evidence]
        )
        self.inferred_beliefs.append(belief)
        self.last_updated = datetime.now().timestamp()

    def record_interaction(self, interaction: Interaction) -> None:
        self.interaction_history.append(interaction)

        if interaction.outcome == "success":
            self.trust_level = max(0.0, min(1.0, self.trust_level + interaction.trust_change))
            self.cooperation_history = self.cooperation_history * 0.95 + 0.05
        elif interaction.outcome == "failure":
            self.trust_level = max(0.0, min(1.0, self.trust_level + interaction.trust_change))
            self.cooperation_history = self.cooperation_history * 0.95 - 0.03

        self.last_updated = datetime.now().timestamp()

    def update_llm_mind_state(self, mind: LLMInferredMind) -> None:
        """v2: 更新 LLM 推断的心智状态"""
        self.current_mind_state = mind
        self.last_llm_inference = datetime.now().timestamp()

        # 从 LLM 推断中提取信念
        for belief_text in mind.beliefs[:3]:
            # 检查是否已存在相似信念
            existing = [b for b in self.inferred_beliefs if belief_text[:20] in b.content]
            if not existing:
                self.add_belief(
                    content=belief_text,
                    confidence=mind.confidence,
                    source="llm",
                    evidence=f"LLM推断: {mind.reasoning[:50]}"
                )

        # 更新意图历史
        if mind.primary_intent:
            self.inferred_intentions.append(mind.primary_intent)
            if len(self.inferred_intentions) > 20:
                self.inferred_intentions = self.inferred_intentions[-20:]

        # 更新欺骗信号
        if mind.deception_signals:
            # 检测到欺骗 → 降低信任
            self.trust_level = max(0.0, self.trust_level - 0.1)

        self.last_updated = datetime.now().timestamp()

    def rebuild_conversation_summary(self, max_interactions: int = 20) -> str:
        """
        v2: 从最近交互历史重建对话摘要

        用于给 LLM 提供上下文进行意图/欺骗分析。
        """
        recent = self.interaction_history[-max_interactions:] if self.interaction_history else []

        if not recent:
            return ""

        lines = []
        for i, interaction in enumerate(recent):
            role = "对方" if interaction.type in ("statement", "task_response") else "我方"
            lines.append(f"[{i+1}] {role} ({interaction.type}): {interaction.content[:80]}")

        self.conversation_summary = "\n".join(lines)
        return self.conversation_summary

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
            "current_mind_state": {
                "primary_intent": self.current_mind_state.primary_intent if self.current_mind_state else None,
                "emotional_state": self.current_mind_state.emotional_state if self.current_mind_state else None,
                "deception_signals": self.current_mind_state.deception_signals if self.current_mind_state else [],
                "confidence": self.current_mind_state.confidence if self.current_mind_state else None,
            } if self.current_mind_state else None,
            "interaction_patterns": self.interaction_patterns,
        }


class DeceptionAssessment:
    """欺骗评估结果"""
    def __init__(self):
        self.likely: bool = False
        self.confidence: float = 0.5
        self.reasons: list[str] = []
        self.signals: list[str] = []
        # v2: LLM 原始分析
        self.llm_analysis: str = ""
        self.llm_confidence: float = 0.0


@dataclass
class IntentionPrediction:
    """意图预测 v2"""
    intention: str
    probability: float
    based_on: list[str]
    # v2: LLM 推理
    category: IntentionCategory = IntentionCategory.UNKNOWN
    reasoning: str = ""
    alternatives: list[str] = field(default_factory=list)


class TheoryOfMind:
    """
    他人心智理论 v2

    v2 升级：
    1. LLM 驱动的意图推断（替代简单统计）
    2. LLM 驱动的欺骗检测（替代规则匹配）
    3. 自动从文本推断信念
    4. 定期刷新心智模型
    """

    # LLM 推断最小间隔（避免频繁调用）
    LLM_INFERENCE_COOLDOWN = 60.0  # 秒

    def __init__(
        self,
        agent_id: str,
        llm_adapter=None,  # LLM 适配器（用于 v2 LLM 推断）
    ):
        self.agent_id = agent_id
        self.llm_adapter = llm_adapter

        # 他人模型
        self.other_models: dict[str, OtherAgentModel] = {}

        # 交互记录（所有他人）
        self.all_interactions: list[Interaction] = []

    def create_model(self, other_id: str, name: str = "Unknown") -> OtherAgentModel:
        if other_id in self.other_models:
            return self.other_models[other_id]
        model = OtherAgentModel(agent_id=other_id, name=name)
        self.other_models[other_id] = model
        return model

    def get_model(self, other_id: str) -> OtherAgentModel | None:
        return self.other_models.get(other_id)

    # ─────────────────────────────────────────────────────────────────────────
    # v2: LLM 驱动的意图推断
    # ─────────────────────────────────────────────────────────────────────────

    async def infer_intent_llm(
        self,
        other_id: str,
        current_message: str,
        context: str | None = None,
    ) -> LLMInferredMind | None:
        """
        v2 核心：使用 LLM 推断他人意图、情绪、信念（异步）

        Args:
            other_id: 对方 Agent ID
            current_message: 对方当前消息
            context: 可选的额外上下文

        Returns:
            LLMInferredMind: LLM 推断的心智状态
        """
        if not self.llm_adapter:
            return None

        model = self.get_model(other_id)
        if not model:
            return None

        # 重建对话摘要
        conversation = model.rebuild_conversation_summary(max_interactions=15)

        system_prompt = """你是一个专业的心理洞察分析师，擅长从对话中推断他人的真实意图、情绪状态和潜在信念。

分析原则：
1. 区分"说了什么"和"真正想要什么"
2. 注意语言中的矛盾和回避
3. 结合历史行为模式判断
4. 识别建立信任 vs 操纵的信号
5. 考虑文化背景和关系动态

输出格式（JSON）：
{
  "primary_intent": "最主要意图（一句话）",
  "intent_probability": 0.85,
  "secondary_intents": ["次要意图1", "次要意图2"],
  "emotional_state": "情绪状态描述",
  "beliefs": ["推断的信念1", "信念2"],
  "knowledge_gaps": ["对方可能不知道的关键信息"],
  "deception_signals": ["可能的欺骗信号1"],
  "confidence": 0.8,
  "reasoning": "简短推理过程（50字以内）"
}"""

        user_prompt = f"""分析以下对话中对方的真实意图：

对方：{other_id}
关系：信任度 {model.trust_level:.0%}，合作历史 {model.cooperation_history:.0%}

历史对话：
{conversation if conversation else "(无历史)"}

当前消息：
{current_message}

{context or ""}

请分析对方的真实意图和心理状态。"""

        try:
            response = await self.llm_adapter.generate_with_system(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

            # 解析 JSON
            import json
            import re

            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                return None

            data = json.loads(json_match.group())

            mind = LLMInferredMind(
                primary_intent=data.get("primary_intent", ""),
                intent_probability=data.get("intent_probability", 0.5),
                secondary_intents=data.get("secondary_intents", []),
                emotional_state=data.get("emotional_state", ""),
                beliefs=data.get("beliefs", []),
                knowledge_gaps=data.get("knowledge_gaps", []),
                deception_signals=data.get("deception_signals", []),
                confidence=data.get("confidence", 0.5),
                reasoning=data.get("reasoning", ""),
                raw_analysis=response,
            )

            # 更新模型
            model.update_llm_mind_state(mind)

            return mind

        except Exception:
            return None

    def infer_intent_fallback(
        self,
        other_id: str,
        current_message: str | None = None,
    ) -> list[IntentionPrediction]:
        """
        Fallback：规则-based 意图预测（无 LLM 时）

        统计方法：
        - 能力置信度 × 关系强度
        - 合作历史加权
        - 信任水平调整
        """
        if other_id not in self.other_models:
            return []

        model = self.other_models[other_id]
        predictions = []

        # 基于能力推断
        for cap_name, cap in model.inferred_capabilities.items():
            if cap.confidence > 0.5:
                predictions.append(IntentionPrediction(
                    intention=f"使用{cap_name}能力",
                    category=IntentionCategory.COOPERATION,
                    probability=cap.confidence * model.relationship_strength,
                    based_on=[f"观察到使用{cap_name}能力"],
                    reasoning="基于能力观察的统计推断",
                ))

        # 基于合作历史
        if model.cooperation_history > 0.6:
            predictions.append(IntentionPrediction(
                intention="合作共赢",
                category=IntentionCategory.COOPERATION,
                probability=model.cooperation_history * 0.8,
                based_on=["合作历史良好"],
                reasoning="基于合作历史的统计推断",
            ))
        elif model.cooperation_history < 0.3:
            predictions.append(IntentionPrediction(
                intention="竞争或防备",
                category=IntentionCategory.COMPETITION,
                probability=(1 - model.cooperation_history) * 0.7,
                based_on=["合作历史不佳"],
                reasoning="基于合作历史的统计推断",
            ))

        # 基于信任
        if model.trust_level > 0.7:
            predictions.append(IntentionPrediction(
                intention="信任并分享",
                category=IntentionCategory.TRUST_BUILDING,
                probability=model.trust_level * 0.6,
                based_on=["高信任水平"],
                reasoning="基于信任水平的统计推断",
            ))

        predictions.sort(key=lambda p: p.probability, reverse=True)
        return predictions[:5]

    async def predict_intention_llm(
        self,
        other_id: str,
        context: str | None = None,
        current_message: str | None = None,
    ) -> list[IntentionPrediction]:
        """
        v2 主接口：预测他人意图（LLM 优先）

        如果有 LLM：
        1. 调用 infer_intent_llm 获取 LLMInferredMind
        2. 转换为 IntentionPrediction 列表

        如果无 LLM：
        → 回退到 infer_intent_fallback
        """
        if not self.llm_adapter:
            return self.infer_intent_fallback(other_id, current_message)

        model = self.get_model(other_id)
        if not model:
            return []

        # 冷却检查：避免过于频繁的 LLM 调用
        now = datetime.now().timestamp()
        if model.last_llm_inference > 0:
            elapsed = now - model.last_llm_inference
            if elapsed < self.LLM_INFERENCE_COOLDOWN and model.current_mind_state:
                # 在冷却期内，直接从缓存的心智状态生成预测
                return self._mind_state_to_predictions(model.current_mind_state)

        # 调用 LLM
        mind = await self.infer_intent_llm(other_id, current_message or "", context)
        if not mind:
            return self.infer_intent_fallback(other_id, current_message)

        return self._mind_state_to_predictions(mind)

    def _mind_state_to_predictions(
        self,
        mind: LLMInferredMind,
    ) -> list[IntentionPrediction]:
        """将 LLMInferredMind 转换为 IntentionPrediction 列表"""
        predictions = []

        # 主意图
        category = self._intent_to_category(mind.primary_intent)
        predictions.append(IntentionPrediction(
            intention=mind.primary_intent,
            category=category,
            probability=mind.intent_probability,
            based_on=["LLM 推断"],
            reasoning=mind.reasoning,
        ))

        # 次要意图
        for intent in mind.secondary_intents[:3]:
            predictions.append(IntentionPrediction(
                intention=intent,
                category=self._intent_to_category(intent),
                probability=mind.intent_probability * 0.6,
                based_on=["LLM 推断（次要）"],
                reasoning="次要意图",
            ))

        return predictions

    def _intent_to_category(self, intent: str) -> IntentionCategory:
        """将意图文本映射到类别"""
        intent_lower = intent.lower()

        if any(k in intent_lower for k in ["合作", "共赢", "一起", "共同", "cooperat", "help"]):
            return IntentionCategory.COOPERATION
        if any(k in intent_lower for k in ["竞争", "赢", "超过", "compete"]):
            return IntentionCategory.COMPETITION
        if any(k in intent_lower for k in ["了解", "知道", "信息", "learn", "know"]):
            return IntentionCategory.INFORMATION_GATHERING
        if any(k in intent_lower for k in ["操纵", "利用", "manipulat", "exploit"]):
            return IntentionCategory.MANIPULATION
        if any(k in intent_lower for k in ["帮助", "帮忙", "help", "assist"]):
            return IntentionCategory.GENUINE_HELP
        if any(k in intent_lower for k in ["保护", "防御", "防备", "protect", "defend"]):
            return IntentionCategory.SELF_PROTECTION
        if any(k in intent_lower for k in ["信任", "相信", "建立", "trust", "build"]):
            return IntentionCategory.TRUST_BUILDING

        return IntentionCategory.UNKNOWN

    # ─────────────────────────────────────────────────────────────────────────
    # v2: LLM 驱动的欺骗检测
    # ─────────────────────────────────────────────────────────────────────────

    async def detect_deception_llm(
        self,
        other_id: str,
        statement: str,
    ) -> DeceptionAssessment | None:
        """
        v2 核心：使用 LLM 检测欺骗（异步）

        分析维度：
        1. 语言矛盾（与历史陈述矛盾）
        2. 情绪不匹配（内容与情绪不一致）
        3. 夸张信号（绝对化用语、过度的自我提升）
        4. 回避信号（转移话题、模糊回答）
        5. 利益动机（欺骗是否符合对方利益）
        """
        if not self.llm_adapter:
            return None

        model = self.get_model(other_id)
        if not model:
            return None

        # 获取已知信念
        beliefs_text = ""
        if model.inferred_beliefs:
            beliefs = [b.content for b in model.inferred_beliefs[-5:]]
            beliefs_text = "\n".join(f"- {b}" for b in beliefs)

        # 历史陈述摘要
        history_summary = ""
        if model.interaction_history:
            statements = [
                i.content[:80]
                for i in model.interaction_history[-10:]
                if i.type == "statement"
            ]
            if statements:
                history_summary = "\n".join(f"- {s}" for s in statements)

        system_prompt = """你是一个专业的欺骗检测分析师。你需要判断对方当前陈述是否可能存在欺骗。

检测维度：
1. **语言矛盾**：与之前陈述或已知信念矛盾
2. **情绪不匹配**：陈述内容与表达情绪不一致
3. **夸张信号**：使用绝对化用语（"永远"/"一定"/"所有人都..."）
4. **回避信号**：模糊回答、转移话题、过度解释
5. **利益动机**：欺骗是否符合对方当前利益
6. **可信度**：陈述细节充分 vs 过于笼统

输出格式（JSON）：
{
  "likely": true/false,
  "confidence": 0.7,
  "signals": ["检测到的欺骗信号1", "信号2"],
  "reasons": ["判断理由1", "理由2"],
  "analysis": "详细分析（3-5句话）"
}"""

        user_prompt = f"""欺骗检测分析：

对方：{other_id}
信任历史：{model.trust_level:.0%}
合作历史：{model.cooperation_history:.0%}

对方已知信念：
{beliefs_text if beliefs_text else "(无)"}

对方历史陈述：
{history_summary if history_summary else "(无历史陈述)"}

当前陈述：
"{statement}"

请判断是否存在欺骗迹象。"""

        try:
            response = await self.llm_adapter.generate_with_system(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

            import json
            import re

            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                return None

            data = json.loads(json_match.group())

            assessment = DeceptionAssessment()
            assessment.likely = data.get("likely", False)
            assessment.confidence = data.get("confidence", 0.5)
            assessment.signals = data.get("signals", [])
            assessment.reasons = data.get("reasons", [])
            assessment.llm_analysis = data.get("analysis", "")
            assessment.llm_confidence = data.get("confidence", 0.5)

            return assessment

        except Exception:
            return None

    def detect_deception_fallback(
        self,
        other_id: str,
        statement: str,
    ) -> DeceptionAssessment:
        """
        Fallback：规则-based 欺骗检测（无 LLM 时）
        """
        assessment = DeceptionAssessment()

        if other_id not in self.other_models:
            return assessment

        model = self.other_models[other_id]

        # 检查与历史矛盾
        for interaction in model.interaction_history[-5:]:
            if interaction.type == "statement":
                if interaction.content[:50] == statement[:50]:
                    assessment.signals.append("与近期陈述重复")
                    assessment.confidence += 0.1

        # 检查与已知信念矛盾
        for belief in model.inferred_beliefs:
            if belief.source == "statement" and belief.content[:30] == statement[:30]:
                if belief.confidence > 0.7:
                    assessment.signals.append("与之前陈述矛盾")
                    assessment.likely = True
                    assessment.confidence += 0.3

        # 检查信任水平
        if model.trust_level < 0.3:
            assessment.signals.append("历史信任水平低")
            assessment.confidence += 0.1

        assessment.confidence = min(1.0, assessment.confidence)
        assessment.likely = assessment.confidence > 0.6

        if assessment.likely:
            assessment.reasons.append("检测到欺骗信号")

        return assessment

    async def detect_deception(
        self,
        other_id: str,
        statement: str,
    ) -> DeceptionAssessment:
        """
        v2 主接口：欺骗检测（LLM 优先，无 LLM 回退到规则）
        """
        if self.llm_adapter:
            result = await self.detect_deception_llm(other_id, statement)
            if result:
                return result

        return self.detect_deception_fallback(other_id, statement)

    # ─────────────────────────────────────────────────────────────────────────
    # 原有接口（兼容）
    # ─────────────────────────────────────────────────────────────────────────

    def infer_capability(
        self,
        other_id: str,
        capability: str,
        confidence: float,
        evidence: str
    ) -> None:
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
        if other_id not in self.other_models:
            self.create_model(other_id)
        model = self.other_models[other_id]
        if success:
            if capability in model.inferred_capabilities:
                cap = model.inferred_capabilities[capability]
                cap.confidence = min(1.0, cap.confidence + quality * 0.1)
                cap.evidence.append(f"Observed success: {quality:.2f}")
            else:
                model.add_capability(capability, 0.6, "First success observation")
        else:
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
        if other_id not in self.other_models:
            self.create_model(other_id)
        self.other_models[other_id].add_belief(content, confidence, source, evidence)

    def record_statement(
        self,
        other_id: str,
        statement: str,
        context: str = ""
    ) -> None:
        if other_id not in self.other_models:
            self.create_model(other_id)
        model = self.other_models[other_id]

        contradictions = [
            b for b in model.inferred_beliefs
            if b.content[:30] == statement[:30] and abs(b.confidence - 0.5) > 0.3
        ]

        if contradictions:
            model.record_interaction(Interaction(
                type="statement",
                content=statement,
                outcome="neutral",
                trust_change=-0.05
            ))
        else:
            model.record_interaction(Interaction(
                type="statement",
                content=statement,
                outcome="neutral",
                trust_change=0.01
            ))

    def predict_intention(
        self,
        other_id: str,
        context: str | None = None
    ) -> list[IntentionPrediction]:
        """
        同步接口（向后兼容）：意图预测

        优先使用 LLM（如果可用），否则回退到规则方法。
        注意：这是同步版本，如果需要真正的 LLM 分析，使用 predict_intention_llm。
        """
        # 同步版本只支持 fallback
        return self.infer_intent_fallback(other_id, context)

    def update_from_interaction(
        self,
        other_id: str,
        interaction_type: str,
        content: str,
        outcome: str,
        trust_change: float
    ) -> None:
        if other_id not in self.other_models:
            self.create_model(other_id)
        model = self.other_models[other_id]

        interaction = Interaction(
            type=interaction_type,
            content=content[:100],
            outcome=outcome,
            trust_change=trust_change
        )

        model.record_interaction(interaction)
        self.all_interactions.append(interaction)

        if model.interaction_history:
            recent_outcomes = [i.outcome for i in model.interaction_history[-10:]]
            accuracy = sum(1 for o in recent_outcomes if o in ["success", "neutral"]) / len(recent_outcomes)
            model.model_accuracy = model.model_accuracy * 0.9 + accuracy * 0.1

    def get_relationship_summary(self, other_id: str) -> str:
        if other_id not in self.other_models:
            return f"与 {other_id} 没有交互记录"

        model = self.other_models[other_id]

        if model.trust_level > 0.7:
            trust_desc = "高度信任"
        elif model.trust_level > 0.5:
            trust_desc = "一般信任"
        elif model.trust_level > 0.3:
            trust_desc = "谨慎信任"
        else:
            trust_desc = "不信任"

        mind_info = ""
        if model.current_mind_state:
            mind_info = f"\n- 当前推断意图：{model.current_mind_state.primary_intent} ({model.current_mind_state.intent_probability:.0%})"
            if model.current_mind_state.emotional_state:
                mind_info += f"\n- 当前情绪：{model.current_mind_state.emotional_state}"

        return f"""
与 {model.name} ({other_id}) 的关系：
- 交互次数：{len(model.interaction_history)}
- {trust_desc}（{model.trust_level:.2f}）
- 合作历史：{model.cooperation_history:.2f}
- 已知能力：{', '.join(model.inferred_capabilities.keys()) or '未知'}
- 模型准确度：{model.model_accuracy:.2f}{mind_info}
        """.strip()

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "model_count": len(self.other_models),
            "total_interactions": len(self.all_interactions),
            "models": [m.to_dict() for m in self.other_models.values()],
        }
