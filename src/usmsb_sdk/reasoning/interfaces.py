"""
Reasoning Engine Interfaces

定义推理引擎的核心接口和数据结构
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import time
import uuid


class ReasoningType(str, Enum):
    """推理类型枚举"""

    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"
    CAUSAL = "causal"
    COUNTERFACTUAL = "counterfactual"
    ANALOGICAL = "analogical"
    SPATIAL = "spatial"
    TEMPORAL = "temporal"
    COMMONSENSE = "commonsense"
    META = "meta"


class UncertaintyType(str, Enum):
    """不确定性类型"""

    PROBABILISTIC = "probabilistic"
    FUZZY = "fuzzy"
    DEMPSTER_SHAFER = "dempster_shafer"
    BAYESIAN = "bayesian"
    INTERVAL = "interval"


@dataclass
class ConfidenceScore:
    """置信度分数"""

    value: float
    lower_bound: float = 0.0
    upper_bound: float = 1.0
    sample_size: int = 1
    evidence_count: int = 0

    def __post_init__(self):
        self.value = max(0.0, min(1.0, self.value))
        self.lower_bound = max(0.0, min(self.value, self.lower_bound))
        self.upper_bound = max(self.value, min(1.0, self.upper_bound))

    def combine(self, other: "ConfidenceScore", method: str = "average") -> "ConfidenceScore":
        """组合两个置信度分数"""
        if method == "average":
            new_value = (self.value + other.value) / 2
        elif method == "multiply":
            new_value = self.value * other.value
        elif method == "max":
            new_value = max(self.value, other.value)
        elif method == "min":
            new_value = min(self.value, other.value)
        else:
            new_value = (self.value + other.value) / 2

        return ConfidenceScore(
            value=new_value,
            lower_bound=min(self.lower_bound, other.lower_bound),
            upper_bound=max(self.upper_bound, other.upper_bound),
            sample_size=self.sample_size + other.sample_size,
            evidence_count=self.evidence_count + other.evidence_count,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "sample_size": self.sample_size,
            "evidence_count": self.evidence_count,
        }


@dataclass
class UncertaintyMeasure:
    """不确定性度量"""

    uncertainty_type: UncertaintyType
    value: Any
    distribution: Optional[Dict[str, float]] = None
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uncertainty_type": self.uncertainty_type.value,
            "value": self.value,
            "distribution": self.distribution,
            "parameters": self.parameters,
        }


@dataclass
class ReasoningStep:
    """推理步骤"""

    step_id: str
    step_type: ReasoningType
    input_premises: List[str]
    output_conclusions: List[str]
    inference_rule: str
    confidence: ConfidenceScore
    uncertainty: Optional[UncertaintyMeasure] = None
    reasoning_trace: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_type": self.step_type.value,
            "input_premises": self.input_premises,
            "output_conclusions": self.output_conclusions,
            "inference_rule": self.inference_rule,
            "confidence": self.confidence.to_dict(),
            "uncertainty": self.uncertainty.to_dict() if self.uncertainty else None,
            "reasoning_trace": self.reasoning_trace,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class ReasoningResult:
    """推理结果"""

    result_id: str
    reasoning_type: ReasoningType
    conclusion: Any
    confidence: ConfidenceScore
    uncertainty: Optional[UncertaintyMeasure] = None
    reasoning_chain: List[ReasoningStep] = field(default_factory=list)
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    explanations: List[str] = field(default_factory=list)
    contradictions: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "reasoning_type": self.reasoning_type.value,
            "conclusion": self.conclusion,
            "confidence": self.confidence.to_dict(),
            "uncertainty": self.uncertainty.to_dict() if self.uncertainty else None,
            "reasoning_chain": [s.to_dict() for s in self.reasoning_chain],
            "alternatives": self.alternatives,
            "explanations": self.explanations,
            "contradictions": self.contradictions,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class IReasoningEngine(ABC):
    """推理引擎接口"""

    @property
    @abstractmethod
    def engine_type(self) -> ReasoningType:
        """引擎类型"""
        pass

    @abstractmethod
    async def reason(
        self, premises: List[Any], context: Optional[Dict[str, Any]] = None
    ) -> ReasoningResult:
        """
        执行推理

        Args:
            premises: 前提/输入
            context: 推理上下文

        Returns:
            ReasoningResult: 推理结果
        """
        pass

    @abstractmethod
    async def validate_reasoning(self, reasoning_result: ReasoningResult) -> Tuple[bool, List[str]]:
        """
        验证推理有效性

        Args:
            reasoning_result: 推理结果

        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误列表)
        """
        pass

    @abstractmethod
    def get_confidence(self, premises: List[Any], conclusion: Any) -> ConfidenceScore:
        """
        计算结论的置信度

        Args:
            premises: 前提
            conclusion: 结论

        Returns:
            ConfidenceScore: 置信度分数
        """
        pass

    @abstractmethod
    async def explain(self, reasoning_result: ReasoningResult) -> List[str]:
        """
        生成推理解释

        Args:
            reasoning_result: 推理结果

        Returns:
            List[str]: 解释列表
        """
        pass


class IReasoningChain(ABC):
    """推理链接口"""

    @abstractmethod
    def add_step(self, step: ReasoningStep) -> None:
        """添加推理步骤"""
        pass

    @abstractmethod
    def get_step(self, step_id: str) -> Optional[ReasoningStep]:
        """获取推理步骤"""
        pass

    @abstractmethod
    def get_chain(self) -> List[ReasoningStep]:
        """获取完整推理链"""
        pass

    @abstractmethod
    def validate_consistency(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """验证一致性"""
        pass

    @abstractmethod
    def detect_contradictions(self) -> List[Dict[str, Any]]:
        """检测矛盾"""
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        pass


class IKnowledgeGraphAdapter(ABC):
    """知识图谱适配器接口"""

    @abstractmethod
    async def query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """查询知识图谱"""
        pass

    @abstractmethod
    async def add_fact(
        self, subject: str, predicate: str, object: str, confidence: float = 1.0
    ) -> bool:
        """添加事实三元组"""
        pass

    @abstractmethod
    async def get_related_concepts(self, concept: str, max_depth: int = 2) -> List[Dict[str, Any]]:
        """获取相关概念"""
        pass

    @abstractmethod
    async def infer_relations(self, entity1: str, entity2: str) -> List[Dict[str, Any]]:
        """推断实体间关系"""
        pass

    @abstractmethod
    async def check_consistency(self, facts: List[Tuple[str, str, str]]) -> Tuple[bool, List[str]]:
        """检查一致性"""
        pass
