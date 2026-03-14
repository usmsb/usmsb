"""
Temporal Reasoning Engine

时间推理引擎：时序、持续时间、频率推理
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

from usmsb_sdk.reasoning.base import BaseReasoningEngine
from usmsb_sdk.reasoning.interfaces import (
    ConfidenceScore,
    IKnowledgeGraphAdapter,
    ReasoningResult,
    ReasoningStep,
    ReasoningType,
)

logger = logging.getLogger(__name__)


class TemporalRelation(StrEnum):
    """时序关系 (Allen's Interval Algebra)"""

    BEFORE = "before"
    AFTER = "after"
    MEETS = "meets"
    MET_BY = "met_by"
    OVERLAPS = "overlaps"
    OVERLAPPED_BY = "overlapped_by"
    STARTS = "starts"
    STARTED_BY = "started_by"
    FINISHES = "finishes"
    FINISHED_BY = "finished_by"
    DURING = "during"
    CONTAINS = "contains"
    EQUALS = "equals"


@dataclass
class TimeInterval:
    """时间区间"""

    interval_id: str
    start: datetime | None = None
    end: datetime | None = None
    duration: timedelta | None = None
    description: str = ""

    def __post_init__(self):
        if self.start and self.end and not self.duration:
            self.duration = self.end - self.start
        elif self.start and self.duration and not self.end:
            self.end = self.start + self.duration


@dataclass
class TemporalEvent:
    """时序事件"""

    event_id: str
    timestamp: datetime | None = None
    interval: TimeInterval | None = None
    event_type: str = ""
    properties: dict[str, Any] = field(default_factory=dict)


class TemporalEngine(BaseReasoningEngine):
    """
    时间推理引擎

    支持：
    - 时序关系推理 (Allen区间代数)
    - 持续时间计算
    - 频率分析
    - 时间约束满足
    """

    def __init__(
        self,
        knowledge_adapter: IKnowledgeGraphAdapter | None = None,
        config: dict[str, Any] | None = None,
    ):
        super().__init__(knowledge_adapter, config)
        self._intervals: dict[str, TimeInterval] = {}
        self._events: dict[str, TemporalEvent] = {}
        self._temporal_constraints: list[tuple[str, str, TemporalRelation]] = []

    @property
    def engine_type(self) -> ReasoningType:
        return ReasoningType.TEMPORAL

    def add_interval(self, interval: TimeInterval) -> None:
        self._intervals[interval.interval_id] = interval

    def add_event(self, event: TemporalEvent) -> None:
        self._events[event.event_id] = event

    def add_constraint(
        self, interval1_id: str, interval2_id: str, relation: TemporalRelation
    ) -> None:
        self._temporal_constraints.append((interval1_id, interval2_id, relation))

    def _determine_relation(
        self, interval1: TimeInterval, interval2: TimeInterval
    ) -> tuple[TemporalRelation, float]:
        if not interval1.start or not interval2.start:
            return TemporalRelation.EQUALS, 0.0

        s1, e1 = interval1.start, interval1.end or interval1.start
        s2, e2 = interval2.start, interval2.end or interval2.start

        if s1 == s2 and e1 == e2:
            return TemporalRelation.EQUALS, 1.0

        if e1 <= s2:
            gap = (s2 - e1).total_seconds()
            if gap < 1:
                return TemporalRelation.MEETS, 1.0
            return TemporalRelation.BEFORE, 1.0 - gap / 86400

        if e2 <= s1:
            gap = (s1 - e2).total_seconds()
            if gap < 1:
                return TemporalRelation.MET_BY, 1.0
            return TemporalRelation.AFTER, 1.0 - gap / 86400

        if s1 < s2 < e1 < e2:
            overlap = (e1 - s2).total_seconds()
            return TemporalRelation.OVERLAPS, min(1.0, overlap / 3600)

        if s2 < s1 < e2 < e1:
            overlap = (e2 - s1).total_seconds()
            return TemporalRelation.OVERLAPPED_BY, min(1.0, overlap / 3600)

        if s1 == s2 and e1 < e2:
            return TemporalRelation.STARTS, 1.0

        if s1 == s2 and e1 > e2:
            return TemporalRelation.STARTED_BY, 1.0

        if e1 == e2 and s1 > s2:
            return TemporalRelation.FINISHES, 1.0

        if e1 == e2 and s1 < s2:
            return TemporalRelation.FINISHED_BY, 1.0

        if s1 > s2 and e1 < e2:
            return TemporalRelation.DURING, 1.0

        if s1 < s2 and e1 > e2:
            return TemporalRelation.CONTAINS, 1.0

        return TemporalRelation.EQUALS, 0.5

    def _calculate_duration(self, interval: TimeInterval) -> tuple[timedelta | None, str]:
        if interval.duration:
            return interval.duration, "已知持续时间"

        if interval.start and interval.end:
            return interval.end - interval.start, "计算得出"

        return None, "无法计算"

    def _infer_order(self, events: list[TemporalEvent]) -> list[dict[str, Any]]:
        ordered = []

        for event in events:
            if event.timestamp:
                ordered.append(
                    {
                        "event_id": event.event_id,
                        "timestamp": event.timestamp,
                        "order": event.timestamp.timestamp(),
                    }
                )
            elif event.interval and event.interval.start:
                ordered.append(
                    {
                        "event_id": event.event_id,
                        "timestamp": event.interval.start,
                        "order": event.interval.start.timestamp(),
                    }
                )

        ordered.sort(key=lambda x: x["order"])
        for i, item in enumerate(ordered):
            item["sequence"] = i + 1

        return ordered

    def _analyze_frequency(self, events: list[TemporalEvent]) -> dict[str, Any]:
        if not events:
            return {"frequency": 0, "interval": None}

        timestamps = []
        for event in events:
            if event.timestamp:
                timestamps.append(event.timestamp)
            elif event.interval and event.interval.start:
                timestamps.append(event.interval.start)

        if len(timestamps) < 2:
            return {"frequency": 1, "interval": None, "count": len(timestamps)}

        timestamps.sort()
        intervals = [
            (timestamps[i + 1] - timestamps[i]).total_seconds() for i in range(len(timestamps) - 1)
        ]

        avg_interval = sum(intervals) / len(intervals)

        return {
            "frequency": len(events),
            "count": len(events),
            "avg_interval_seconds": avg_interval,
            "avg_interval_human": str(timedelta(seconds=avg_interval)),
            "min_interval": min(intervals),
            "max_interval": max(intervals),
        }

    async def reason(
        self, premises: list[Any], context: dict[str, Any] | None = None
    ) -> ReasoningResult:
        context = context or {}

        reasoning_chain: list[ReasoningStep] = []

        if not premises:
            return self._create_result(
                conclusion="无法进行时间推理：缺少输入",
                confidence=ConfidenceScore(value=0.0),
                reasoning_chain=reasoning_chain,
            )

        first_premise = premises[0]

        if isinstance(first_premise, dict):
            query_type = first_premise.get("query_type", "relation")

            if query_type == "relation":
                i1_id = first_premise.get("interval1")
                i2_id = first_premise.get("interval2")

                if i1_id in self._intervals and i2_id in self._intervals:
                    i1 = self._intervals[i1_id]
                    i2 = self._intervals[i2_id]
                    relation, confidence = self._determine_relation(i1, i2)

                    step = self._create_step(
                        step_type=ReasoningType.TEMPORAL,
                        input_premises=[f"区间 {i1_id}", f"区间 {i2_id}"],
                        output_conclusions=[f"关系: {relation.value}"],
                        inference_rule="allen_interval_algebra",
                        confidence=ConfidenceScore(value=confidence),
                        reasoning_trace=f"区间 {i1_id} 与 {i2_id} 的时序关系: {relation.value}",
                    )
                    reasoning_chain.append(step)

                    result = self._create_result(
                        conclusion=f"区间 {i1_id} 与 {i2_id} 的关系是: {relation.value}",
                        confidence=ConfidenceScore(value=confidence),
                        reasoning_chain=reasoning_chain,
                        explanations=[
                            "使用Allen区间代数确定时序关系",
                            f"关系类型: {relation.value}",
                        ],
                    )
                else:
                    result = self._create_result(
                        conclusion="无法确定时序关系：区间不存在",
                        confidence=ConfidenceScore(value=0.0),
                        reasoning_chain=reasoning_chain,
                    )

            elif query_type == "duration":
                interval_id = first_premise.get("interval")

                if interval_id in self._intervals:
                    interval = self._intervals[interval_id]
                    duration, method = self._calculate_duration(interval)

                    if duration:
                        duration.total_seconds() / 3600

                        step = self._create_step(
                            step_type=ReasoningType.TEMPORAL,
                            input_premises=[f"区间 {interval_id}"],
                            output_conclusions=[f"持续时间: {duration}"],
                            inference_rule="duration_calculation",
                            confidence=ConfidenceScore(value=1.0),
                            reasoning_trace=f"区间 {interval_id} 持续时间: {duration} ({method})",
                        )
                        reasoning_chain.append(step)

                        result = self._create_result(
                            conclusion=f"区间 {interval_id} 的持续时间是 {duration}",
                            confidence=ConfidenceScore(value=1.0),
                            reasoning_chain=reasoning_chain,
                        )
                    else:
                        result = self._create_result(
                            conclusion=f"无法计算区间 {interval_id} 的持续时间",
                            confidence=ConfidenceScore(value=0.0),
                            reasoning_chain=reasoning_chain,
                        )
                else:
                    result = self._create_result(
                        conclusion="无法计算持续时间：区间不存在",
                        confidence=ConfidenceScore(value=0.0),
                        reasoning_chain=reasoning_chain,
                    )

            elif query_type == "order":
                event_ids = first_premise.get("events", [])
                events = [self._events[eid] for eid in event_ids if eid in self._events]

                if events:
                    ordered = self._infer_order(events)

                    for item in ordered:
                        step = self._create_step(
                            step_type=ReasoningType.TEMPORAL,
                            input_premises=[item["event_id"]],
                            output_conclusions=[f"顺序: {item['sequence']}"],
                            inference_rule="temporal_ordering",
                            confidence=ConfidenceScore(value=1.0),
                            reasoning_trace=f"事件 {item['event_id']} 排在第 {item['sequence']} 位",
                        )
                        reasoning_chain.append(step)

                    order_desc = " -> ".join([o["event_id"] for o in ordered])

                    result = self._create_result(
                        conclusion=f"事件顺序: {order_desc}",
                        confidence=ConfidenceScore(value=1.0),
                        reasoning_chain=reasoning_chain,
                    )
                else:
                    result = self._create_result(
                        conclusion="无法确定事件顺序：事件不存在",
                        confidence=ConfidenceScore(value=0.0),
                        reasoning_chain=reasoning_chain,
                    )

            elif query_type == "frequency":
                event_ids = first_premise.get("events", [])
                events = [self._events[eid] for eid in event_ids if eid in self._events]

                if events:
                    freq_analysis = self._analyze_frequency(events)

                    step = self._create_step(
                        step_type=ReasoningType.TEMPORAL,
                        input_premises=[e.event_id for e in events],
                        output_conclusions=[f"频率分析: {freq_analysis['frequency']} 次"],
                        inference_rule="frequency_analysis",
                        confidence=ConfidenceScore(value=1.0),
                        reasoning_trace=f"分析 {len(events)} 个事件的频率: 平均间隔 {freq_analysis.get('avg_interval_human', 'N/A')}",
                    )
                    reasoning_chain.append(step)

                    result = self._create_result(
                        conclusion=f"事件频率分析: {freq_analysis['frequency']} 次, 平均间隔 {freq_analysis.get('avg_interval_human', 'N/A')}",
                        confidence=ConfidenceScore(value=1.0),
                        reasoning_chain=reasoning_chain,
                        metadata=freq_analysis,
                    )
                else:
                    result = self._create_result(
                        conclusion="无法分析频率：事件不存在",
                        confidence=ConfidenceScore(value=0.0),
                        reasoning_chain=reasoning_chain,
                    )

            else:
                result = self._create_result(
                    conclusion=f"未知的时间查询类型: {query_type}",
                    confidence=ConfidenceScore(value=0.0),
                    reasoning_chain=reasoning_chain,
                )
        else:
            result = self._create_result(
                conclusion="时间推理需要字典格式的查询输入",
                confidence=ConfidenceScore(value=0.0),
                reasoning_chain=reasoning_chain,
            )

        self._reasoning_history.append(result)
        return result

    async def validate_reasoning(self, reasoning_result: ReasoningResult) -> tuple[bool, list[str]]:
        errors = []

        for step in reasoning_result.reasoning_chain:
            if step.inference_rule == "allen_interval_algebra":
                if len(step.input_premises) < 2:
                    errors.append(f"步骤 {step.step_id}: 时序关系推理需要2个区间")

        return len(errors) == 0, errors

    def get_confidence(self, premises: list[Any], conclusion: Any) -> ConfidenceScore:
        return ConfidenceScore(value=0.8)
