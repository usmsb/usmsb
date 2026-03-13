"""
元学习器 - Meta-Learner

学习如何学习，优化学习策略
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from .models import (
    MetaLearningRecord,
    LearningType,
    LearningGoal,
    Capability,
    KnowledgeUnit,
    KnowledgeState,
)

logger = logging.getLogger(__name__)


@dataclass
class LearningStrategy:
    """学习策略"""

    name: str
    description: str
    applicable_contexts: List[str]
    expected_efficiency: float
    parameters: Dict[str, Any] = field(default_factory=dict)
    success_history: List[float] = field(default_factory=list)


@dataclass
class LearningContext:
    """学习上下文"""

    domain: str
    difficulty: float
    prior_knowledge: float
    time_available: float
    goal_importance: float
    resource_constraints: Dict[str, Any] = field(default_factory=dict)


class MetaLearner:
    """
    元学习器

    核心职责：
    1. 学习策略管理 - 维护和优化学习策略库
    2. 上下文感知 - 识别学习场景并选择最优策略
    3. 学习效率优化 - 最大化学习效率
    4. 知识迁移优化 - 优化跨领域知识迁移
    5. 学习过程监控 - 追踪和评估学习效果
    """

    def __init__(self, llm_manager=None, knowledge_base=None):
        self.llm = llm_manager
        self.knowledge = knowledge_base

        self._strategies: Dict[str, LearningStrategy] = {}
        self._meta_records: List[MetaLearningRecord] = []
        self._learning_history: List[Dict[str, Any]] = []

        self._context_patterns: Dict[str, List[str]] = {}
        self._optimal_conditions: Dict[str, Dict[str, Any]] = {}

        self._initialized = False

    async def initialize(self):
        """初始化元学习器"""
        if self._initialized:
            return

        self._strategies = {
            "iterative_practice": LearningStrategy(
                name="iterative_practice",
                description="迭代练习 - 通过反复实践巩固知识",
                applicable_contexts=["skill_learning", "procedure_learning"],
                expected_efficiency=0.7,
                parameters={"iterations": 3, "feedback_delay": 1.0},
            ),
            "analogical_transfer": LearningStrategy(
                name="analogical_transfer",
                description="类比迁移 - 从相似领域迁移知识",
                applicable_contexts=["new_domain", "cross_domain"],
                expected_efficiency=0.6,
                parameters={"similarity_threshold": 0.5},
            ),
            "chunking": LearningStrategy(
                name="chunking",
                description="分块学习 - 将复杂知识分解为小块",
                applicable_contexts=["complex_topic", "large_knowledge"],
                expected_efficiency=0.8,
                parameters={"chunk_size": 5},
            ),
            "spaced_repetition": LearningStrategy(
                name="spaced_repetition",
                description="间隔重复 - 按最优间隔复习",
                applicable_contexts=["memorization", "long_term_retention"],
                expected_efficiency=0.9,
                parameters={"intervals": [1, 3, 7, 14, 30]},
            ),
            "active_recall": LearningStrategy(
                name="active_recall",
                description="主动回忆 - 通过测试强化记忆",
                applicable_contexts=["consolidation", "retention_check"],
                expected_efficiency=0.85,
                parameters={"test_frequency": 0.2},
            ),
            "elaboration": LearningStrategy(
                name="elaboration",
                description="精细加工 - 深度理解和关联知识",
                applicable_contexts=["deep_learning", "concept_mastery"],
                expected_efficiency=0.75,
                parameters={"depth": 3, "associations": True},
            ),
            "self_explanation": LearningStrategy(
                name="self_explanation",
                description="自我解释 - 解释概念增强理解",
                applicable_contexts=["concept_learning", "reasoning"],
                expected_efficiency=0.8,
                parameters={"explain_depth": 2},
            ),
            "interleaving": LearningStrategy(
                name="interleaving",
                description="交叉练习 - 混合不同主题学习",
                applicable_contexts=["multi_skill", "discrimination"],
                expected_efficiency=0.7,
                parameters={"mix_ratio": 0.5},
            ),
        }

        self._initialized = True
        logger.info(f"MetaLearner initialized with {len(self._strategies)} strategies")

    async def select_optimal_strategy(
        self,
        context: LearningContext,
        available_strategies: Optional[List[str]] = None,
    ) -> Tuple[str, float]:
        """
        选择最优学习策略

        Args:
            context: 学习上下文
            available_strategies: 可用策略列表（可选）

        Returns:
            (策略名称, 预期效率分数)
        """
        await self._ensure_initialized()

        candidates = available_strategies or list(self._strategies.keys())

        strategy_scores = {}
        for strategy_name in candidates:
            if strategy_name not in self._strategies:
                continue

            strategy = self._strategies[strategy_name]

            context_match = self._calculate_context_match(strategy, context)

            historical_performance = self._get_historical_performance(strategy_name, context)

            adaptation_score = self._calculate_adaptation_score(strategy, context)

            score = (
                context_match * 0.3
                + historical_performance * 0.4
                + strategy.expected_efficiency * 0.2
                + adaptation_score * 0.1
            )

            strategy_scores[strategy_name] = score

        if not strategy_scores:
            return "iterative_practice", 0.5

        best_strategy = max(strategy_scores, key=strategy_scores.get)
        return best_strategy, strategy_scores[best_strategy]

    def _calculate_context_match(
        self,
        strategy: LearningStrategy,
        context: LearningContext,
    ) -> float:
        """计算策略与上下文的匹配度"""
        domain = context.domain

        match_score = 0.0

        for applicable in strategy.applicable_contexts:
            if applicable in domain.lower():
                match_score += 0.3

        if context.difficulty > 0.7 and "chunking" in strategy.name:
            match_score += 0.2
        elif context.difficulty < 0.3 and "spaced_repetition" in strategy.name:
            match_score += 0.2

        if context.prior_knowledge > 0.6 and "analogical_transfer" in strategy.name:
            match_score += 0.2

        if context.goal_importance > 0.8:
            match_score += strategy.expected_efficiency * 0.1

        return min(1.0, match_score)

    def _get_historical_performance(
        self,
        strategy_name: str,
        context: LearningContext,
    ) -> float:
        """获取策略的历史表现"""
        relevant_records = [r for r in self._meta_records if r.learning_strategy == strategy_name]

        if not relevant_records:
            return 0.5

        avg_efficiency = sum(r.efficiency_score for r in relevant_records) / len(relevant_records)
        avg_retention = sum(r.retention_rate for r in relevant_records) / len(relevant_records)

        return avg_efficiency * 0.6 + avg_retention * 0.4

    def _calculate_adaptation_score(
        self,
        strategy: LearningStrategy,
        context: LearningContext,
    ) -> float:
        """计算策略适应性分数"""
        base_score = strategy.expected_efficiency

        for condition, value in self._optimal_conditions.get(strategy.name, {}).items():
            if condition == "time_available":
                if value <= context.time_available:
                    base_score += 0.1
            elif condition == "difficulty_range":
                if value[0] <= context.difficulty <= value[1]:
                    base_score += 0.1

        return min(1.0, base_score)

    async def execute_learning(
        self,
        goal: LearningGoal,
        context: LearningContext,
    ) -> Dict[str, Any]:
        """
        执行学习过程

        Args:
            goal: 学习目标
            context: 学习上下文

        Returns:
            学习结果
        """
        await self._ensure_initialized()

        strategy_name, efficiency_score = await self.select_optimal_strategy(context)

        strategy = self._strategies[strategy_name]

        start_time = datetime.now().timestamp()

        learning_result = await self._apply_strategy(strategy, goal, context)

        end_time = datetime.now().timestamp()

        record = MetaLearningRecord(
            learning_strategy=strategy_name,
            context_description=f"{context.domain} (difficulty: {context.difficulty})",
            efficiency_score=learning_result.get("efficiency", efficiency_score),
            retention_rate=learning_result.get("retention", 0.5),
            transfer_success=learning_result.get("transfer_success", 0.0),
            time_to_mastery=end_time - start_time,
            lessons_learned=learning_result.get("lessons", []),
            recommended_approaches=learning_result.get("recommendations", []),
        )

        self._meta_records.append(record)
        self._update_strategy_performance(strategy_name, learning_result)

        return {
            "strategy_used": strategy_name,
            "efficiency": record.efficiency_score,
            "retention": record.retention_rate,
            "knowledge_gained": learning_result.get("knowledge_gained", []),
            "improvements": learning_result.get("improvements", []),
        }

    async def _apply_strategy(
        self,
        strategy: LearningStrategy,
        goal: LearningGoal,
        context: LearningContext,
    ) -> Dict[str, Any]:
        """应用学习策略"""
        result = {
            "efficiency": strategy.expected_efficiency,
            "retention": 0.5,
            "transfer_success": 0.0,
            "knowledge_gained": [],
            "lessons": [],
            "recommendations": [],
        }

        if strategy.name == "iterative_practice":
            result = await self._apply_iterative_practice(goal, context, strategy.parameters)

        elif strategy.name == "analogical_transfer":
            result = await self._apply_analogical_transfer(goal, context, strategy.parameters)

        elif strategy.name == "chunking":
            result = await self._apply_chunking(goal, context, strategy.parameters)

        elif strategy.name == "spaced_repetition":
            result = await self._apply_spaced_repetition(goal, context, strategy.parameters)

        elif strategy.name == "self_explanation":
            result = await self._apply_self_explanation(goal, context, strategy.parameters)

        elif strategy.name == "elaboration":
            result = await self._apply_elaboration(goal, context, strategy.parameters)

        return result

    async def _apply_iterative_practice(
        self,
        goal: LearningGoal,
        context: LearningContext,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """应用迭代练习策略"""
        iterations = params.get("iterations", 3)
        knowledge_gained = []
        improvements = []

        for i in range(iterations):
            if self.llm:
                practice_result = await self._practice_iteration(goal, i)
                knowledge_gained.extend(practice_result.get("knowledge", []))
                improvements.extend(practice_result.get("improvements", []))

        efficiency = min(0.95, 0.6 + iterations * 0.1)
        retention = min(0.9, 0.5 + iterations * 0.15)

        return {
            "efficiency": efficiency,
            "retention": retention,
            "transfer_success": 0.3,
            "knowledge_gained": knowledge_gained,
            "lessons": [f"迭代{iterations}次练习效果良好"],
            "recommendations": ["建议继续实践以巩固"],
            "improvements": improvements,
        }

    async def _apply_analogical_transfer(
        self,
        goal: LearningGoal,
        context: LearningContext,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """应用类比迁移策略"""
        threshold = params.get("similarity_threshold", 0.5)

        similar_domains = await self._find_similar_domains(context.domain, threshold)

        transferred_knowledge = []
        for domain in similar_domains:
            domain_knowledge = await self._extract_transferable_knowledge(domain, context.domain)
            transferred_knowledge.extend(domain_knowledge)

        transfer_success = min(1.0, len(transferred_knowledge) * 0.2)

        return {
            "efficiency": 0.7 + transfer_success * 0.2,
            "retention": 0.6,
            "transfer_success": transfer_success,
            "knowledge_gained": transferred_knowledge,
            "lessons": [f"从{len(similar_domains)}个相似领域迁移了知识"],
            "recommendations": ["验证迁移的知识在新领域的适用性"],
            "improvements": [],
        }

    async def _apply_chunking(
        self,
        goal: LearningGoal,
        context: LearningContext,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """应用分块学习策略"""
        chunk_size = params.get("chunk_size", 5)

        chunks = await self._decompose_goal(goal, chunk_size)

        learned_chunks = []
        for chunk in chunks:
            if self.llm:
                chunk_result = await self._learn_chunk(chunk)
                learned_chunks.append(chunk_result)

        efficiency = 0.8 if len(learned_chunks) == len(chunks) else 0.6
        retention = 0.7 + len(learned_chunks) * 0.05

        return {
            "efficiency": efficiency,
            "retention": min(0.95, retention),
            "transfer_success": 0.2,
            "knowledge_gained": [c.get("knowledge") for c in learned_chunks if c.get("knowledge")],
            "lessons": [f"成功将目标分解为{len(chunks)}块并学习"],
            "recommendations": ["按顺序复习各块内容"],
            "improvements": [],
        }

    async def _apply_spaced_repetition(
        self,
        goal: LearningGoal,
        context: LearningContext,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """应用间隔重复策略"""
        intervals = params.get("intervals", [1, 3, 7, 14, 30])

        schedule = self._create_repetition_schedule(goal, intervals)

        return {
            "efficiency": 0.9,
            "retention": 0.95,
            "transfer_success": 0.1,
            "knowledge_gained": [],
            "lessons": [f"创建了{len(schedule)}次复习计划"],
            "recommendations": ["按计划执行复习"],
            "improvements": [],
            "repetition_schedule": schedule,
        }

    async def _apply_self_explanation(
        self,
        goal: LearningGoal,
        context: LearningContext,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """应用自我解释策略"""
        depth = params.get("explain_depth", 2)

        explanations = []
        if self.llm:
            for i in range(depth):
                explanation = await self._generate_explanation(goal, depth=i + 1)
                explanations.append(explanation)

        return {
            "efficiency": 0.8,
            "retention": 0.85,
            "transfer_success": 0.3,
            "knowledge_gained": explanations,
            "lessons": ["深度解释有助于理解"],
            "recommendations": ["尝试向他人解释以巩固理解"],
            "improvements": [],
        }

    async def _apply_elaboration(
        self,
        goal: LearningGoal,
        context: LearningContext,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """应用精细加工策略"""
        depth = params.get("depth", 3)
        make_associations = params.get("associations", True)

        elaborations = []
        associations = []

        if self.llm:
            elaborations = await self._elaborate_knowledge(goal, depth)

            if make_associations:
                associations = await self._find_knowledge_associations(goal)

        return {
            "efficiency": 0.75,
            "retention": 0.8,
            "transfer_success": 0.4,
            "knowledge_gained": elaborations,
            "lessons": [f"创建了{len(associations)}个知识关联"],
            "recommendations": ["定期回顾关联网络"],
            "improvements": [],
            "associations": associations,
        }

    def _update_strategy_performance(
        self,
        strategy_name: str,
        result: Dict[str, Any],
    ):
        """更新策略性能记录"""
        if strategy_name in self._strategies:
            strategy = self._strategies[strategy_name]
            strategy.success_history.append(result.get("efficiency", 0.5))

            if len(strategy.success_history) > 20:
                strategy.success_history = strategy.success_history[-20:]

            avg_performance = sum(strategy.success_history) / len(strategy.success_history)
            strategy.expected_efficiency = (
                strategy.expected_efficiency * 0.7 + avg_performance * 0.3
            )

    async def optimize_learning_parameters(self) -> Dict[str, Any]:
        """
        优化学习参数

        分析历史学习记录，优化各策略的参数
        """
        await self._ensure_initialized()

        optimizations = {}

        for strategy_name, strategy in self._strategies.items():
            strategy_records = [
                r for r in self._meta_records if r.learning_strategy == strategy_name
            ]

            if not strategy_records:
                continue

            best_record = max(strategy_records, key=lambda r: r.efficiency_score)

            optimizations[strategy_name] = {
                "best_conditions": best_record.optimal_conditions,
                "recommended_params": self._extract_best_params(best_record),
                "historical_efficiency": best_record.efficiency_score,
            }

            self._optimal_conditions[strategy_name] = best_record.optimal_conditions

        return optimizations

    def _extract_best_params(self, record: MetaLearningRecord) -> Dict[str, Any]:
        """从最佳记录中提取参数"""
        params = {}
        for approach in record.recommended_approaches:
            if "迭代" in approach:
                params["iterations"] = 5
            elif "间隔" in approach:
                params["intervals"] = [1, 3, 7, 14, 30, 60]
        return params

    async def learn_from_failure(
        self,
        failed_goal: LearningGoal,
        failure_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        从失败中学习

        分析失败原因，调整学习策略
        """
        analysis = {
            "failure_reasons": [],
            "strategy_adjustments": [],
            "alternative_approaches": [],
        }

        if self.llm:
            analysis = await self._analyze_failure(failed_goal, failure_context)

        for strategy_name in analysis.get("strategy_adjustments", []):
            if strategy_name in self._strategies:
                self._strategies[strategy_name].expected_efficiency *= 0.9

        return analysis

    async def transfer_knowledge(
        self,
        source_domain: str,
        target_domain: str,
        knowledge_ids: List[str],
    ) -> Dict[str, Any]:
        """
        知识迁移

        将知识从一个领域迁移到另一个领域
        """
        transferred = []

        for kid in knowledge_ids:
            if self.knowledge:
                knowledge = await self.knowledge.retrieve(kid)
                if knowledge:
                    adapted = await self._adapt_knowledge(knowledge, source_domain, target_domain)
                    transferred.append(adapted)

        return {
            "transferred_count": len(transferred),
            "transfer_details": transferred,
            "adaptation_required": len(transferred) > 0,
        }

    async def _ensure_initialized(self):
        """确保已初始化"""
        if not self._initialized:
            await self.initialize()

    def get_meta_learning_stats(self) -> Dict[str, Any]:
        """获取元学习统计"""
        return {
            "total_learning_sessions": len(self._meta_records),
            "strategies_available": len(self._strategies),
            "strategy_performance": {
                name: {
                    "efficiency": s.expected_efficiency,
                    "success_rate": sum(s.success_history) / len(s.success_history)
                    if s.success_history
                    else 0.5,
                    "applications": len(s.success_history),
                }
                for name, s in self._strategies.items()
            },
            "optimal_conditions": self._optimal_conditions,
        }

    async def _practice_iteration(self, goal: LearningGoal, iteration: int) -> Dict[str, Any]:
        if not self.llm:
            return {"knowledge": [], "improvements": []}
        prompt = f"""针对学习目标"{goal.title}"进行第{iteration + 1}次练习。
请输出：
1. 练习要点
2. 发现的问题
3. 改进建议"""
        try:
            response = await self.llm.chat(prompt)
            return {
                "knowledge": [f"练习{iteration + 1}: {response[:200]}"],
                "improvements": [],
            }
        except Exception:
            return {"knowledge": [], "improvements": []}

    async def _find_similar_domains(self, domain: str, threshold: float) -> List[str]:
        return ["编程", "问题解决", "系统设计"][:2]

    async def _extract_transferable_knowledge(self, source: str, target: str) -> List[str]:
        return [f"从{source}迁移到{target}的知识模式"]

    async def _decompose_goal(self, goal: LearningGoal, chunk_size: int) -> List[Dict]:
        return [{"id": i, "content": f"子任务{i}"} for i in range(chunk_size)]

    async def _learn_chunk(self, chunk: Dict) -> Dict[str, Any]:
        return {"knowledge": f"学习了{chunk.get('id')}"}

    def _create_repetition_schedule(self, goal: LearningGoal, intervals: List[int]) -> List[Dict]:
        import time

        return [{"day": d, "goal_id": goal.id} for d in intervals]

    async def _generate_explanation(self, goal: LearningGoal, depth: int) -> str:
        if not self.llm:
            return f"深度{depth}解释: {goal.title}"
        return f"对'{goal.title}'的第{depth}层解释"

    async def _elaborate_knowledge(self, goal: LearningGoal, depth: int) -> List[str]:
        return [f"精细加工{i}: {goal.title}" for i in range(depth)]

    async def _find_knowledge_associations(self, goal: LearningGoal) -> List[Dict]:
        return [{"from": goal.id, "to": "related_knowledge"}]

    async def _analyze_failure(self, goal: LearningGoal, context: Dict) -> Dict[str, Any]:
        return {
            "failure_reasons": ["策略不匹配"],
            "strategy_adjustments": ["iterative_practice"],
            "alternative_approaches": ["尝试分块学习"],
        }

    async def _adapt_knowledge(self, knowledge: Any, source: str, target: str) -> Dict[str, Any]:
        return {"original": knowledge, "adapted_for": target}
