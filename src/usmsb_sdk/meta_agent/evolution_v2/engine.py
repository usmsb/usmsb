"""
自主进化引擎 - Self Evolution Engine

整合所有进化组件，实现AGI系统的自主进化

v2.1 新增组件：
- CausalDiscoveryEngine: 因果发现
- CausalMetaLearner: 因果元学习
- CausalPlanner: 因果规划
- CausalVerifier: 因果验证
- ReasoningEnhancer: 推理增强
- AutoSkillEngine: Skill 自创建
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from .capability_assessor import CapabilityAssessor
from .curiosity_engine import CuriosityEngine
from .goal_generator import GoalGenerator
from .knowledge_solidifier import KnowledgeSolidifier
from .meta_learner import LearningContext, MetaLearner
from .models import (
    CapabilityTransfer,
    EvolutionPhase,
    EvolutionState,
    LearningGoal,
    SelfReflection,
)
from .self_optimizer import SelfOptimizer

# v2.1 因果学习组件
from .causal_discovery import CausalDiscoveryEngine
from .causal_meta_learner import CausalMetaLearner, CausalMetaLearnerConfig
from .causal_planner import CausalPlanner, CausalPlannerConfig
from .causal_verifier import CausalVerifier
from .reasoning_enhancer import ReasoningEnhancer
from .auto_skill import AutoSkillEngine, AutoSkillEngineConfig

logger = logging.getLogger(__name__)


class SelfEvolutionEngine:
    """
    自主进化引擎

    整合元学习、能力评估、知识固化、好奇心驱动、自我优化等组件，
    实现AGI系统的全面自主进化能力。

    v2.1 新增：因果学习系统
    - 因果发现：PC Algorithm 完整实现
    - 因果元学习：MAML + EWC
    - 因果规划：跨任务策略迁移
    - 因果验证：do-calculus 反事实推断
    - 推理增强：CoT + 多路径一致性
    - Skill 自创建：自动发现缺口并创建 Skill

    核心特性：
    1. 自主学习 - 无监督的知识获取
    2. 能力进化 - 技能提升、新能力涌现
    3. 自我评估 - 性能监控、弱点识别
    4. 自我优化 - 策略调整、参数优化
    5. 知识固化 - 将临时知识转化为永久能力
    6. 因果学习 - 深度因果发现和泛化
    """

    def __init__(
        self,
        llm_manager=None,
        knowledge_base=None,
        config: dict[str, Any] | None = None,
    ):
        self.llm = llm_manager
        self.knowledge = knowledge_base
        self.config = config or {}

        self._state = EvolutionState()

        # v2.0 组件
        self._meta_learner = MetaLearner(llm_manager, knowledge_base)
        self._capability_assessor = CapabilityAssessor(llm_manager, knowledge_base)
        self._knowledge_solidifier = KnowledgeSolidifier(
            llm_manager, knowledge_base, self._capability_assessor
        )
        self._curiosity_engine = CuriosityEngine(
            llm_manager, knowledge_base, self._capability_assessor
        )
        self._self_optimizer = SelfOptimizer(
            llm_manager, self._capability_assessor, self._meta_learner
        )
        self._goal_generator = GoalGenerator(
            llm_manager, self._capability_assessor, self._curiosity_engine
        )

        # v2.1 因果学习组件
        self._causal_discovery = CausalDiscoveryEngine()
        self._causal_meta_learner = CausalMetaLearner(
            llm_manager, knowledge_base, CausalMetaLearnerConfig()
        )
        self._causal_verifier = CausalVerifier(causal_graph=None)
        self._reasoning_enhancer = ReasoningEnhancer(llm_manager)
        self._auto_skill_engine = AutoSkillEngine(
            causal_graph=None,
            llm_manager=llm_manager,
            skill_registry={},
            curiosity_engine=self._curiosity_engine,
            task_executor=None,
            config=AutoSkillEngineConfig(),
        )

        # 因果规划器（在获取因果图后初始化）
        self._causal_planner: CausalPlanner | None = None

        self._running = False
        self._evolution_task: asyncio.Task | None = None
        self._evolution_interval = self.config.get("evolution_interval", 300)

        self._performance_history: list[float] = []
        self._transfer_records: list[CapabilityTransfer] = []

        self._initialized = False

    async def initialize(self):
        """初始化进化引擎"""
        if self._initialized:
            return

        # v2.0 组件初始化
        await self._meta_learner.initialize()
        await self._capability_assessor.initialize()
        await self._knowledge_solidifier.initialize()
        await self._curiosity_engine.initialize()
        await self._self_optimizer.initialize()
        await self._goal_generator.initialize()

        # v2.1 因果组件初始化
        await self._causal_discovery.initialize()
        await self._causal_meta_learner.initialize()

        self._initialized = True
        logger.info("SelfEvolutionEngine (v2.1) initialized")

    async def start(self):
        """启动进化引擎"""
        if self._running:
            return

        await self._ensure_initialized()

        self._running = True
        self._evolution_task = asyncio.create_task(self._evolution_loop())
        logger.info("SelfEvolutionEngine started")

    async def stop(self):
        """停止进化引擎"""
        self._running = False
        if self._evolution_task:
            self._evolution_task.cancel()
            try:
                await self._evolution_task
            except asyncio.CancelledError:
                pass
        logger.info("SelfEvolutionEngine stopped")

    async def _evolution_loop(self):
        """进化主循环"""
        while self._running:
            try:
                await asyncio.sleep(self._evolution_interval)

                await self._execute_evolution_cycle()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Evolution cycle error: {e}")
                await asyncio.sleep(60)

    async def _execute_evolution_cycle(self):
        """执行进化周期"""
        logger.info(f"Starting evolution cycle (generation {self._state.generation})")

        self._update_evolution_phase()

        reflection = await self.self_reflect()

        learning_result = await self.autonomous_learning()

        consolidation_result = await self.consolidate_knowledge()

        optimization_result = await self.optimize_self()

        # v2.1: 因果学习循环
        await self._causal_learning_loop()

        # v2.1: AutoSkillEngine 清理
        if self._auto_skill_engine:
            await self._auto_skill_engine.skill_curator.run_curation()

        self._state.generation += 1
        self._state.last_evolution = datetime.now().timestamp()

        self._record_evolution(
            {
                "generation": self._state.generation,
                "phase": self._state.phase.value,
                "reflection": reflection.observations[:3] if reflection.observations else [],
                "learning": learning_result.get("knowledge_gained", []),
                "consolidation": consolidation_result,
                "optimization": optimization_result,
            }
        )

        logger.info(f"Evolution cycle {self._state.generation} completed")

    def _update_evolution_phase(self):
        """更新进化阶段"""
        avg_capability = self._calculate_average_capability()
        knowledge_count = self._knowledge_solidifier.get_knowledge_state_summary()["total"]
        active_goals = len(self._goal_generator.get_active_goals())

        if avg_capability < 0.3:
            self._state.phase = EvolutionPhase.EXPLORATION
        elif avg_capability < 0.5:
            self._state.phase = EvolutionPhase.ACQUISITION
        elif avg_capability < 0.7:
            self._state.phase = EvolutionPhase.CONSOLIDATION
        elif avg_capability < 0.9:
            self._state.phase = EvolutionPhase.OPTIMIZATION
        else:
            self._state.phase = EvolutionPhase.MASTERY

        self._state.total_knowledge = knowledge_count
        self._state.active_goals = active_goals

    def _calculate_average_capability(self) -> float:
        """计算平均能力分数"""
        caps = self._capability_assessor.get_all_capabilities()
        if not caps:
            return 0.0
        return sum(c.score for c in caps.values()) / len(caps)

    async def autonomous_learning(self) -> dict[str, Any]:
        """
        自主学习

        无监督的知识获取和能力提升
        """
        await self._ensure_initialized()

        result = {
            "knowledge_gained": [],
            "capabilities_improved": [],
            "goals_completed": [],
        }

        goals = await self._goal_generator.generate_goals(count=3)

        for goal in goals[:2]:
            goal_result = await self._pursue_goal(goal)
            result["knowledge_gained"].extend(goal_result.get("knowledge", []))
            result["capabilities_improved"].extend(goal_result.get("improvements", []))

        exploration = await self._curiosity_engine.explore()
        result["knowledge_gained"].extend(exploration.knowledge_gained)

        for discovery in exploration.discoveries:
            await self._knowledge_solidifier.add_knowledge(
                content=discovery,
                source="exploration",
            )

        return result

    async def _pursue_goal(self, goal: LearningGoal) -> dict[str, Any]:
        """追求学习目标"""
        result = {"knowledge": [], "improvements": []}

        goal.started_at = datetime.now().timestamp()

        context = LearningContext(
            domain=goal.title,
            difficulty=0.5,
            prior_knowledge=0.3,
            time_available=1800,
            goal_importance=0.8,
        )

        learning_result = await self._meta_learner.execute_learning(goal, context)

        result["knowledge"].extend(learning_result.get("knowledge_gained", []))

        if goal.target_capability:
            await self._capability_assessor.record_performance(
                goal.target_capability,
                success=True,
                performance_score=learning_result.get("efficiency", 0.5),
            )
            result["improvements"].append(goal.target_capability)

        goal.progress = 1.0
        self._goal_generator.complete_goal(goal.id, success=True)

        return result

    async def self_reflect(self) -> SelfReflection:
        """
        自我反思

        评估自己的推理和决策
        """
        await self._ensure_initialized()

        reflection = await self._capability_assessor.generate_self_reflection()

        optimization_suggestions = await self._self_optimizer.suggest_improvements(reflection)

        reflection.action_items.extend(
            [
                {"action": s["suggestion"], "priority": s.get("priority", "medium")}
                for s in optimization_suggestions[:3]
            ]
        )

        self._state.self_awareness_score = reflection.confidence_level

        return reflection

    async def consolidate_knowledge(self) -> dict[str, Any]:
        """
        知识固化

        将临时知识转化为永久能力
        """
        await self._ensure_initialized()

        result = await self._knowledge_solidifier.consolidate_knowledge()

        compression = await self._knowledge_solidifier.compress_knowledge()
        result["compression"] = compression

        self._state.total_knowledge = self._knowledge_solidifier.get_knowledge_state_summary()[
            "total"
        ]

        return result

    async def optimize_self(self) -> dict[str, Any]:
        """
        自我优化

        策略调整、参数优化
        """
        await self._ensure_initialized()

        result = await self._self_optimizer.optimize()

        optimizations = await self._meta_learner.optimize_learning_parameters()
        result["meta_optimizations"] = optimizations

        avg_performance = self._calculate_average_capability()
        await self._self_optimizer.update_performance(avg_performance)

        self._state.adaptation_rate = result.get("improvements", []) and 0.7 or 0.5

        return result

    # ==================== v2.1 因果学习系统 ====================

    async def _causal_learning_loop(self) -> dict[str, Any]:
        """
        因果学习主循环

        v2.1 新增

        1. 收集新经验（从执行记录中）
        2. 增量更新因果图
        3. 定期全量重构因果图
        4. 运行元学习更新
        """
        result = {
            "causal_graph_updated": False,
            "full_rebuild_triggered": False,
            "meta_learning_performed": False,
        }

        try:
            # 1. 收集新经验
            new_records = await self._collect_new_experiences()

            if new_records:
                # 2. 检查是否应该增量更新
                if self._causal_discovery.updater.should_incremental_update():
                    updated_graph, triggered = self._causal_discovery.discover_incremental(
                        new_records
                    )

                    if updated_graph:
                        # 更新因果规划器
                        self._update_causal_planner(updated_graph)

                        result["causal_graph_updated"] = True

                        # 检查是否触发了全量重构
                        if triggered:
                            result["full_rebuild_triggered"] = True
                            logger.info("Causal graph full rebuild triggered")

                # 3. 记录用于元学习 (placeholder - 元学习更新需要更复杂的实现)
                # TODO: 实现元学习状态更新
                new_records_count = len(new_records) if new_records else 0
                if new_records_count > 0:
                    logger.debug(f"Recorded {new_records_count} new records for meta-learning")

            # 4. 检查是否应该全量重构
            if self._causal_discovery.updater.should_full_rebuild():
                all_records = await self._get_all_task_records()
                if all_records:
                    graph = self._causal_discovery.full_rebuild(all_records)
                    if graph:
                        self._update_causal_planner(graph)
                        result["full_rebuild_triggered"] = True

            logger.debug(f"Causal learning loop completed: {result}")

        except Exception as e:
            logger.error(f"Causal learning loop error: {e}")

        return result

    def _update_causal_planner(self, causal_graph) -> None:
        """更新因果规划器"""
        if causal_graph and self._causal_discovery:
            self._causal_verifier = CausalVerifier(causal_graph=causal_graph)
            self._auto_skill_engine.graph = causal_graph

            if self.llm:
                self._causal_planner = CausalPlanner(
                    causal_graph=causal_graph,
                    llm_manager=self.llm,
                    config=CausalPlannerConfig(),
                )

    async def _collect_new_experiences(self) -> list:
        """收集新经验"""
        # 简化实现，实际应该从数据库或任务执行器获取
        return []

    async def _get_all_task_records(self) -> list:
        """获取所有任务记录"""
        # 简化实现，实际应该从数据库获取
        return []

    async def enhance_reasoning(
        self,
        task: Any,
        context: Any,
    ) -> "ReasoningResult":
        """
        增强推理

        v2.1 新增
        使用 ReasoningEnhancer 增强推理过程
        """
        return await self._reasoning_enhancer.reason(
            task=task,
            context=context,
        )

    async def verify_strategy(
        self,
        strategy_a: Any,
        strategy_b: Any,
        task: Any,
    ) -> "VerificationResult":
        """
        验证策略

        v2.1 新增
        使用 CausalVerifier 验证策略
        """
        from .causal_verifier import VerificationContext

        context = VerificationContext(
            task_id=getattr(task, "task_id", "unknown"),
            strategy_a=strategy_a,
            strategy_b=strategy_b,
            outcome_a=None,
            task_features=getattr(task, "features", {}),
            historical_records=[],
            verification_cost=1.0,
        )

        return await self._causal_verifier.verify_counterfactual(context)

    # ==================== 能力迁移 ====================

    async def transfer_capability(
        self,
        source_capability_id: str,
        target_domain: str,
    ) -> CapabilityTransfer:
        """
        能力迁移

        将能力从一领域迁移到另一领域
        """
        await self._ensure_initialized()

        source_cap = self._capability_assessor.get_capability(source_capability_id)
        if not source_cap:
            return CapabilityTransfer(
                source_capability=source_capability_id,
                target_domain=target_domain,
                adaptation_required=1.0,
                transfer_success=0.0,
            )

        transfer_result = await self._meta_learner.transfer_knowledge(
            source_domain=source_cap.name,
            target_domain=target_domain,
            knowledge_ids=[],
        )

        transfer = CapabilityTransfer(
            source_capability=source_capability_id,
            target_domain=target_domain,
            adaptation_required=1.0 - source_cap.score,
            transfer_success=transfer_result.get("transferred_count", 0) * 0.2,
            knowledge_extracted=transfer_result.get("transfer_details", []),
        )

        if transfer.transfer_success > 0.3:
            new_cap = await self._create_derived_capability(source_cap, target_domain)
            transfer.new_capability_id = new_cap.id

        self._transfer_records.append(transfer)

        return transfer

    async def _create_derived_capability(
        self,
        source: Any,
        target_domain: str,
    ):
        """创建派生能力"""
        from .models import Capability

        new_cap = Capability(
            name=f"{target_domain}_{source.name[:5]}",
            description=f"从{source.name}迁移到{target_domain}的能力",
            score=source.score * 0.7,
            prerequisite_ids=[source.id],
        )

        self._capability_assessor.add_capability(new_cap)

        return new_cap

    async def learn_from_interaction(
        self,
        interaction_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        从交互中学习

        Args:
            interaction_data: 交互数据（对话、任务执行等）

        Returns:
            学习结果
        """
        await self._ensure_initialized()

        result = {
            "knowledge_added": 0,
            "capabilities_updated": [],
        }

        messages = interaction_data.get("messages", [])
        success = interaction_data.get("success", True)
        task_type = interaction_data.get("task_type", "general")

        for message in messages:
            if isinstance(message, dict):
                content = message.get("content", "")
                if content and len(content) > 20:
                    await self._knowledge_solidifier.add_knowledge(
                        content=content,
                        source="interaction",
                        metadata={"task_type": task_type, "success": success},
                    )
                    result["knowledge_added"] += 1

        related_caps = self._find_related_capabilities(task_type)
        for cap_id in related_caps:
            await self._capability_assessor.record_performance(
                cap_id,
                success=success,
                performance_score=0.7 if success else 0.3,
            )
            result["capabilities_updated"].append(cap_id)

        return result

    def _find_related_capabilities(self, task_type: str) -> list[str]:
        """找到与任务类型相关的能力"""
        mapping = {
            "coding": ["code_generation", "debugging", "problem_solving"],
            "conversation": ["communication", "reasoning"],
            "analysis": ["reasoning", "pattern_recognition", "knowledge_integration"],
            "planning": ["planning", "decision_making", "reasoning"],
            "execution": ["execution", "tool_usage"],
        }

        return mapping.get(task_type, ["reasoning", "learning"])

    def _record_evolution(self, record: dict[str, Any]):
        """记录进化历史"""
        self._state.evolution_history.append(record)
        if len(self._state.evolution_history) > 100:
            self._state.evolution_history = self._state.evolution_history[-100:]

    async def _ensure_initialized(self):
        """确保已初始化"""
        if not self._initialized:
            await self.initialize()

    def get_evolution_state(self) -> EvolutionState:
        """获取进化状态"""
        return self._state

    def get_comprehensive_report(self) -> dict[str, Any]:
        """获取综合报告"""
        return {
            "evolution_state": {
                "generation": self._state.generation,
                "phase": self._state.phase.value,
                "total_knowledge": self._state.total_knowledge,
                "learning_efficiency": self._state.learning_efficiency,
                "adaptation_rate": self._state.adaptation_rate,
                "self_awareness": self._state.self_awareness_score,
            },
            "capabilities": self._capability_assessor.get_performance_summary(),
            "knowledge": self._knowledge_solidifier.get_knowledge_state_summary(),
            "curiosity": self._curiosity_engine.get_curiosity_stats(),
            "goals": self._goal_generator.get_goal_stats(),
            "meta_learning": self._meta_learner.get_meta_learning_stats(),
            "optimization": {
                "parameters": {
                    name: p.current_value for name, p in self._self_optimizer._parameters.items()
                },
            },
        }

    # ==================== v2.0 兼容接口 ====================

    async def evolve(self) -> dict[str, Any]:
        """
        执行一次进化迭代（兼容 v2.0 EvolutionEngine）

        Returns:
            dict with keys: knowledge_added, patterns_identified
        """
        try:
            # v2.1 的进化逻辑在 _execute_evolution_cycle 中
            # 这里只触发一次学习
            result = await self.learn_from_interaction({
                "messages": [],
                "success": True,
                "task_type": "general",
            })
            return {
                "knowledge_added": result.get("knowledge_added", 0),
                "patterns_identified": 0,
            }
        except Exception as e:
            logger.error(f"evolve() failed: {e}")
            return {"knowledge_added": 0, "patterns_identified": 0}

    def get_evolution_stats(self) -> dict[str, Any]:
        """
        获取进化统计（兼容 v2.0 EvolutionEngine）
        """
        report = self.get_comprehensive_report()
        return {
            "total_evolutions": report.get("evolution_state", {}).get("generation", 0),
            "by_type": {
                "knowledge_gain": report.get("knowledge", {}).get("total", 0),
                "skill_improvement": 0,
                "pattern_learning": 0,
            },
            "by_status": {
                "applied": report.get("knowledge", {}).get("total", 0),
                "pending": 0,
            },
            "capabilities": {
                k: {"score": v.get("score", 0.5)}
                for k, v in report.get("capabilities", {}).items()
            },
        }


async def create_evolution_engine(
    llm_manager=None,
    knowledge_base=None,
    config: dict[str, Any] | None = None,
) -> SelfEvolutionEngine:
    """创建并初始化进化引擎"""
    engine = SelfEvolutionEngine(
        llm_manager=llm_manager,
        knowledge_base=knowledge_base,
        config=config,
    )
    await engine.initialize()
    return engine
