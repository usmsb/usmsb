"""
Analogical Reasoning Engine

类比推理引擎：基于相似性的推理
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import logging

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
class AnalogicalMapping:
    """类比映射"""

    source_domain: str
    target_domain: str
    attribute_mappings: Dict[str, str]
    relation_mappings: Dict[str, str]
    similarity_score: float


@dataclass
class Case:
    """案例"""

    case_id: str
    domain: str
    attributes: Dict[str, Any]
    relations: List[Tuple[str, str, str]]
    outcome: Any


class AnalogicalEngine(BaseReasoningEngine):
    """
    类比推理引擎

    支持：
    - 结构映射
    - 属性相似性计算
    - 关系相似性计算
    - 案例检索与推理
    """

    def __init__(
        self,
        knowledge_adapter: Optional[IKnowledgeGraphAdapter] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(knowledge_adapter, config)
        self._cases: Dict[str, Case] = {}
        self._domain_knowledge: Dict[str, Dict[str, Any]] = {}

    @property
    def engine_type(self) -> ReasoningType:
        return ReasoningType.ANALOGICAL

    def add_case(self, case: Case) -> None:
        self._cases[case.case_id] = case

    def add_domain_knowledge(
        self, domain: str, attributes: Dict[str, Any], relations: List[Tuple[str, str, str]]
    ) -> None:
        self._domain_knowledge[domain] = {
            "attributes": attributes,
            "relations": relations,
        }

    def _calculate_attribute_similarity(
        self, attrs1: Dict[str, Any], attrs2: Dict[str, Any]
    ) -> Tuple[float, Dict[str, float]]:
        if not attrs1 or not attrs2:
            return 0.0, {}

        similarities = {}
        common_keys = set(attrs1.keys()) & set(attrs2.keys())

        for key in common_keys:
            v1, v2 = attrs1[key], attrs2[key]

            if type(v1) != type(v2):
                similarities[key] = 0.0
            elif isinstance(v1, (int, float)):
                max_val = max(abs(v1), abs(v2), 1)
                similarities[key] = 1.0 - abs(v1 - v2) / max_val
            elif isinstance(v1, str):
                if v1 == v2:
                    similarities[key] = 1.0
                else:
                    words1, words2 = set(v1.lower().split()), set(v2.lower().split())
                    if words1 and words2:
                        intersection = len(words1 & words2)
                        union = len(words1 | words2)
                        similarities[key] = intersection / union
                    else:
                        similarities[key] = 0.0
            elif isinstance(v1, bool):
                similarities[key] = 1.0 if v1 == v2 else 0.0
            else:
                similarities[key] = 1.0 if v1 == v2 else 0.0

        overall = sum(similarities.values()) / len(common_keys) if common_keys else 0.0
        return overall, similarities

    def _calculate_relation_similarity(
        self, rels1: List[Tuple[str, str, str]], rels2: List[Tuple[str, str, str]]
    ) -> Tuple[float, List[Dict[str, Any]]]:
        if not rels1 or not rels2:
            return 0.0, []

        matches = []

        for r1 in rels1:
            for r2 in rels2:
                if r1[1] == r2[1]:
                    matches.append(
                        {
                            "source": r1,
                            "target": r2,
                            "relation": r1[1],
                            "match": True,
                        }
                    )

        max_rels = max(len(rels1), len(rels2))
        similarity = len(matches) / max_rels if max_rels > 0 else 0.0

        return similarity, matches

    def _find_similar_cases(
        self,
        target_attributes: Dict[str, Any],
        target_relations: List[Tuple[str, str, str]],
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        similar = []

        for case_id, case in self._cases.items():
            attr_sim, attr_details = self._calculate_attribute_similarity(
                target_attributes, case.attributes
            )
            rel_sim, rel_details = self._calculate_relation_similarity(
                target_relations, case.relations
            )

            overall_sim = 0.6 * attr_sim + 0.4 * rel_sim

            similar.append(
                {
                    "case": case,
                    "similarity": overall_sim,
                    "attribute_similarity": attr_sim,
                    "relation_similarity": rel_sim,
                    "attribute_details": attr_details,
                    "relation_details": rel_details,
                }
            )

        similar.sort(key=lambda x: x["similarity"], reverse=True)
        return similar[:top_k]

    def _create_mapping(self, source_case: Case, target_attrs: Dict[str, Any]) -> AnalogicalMapping:
        attr_mappings = {}
        for s_attr, s_val in source_case.attributes.items():
            for t_attr, t_val in target_attrs.items():
                if s_attr == t_attr:
                    attr_mappings[s_attr] = t_attr
                    break

        rel_mappings = {}
        for rel in source_case.relations:
            rel_key = f"{rel[0]}_{rel[1]}_{rel[2]}"
            rel_mappings[rel_key] = rel_key

        _, attr_sim = self._calculate_attribute_similarity(source_case.attributes, target_attrs)

        return AnalogicalMapping(
            source_domain=source_case.domain,
            target_domain="target",
            attribute_mappings=attr_mappings,
            relation_mappings=rel_mappings,
            similarity_score=sum(attr_sim.values()) / len(attr_sim) if attr_sim else 0.0,
        )

    async def reason(
        self, premises: List[Any], context: Optional[Dict[str, Any]] = None
    ) -> ReasoningResult:
        context = context or {}

        reasoning_chain: List[ReasoningStep] = []

        if not premises:
            return self._create_result(
                conclusion="无法进行类比推理：缺少输入",
                confidence=ConfidenceScore(value=0.0),
                reasoning_chain=reasoning_chain,
            )

        first_premise = premises[0]

        if isinstance(first_premise, dict):
            target_attrs = first_premise.get("attributes", {})
            target_rels = first_premise.get("relations", [])
        else:
            target_attrs = {"content": str(first_premise)}
            target_rels = []

        similar_cases = self._find_similar_cases(target_attrs, target_rels)

        if not similar_cases:
            return self._create_result(
                conclusion="无法找到相似案例进行类比推理",
                confidence=ConfidenceScore(value=0.0),
                reasoning_chain=reasoning_chain,
            )

        for sim_case in similar_cases:
            case = sim_case["case"]

            mapping = self._create_mapping(case, target_attrs)

            step = self._create_step(
                step_type=ReasoningType.ANALOGICAL,
                input_premises=[f"目标: {target_attrs}"],
                output_conclusions=[f"类比源: {case.case_id} ({case.domain})"],
                inference_rule="structure_mapping",
                confidence=ConfidenceScore(value=sim_case["similarity"]),
                uncertainty=UncertaintyMeasure(
                    uncertainty_type=UncertaintyType.PROBABILISTIC,
                    value=sim_case["similarity"],
                    parameters={
                        "attribute_similarity": sim_case["attribute_similarity"],
                        "relation_similarity": sim_case["relation_similarity"],
                    },
                ),
                reasoning_trace=f"案例 {case.case_id} 相似度: {sim_case['similarity']:.2f} "
                f"(属性: {sim_case['attribute_similarity']:.2f}, "
                f"关系: {sim_case['relation_similarity']:.2f})",
            )
            reasoning_chain.append(step)

        best_case = similar_cases[0]
        best_outcome = best_case["case"].outcome

        transferred_outcome = best_outcome
        if isinstance(best_outcome, str) and "{target}" in best_outcome:
            transferred_outcome = best_outcome.replace("{target}", "目标对象")

        result = self._create_result(
            conclusion=transferred_outcome,
            confidence=ConfidenceScore(value=best_case["similarity"]),
            reasoning_chain=reasoning_chain,
            uncertainty=UncertaintyMeasure(
                uncertainty_type=UncertaintyType.PROBABILISTIC,
                value=best_case["similarity"],
            ),
            alternatives=[
                {
                    "case": sc["case"].case_id,
                    "outcome": sc["case"].outcome,
                    "similarity": sc["similarity"],
                }
                for sc in similar_cases[1:]
            ],
            explanations=[
                f"类比推理: 基于相似案例 {best_case['case'].case_id}",
                f"源域: {best_case['case'].domain}",
                f"相似度: {best_case['similarity']:.2%}",
                f"属性相似: {best_case['attribute_similarity']:.2%}",
                f"关系相似: {best_case['relation_similarity']:.2%}",
            ],
        )

        self._reasoning_history.append(result)
        return result

    async def validate_reasoning(self, reasoning_result: ReasoningResult) -> Tuple[bool, List[str]]:
        errors = []

        if reasoning_result.confidence.value < 0.3:
            errors.append("类比相似度过低，推理结论可能不可靠")

        if not reasoning_result.alternatives:
            errors.append("类比推理应考虑多个相似案例")

        return len(errors) == 0, errors

    def get_confidence(self, premises: List[Any], conclusion: Any) -> ConfidenceScore:
        if not premises:
            return ConfidenceScore(value=0.0)

        first_premise = premises[0]
        if isinstance(first_premise, dict):
            target_attrs = first_premise.get("attributes", {})
        else:
            target_attrs = {"content": str(first_premise)}

        similar_cases = self._find_similar_cases(target_attrs, [], top_k=1)

        if similar_cases:
            return ConfidenceScore(value=similar_cases[0]["similarity"])

        return ConfidenceScore(value=0.0)
