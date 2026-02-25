"""
Reasoning Engine Base Classes

推理引擎的基类实现
"""

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
import logging
import time
import uuid

from usmsb_sdk.reasoning.interfaces import (
    IReasoningChain,
    IReasoningEngine,
    IKnowledgeGraphAdapter,
    ReasoningType,
    ReasoningResult,
    ReasoningStep,
    ConfidenceScore,
    UncertaintyMeasure,
)

logger = logging.getLogger(__name__)


@dataclass
class ReasoningContext:
    """推理上下文"""

    context_id: str
    query: str
    background_knowledge: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    goals: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    max_depth: int = 10
    timeout: float = 60.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReasoningChain(IReasoningChain):
    """推理链实现"""

    def __init__(self, chain_id: Optional[str] = None):
        self.chain_id = chain_id or str(uuid.uuid4())[:8]
        self._steps: List[ReasoningStep] = []
        self._step_index: Dict[str, ReasoningStep] = {}
        self._conclusions: Set[str] = set()
        self._contradictions: List[Dict[str, Any]] = []

    def add_step(self, step: ReasoningStep) -> None:
        self._steps.append(step)
        self._step_index[step.step_id] = step
        for conclusion in step.output_conclusions:
            self._conclusions.add(conclusion)

    def get_step(self, step_id: str) -> Optional[ReasoningStep]:
        return self._step_index.get(step_id)

    def get_chain(self) -> List[ReasoningStep]:
        return self._steps.copy()

    def validate_consistency(self) -> Tuple[bool, List[Dict[str, Any]]]:
        contradictions = self.detect_contradictions()
        return len(contradictions) == 0, contradictions

    def detect_contradictions(self) -> List[Dict[str, Any]]:
        contradictions = []
        negation_patterns = ["not ", "非", "不", "no ", "never "]

        for step in self._steps:
            for conclusion in step.output_conclusions:
                for other_step in self._steps:
                    if step.step_id == other_step.step_id:
                        continue
                    for other_conclusion in other_step.output_conclusions:
                        for pattern in negation_patterns:
                            if (
                                pattern + conclusion in other_conclusion
                                or conclusion.startswith(pattern)
                                and conclusion[len(pattern) :] in other_conclusion
                            ):
                                contradictions.append(
                                    {
                                        "type": "direct_negation",
                                        "conclusion1": conclusion,
                                        "conclusion2": other_conclusion,
                                        "step1": step.step_id,
                                        "step2": other_step.step_id,
                                    }
                                )

        self._contradictions = contradictions
        return contradictions

    def get_dependencies(self, step_id: str) -> List[str]:
        dependencies = []
        step = self.get_step(step_id)
        if step:
            for premise in step.input_premises:
                for other_step in self._steps:
                    if premise in other_step.output_conclusions:
                        dependencies.append(other_step.step_id)
        return dependencies

    def get_derived_conclusions(self) -> Set[str]:
        return self._conclusions.copy()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "steps": [s.to_dict() for s in self._steps],
            "conclusions": list(self._conclusions),
            "contradictions": self._contradictions,
        }


class BaseReasoningEngine(IReasoningEngine):
    """推理引擎基类"""

    def __init__(
        self,
        knowledge_adapter: Optional[IKnowledgeGraphAdapter] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.knowledge_adapter = knowledge_adapter
        self.config = config or {}
        self._engine_id = str(uuid.uuid4())[:8]
        self._reasoning_history: List[ReasoningResult] = []

    @property
    @abstractmethod
    def engine_type(self) -> ReasoningType:
        pass

    def _create_result(
        self,
        conclusion: Any,
        confidence: ConfidenceScore,
        reasoning_chain: List[ReasoningStep],
        uncertainty: Optional[UncertaintyMeasure] = None,
        alternatives: Optional[List[Dict[str, Any]]] = None,
        explanations: Optional[List[str]] = None,
    ) -> ReasoningResult:
        return ReasoningResult(
            result_id=str(uuid.uuid4())[:8],
            reasoning_type=self.engine_type,
            conclusion=conclusion,
            confidence=confidence,
            uncertainty=uncertainty,
            reasoning_chain=reasoning_chain,
            alternatives=alternatives or [],
            explanations=explanations or [],
        )

    def _create_step(
        self,
        step_type: ReasoningType,
        input_premises: List[str],
        output_conclusions: List[str],
        inference_rule: str,
        confidence: ConfidenceScore,
        uncertainty: Optional[UncertaintyMeasure] = None,
        reasoning_trace: str = "",
    ) -> ReasoningStep:
        return ReasoningStep(
            step_id=str(uuid.uuid4())[:8],
            step_type=step_type,
            input_premises=input_premises,
            output_conclusions=output_conclusions,
            inference_rule=inference_rule,
            confidence=confidence,
            uncertainty=uncertainty,
            reasoning_trace=reasoning_trace,
        )

    async def _query_knowledge(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        if self.knowledge_adapter:
            return await self.knowledge_adapter.query(query, parameters)
        return []

    async def _get_background_knowledge(self, concepts: List[str]) -> Dict[str, List[str]]:
        result = {}
        if self.knowledge_adapter:
            for concept in concepts:
                related = await self.knowledge_adapter.get_related_concepts(concept)
                result[concept] = [r.get("concept", "") for r in related]
        return result

    def get_history(self) -> List[ReasoningResult]:
        return self._reasoning_history.copy()

    def clear_history(self) -> None:
        self._reasoning_history.clear()

    @abstractmethod
    async def reason(
        self, premises: List[Any], context: Optional[Dict[str, Any]] = None
    ) -> ReasoningResult:
        pass

    @abstractmethod
    async def validate_reasoning(self, reasoning_result: ReasoningResult) -> Tuple[bool, List[str]]:
        pass

    @abstractmethod
    def get_confidence(self, premises: List[Any], conclusion: Any) -> ConfidenceScore:
        pass

    async def explain(self, reasoning_result: ReasoningResult) -> List[str]:
        explanations = []
        for step in reasoning_result.reasoning_chain:
            if step.reasoning_trace:
                explanations.append(step.reasoning_trace)
            else:
                explanations.append(
                    f"应用 {step.inference_rule} 从 {step.input_premises} 推导出 {step.output_conclusions}"
                )
        return explanations
