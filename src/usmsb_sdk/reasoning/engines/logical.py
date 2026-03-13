"""
Logical Reasoning Engines

逻辑推理引擎：演绎、归纳、溯因推理
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Set
import logging
import re
from collections import defaultdict

from usmsb_sdk.reasoning.base import BaseReasoningEngine
from usmsb_sdk.reasoning.interfaces import (
    IKnowledgeGraphAdapter,
    ReasoningType,
    ReasoningResult,
    ReasoningStep,
    ConfidenceScore,
    UncertaintyMeasure,
    UncertaintyType,
)

logger = logging.getLogger(__name__)


@dataclass
class LogicalRule:
    """逻辑规则"""

    rule_id: str
    rule_type: str
    premises: List[str]
    conclusion: str
    conditions: List[str] = field(default_factory=list)
    priority: int = 0
    confidence: float = 1.0


class DeductiveEngine(BaseReasoningEngine):
    """
    演绎推理引擎

    从一般到特殊的推理，保证前提真则结论必真。
    支持经典逻辑推理规则：
    - 肯定前件 (Modus Ponens)
    - 否定后件 (Modus Tollens)
    - 假言三段论
    - 析取三段论
    - 全称实例化
    """

    def __init__(
        self,
        knowledge_adapter: Optional[IKnowledgeGraphAdapter] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(knowledge_adapter, config)
        self._rules: Dict[str, LogicalRule] = {}
        self._facts: Set[str] = set()
        self._initialize_default_rules()

    @property
    def engine_type(self) -> ReasoningType:
        return ReasoningType.DEDUCTIVE

    def _initialize_default_rules(self):
        default_rules = [
            LogicalRule("mp_1", "modus_ponens", ["P->Q", "P"], "Q"),
            LogicalRule("mt_1", "modus_tollens", ["P->Q", "~Q"], "~P"),
            LogicalRule("hs_1", "hypothetical_syllogism", ["P->Q", "Q->R"], "P->R"),
            LogicalRule("ds_1", "disjunctive_syllogism", ["P|Q", "~P"], "Q"),
            LogicalRule("ds_2", "disjunctive_syllogism", ["P|Q", "~Q"], "P"),
        ]
        for rule in default_rules:
            self._rules[rule.rule_id] = rule

    def add_rule(self, rule: LogicalRule) -> None:
        self._rules[rule.rule_id] = rule

    def add_fact(self, fact: str) -> None:
        self._facts.add(fact)

    def _normalize_formula(self, formula: str) -> str:
        formula = formula.strip()
        formula = re.sub(r"\s+", " ", formula)
        return formula

    def _match_pattern(self, pattern: str, formula: str) -> Optional[Dict[str, str]]:
        pattern = self._normalize_formula(pattern)
        formula = self._normalize_formula(formula)

        if pattern == formula:
            return {}

        if "->" in pattern:
            parts = pattern.split("->")
            if len(parts) == 2 and "->" in formula:
                fparts = formula.split("->")
                if len(fparts) == 2:
                    return {
                        parts[0].strip(): fparts[0].strip(),
                        parts[1].strip(): fparts[1].strip(),
                    }

        if pattern.startswith("~"):
            if formula.startswith("~"):
                return {pattern[1:]: formula[1:]}
            elif formula.startswith("not "):
                return {pattern[1:]: formula[4:]}

        return None

    def _apply_modus_ponens(self, premises: List[str]) -> Tuple[Optional[str], ConfidenceScore]:
        for i, p1 in enumerate(premises):
            for j, p2 in enumerate(premises):
                if i == j:
                    continue

                if "->" in p1:
                    antecedent, consequent = p1.split("->", 1)
                    antecedent = antecedent.strip()
                    consequent = consequent.strip()

                    if p2 == antecedent:
                        conf = ConfidenceScore(value=1.0, evidence_count=2)
                        return consequent, conf

                    if p2.startswith("~") and antecedent.startswith("~"):
                        if p2[1:] == antecedent[1:]:
                            conf = ConfidenceScore(value=1.0, evidence_count=2)
                            return consequent, conf

        return None, ConfidenceScore(value=0.0)

    def _apply_modus_tollens(self, premises: List[str]) -> Tuple[Optional[str], ConfidenceScore]:
        for i, p1 in enumerate(premises):
            for j, p2 in enumerate(premises):
                if i == j:
                    continue

                if "->" in p1:
                    antecedent, consequent = p1.split("->", 1)
                    antecedent = antecedent.strip()
                    consequent = consequent.strip()

                    negated_consequent = f"~{consequent}"
                    if p2 == negated_consequent:
                        conf = ConfidenceScore(value=1.0, evidence_count=2)
                        return f"~{antecedent}", conf

        return None, ConfidenceScore(value=0.0)

    async def reason(
        self, premises: List[Any], context: Optional[Dict[str, Any]] = None
    ) -> ReasoningResult:
        context = context or {}
        normalized_premises = [self._normalize_formula(str(p)) for p in premises]

        reasoning_chain: List[ReasoningStep] = []
        derived_facts = set(normalized_premises)
        all_derived = []

        changed = True
        max_iterations = context.get("max_iterations", 100)
        iteration = 0

        while changed and iteration < max_iterations:
            changed = False
            iteration += 1

            current_premises = list(derived_facts)

            conclusion, confidence = self._apply_modus_ponens(current_premises)
            if conclusion and conclusion not in derived_facts:
                derived_facts.add(conclusion)
                all_derived.append(conclusion)
                changed = True

                step = self._create_step(
                    step_type=ReasoningType.DEDUCTIVE,
                    input_premises=[p for p in current_premises if "->" in p or p != conclusion][
                        :2
                    ],
                    output_conclusions=[conclusion],
                    inference_rule="modus_ponens",
                    confidence=confidence,
                    reasoning_trace=f"应用肯定前件规则推导出: {conclusion}",
                )
                reasoning_chain.append(step)

            conclusion, confidence = self._apply_modus_tollens(current_premises)
            if conclusion and conclusion not in derived_facts:
                derived_facts.add(conclusion)
                all_derived.append(conclusion)
                changed = True

                step = self._create_step(
                    step_type=ReasoningType.DEDUCTIVE,
                    input_premises=[p for p in current_premises if "->" in p][:1]
                    + [p for p in current_premises if p.startswith("~")][:1],
                    output_conclusions=[conclusion],
                    inference_rule="modus_tollens",
                    confidence=confidence,
                    reasoning_trace=f"应用否定后件规则推导出: {conclusion}",
                )
                reasoning_chain.append(step)

        final_conclusion = all_derived[-1] if all_derived else "无法推导出新结论"
        final_confidence = (
            reasoning_chain[-1].confidence if reasoning_chain else ConfidenceScore(value=0.5)
        )

        result = self._create_result(
            conclusion=final_conclusion,
            confidence=final_confidence,
            reasoning_chain=reasoning_chain,
            alternatives=[{"conclusion": c, "type": "derived"} for c in all_derived[:-1]]
            if len(all_derived) > 1
            else [],
            explanations=[step.reasoning_trace for step in reasoning_chain],
        )

        self._reasoning_history.append(result)
        return result

    async def validate_reasoning(self, reasoning_result: ReasoningResult) -> Tuple[bool, List[str]]:
        errors = []

        for step in reasoning_result.reasoning_chain:
            if step.inference_rule == "modus_ponens":
                has_implication = any("->" in p for p in step.input_premises)
                if not has_implication:
                    errors.append(f"步骤 {step.step_id}: 肯定前件需要包含蕴含式前提")

            elif step.inference_rule == "modus_tollens":
                has_negation = any(p.startswith("~") for p in step.input_premises)
                if not has_negation:
                    errors.append(f"步骤 {step.step_id}: 否定后件需要包含否定式前提")

        return len(errors) == 0, errors

    def get_confidence(self, premises: List[Any], conclusion: Any) -> ConfidenceScore:
        normalized_premises = [self._normalize_formula(str(p)) for p in premises]
        normalized_conclusion = self._normalize_formula(str(conclusion))

        for p in normalized_premises:
            if "->" in p:
                antecedent, consequent = p.split("->", 1)
                if consequent.strip() == normalized_conclusion:
                    if antecedent.strip() in normalized_premises:
                        return ConfidenceScore(value=1.0, evidence_count=2)

        return ConfidenceScore(value=0.0, evidence_count=len(premises))


class InductiveEngine(BaseReasoningEngine):
    """
    归纳推理引擎

    从特殊到一般的推理，结论具有概率性。
    支持：
    - 简单枚举归纳
    - 统计归纳
    - 类比归纳
    - 因果归纳
    """

    def __init__(
        self,
        knowledge_adapter: Optional[IKnowledgeGraphAdapter] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(knowledge_adapter, config)
        self._observations: List[Dict[str, Any]] = []
        self._hypotheses: Dict[str, Dict[str, Any]] = {}

    @property
    def engine_type(self) -> ReasoningType:
        return ReasoningType.INDUCTIVE

    def add_observation(self, observation: Dict[str, Any]) -> None:
        self._observations.append(observation)

    def _calculate_support(
        self, hypothesis: str, observations: List[Dict[str, Any]]
    ) -> Tuple[int, int, float]:
        supporting = 0
        total = len(observations)

        for obs in observations:
            if self._observation_supports_hypothesis(obs, hypothesis):
                supporting += 1

        ratio = supporting / total if total > 0 else 0.0
        return supporting, total, ratio

    def _observation_supports_hypothesis(
        self, observation: Dict[str, Any], hypothesis: str
    ) -> bool:
        obs_str = str(observation.get("content", observation))
        hyp_parts = hypothesis.lower().split()

        match_count = sum(1 for part in hyp_parts if part in obs_str.lower())
        return match_count >= len(hyp_parts) * 0.5

    def _generate_hypothesis(self, observations: List[Dict[str, Any]]) -> List[str]:
        hypotheses = []

        if not observations:
            return hypotheses

        feature_counts: Dict[str, int] = defaultdict(int)

        for obs in observations:
            content = str(obs.get("content", obs))
            words = content.lower().split()
            for word in set(words):
                if len(word) > 2:
                    feature_counts[word] += 1

        total = len(observations)
        for feature, count in feature_counts.items():
            if count >= total * 0.7:
                hypotheses.append(f"所有观察都具有特征 '{feature}'")

        return hypotheses

    async def reason(
        self, premises: List[Any], context: Optional[Dict[str, Any]] = None
    ) -> ReasoningResult:
        context = context or {}

        observations = []
        for p in premises:
            if isinstance(p, dict):
                observations.append(p)
            else:
                observations.append({"content": str(p)})

        self._observations.extend(observations)

        reasoning_chain: List[ReasoningStep] = []

        hypotheses = self._generate_hypothesis(observations)

        evaluated_hypotheses = []
        for hypothesis in hypotheses:
            supporting, total, ratio = self._calculate_support(hypothesis, observations)

            confidence = ConfidenceScore(
                value=ratio,
                sample_size=total,
                evidence_count=supporting,
            )

            evaluated_hypotheses.append(
                {
                    "hypothesis": hypothesis,
                    "supporting": supporting,
                    "total": total,
                    "ratio": ratio,
                    "confidence": confidence,
                }
            )

            step = self._create_step(
                step_type=ReasoningType.INDUCTIVE,
                input_premises=[str(o) for o in observations[:3]],
                output_conclusions=[hypothesis],
                inference_rule="enumerative_induction",
                confidence=confidence,
                uncertainty=UncertaintyMeasure(
                    uncertainty_type=UncertaintyType.PROBABILISTIC,
                    value=ratio,
                    parameters={"sample_size": total, "supporting": supporting},
                ),
                reasoning_trace=f"基于 {supporting}/{total} 个观察支持假设: {hypothesis}",
            )
            reasoning_chain.append(step)

        if not evaluated_hypotheses:
            return self._create_result(
                conclusion="无法从观察中归纳出有效假设",
                confidence=ConfidenceScore(value=0.0),
                reasoning_chain=reasoning_chain,
            )

        best_hypothesis = max(evaluated_hypotheses, key=lambda h: h["ratio"])

        result = self._create_result(
            conclusion=best_hypothesis["hypothesis"],
            confidence=best_hypothesis["confidence"],
            reasoning_chain=reasoning_chain,
            uncertainty=UncertaintyMeasure(
                uncertainty_type=UncertaintyType.PROBABILISTIC,
                value=best_hypothesis["ratio"],
                parameters={
                    "sample_size": best_hypothesis["total"],
                    "supporting": best_hypothesis["supporting"],
                },
            ),
            alternatives=[
                h for h in evaluated_hypotheses if h["hypothesis"] != best_hypothesis["hypothesis"]
            ],
            explanations=[
                f"归纳推理: 从 {len(observations)} 个观察中得出假设",
                f"支持度: {best_hypothesis['supporting']}/{best_hypothesis['total']} = {best_hypothesis['ratio']:.2%}",
            ],
        )

        self._reasoning_history.append(result)
        return result

    async def validate_reasoning(self, reasoning_result: ReasoningResult) -> Tuple[bool, List[str]]:
        errors = []

        if reasoning_result.confidence.value < 0.5:
            errors.append("归纳结论置信度过低")

        if reasoning_result.uncertainty:
            sample_size = reasoning_result.uncertainty.parameters.get("sample_size", 0)
            if sample_size < 5:
                errors.append(f"样本量过小 ({sample_size})，归纳结论可能不可靠")

        return len(errors) == 0, errors

    def get_confidence(self, premises: List[Any], conclusion: Any) -> ConfidenceScore:
        observations = [{"content": str(p)} for p in premises]
        hypothesis = str(conclusion)

        supporting, total, ratio = self._calculate_support(hypothesis, observations)

        return ConfidenceScore(
            value=ratio,
            sample_size=total,
            evidence_count=supporting,
        )


class AbductiveEngine(BaseReasoningEngine):
    """
    溯因推理引擎

    从结果推导最佳解释的推理。
    支持：
    - 最佳解释推理 (Inference to the Best Explanation)
    - 假设生成
    - 解释评估
    """

    def __init__(
        self,
        knowledge_adapter: Optional[IKnowledgeGraphAdapter] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(knowledge_adapter, config)
        self._explanation_templates: Dict[str, Dict[str, Any]] = {}

    @property
    def engine_type(self) -> ReasoningType:
        return ReasoningType.ABDUCTIVE

    def add_explanation_template(
        self,
        effect: str,
        possible_causes: List[str],
        prior_probabilities: Optional[Dict[str, float]] = None,
    ) -> None:
        self._explanation_templates[effect] = {
            "possible_causes": possible_causes,
            "prior_probabilities": prior_probabilities
            or {c: 1.0 / len(possible_causes) for c in possible_causes},
        }

    def _generate_hypotheses(
        self, observation: str, context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        hypotheses = []

        if observation in self._explanation_templates:
            template = self._explanation_templates[observation]
            for cause in template["possible_causes"]:
                prior = template["prior_probabilities"].get(cause, 0.5)
                hypotheses.append(
                    {
                        "cause": cause,
                        "prior_probability": prior,
                        "source": "template",
                    }
                )

        generic_causes = [
            f"{observation} 的自然原因",
            f"{observation} 的人为原因",
            f"{observation} 的随机因素",
        ]

        for cause in generic_causes:
            hypotheses.append(
                {
                    "cause": cause,
                    "prior_probability": 0.2,
                    "source": "generic",
                }
            )

        return hypotheses

    def _evaluate_hypothesis(
        self, hypothesis: Dict[str, Any], observation: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        cause = hypothesis["cause"]
        prior = hypothesis["prior_probability"]

        explanatory_power = 0.5
        if any(word in cause.lower() for word in observation.lower().split()):
            explanatory_power = 0.8

        simplicity = 1.0 / (1 + len(cause.split()))

        coherence = 0.5
        if "background" in context:
            background = context["background"]
            if any(word in str(background).lower() for word in cause.lower().split()):
                coherence = 0.9

        overall_score = prior * 0.3 + explanatory_power * 0.4 + simplicity * 0.15 + coherence * 0.15

        return {
            "cause": cause,
            "prior_probability": prior,
            "explanatory_power": explanatory_power,
            "simplicity": simplicity,
            "coherence": coherence,
            "overall_score": overall_score,
            "source": hypothesis["source"],
        }

    async def reason(
        self, premises: List[Any], context: Optional[Dict[str, Any]] = None
    ) -> ReasoningResult:
        context = context or {}

        if not premises:
            return self._create_result(
                conclusion="无观察数据，无法进行溯因推理",
                confidence=ConfidenceScore(value=0.0),
                reasoning_chain=[],
            )

        observation = str(premises[0])

        reasoning_chain: List[ReasoningStep] = []

        hypotheses = self._generate_hypotheses(observation, context)

        evaluated = []
        for hyp in hypotheses:
            eval_result = self._evaluate_hypothesis(hyp, observation, context)
            evaluated.append(eval_result)

            confidence = ConfidenceScore(
                value=eval_result["overall_score"],
                evidence_count=1,
            )

            step = self._create_step(
                step_type=ReasoningType.ABDUCTIVE,
                input_premises=[observation],
                output_conclusions=[eval_result["cause"]],
                inference_rule="inference_to_best_explanation",
                confidence=confidence,
                reasoning_trace=f"假设 '{eval_result['cause']}' 解释力={eval_result['explanatory_power']:.2f}, "
                f"先验={eval_result['prior_probability']:.2f}, "
                f"综合得分={eval_result['overall_score']:.2f}",
            )
            reasoning_chain.append(step)

        evaluated.sort(key=lambda x: x["overall_score"], reverse=True)

        best_explanation = (
            evaluated[0] if evaluated else {"cause": "无法解释", "overall_score": 0.0}
        )

        result = self._create_result(
            conclusion=best_explanation["cause"],
            confidence=ConfidenceScore(value=best_explanation["overall_score"]),
            reasoning_chain=reasoning_chain,
            uncertainty=UncertaintyMeasure(
                uncertainty_type=UncertaintyType.PROBABILISTIC,
                value=best_explanation["overall_score"],
                parameters={"method": "bayesian_abduction"},
            ),
            alternatives=[e for e in evaluated[1:4]],
            explanations=[
                f"对观察 '{observation}' 的最佳解释推理",
                f"最佳解释: {best_explanation['cause']}",
                f"解释力: {best_explanation['explanatory_power']:.2f}",
                f"简洁度: {best_explanation['simplicity']:.2f}",
                f"一致性: {best_explanation['coherence']:.2f}",
            ],
        )

        self._reasoning_history.append(result)
        return result

    async def validate_reasoning(self, reasoning_result: ReasoningResult) -> Tuple[bool, List[str]]:
        errors = []

        if reasoning_result.confidence.value < 0.3:
            errors.append("溯因推理结论置信度过低，解释可能不可靠")

        if len(reasoning_result.alternatives) == 0:
            errors.append("缺少备选解释，溯因推理需要考虑多种可能性")

        return len(errors) == 0, errors

    def get_confidence(self, premises: List[Any], conclusion: Any) -> ConfidenceScore:
        if not premises:
            return ConfidenceScore(value=0.0)

        observation = str(premises[0])
        conclusion_str = str(conclusion)

        hypotheses = self._generate_hypotheses(obsation, {})

        for hyp in hypotheses:
            if hyp["cause"] == conclusion_str:
                eval_result = self._evaluate_hypothesis(hyp, observation, {})
                return ConfidenceScore(value=eval_result["overall_score"])

        return ConfidenceScore(value=0.0)
