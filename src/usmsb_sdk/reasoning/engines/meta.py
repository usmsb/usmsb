"""
Meta-Reasoning Engine

元推理引擎：关于推理的推理
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from usmsb_sdk.reasoning.base import BaseReasoningEngine
from usmsb_sdk.reasoning.interfaces import (
    ConfidenceScore,
    IKnowledgeGraphAdapter,
    IReasoningEngine,
    ReasoningResult,
    ReasoningStep,
    ReasoningType,
)

logger = logging.getLogger(__name__)


@dataclass
class ReasoningStrategy:
    """推理策略"""

    strategy_id: str
    name: str
    applicable_types: list[ReasoningType]
    priority: int
    conditions: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningEvaluation:
    """推理评估"""

    evaluation_id: str
    result_id: str
    quality_score: float
    consistency_score: float
    completeness_score: float
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class MetaReasoningEngine(BaseReasoningEngine):
    """
    元推理引擎

    支持：
    - 推理策略选择
    - 推理质量评估
    - 推理过程优化
    - 推理资源管理
    """

    def __init__(
        self,
        knowledge_adapter: IKnowledgeGraphAdapter | None = None,
        config: dict[str, Any] | None = None,
    ):
        super().__init__(knowledge_adapter, config)
        self._engines: dict[ReasoningType, IReasoningEngine] = {}
        self._strategies: dict[str, ReasoningStrategy] = {}
        self._evaluations: dict[str, ReasoningEvaluation] = {}
        self._reasoning_history: list[ReasoningResult] = []
        self._initialize_strategies()

    @property
    def engine_type(self) -> ReasoningType:
        return ReasoningType.META

    def _initialize_strategies(self):
        default_strategies = [
            ReasoningStrategy(
                strategy_id="deductive_first",
                name="演绎优先策略",
                applicable_types=[ReasoningType.DEDUCTIVE],
                priority=100,
                conditions={"certainty": "high"},
            ),
            ReasoningStrategy(
                strategy_id="abductive_explanation",
                name="溯因解释策略",
                applicable_types=[ReasoningType.ABDUCTIVE],
                priority=80,
                conditions={"goal": "explanation"},
            ),
            ReasoningStrategy(
                strategy_id="analogical_similar",
                name="类比相似策略",
                applicable_types=[ReasoningType.ANALOGICAL],
                priority=70,
                conditions={"context": "similar_cases"},
            ),
            ReasoningStrategy(
                strategy_id="causal_analysis",
                name="因果分析策略",
                applicable_types=[ReasoningType.CAUSAL],
                priority=90,
                conditions={"goal": "causation"},
            ),
        ]
        for strategy in default_strategies:
            self._strategies[strategy.strategy_id] = strategy

    def register_engine(self, reasoning_type: ReasoningType, engine: IReasoningEngine) -> None:
        self._engines[reasoning_type] = engine

    def select_strategy(self, context: dict[str, Any]) -> list[ReasoningStrategy]:
        applicable = []

        for strategy in self._strategies.values():
            match_score = self._calculate_strategy_match(strategy, context)
            if match_score > 0.5:
                applicable.append((strategy, match_score))

        applicable.sort(key=lambda x: (x[0].priority, x[1]), reverse=True)
        return [s[0] for s in applicable]

    def _calculate_strategy_match(
        self, strategy: ReasoningStrategy, context: dict[str, Any]
    ) -> float:
        if not strategy.conditions:
            return 0.5

        match_score = 0.0
        total_conditions = len(strategy.conditions)

        for key, expected_value in strategy.conditions.items():
            actual_value = context.get(key)
            if actual_value == expected_value:
                match_score += 1.0
            elif isinstance(expected_value, str) and isinstance(actual_value, str):
                if expected_value.lower() in actual_value.lower():
                    match_score += 0.5

        return match_score / total_conditions if total_conditions > 0 else 0.5

    def evaluate_reasoning(self, reasoning_result: ReasoningResult) -> ReasoningEvaluation:
        issues = []
        recommendations = []

        quality_score = reasoning_result.confidence.value

        consistency_score = self._evaluate_consistency(reasoning_result)
        if consistency_score < 0.7:
            issues.append("推理链存在不一致")
            recommendations.append("检查推理步骤之间的逻辑关系")

        completeness_score = self._evaluate_completeness(reasoning_result)
        if completeness_score < 0.5:
            issues.append("推理不完整")
            recommendations.append("考虑更多相关因素")

        if reasoning_result.uncertainty and reasoning_result.uncertainty.value < 0.5:
            issues.append("不确定性较高")
            recommendations.append("寻求更多信息或使用更强的推理方法")

        overall_quality = 0.4 * quality_score + 0.3 * consistency_score + 0.3 * completeness_score

        evaluation = ReasoningEvaluation(
            evaluation_id=f"eval_{time.time():.0f}",
            result_id=reasoning_result.result_id,
            quality_score=overall_quality,
            consistency_score=consistency_score,
            completeness_score=completeness_score,
            issues=issues,
            recommendations=recommendations,
        )

        self._evaluations[evaluation.evaluation_id] = evaluation
        return evaluation

    def _evaluate_consistency(self, reasoning_result: ReasoningResult) -> float:
        if not reasoning_result.reasoning_chain:
            return 1.0

        contradictions = reasoning_result.contradictions
        if contradictions:
            return max(0.0, 1.0 - len(contradictions) * 0.3)

        chain = reasoning_result.reasoning_chain
        connected = 0
        total = len(chain) - 1 if len(chain) > 1 else 1

        for i in range(len(chain) - 1):
            current_outputs = set(chain[i].output_conclusions)
            next_inputs = set(chain[i + 1].input_premises)
            if current_outputs & next_inputs:
                connected += 1

        return connected / total if total > 0 else 1.0

    def _evaluate_completeness(self, reasoning_result: ReasoningResult) -> float:
        score = 0.5

        if reasoning_result.reasoning_chain:
            score += 0.2

        if reasoning_result.alternatives:
            score += 0.1

        if reasoning_result.explanations:
            score += 0.1

        if reasoning_result.uncertainty:
            score += 0.1

        return min(1.0, score)

    def optimize_reasoning(self, reasoning_result: ReasoningResult) -> dict[str, Any]:
        evaluation = self.evaluate_reasoning(reasoning_result)

        optimizations = []

        if evaluation.consistency_score < 0.7:
            optimizations.append(
                {
                    "type": "consistency",
                    "action": "resolve_contradictions",
                    "priority": "high",
                }
            )

        if evaluation.completeness_score < 0.5:
            optimizations.append(
                {
                    "type": "completeness",
                    "action": "add_missing_steps",
                    "priority": "medium",
                }
            )

        if reasoning_result.confidence.value < 0.5:
            optimizations.append(
                {
                    "type": "confidence",
                    "action": "gather_more_evidence",
                    "priority": "high",
                }
            )

        return {
            "evaluation": evaluation,
            "optimizations": optimizations,
            "recommended_actions": evaluation.recommendations,
        }

    def select_engine(self, context: dict[str, Any]) -> IReasoningEngine | None:
        strategies = self.select_strategy(context)

        for strategy in strategies:
            for rtype in strategy.applicable_types:
                if rtype in self._engines:
                    return self._engines[rtype]

        return None

    async def reason(
        self, premises: list[Any], context: dict[str, Any] | None = None
    ) -> ReasoningResult:
        context = context or {}

        reasoning_chain: list[ReasoningStep] = []

        start_time = time.time()

        selected_engine = self.select_engine(context)

        engine_selection_step = self._create_step(
            step_type=ReasoningType.META,
            input_premises=[str(context)],
            output_conclusions=[
                f"选择引擎: {selected_engine.engine_type.value if selected_engine else 'none'}"
            ],
            inference_rule="engine_selection",
            confidence=ConfidenceScore(value=0.8),
            reasoning_trace="元推理: 分析上下文并选择最佳推理引擎",
        )
        reasoning_chain.append(engine_selection_step)

        if selected_engine:
            result = await selected_engine.reason(premises, context)

            evaluation_step = self._create_step(
                step_type=ReasoningType.META,
                input_premises=[result.result_id],
                output_conclusions=[f"评估质量: {result.confidence.value:.2f}"],
                inference_rule="quality_evaluation",
                confidence=ConfidenceScore(value=0.9),
                reasoning_trace=f"元推理: 评估 {selected_engine.engine_type.value} 推理结果质量",
            )
            reasoning_chain.append(evaluation_step)

            evaluation = self.evaluate_reasoning(result)

            meta_conclusion = {
                "primary_result": result.conclusion,
                "engine_used": selected_engine.engine_type.value,
                "quality_score": evaluation.quality_score,
                "recommendations": evaluation.recommendations,
            }

            final_result = self._create_result(
                conclusion=meta_conclusion,
                confidence=ConfidenceScore(
                    value=result.confidence.value * evaluation.quality_score
                ),
                reasoning_chain=reasoning_chain + result.reasoning_chain,
                explanations=[
                    f"元推理协调: 使用 {selected_engine.engine_type.value} 引擎",
                    f"推理质量: {evaluation.quality_score:.2%}",
                    f"一致性: {evaluation.consistency_score:.2%}",
                    f"完整性: {evaluation.completeness_score:.2%}",
                ]
                + result.explanations,
            )
        else:
            strategies_step = self._create_step(
                step_type=ReasoningType.META,
                input_premises=[str(context)],
                output_conclusions=["无适用引擎"],
                inference_rule="fallback",
                confidence=ConfidenceScore(value=0.3),
                reasoning_trace="元推理: 无法找到适用的推理引擎",
            )
            reasoning_chain.append(strategies_step)

            final_result = self._create_result(
                conclusion="无法选择合适的推理引擎进行推理",
                confidence=ConfidenceScore(value=0.0),
                reasoning_chain=reasoning_chain,
                explanations=["建议: 注册更多推理引擎或提供更丰富的上下文"],
            )

        elapsed_time = time.time() - start_time
        final_result.metadata["elapsed_time"] = elapsed_time

        self._reasoning_history.append(final_result)
        return final_result

    async def validate_reasoning(self, reasoning_result: ReasoningResult) -> tuple[bool, list[str]]:
        evaluation = self.evaluate_reasoning(reasoning_result)

        return (
            evaluation.quality_score >= 0.5,
            evaluation.issues,
        )

    def get_confidence(self, premises: list[Any], conclusion: Any) -> ConfidenceScore:
        return ConfidenceScore(value=0.7)

    def get_reasoning_stats(self) -> dict[str, Any]:
        if not self._evaluations:
            return {"count": 0}

        evaluations = list(self._evaluations.values())

        return {
            "count": len(evaluations),
            "avg_quality": sum(e.quality_score for e in evaluations) / len(evaluations),
            "avg_consistency": sum(e.consistency_score for e in evaluations) / len(evaluations),
            "avg_completeness": sum(e.completeness_score for e in evaluations) / len(evaluations),
            "total_issues": sum(len(e.issues) for e in evaluations),
        }
