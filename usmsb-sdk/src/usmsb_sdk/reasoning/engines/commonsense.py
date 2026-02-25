"""
Commonsense Reasoning Engine

常识推理引擎：物理常识、社会常识推理
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Set
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
class CommonsenseRule:
    """常识规则"""

    rule_id: str
    domain: str
    condition: str
    conclusion: str
    confidence: float
    exceptions: List[str] = field(default_factory=list)


class CommonsenseEngine(BaseReasoningEngine):
    """
    常识推理引擎

    支持：
    - 物理常识推理
    - 社会常识推理
    - 日常常识推理
    - 规则库管理
    """

    def __init__(
        self,
        knowledge_adapter: Optional[IKnowledgeGraphAdapter] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(knowledge_adapter, config)
        self._rules: Dict[str, CommonsenseRule] = {}
        self._concept_properties: Dict[str, Dict[str, Any]] = {}
        self._physical_rules: List[Dict[str, Any]] = []
        self._social_rules: List[Dict[str, Any]] = []
        self._initialize_commonsense()

    @property
    def engine_type(self) -> ReasoningType:
        return ReasoningType.COMMONSENSE

    def _initialize_commonsense(self):
        physical_rules = [
            {
                "id": "gravity",
                "rule": "物体下落",
                "condition": "物体在空中且无支撑",
                "effect": "物体会下落",
                "confidence": 0.99,
            },
            {
                "id": "solid",
                "rule": "固体碰撞",
                "condition": "两个固体相互靠近",
                "effect": "会发生碰撞或阻挡",
                "confidence": 0.95,
            },
            {
                "id": "liquid",
                "rule": "液体流动",
                "condition": "液体在容器中且容器倾斜",
                "effect": "液体会流动",
                "confidence": 0.98,
            },
            {
                "id": "heat",
                "rule": "热传导",
                "condition": "热物体接触冷物体",
                "effect": "热量会从高温传递到低温",
                "confidence": 0.95,
            },
            {
                "id": "friction",
                "rule": "摩擦力",
                "condition": "物体在表面移动",
                "effect": "会产生摩擦力阻碍运动",
                "confidence": 0.9,
            },
        ]
        self._physical_rules = physical_rules

        social_rules = [
            {
                "id": "greeting",
                "rule": "问候回应",
                "condition": "A向B打招呼",
                "effect": "B通常会回应问候",
                "confidence": 0.85,
            },
            {
                "id": "help",
                "rule": "帮助感谢",
                "condition": "A帮助了B",
                "effect": "B通常会表示感谢",
                "confidence": 0.9,
            },
            {
                "id": "queue",
                "rule": "排队秩序",
                "condition": "有多人等待服务",
                "effect": "人们会排队等候",
                "confidence": 0.8,
            },
            {
                "id": "turn",
                "rule": "轮流说话",
                "condition": "多人对话中",
                "effect": "人们会轮流发言",
                "confidence": 0.75,
            },
            {
                "id": "apology",
                "rule": "道歉回应",
                "condition": "A向B道歉",
                "effect": "B通常会接受道歉",
                "confidence": 0.7,
            },
        ]
        self._social_rules = social_rules

        self._concept_properties = {
            "水": {"状态": "液体", "特性": ["流动", "透明"], "温度_凝固": 0, "温度_沸腾": 100},
            "冰": {"状态": "固体", "特性": ["硬", "冷"], "温度_融化": 0},
            "火": {"状态": "等离子体", "特性": ["热", "发光"], "危险": True},
            "石头": {"状态": "固体", "特性": ["硬", "重"]},
            "木头": {"状态": "固体", "特性": ["可燃", "轻"]},
            "人": {
                "类型": "生物",
                "特性": ["思考", "行走", "说话"],
                "需求": ["食物", "水", "睡眠"],
            },
            "鸟": {"类型": "动物", "特性": ["飞行", "鸣叫"], "部位": ["翅膀", "羽毛"]},
            "鱼": {"类型": "动物", "特性": ["游泳"], "环境": "水"},
            "汽车": {"类型": "交通工具", "动力": "燃料", "特性": ["快速移动"]},
            "房子": {"类型": "建筑", "功能": "居住", "特性": ["固定", "遮蔽"]},
        }

    def add_rule(self, rule: CommonsenseRule) -> None:
        self._rules[rule.rule_id] = rule

    def _match_rule(self, situation: str, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        matches = []
        situation_lower = situation.lower()

        for rule in rules:
            condition_words = rule["condition"].lower().split()
            match_count = sum(1 for word in condition_words if word in situation_lower)

            if match_count >= len(condition_words) * 0.5:
                matches.append(
                    {
                        "rule": rule,
                        "match_score": match_count / len(condition_words),
                    }
                )

        matches.sort(key=lambda x: x["match_score"], reverse=True)
        return matches

    def _infer_properties(
        self, concept: str, property_name: Optional[str] = None
    ) -> Dict[str, Any]:
        if concept not in self._concept_properties:
            return {"found": False, "concept": concept}

        props = self._concept_properties[concept]

        if property_name:
            if property_name in props:
                return {
                    "found": True,
                    "concept": concept,
                    "property": property_name,
                    "value": props[property_name],
                }
            return {"found": False, "concept": concept, "property": property_name}

        return {"found": True, "concept": concept, "properties": props}

    def _check_exception(self, rule: CommonsenseRule, context: Dict[str, Any]) -> bool:
        for exception in rule.exceptions:
            if exception in str(context):
                return True
        return False

    async def reason(
        self, premises: List[Any], context: Optional[Dict[str, Any]] = None
    ) -> ReasoningResult:
        context = context or {}

        reasoning_chain: List[ReasoningStep] = []

        if not premises:
            return self._create_result(
                conclusion="无法进行常识推理：缺少输入",
                confidence=ConfidenceScore(value=0.0),
                reasoning_chain=reasoning_chain,
            )

        first_premise = premises[0]

        if isinstance(first_premise, dict):
            query_type = first_premise.get("query_type", "inference")

            if query_type == "physical":
                situation = first_premise.get("situation", "")
                matches = self._match_rule(situation, self._physical_rules)

                if matches:
                    best_match = matches[0]
                    rule = best_match["rule"]

                    step = self._create_step(
                        step_type=ReasoningType.COMMONSENSE,
                        input_premises=[situation],
                        output_conclusions=[rule["effect"]],
                        inference_rule="physical_commonsense",
                        confidence=ConfidenceScore(
                            value=rule["confidence"] * best_match["match_score"]
                        ),
                        reasoning_trace=f"物理常识推理: {rule['condition']} -> {rule['effect']}",
                    )
                    reasoning_chain.append(step)

                    result = self._create_result(
                        conclusion=rule["effect"],
                        confidence=ConfidenceScore(
                            value=rule["confidence"] * best_match["match_score"]
                        ),
                        reasoning_chain=reasoning_chain,
                        alternatives=[m["rule"]["effect"] for m in matches[1:3]],
                        explanations=[
                            f"应用物理常识规则: {rule['rule']}",
                            f"条件: {rule['condition']}",
                            f"匹配度: {best_match['match_score']:.2%}",
                        ],
                    )
                else:
                    result = self._create_result(
                        conclusion="未找到匹配的物理常识规则",
                        confidence=ConfidenceScore(value=0.0),
                        reasoning_chain=reasoning_chain,
                    )

            elif query_type == "social":
                situation = first_premise.get("situation", "")
                matches = self._match_rule(situation, self._social_rules)

                if matches:
                    best_match = matches[0]
                    rule = best_match["rule"]

                    step = self._create_step(
                        step_type=ReasoningType.COMMONSENSE,
                        input_premises=[situation],
                        output_conclusions=[rule["effect"]],
                        inference_rule="social_commonsense",
                        confidence=ConfidenceScore(
                            value=rule["confidence"] * best_match["match_score"]
                        ),
                        uncertainty=UncertaintyMeasure(
                            uncertainty_type=UncertaintyType.PROBABILISTIC,
                            value=rule["confidence"],
                        ),
                        reasoning_trace=f"社会常识推理: {rule['condition']} -> {rule['effect']}",
                    )
                    reasoning_chain.append(step)

                    result = self._create_result(
                        conclusion=rule["effect"],
                        confidence=ConfidenceScore(
                            value=rule["confidence"] * best_match["match_score"]
                        ),
                        uncertainty=UncertaintyMeasure(
                            uncertainty_type=UncertaintyType.PROBABILISTIC,
                            value=rule["confidence"],
                        ),
                        reasoning_chain=reasoning_chain,
                        alternatives=[m["rule"]["effect"] for m in matches[1:3]],
                        explanations=[
                            f"应用社会常识规则: {rule['rule']}",
                            f"注意: 社会常识存在文化差异",
                        ],
                    )
                else:
                    result = self._create_result(
                        conclusion="未找到匹配的社会常识规则",
                        confidence=ConfidenceScore(value=0.0),
                        reasoning_chain=reasoning_chain,
                    )

            elif query_type == "property":
                concept = first_premise.get("concept", "")
                property_name = first_premise.get("property")

                props = self._infer_properties(concept, property_name)

                if props.get("found"):
                    if property_name:
                        conclusion = f"{concept} 的 {property_name} 是 {props['value']}"
                    else:
                        conclusion = f"{concept} 的属性: {props['properties']}"

                    step = self._create_step(
                        step_type=ReasoningType.COMMONSENSE,
                        input_premises=[concept],
                        output_conclusions=[conclusion],
                        inference_rule="concept_property_lookup",
                        confidence=ConfidenceScore(value=0.9),
                        reasoning_trace=f"查询概念属性: {concept}",
                    )
                    reasoning_chain.append(step)

                    result = self._create_result(
                        conclusion=conclusion,
                        confidence=ConfidenceScore(value=0.9),
                        reasoning_chain=reasoning_chain,
                    )
                else:
                    result = self._create_result(
                        conclusion=f"未找到概念 '{concept}' 的相关信息",
                        confidence=ConfidenceScore(value=0.0),
                        reasoning_chain=reasoning_chain,
                    )

            else:
                situation = str(first_premise.get("situation", first_premise))

                physical_matches = self._match_rule(situation, self._physical_rules)
                social_matches = self._match_rule(situation, self._social_rules)

                all_matches = [(m, "physical") for m in physical_matches] + [
                    (m, "social") for m in social_matches
                ]
                all_matches.sort(key=lambda x: x[0]["match_score"], reverse=True)

                if all_matches:
                    best_match, domain = all_matches[0]
                    rule = best_match["rule"]

                    step = self._create_step(
                        step_type=ReasoningType.COMMONSENSE,
                        input_premises=[situation],
                        output_conclusions=[rule["effect"]],
                        inference_rule=f"{domain}_commonsense",
                        confidence=ConfidenceScore(
                            value=rule["confidence"] * best_match["match_score"]
                        ),
                        reasoning_trace=f"常识推理 ({domain}): {rule['condition']} -> {rule['effect']}",
                    )
                    reasoning_chain.append(step)

                    result = self._create_result(
                        conclusion=rule["effect"],
                        confidence=ConfidenceScore(
                            value=rule["confidence"] * best_match["match_score"]
                        ),
                        reasoning_chain=reasoning_chain,
                        explanations=[
                            f"应用常识规则 ({domain}领域)",
                            f"规则: {rule['rule']}",
                        ],
                    )
                else:
                    result = self._create_result(
                        conclusion="未找到适用的常识规则",
                        confidence=ConfidenceScore(value=0.0),
                        reasoning_chain=reasoning_chain,
                    )
        else:
            situation = str(first_premise)

            physical_matches = self._match_rule(situation, self._physical_rules)
            social_matches = self._match_rule(situation, self._social_rules)

            all_matches = [(m, "physical") for m in physical_matches] + [
                (m, "social") for m in social_matches
            ]
            all_matches.sort(key=lambda x: x[0]["match_score"], reverse=True)

            if all_matches:
                best_match, domain = all_matches[0]
                rule = best_match["rule"]

                step = self._create_step(
                    step_type=ReasoningType.COMMONSENSE,
                    input_premises=[situation],
                    output_conclusions=[rule["effect"]],
                    inference_rule=f"{domain}_commonsense",
                    confidence=ConfidenceScore(
                        value=rule["confidence"] * best_match["match_score"]
                    ),
                    reasoning_trace=f"常识推理: {rule['effect']}",
                )
                reasoning_chain.append(step)

                result = self._create_result(
                    conclusion=rule["effect"],
                    confidence=ConfidenceScore(
                        value=rule["confidence"] * best_match["match_score"]
                    ),
                    reasoning_chain=reasoning_chain,
                )
            else:
                result = self._create_result(
                    conclusion="无法识别的常识推理场景",
                    confidence=ConfidenceScore(value=0.0),
                    reasoning_chain=reasoning_chain,
                )

        self._reasoning_history.append(result)
        return result

    async def validate_reasoning(self, reasoning_result: ReasoningResult) -> Tuple[bool, List[str]]:
        errors = []

        for step in reasoning_result.reasoning_chain:
            if step.inference_rule == "social_commonsense":
                if step.confidence.value > 0.9:
                    errors.append("社会常识推理置信度过高，应考虑文化差异")

        return len(errors) == 0, errors

    def get_confidence(self, premises: List[Any], conclusion: Any) -> ConfidenceScore:
        return ConfidenceScore(value=0.7, evidence_count=1)
