"""
Spatial Reasoning Engine

空间推理引擎：位置、方向、距离推理
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import logging
import math

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
class SpatialEntity:
    """空间实体"""

    entity_id: str
    position: Tuple[float, float, float]
    size: Optional[Tuple[float, float, float]] = None
    orientation: Optional[Tuple[float, float, float]] = None
    entity_type: str = "object"


@dataclass
class SpatialRelation:
    """空间关系"""

    relation_type: str
    entity1: str
    entity2: str
    confidence: float = 1.0


class SpatialEngine(BaseReasoningEngine):
    """
    空间推理引擎

    支持：
    - 位置推理
    - 方向推理
    - 距离计算
    - 拓扑关系推理
    - 空间包含/重叠判断
    """

    DIRECTION_THRESHOLD = 22.5

    def __init__(
        self,
        knowledge_adapter: Optional[IKnowledgeGraphAdapter] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(knowledge_adapter, config)
        self._entities: Dict[str, SpatialEntity] = {}
        self._relations: List[SpatialRelation] = []

    @property
    def engine_type(self) -> ReasoningType:
        return ReasoningType.SPATIAL

    def add_entity(self, entity: SpatialEntity) -> None:
        self._entities[entity.entity_id] = entity

    def _calculate_distance(
        self, pos1: Tuple[float, float, float], pos2: Tuple[float, float, float]
    ) -> float:
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(pos1, pos2)))

    def _calculate_direction(
        self, from_pos: Tuple[float, float, float], to_pos: Tuple[float, float, float]
    ) -> Tuple[str, float]:
        dx = to_pos[0] - from_pos[0]
        dy = to_pos[1] - from_pos[1]

        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360

        directions = [
            ("东", 0, 45),
            ("东北", 45, 90),
            ("北", 90, 135),
            ("西北", 135, 180),
            ("西", 180, 225),
            ("西南", 225, 270),
            ("南", 270, 315),
            ("东南", 315, 360),
        ]

        for name, start, end in directions:
            if start <= angle < end:
                return name, angle

        return "东", angle

    def _check_containment(
        self, container: SpatialEntity, contained: SpatialEntity
    ) -> Tuple[bool, float]:
        if not container.size or not contained.size:
            return False, 0.0

        c_pos = container.position
        c_size = container.size
        o_pos = contained.position
        o_size = contained.size

        c_min = tuple(p - s / 2 for p, s in zip(c_pos, c_size))
        c_max = tuple(p + s / 2 for p, s in zip(c_pos, c_size))
        o_min = tuple(p - s / 2 for p, s in zip(o_pos, o_size))
        o_max = tuple(p + s / 2 for p, s in zip(o_pos, o_size))

        contained_flag = all(
            om >= cm and ox <= cx for om, cm, ox, cx in zip(o_min, c_min, o_max, c_max)
        )

        if contained_flag:
            volume_container = c_size[0] * c_size[1] * c_size[2]
            volume_object = o_size[0] * o_size[1] * o_size[2]
            confidence = min(1.0, volume_container / (volume_object + 1))
        else:
            confidence = 0.0

        return contained_flag, confidence

    def _check_overlap(self, entity1: SpatialEntity, entity2: SpatialEntity) -> Tuple[bool, float]:
        if not entity1.size or not entity2.size:
            dist = self._calculate_distance(entity1.position, entity2.position)
            overlap = dist < 0.5
            return overlap, 1.0 - dist

        pos1, size1 = entity1.position, entity1.size
        pos2, size2 = entity2.position, entity2.size

        min1 = tuple(p - s / 2 for p, s in zip(pos1, size1))
        max1 = tuple(p + s / 2 for p, s in zip(pos1, size1))
        min2 = tuple(p - s / 2 for p, s in zip(pos2, size2))
        max2 = tuple(p + s / 2 for p, s in zip(pos2, size2))

        overlap_dist = [max(0, min(max1[i], max2[i]) - max(min1[i], min2[i])) for i in range(3)]
        overlap_volume = overlap_dist[0] * overlap_dist[1] * overlap_dist[2]

        vol1 = size1[0] * size1[1] * size1[2]
        vol2 = size2[0] * size2[1] * size2[2]

        has_overlap = overlap_volume > 0
        overlap_ratio = overlap_volume / min(vol1, vol2) if min(vol1, vol2) > 0 else 0

        return has_overlap, overlap_ratio

    def _get_topological_relation(
        self, entity1: SpatialEntity, entity2: SpatialEntity
    ) -> Tuple[str, float]:
        is_contained, conf_contained = self._check_containment(entity2, entity1)
        if is_contained:
            return "包含", conf_contained

        is_contained, conf_contained = self._check_containment(entity1, entity2)
        if is_contained:
            return "被包含", conf_contained

        has_overlap, overlap_ratio = self._check_overlap(entity1, entity2)
        if has_overlap:
            return "重叠", overlap_ratio

        dist = self._calculate_distance(entity1.position, entity2.position)

        size1 = entity1.size or (1, 1, 1)
        size2 = entity2.size or (1, 1, 1)
        max_extent = max(max(size1), max(size2))

        if dist < max_extent:
            return "相邻", 1.0 - dist / max_extent

        return "分离", 1.0

    async def reason(
        self, premises: List[Any], context: Optional[Dict[str, Any]] = None
    ) -> ReasoningResult:
        context = context or {}

        reasoning_chain: List[ReasoningStep] = []

        if not premises:
            return self._create_result(
                conclusion="无法进行空间推理：缺少输入",
                confidence=ConfidenceScore(value=0.0),
                reasoning_chain=reasoning_chain,
            )

        first_premise = premises[0]

        if isinstance(first_premise, dict):
            query_type = first_premise.get("query_type", "relation")

            if query_type == "distance":
                e1_id = first_premise.get("entity1")
                e2_id = first_premise.get("entity2")

                if e1_id in self._entities and e2_id in self._entities:
                    e1 = self._entities[e1_id]
                    e2 = self._entities[e2_id]
                    dist = self._calculate_distance(e1.position, e2.position)

                    step = self._create_step(
                        step_type=ReasoningType.SPATIAL,
                        input_premises=[f"{e1_id}: {e1.position}", f"{e2_id}: {e2.position}"],
                        output_conclusions=[f"距离: {dist:.2f}"],
                        inference_rule="euclidean_distance",
                        confidence=ConfidenceScore(value=1.0),
                        reasoning_trace=f"计算 {e1_id} 和 {e2_id} 之间的距离: {dist:.2f}",
                    )
                    reasoning_chain.append(step)

                    result = self._create_result(
                        conclusion=f"{e1_id} 和 {e2_id} 之间的距离是 {dist:.2f} 单位",
                        confidence=ConfidenceScore(value=1.0),
                        reasoning_chain=reasoning_chain,
                        explanations=[f"欧几里得距离计算", f"距离: {dist:.2f}"],
                    )
                else:
                    result = self._create_result(
                        conclusion="无法计算距离：实体不存在",
                        confidence=ConfidenceScore(value=0.0),
                        reasoning_chain=reasoning_chain,
                    )

            elif query_type == "direction":
                from_id = first_premise.get("from")
                to_id = first_premise.get("to")

                if from_id in self._entities and to_id in self._entities:
                    from_e = self._entities[from_id]
                    to_e = self._entities[to_id]
                    direction, angle = self._calculate_direction(from_e.position, to_e.position)

                    step = self._create_step(
                        step_type=ReasoningType.SPATIAL,
                        input_premises=[
                            f"{from_id}: {from_e.position}",
                            f"{to_id}: {to_e.position}",
                        ],
                        output_conclusions=[f"方向: {direction} (角度: {angle:.1f}°)"],
                        inference_rule="direction_calculation",
                        confidence=ConfidenceScore(value=1.0),
                        reasoning_trace=f"{to_id} 在 {from_id} 的 {direction} 方向",
                    )
                    reasoning_chain.append(step)

                    result = self._create_result(
                        conclusion=f"{to_id} 在 {from_id} 的 {direction} 方向 (角度: {angle:.1f}°)",
                        confidence=ConfidenceScore(value=1.0),
                        reasoning_chain=reasoning_chain,
                    )
                else:
                    result = self._create_result(
                        conclusion="无法计算方向：实体不存在",
                        confidence=ConfidenceScore(value=0.0),
                        reasoning_chain=reasoning_chain,
                    )

            elif query_type == "relation":
                e1_id = first_premise.get("entity1")
                e2_id = first_premise.get("entity2")

                if e1_id in self._entities and e2_id in self._entities:
                    e1 = self._entities[e1_id]
                    e2 = self._entities[e2_id]
                    rel, conf = self._get_topological_relation(e1, e2)

                    step = self._create_step(
                        step_type=ReasoningType.SPATIAL,
                        input_premises=[f"{e1_id}", f"{e2_id}"],
                        output_conclusions=[f"关系: {rel}"],
                        inference_rule="topological_relation",
                        confidence=ConfidenceScore(value=conf),
                        reasoning_trace=f"{e1_id} 与 {e2_id} 的空间关系: {rel}",
                    )
                    reasoning_chain.append(step)

                    result = self._create_result(
                        conclusion=f"{e1_id} 与 {e2_id} 的空间关系是: {rel}",
                        confidence=ConfidenceScore(value=conf),
                        reasoning_chain=reasoning_chain,
                    )
                else:
                    result = self._create_result(
                        conclusion="无法确定空间关系：实体不存在",
                        confidence=ConfidenceScore(value=0.0),
                        reasoning_chain=reasoning_chain,
                    )

            else:
                result = self._create_result(
                    conclusion=f"未知的空间查询类型: {query_type}",
                    confidence=ConfidenceScore(value=0.0),
                    reasoning_chain=reasoning_chain,
                )
        else:
            result = self._create_result(
                conclusion="空间推理需要字典格式的查询输入",
                confidence=ConfidenceScore(value=0.0),
                reasoning_chain=reasoning_chain,
            )

        self._reasoning_history.append(result)
        return result

    async def validate_reasoning(self, reasoning_result: ReasoningResult) -> Tuple[bool, List[str]]:
        errors = []

        for step in reasoning_result.reasoning_chain:
            if step.inference_rule in ["euclidean_distance", "direction_calculation"]:
                if len(step.input_premises) < 2:
                    errors.append(f"步骤 {step.step_id}: 需要2个实体作为输入")

        return len(errors) == 0, errors

    def get_confidence(self, premises: List[Any], conclusion: Any) -> ConfidenceScore:
        return ConfidenceScore(value=1.0)

    def get_nearby_entities(self, entity_id: str, radius: float) -> List[Dict[str, Any]]:
        if entity_id not in self._entities:
            return []

        center = self._entities[entity_id]
        nearby = []

        for eid, entity in self._entities.items():
            if eid == entity_id:
                continue

            dist = self._calculate_distance(center.position, entity.position)
            if dist <= radius:
                direction, _ = self._calculate_direction(center.position, entity.position)
                nearby.append(
                    {
                        "entity_id": eid,
                        "distance": dist,
                        "direction": direction,
                    }
                )

        nearby.sort(key=lambda x: x["distance"])
        return nearby
