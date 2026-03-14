"""
Causal Reasoning Engine

因果推理引擎：因果关系分析、反事实推理
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from usmsb_sdk.reasoning.base import BaseReasoningEngine
from usmsb_sdk.reasoning.interfaces import (
    ConfidenceScore,
    IKnowledgeGraphAdapter,
    ReasoningResult,
    ReasoningStep,
    ReasoningType,
    UncertaintyMeasure,
    UncertaintyType,
)

logger = logging.getLogger(__name__)


@dataclass
class CausalRelation:
    """因果关系"""

    cause: str
    effect: str
    strength: float
    necessary: bool = False
    sufficient: bool = False
    conditions: list[str] = field(default_factory=list)


@dataclass
class Intervention:
    """干预操作"""

    variable: str
    value: Any
    description: str = ""


class CausalEngine(BaseReasoningEngine):
    """
    因果推理引擎

    支持：
    - 因果关系发现
    - 因果效应估计
    - 反事实推理
    - 干预分析
    """

    def __init__(
        self,
        knowledge_adapter: IKnowledgeGraphAdapter | None = None,
        config: dict[str, Any] | None = None,
    ):
        super().__init__(knowledge_adapter, config)
        self._causal_graph: dict[str, list[CausalRelation]] = defaultdict(list)
        self._variables: set[str] = set()
        self._observations: list[dict[str, Any]] = []

    @property
    def engine_type(self) -> ReasoningType:
        return ReasoningType.CAUSAL

    def add_causal_relation(
        self,
        cause: str,
        effect: str,
        strength: float,
        necessary: bool = False,
        sufficient: bool = False,
    ) -> None:
        relation = CausalRelation(
            cause=cause,
            effect=effect,
            strength=strength,
            necessary=necessary,
            sufficient=sufficient,
        )
        self._causal_graph[cause].append(relation)
        self._variables.add(cause)
        self._variables.add(effect)

    def add_observation(self, observation: dict[str, Any]) -> None:
        self._observations.append(observation)

    def _discover_causes(self, effect: str, depth: int = 2) -> list[dict[str, Any]]:
        causes = []

        for cause, relations in self._causal_graph.items():
            for rel in relations:
                if rel.effect == effect:
                    causes.append(
                        {
                            "cause": cause,
                            "strength": rel.strength,
                            "necessary": rel.necessary,
                            "sufficient": rel.sufficient,
                            "depth": 1,
                        }
                    )

                    if depth > 1:
                        indirect = self._discover_causes(cause, depth - 1)
                        for ind in indirect:
                            ind["depth"] += 1
                            ind["indirect_path"] = [ind.get("cause"), cause]
                        causes.extend(indirect)

        return causes

    def _estimate_causal_effect(
        self, cause: str, effect: str, observations: list[dict[str, Any]]
    ) -> tuple[float, dict[str, Any]]:
        if not observations:
            return 0.5, {"method": "prior", "confidence": 0.0}

        cause_present = [o for o in observations if o.get(cause) or o.get(cause) == 1]
        cause_absent = [o for o in observations if not o.get(cause) or o.get(cause) == 0]

        if not cause_present or not cause_absent:
            return 0.5, {"method": "insufficient_data", "confidence": 0.0}

        effect_when_cause_present = sum(
            1 for o in cause_present if o.get(effect) or o.get(effect) == 1
        ) / len(cause_present)
        effect_when_cause_absent = sum(
            1 for o in cause_absent if o.get(effect) or o.get(effect) == 1
        ) / len(cause_absent)

        causal_effect = effect_when_cause_present - effect_when_cause_absent

        return causal_effect, {
            "method": "difference_in_means",
            "p1": effect_when_cause_present,
            "p0": effect_when_cause_absent,
            "n1": len(cause_present),
            "n0": len(cause_absent),
            "confidence": min(len(cause_present), len(cause_absent)) / 100,
        }

    def _counterfactual_reasoning(
        self, factual: dict[str, Any], intervention: Intervention, target: str
    ) -> tuple[Any, ConfidenceScore, str]:
        var = intervention.variable
        new_value = intervention.value

        old_value = factual.get(var)
        if old_value is None:
            return None, ConfidenceScore(value=0.0), f"变量 {var} 不存在于事实中"

        target_value = factual.get(target)

        effect, stats = self._estimate_causal_effect(var, target, self._observations)

        if new_value or new_value == 1:
            if target_value or target_value == 1:
                counterfactual_target = target_value - effect
            else:
                counterfactual_target = target_value + effect
        else:
            if target_value or target_value == 1:
                counterfactual_target = target_value + effect
            else:
                counterfactual_target = target_value - effect

        counterfactual_target = max(0, min(1, counterfactual_target))

        confidence = ConfidenceScore(
            value=stats.get("confidence", 0.5),
            evidence_count=stats.get("n1", 0) + stats.get("n0", 0),
        )

        trace = (
            f"反事实推理: 如果 {var} = {new_value} (事实: {old_value}), "
            f"则 {target} = {counterfactual_target:.2f} (事实: {target_value})"
        )

        return counterfactual_target, confidence, trace

    async def reason(
        self, premises: list[Any], context: dict[str, Any] | None = None
    ) -> ReasoningResult:
        context = context or {}

        reasoning_chain: list[ReasoningStep] = []

        if not premises:
            return self._create_result(
                conclusion="无法进行因果推理：缺少输入",
                confidence=ConfidenceScore(value=0.0),
                reasoning_chain=reasoning_chain,
            )

        first_premise = premises[0]

        if isinstance(first_premise, dict):
            if "effect" in first_premise:
                effect = first_premise["effect"]
                causes = self._discover_causes(effect)

                causes.sort(key=lambda x: x["strength"] * (1 / x["depth"]), reverse=True)

                for c in causes[:3]:
                    step = self._create_step(
                        step_type=ReasoningType.CAUSAL,
                        input_premises=[effect],
                        output_conclusions=[c["cause"]],
                        inference_rule="causal_discovery",
                        confidence=ConfidenceScore(value=c["strength"]),
                        reasoning_trace=f"发现 {c['cause']} -> {effect} (强度: {c['strength']:.2f})",
                    )
                    reasoning_chain.append(step)

                best_cause = causes[0] if causes else {"cause": "未知原因", "strength": 0.0}

                result = self._create_result(
                    conclusion=f"{best_cause['cause']} 导致 {effect}",
                    confidence=ConfidenceScore(value=best_cause["strength"]),
                    reasoning_chain=reasoning_chain,
                    alternatives=list(causes[1:4]),
                    explanations=[
                        f"因果分析: {effect} 的可能原因",
                        f"最可能原因: {best_cause['cause']} (强度: {best_cause['strength']:.2f})",
                    ],
                )

            elif "intervention" in first_premise and "target" in first_premise:
                factual = first_premise.get("factual", {})
                intervention_data = first_premise["intervention"]
                target = first_premise["target"]

                intervention = Intervention(
                    variable=intervention_data.get("variable"),
                    value=intervention_data.get("value"),
                    description=intervention_data.get("description", ""),
                )

                cf_result, confidence, trace = self._counterfactual_reasoning(
                    factual, intervention, target
                )

                step = self._create_step(
                    step_type=ReasoningType.COUNTERFACTUAL,
                    input_premises=[str(factual), str(intervention_data)],
                    output_conclusions=[f"{target} = {cf_result}"],
                    inference_rule="counterfactual_intervention",
                    confidence=confidence,
                    uncertainty=UncertaintyMeasure(
                        uncertainty_type=UncertaintyType.PROBABILISTIC,
                        value=cf_result
                        if isinstance(cf_result, float)
                        else float(cf_result if cf_result else 0),
                    ),
                    reasoning_trace=trace,
                )
                reasoning_chain.append(step)

                result = self._create_result(
                    conclusion=f"如果 {intervention.variable} = {intervention.value}, 则 {target} = {cf_result:.2f}",
                    confidence=confidence,
                    reasoning_chain=reasoning_chain,
                    explanations=[
                        trace,
                        f"因果效应估计: {confidence.value:.2f}",
                    ],
                )
            else:
                result = self._create_result(
                    conclusion="无法识别的因果推理请求格式",
                    confidence=ConfidenceScore(value=0.0),
                    reasoning_chain=reasoning_chain,
                )
        else:
            effect = str(first_premise)
            causes = self._discover_causes(effect)

            if causes:
                best_cause = causes[0]

                step = self._create_step(
                    step_type=ReasoningType.CAUSAL,
                    input_premises=[effect],
                    output_conclusions=[best_cause["cause"]],
                    inference_rule="causal_discovery",
                    confidence=ConfidenceScore(value=best_cause["strength"]),
                    reasoning_trace=f"发现 {best_cause['cause']} -> {effect}",
                )
                reasoning_chain.append(step)

                result = self._create_result(
                    conclusion=f"{best_cause['cause']} 可能导致 {effect}",
                    confidence=ConfidenceScore(value=best_cause["strength"]),
                    reasoning_chain=reasoning_chain,
                    alternatives=list(causes[1:3]),
                )
            else:
                result = self._create_result(
                    conclusion=f"未找到 {effect} 的已知原因",
                    confidence=ConfidenceScore(value=0.0),
                    reasoning_chain=reasoning_chain,
                )

        self._reasoning_history.append(result)
        return result

    async def validate_reasoning(self, reasoning_result: ReasoningResult) -> tuple[bool, list[str]]:
        errors = []

        for step in reasoning_result.reasoning_chain:
            if step.inference_rule == "counterfactual_intervention":
                if step.confidence.value < 0.3:
                    errors.append("反事实推理置信度过低，可能存在混杂因素")

        if not reasoning_result.reasoning_chain:
            errors.append("因果推理未产生任何推理步骤")

        return len(errors) == 0, errors

    def get_confidence(self, premises: list[Any], conclusion: Any) -> ConfidenceScore:
        if not premises:
            return ConfidenceScore(value=0.0)

        first_premise = premises[0]
        effect = (
            str(first_premise)
            if not isinstance(first_premise, dict)
            else first_premise.get("effect", str(first_premise))
        )
        cause = str(conclusion)

        for _c, relations in self._causal_graph.items():
            for rel in relations:
                if rel.cause == cause and rel.effect == effect:
                    return ConfidenceScore(value=rel.strength)

        return ConfidenceScore(value=0.0)

    def intervene(
        self, variable: str, value: Any, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        context = context or {}

        effects = []
        for rel in self._causal_graph.get(variable, []):
            if value:
                predicted_effect = rel.strength
            else:
                predicted_effect = -rel.strength

            effects.append(
                {
                    "effect": rel.effect,
                    "change": predicted_effect,
                    "necessary": rel.necessary,
                    "sufficient": rel.sufficient,
                }
            )

        return {
            "intervention": {"variable": variable, "value": value},
            "predicted_effects": effects,
        }
