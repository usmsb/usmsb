"""
Reasoning Chain Manager

推理链管理与执行
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Callable
import logging
import time
import asyncio
from enum import Enum

from usmsb_sdk.reasoning.interfaces import (
    IReasoningEngine,
    ReasoningType,
    ReasoningResult,
    ReasoningStep,
    ConfidenceScore,
)
from usmsb_sdk.reasoning.base import ReasoningChain

logger = logging.getLogger(__name__)


class ChainStatus(str, Enum):
    """推理链状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class ChainExecutionResult:
    """推理链执行结果"""

    chain_id: str
    status: ChainStatus
    results: List[ReasoningResult]
    final_conclusion: Any
    overall_confidence: ConfidenceScore
    execution_time: float
    steps_executed: int
    errors: List[str] = field(default_factory=list)


@dataclass
class ChainNode:
    """推理链节点"""

    node_id: str
    engine_type: ReasoningType
    input_sources: List[str]
    premises: List[Any]
    condition: Optional[Callable] = None
    next_nodes: List[str] = field(default_factory=list)
    result: Optional[ReasoningResult] = None


class ReasoningChainManager:
    """
    推理链管理器

    功能：
    - 推理链构建
    - 推理链执行
    - 推理链优化
    - 并行推理支持
    """

    def __init__(self):
        self._engines: Dict[ReasoningType, IReasoningEngine] = {}
        self._chains: Dict[str, ReasoningChain] = {}
        self._chain_nodes: Dict[str, Dict[str, ChainNode]] = {}
        self._execution_history: List[ChainExecutionResult] = []

    def register_engine(self, reasoning_type: ReasoningType, engine: IReasoningEngine) -> None:
        self._engines[reasoning_type] = engine

    def create_chain(self, chain_id: Optional[str] = None) -> str:
        chain_id = chain_id or f"chain_{time.time():.0f}"
        self._chains[chain_id] = ReasoningChain(chain_id=chain_id)
        self._chain_nodes[chain_id] = {}
        return chain_id

    def add_node(self, chain_id: str, node: ChainNode) -> None:
        if chain_id not in self._chain_nodes:
            raise ValueError(f"推理链 {chain_id} 不存在")

        self._chain_nodes[chain_id][node.node_id] = node

    def add_step_to_chain(self, chain_id: str, step: ReasoningStep) -> None:
        if chain_id not in self._chains:
            raise ValueError(f"推理链 {chain_id} 不存在")

        self._chains[chain_id].add_step(step)

    def build_sequential_chain(self, steps: List[Tuple[ReasoningType, List[Any]]]) -> str:
        chain_id = self.create_chain()

        for i, (engine_type, premises) in enumerate(steps):
            node_id = f"node_{i}"
            input_sources = [f"node_{i - 1}"] if i > 0 else []

            node = ChainNode(
                node_id=node_id,
                engine_type=engine_type,
                input_sources=input_sources,
                premises=premises,
                next_nodes=[f"node_{i + 1}"] if i < len(steps) - 1 else [],
            )
            self.add_node(chain_id, node)

        return chain_id

    def build_parallel_chain(
        self, parallel_steps: List[List[Tuple[ReasoningType, List[Any]]]]
    ) -> str:
        chain_id = self.create_chain()

        merge_node_id = "node_merge"

        for branch_idx, branch in enumerate(parallel_steps):
            branch_prefix = f"branch_{branch_idx}_"

            for step_idx, (engine_type, premises) in enumerate(branch):
                node_id = f"{branch_prefix}node_{step_idx}"
                input_sources = [f"{branch_prefix}node_{step_idx - 1}"] if step_idx > 0 else []
                next_nodes = (
                    [f"{branch_prefix}node_{step_idx + 1}"]
                    if step_idx < len(branch) - 1
                    else [merge_node_id]
                )

                node = ChainNode(
                    node_id=node_id,
                    engine_type=engine_type,
                    input_sources=input_sources,
                    premises=premises,
                    next_nodes=next_nodes,
                )
                self.add_node(chain_id, node)

        merge_node = ChainNode(
            node_id=merge_node_id,
            engine_type=ReasoningType.META,
            input_sources=[],
            premises=[],
            next_nodes=[],
        )
        self.add_node(chain_id, merge_node)

        return chain_id

    async def execute_chain(
        self, chain_id: str, initial_premises: Optional[List[Any]] = None
    ) -> ChainExecutionResult:
        start_time = time.time()

        if chain_id not in self._chain_nodes:
            return ChainExecutionResult(
                chain_id=chain_id,
                status=ChainStatus.FAILED,
                results=[],
                final_conclusion=None,
                overall_confidence=ConfidenceScore(value=0.0),
                execution_time=0.0,
                steps_executed=0,
                errors=[f"推理链 {chain_id} 不存在"],
            )

        nodes = self._chain_nodes[chain_id]
        results: List[ReasoningResult] = []
        errors: List[str] = []
        executed_count = 0

        try:
            execution_order = self._determine_execution_order(nodes)

            current_premises = initial_premises or []

            for node_id in execution_order:
                node = nodes[node_id]

                if node.condition and not node.condition(current_premises):
                    continue

                engine = self._engines.get(node.engine_type)
                if not engine:
                    errors.append(f"未找到推理引擎: {node.engine_type}")
                    continue

                input_premises = node.premises or current_premises

                result = await engine.reason(input_premises)
                node.result = result
                results.append(result)
                executed_count += 1

                if result.reasoning_chain:
                    for step in result.reasoning_chain:
                        self._chains[chain_id].add_step(step)

                current_premises = [result.conclusion]

            final_conclusion = results[-1].conclusion if results else None

            overall_confidence = self._calculate_overall_confidence(results)

            execution_result = ChainExecutionResult(
                chain_id=chain_id,
                status=ChainStatus.COMPLETED,
                results=results,
                final_conclusion=final_conclusion,
                overall_confidence=overall_confidence,
                execution_time=time.time() - start_time,
                steps_executed=executed_count,
                errors=errors,
            )

        except Exception as e:
            logger.error(f"推理链执行失败: {e}")
            execution_result = ChainExecutionResult(
                chain_id=chain_id,
                status=ChainStatus.FAILED,
                results=results,
                final_conclusion=None,
                overall_confidence=ConfidenceScore(value=0.0),
                execution_time=time.time() - start_time,
                steps_executed=executed_count,
                errors=[str(e)],
            )

        self._execution_history.append(execution_result)
        return execution_result

    async def execute_parallel(
        self, chain_id: str, initial_premises: Optional[List[Any]] = None
    ) -> ChainExecutionResult:
        start_time = time.time()

        if chain_id not in self._chain_nodes:
            return ChainExecutionResult(
                chain_id=chain_id,
                status=ChainStatus.FAILED,
                results=[],
                final_conclusion=None,
                overall_confidence=ConfidenceScore(value=0.0),
                execution_time=0.0,
                steps_executed=0,
                errors=[f"推理链 {chain_id} 不存在"],
            )

        nodes = self._chain_nodes[chain_id]
        results: List[ReasoningResult] = []
        errors: List[str] = []

        branches = self._identify_branches(nodes)

        branch_tasks = []
        for branch_nodes in branches:
            task = self._execute_branch(branch_nodes, initial_premises or [])
            branch_tasks.append(task)

        branch_results = await asyncio.gather(*branch_tasks, return_exceptions=True)

        for result in branch_results:
            if isinstance(result, Exception):
                errors.append(str(result))
            elif isinstance(result, ReasoningResult):
                results.append(result)

        final_conclusion = self._merge_results(results)
        overall_confidence = self._calculate_overall_confidence(results)

        execution_result = ChainExecutionResult(
            chain_id=chain_id,
            status=ChainStatus.COMPLETED if not errors else ChainStatus.FAILED,
            results=results,
            final_conclusion=final_conclusion,
            overall_confidence=overall_confidence,
            execution_time=time.time() - start_time,
            steps_executed=len(results),
            errors=errors,
        )

        self._execution_history.append(execution_result)
        return execution_result

    async def _execute_branch(
        self, branch_nodes: List[ChainNode], premises: List[Any]
    ) -> ReasoningResult:
        current_premises = premises
        result = None

        for node in branch_nodes:
            engine = self._engines.get(node.engine_type)
            if not engine:
                raise ValueError(f"未找到推理引擎: {node.engine_type}")

            result = await engine.reason(current_premises)
            node.result = result
            current_premises = [result.conclusion]

        return result

    def _determine_execution_order(self, nodes: Dict[str, ChainNode]) -> List[str]:
        ordered = []
        visited = set()

        def visit(node_id: str):
            if node_id in visited:
                return
            visited.add(node_id)

            node = nodes.get(node_id)
            if node:
                for source in node.input_sources:
                    visit(source)
                ordered.append(node_id)

        for node_id in nodes:
            visit(node_id)

        return ordered

    def _identify_branches(self, nodes: Dict[str, ChainNode]) -> List[List[ChainNode]]:
        branches = []
        current_branch = []

        for node_id in sorted(nodes.keys()):
            node = nodes[node_id]

            if node_id.startswith("branch_"):
                branch_parts = node_id.split("_")
                branch_idx = int(branch_parts[1])

                while len(branches) <= branch_idx:
                    branches.append([])

                branches[branch_idx].append(node)
            else:
                current_branch.append(node)

        if current_branch:
            branches.append(current_branch)

        return branches

    def _merge_results(self, results: List[ReasoningResult]) -> Any:
        if not results:
            return None

        if len(results) == 1:
            return results[0].conclusion

        conclusions = [r.conclusion for r in results]

        if all(isinstance(c, dict) for c in conclusions):
            merged = {}
            for c in conclusions:
                merged.update(c)
            return merged

        if all(isinstance(c, (int, float)) for c in conclusions):
            return sum(conclusions) / len(conclusions)

        return {"merged_conclusions": conclusions}

    def _calculate_overall_confidence(self, results: List[ReasoningResult]) -> ConfidenceScore:
        if not results:
            return ConfidenceScore(value=0.0)

        if len(results) == 1:
            return results[0].confidence

        values = [r.confidence.value for r in results]
        avg_value = sum(values) / len(values)
        min_value = min(values)

        return ConfidenceScore(
            value=avg_value,
            lower_bound=min_value,
            upper_bound=max(values),
            evidence_count=sum(r.confidence.evidence_count for r in results),
        )

    def get_chain(self, chain_id: str) -> Optional[ReasoningChain]:
        return self._chains.get(chain_id)

    def get_execution_history(self) -> List[ChainExecutionResult]:
        return self._execution_history.copy()

    def validate_chain(self, chain_id: str) -> Tuple[bool, List[str]]:
        errors = []

        if chain_id not in self._chain_nodes:
            return False, [f"推理链 {chain_id} 不存在"]

        nodes = self._chain_nodes[chain_id]

        for node_id, node in nodes.items():
            if node.engine_type not in self._engines:
                errors.append(f"节点 {node_id} 使用的引擎类型 {node.engine_type} 未注册")

            for source in node.input_sources:
                if source not in nodes:
                    errors.append(f"节点 {node_id} 引用了不存在的输入源 {source}")

        chain = self._chains.get(chain_id)
        if chain:
            is_consistent, contradictions = chain.validate_consistency()
            if not is_consistent:
                errors.extend([str(c) for c in contradictions])

        return len(errors) == 0, errors

    def optimize_chain(self, chain_id: str) -> Dict[str, Any]:
        if chain_id not in self._chain_nodes:
            return {"error": f"推理链 {chain_id} 不存在"}

        nodes = self._chain_nodes[chain_id]
        optimizations = []

        independent_nodes = []
        dependent_nodes = []

        for node_id, node in nodes.items():
            if not node.input_sources:
                independent_nodes.append(node_id)
            else:
                dependent_nodes.append(node_id)

        if len(independent_nodes) > 1:
            optimizations.append(
                {
                    "type": "parallelization",
                    "description": f"发现 {len(independent_nodes)} 个可并行执行的独立节点",
                    "nodes": independent_nodes,
                }
            )

        redundant_nodes = []
        conclusions_seen = {}
        for node_id, node in nodes.items():
            if node.result and node.result.conclusion:
                conclusion_str = str(node.result.conclusion)
                if conclusion_str in conclusions_seen:
                    redundant_nodes.append((node_id, conclusions_seen[conclusion_str]))
                else:
                    conclusions_seen[conclusion_str] = node_id

        if redundant_nodes:
            optimizations.append(
                {
                    "type": "redundancy_removal",
                    "description": f"发现 {len(redundant_nodes)} 个可能的冗余节点",
                    "nodes": redundant_nodes,
                }
            )

        return {
            "chain_id": chain_id,
            "optimizations": optimizations,
            "node_count": len(nodes),
            "estimated_speedup": len(independent_nodes) if len(independent_nodes) > 1 else 1,
        }
