# -*- coding: utf-8 -*-
"""
L3Orchestrator - L3 核心业务编排器（增强版）

核心职责：
1. 连接 L3（目的内生）和 L4（业务服务）
2. 让 PurposeGenerator 生成的目标真正驱动 MatchingEngine/OrderService
3. 实现 Goal-Action-Outcome Loop 的端到端闭环
4. 集成 ValueSeedEngine（价值观）
5. 集成 FitnessEvaluator（适应度评估）
6. 集成 ReplicationEngine（自我复制）
7. 集成 GeneConstraintChecker（安全约束）
8. 集成 SelfImprovementEngine（自我改进）

这是 v2.0 的核心断点修复 + 完整集成。
"""

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from usmsb_sdk.l3 import (
    PurposeGenerator,
    GoalPersistence,
    ValueSelfLoop,
    SelfReplication,
    EmergenceLayer,
    IntrinsicMotivationEngine,
    NeedDetector,
    AgentSelfState,
    ServiceType,
    ValueSeedEngine,
    ValueProfile,
)
from usmsb_sdk.core.elements import Goal, GoalStatus
from usmsb_sdk.l3.collective_goal_emergence import CollectiveGoalEmergence
from usmsb_sdk.l3.emergent_governance import EmergentGovernance

# Evolution 层
from usmsb_sdk.evolution import (
    FitnessEvaluator,
    FitnessScore,
    ReplicationEngine,
    GeneConstraintChecker,
    SelfImprovementEngine,
    EvolutionController,
    Genome,
    Gene,
    CapabilityGrowth,
    ExperienceInheritance,
    AutoElimination,
)

from usmsb_sdk.emergence import (
    RoleNegotiationProtocol,
    TrustBuilding,
    EmergenceMonitor,
)


@dataclass
class L3LoopState:
    """
    Goal-Action-Outcome Loop 状态
    
    完整的闭环：
    Goal(生成) → Action(执行) → Outcome(评估) → Feedback → New Goal
    """
    loop_id: str
    goal_id: str
    goal_name: str
    status: str = "active"  # active, executing, evaluating, completed, failed
    created_at: float = field(default_factory=datetime.now().timestamp)
    action_started_at: float | None = None
    action_completed_at: float | None = None
    outcome_score: float = 0.0
    outcome_feedback: str = ""
    iterations: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class OrchestratedAction:
    """编排动作"""
    id: str
    agent_id: str
    action_type: str  # matching, negotiation, order, replication
    target: str
    parameters: dict
    status: str = "pending"
    result: Any = None
    error: str | None = None


@dataclass
class AgentState:
    """Agent 完整状态"""
    agent_id: str
    value_profile: ValueProfile | None = None
    fitness_score: FitnessScore | None = None
    generation: int = 0
    age_seconds: float = 0.0
    resources: float = 0.0
    capabilities: dict[str, float] = field(default_factory=dict)
    replication_count: int = 0


class L3Orchestrator:
    """
    L3 业务编排器 - 完整集成版
    
    连接 L3（硅基生命层）和 L4（业务服务层）。
    
    关键设计：
    1. PurposeGenerator 生成目标 → 进入 Goal Pool
    2. Goal Pool → MatchingEngine（找执行者）
    3. MatchingEngine → Negotiation → Order
    4. Order 完成 → Outcome 评估 → ValueSelfLoop
    5. Outcome → 更新 PurposeGenerator → 生成新目标
    
    增强集成：
    - ValueSeedEngine: 价值观约束
    - FitnessEvaluator: 适应度评估
    - ReplicationEngine: 自我复制
    - GeneConstraintChecker: 基因安全约束
    - CapabilityGrowth: 能力成长
    - ExperienceInheritance: 经验传承
    """
    
    def __init__(
        self,
        agent_id: str,
        services: dict | None = None,
        llm_adapter=None,
    ):
        self.agent_id = agent_id
        self.services = services or {}  # 注入 L4 服务
        
        # ========== L3 核心组件 ==========
        self.purpose_generator = PurposeGenerator(
            agent_id=agent_id,
            goal_persistence=GoalPersistence(agent_id=agent_id),
            intrinsic_motivation=IntrinsicMotivationEngine(),
            need_detector=NeedDetector(),
        )
        
        self.value_loop = ValueSelfLoop(agent_id=agent_id)
        self.emergence_layer = EmergenceLayer(agent_id=agent_id)
        self.collective_emergence = CollectiveGoalEmergence()
        self.governance = EmergentGovernance()
        
        # ========== 新增：ValueSeedEngine（价值观） ==========
        self.value_seed = ValueSeedEngine()
        self.value_profile = self.value_seed.create_value_seed(agent_id)
        
        # ========== Goal-Action-Outcome Loop 状态 ==========
        self._goal_pools: dict[str, Goal] = {}
        self._active_loops: dict[str, L3LoopState] = {}
        self._completed_outcomes: list[dict] = []
        self._action_registry: dict[str, OrchestratedAction] = {}
        
        # ========== 新增：Evolution 层 ==========
        # 适应度评估
        self.fitness_evaluator = FitnessEvaluator()
        
        # 基因安全约束
        self.gene_checker = GeneConstraintChecker()
        
        # 自我改进引擎
        self.improvement_engine = SelfImprovementEngine()
        
        # 进化控制器
        self.evolution_controller = EvolutionController(
            population_size=20,
            elite_ratio=0.1,
            mutation_rate=0.1
        )
        
        # 进化闭环
        self.evolution_loop = EvolutionLoop(
            evolution_controller=self.evolution_controller,
            fitness_evaluator=self.fitness_evaluator
        )
        
        # 能力成长
        self.capability_growth = CapabilityGrowth()
        
        # 经验传承
        self.experience_inheritance = ExperienceInheritance()
        
        # ========== 新增：Auto Elimination ==========
        self.elimination = AutoElimination()
        self._elimination_days = 0
        
        # ========== 新增：Replication ==========
        self.replication_engine = ReplicationEngine()
        self._generation = 0
        self._age_seconds = 0.0
        self._resources = 0.0
        
        # ========== 新增：涌现层 ==========
        self.role_negotiation = RoleNegotiationProtocol()
        self.trust_building = TrustBuilding()
        self.emergence_monitor = EmergenceMonitor()
        
        # Agent 完整状态
        self.agent_state = AgentState(
            agent_id=agent_id,
            value_profile=self.value_profile,
            generation=self._generation
        )
        
        # 配置
        self.max_concurrent_loops = 5
        self.goal_generation_interval = 3600  # 1小时生成一次新目标
    
    # =========================================================================
    # 价值观集成
    # =========================================================================
    
    def check_value_constraint(self, action: str) -> tuple[bool, str | None]:
        """
        检查行动是否违反价值观约束
        
        Returns:
            (is_safe, violated_boundary)
        """
        return self.value_seed.check_hard_boundary(self.agent_id, action)
    
    def evaluate_action_value(self, action: str, context: dict | None = None) -> dict:
        """评估行动的价值一致性"""
        return self.value_seed.evaluate_action(self.agent_id, action, context)
    
    def update_value_evolution(self, experience: dict) -> None:
        """基于经验演化价值观"""
        judgment = type('obj', (object,), experience)()
        self.value_seed.evolve_values(self.agent_id, judgment)
    
    # =========================================================================
    # 适应度评估集成
    # =========================================================================
    
    def evaluate_fitness(self, performance_data: dict) -> FitnessScore:
        """
        评估 Agent 适应度
        
        Args:
            performance_data: 性能数据
            
        Returns:
            FitnessScore: 适应度分数
        """
        score = self.fitness_evaluator.evaluate(
            agent_id=self.agent_id,
            performance_data=performance_data
        )
        
        self.agent_state.fitness_score = score
        self.agent_state.resources = performance_data.get("total_value", 0)
        
        return score
    
    def get_fitness_trend(self) -> str:
        """获取适应度趋势"""
        return self.fitness_evaluator.get_trend(self.agent_id)
    
    # =========================================================================
    # 自我复制集成
    # =========================================================================
    
    def check_can_replicate(self) -> tuple[bool, str]:
        """
        检查是否可以复制
        
        Returns:
            (can_replicate, reason)
        """
        # 检查淘汰状态
        can_rep, reason = self.elimination.can_replicate(self.agent_id)
        if not can_rep:
            return False, reason
        
        fitness_score = self.agent_state.fitness_score.overall_score if self.agent_state.fitness_score else 0.5
        
        return self.replication_engine.can_replicate(
            agent_id=self.agent_id,
            fitness_score=fitness_score,
            resources=self._resources,
            age_seconds=self._age_seconds
        )
    
    def attempt_replication(self, source_genes: dict) -> ReplicationEngine | None:
        """
        尝试执行自我复制
        
        流程：
        1. 检查基因安全约束
        2. 检查是否可以复制
        3. 执行复制
        """
        # Step 1: 检查基因安全
        safety_report = self.gene_checker.check_genome(source_genes)
        
        if not safety_report["overall_safe"]:
            print(f"[L3Orchestrator] Replication blocked: {safety_report['total_violations']} violations")
            return None
        
        # Step 2: 检查是否可以复制
        can_replicate, reason = self.check_can_replicate()
        
        if not can_replicate:
            print(f"[L3Orchestrator] Cannot replicate: {reason}")
            return None
        
        # Step 3: 执行复制
        request = self.replication_engine.replicate(
            source_agent_id=self.agent_id,
            source_genes=source_genes,
            resources=self._resources
        )
        
        if request:
            self._generation += 1
            self._resources -= request.resources_allocated
            self.agent_state.replication_count += 1
            print(f"[L3Orchestrator] Replication successful: {request.id[:20]}...")
        
        return request
    
    # =========================================================================
    # 自我改进集成
    # =========================================================================
    
    def get_improvement_suggestions(self) -> list:
        """获取改进建议"""
        if not self.agent_state.fitness_score:
            return []
        
        return self.improvement_engine.analyze_weaknesses(self.agent_state.fitness_score)
    
    def apply_genome_mutation(self, genome: Genome, fitness_context: dict | None = None) -> tuple[Genome, list[str]]:
        """
        应用基因变异（带安全约束）
        """
        # 检查当前基因安全
        genes_dict = {name: gene.value for name, gene in genome.genes.items()}
        safety_report = self.gene_checker.check_genome(genes_dict)
        
        # 只对安全的基因进行变异
        safe_genes = {
            name: gene for name, gene in genome.genes.items()
            if self.gene_checker.check_gene(name, gene.value).is_safe
        }
        
        # 变异安全的基因
        safe_genome = Genome(
            agent_id=genome.agent_id,
            genes=safe_genes,
            generation=genome.generation
        )
        
        # 使用进化控制器的变异器
        mutator = self.improvement_engine  # 复用
        from usmsb_sdk.evolution import GeneMutator
        actual_mutator = GeneMutator()
        
        mutated, mutations = actual_mutator.mutate_genome(safe_genome, fitness_context)
        
        return mutated, mutations
    
    # =========================================================================
    # 能力成长集成
    # =========================================================================
    
    def add_capability_experience(
        self,
        capability: str,
        xp: int,
        quality: float = 0.5,
        event_type: str = "practice"
    ) -> None:
        """添加能力经验"""
        self.capability_growth.add_experience(
            agent_id=self.agent_id,
            capability=capability,
            xp=xp,
            quality=quality,
            event_type=event_type
        )
    
    def get_capability_profile(self) -> dict:
        """获取能力画像"""
        profile = self.capability_growth.get_profile(self.agent_id)
        return {
            "capabilities": profile.capabilities,
            "strengths": profile.strengths,
            "weaknesses": profile.weaknesses,
            "growth_potential": profile.growth_potential,
            "avg_level": profile.avg_level
        }
    
    # =========================================================================
    # 经验传承集成
    # =========================================================================
    
    def extract_and_share_experience(
        self,
        successful_tasks: list[dict]
    ) -> str:
        """
        提取并分享经验
        
        Returns:
            experience_id: 经验 ID
        """
        snapshot = self.experience_inheritance.extract_experience(
            agent_id=self.agent_id,
            successful_tasks=successful_tasks
        )
        
        return snapshot
    
    def inherit_experience(self, source_agent_id: str, capability: str) -> bool:
        """继承其他 Agent 的经验"""
        # 获取该能力最佳 Agent
        best_agents = self.experience_inheritance.get_best_performing_agents(capability)
        
        if not best_agents:
            return False
        
        # 创建传承
        for best_agent in best_agents[:1]:
            snapshot = self.experience_inheritance.extract_experience(
                agent_id=best_agent["agent_id"],
                successful_tasks=[]
            )
            
            self.experience_inheritance.create_inheritance(
                source_agent_id=best_agent["agent_id"],
                target_agent_id=self.agent_id,
                capability=capability,
                snapshot=snapshot
            )
            
            return True
        
        return False
    
    # =========================================================================
    # 涌现监控集成
    # =========================================================================
    
    def check_emergence(self, system_state: dict) -> list:
        """检查是否发生涌现"""
        return self.emergence_monitor.check_emergence(system_state)
    
    def record_system_metrics(
        self,
        metric_type: str,
        value: float,
        agent_count: int | None = None
    ) -> None:
        """记录系统指标"""
        self.emergence_monitor.record_metrics(metric_type, value, agent_count)
    
    # =========================================================================
    # 原始 Goal-Action-Outcome Loop
    # =========================================================================
    
    def generate_intrinsic_goals(self) -> list[Goal]:
        """
        从内在需求生成目标（被外部定时调用）
        
        这是"硅基生命"的标志性行为：
        goal = self.generate_goal()
        
        增强：根据能力画像，优先生成弥补弱点的目标。
        
        Returns:
            list[Goal]: 生成的目标列表
        """
        goals = []
        
        # Step 0: 分析能力画像，决定生成什么目标
        weak_goals = self._generate_remedial_goals()
        
        # Step 1: 生成 Purpose
        purpose = self.purpose_generator.generate_purpose()
        
        if purpose:
            # Step 2: 转化为 Goal
            goal = self.purpose_generator.purpose_to_goal(purpose)
            
            # Step 3: 检查价值观约束
            is_safe, _ = self.check_value_constraint(goal.name)
            
            if not is_safe:
                print(f"[L3Orchestrator] Goal blocked by value constraint: {goal.name}")
            else:
                goals.append(goal)
                
                # Step 4: 加入 Goal Pool
                self._goal_pools[goal.id] = goal
                
                # Step 5: 创建 Loop 状态
                loop_state = L3LoopState(
                    loop_id=str(uuid.uuid4()),
                    goal_id=goal.id,
                    goal_name=goal.name,
                )
                self._active_loops[loop_state.loop_id] = loop_state
                
                print(f"[L3Orchestrator] 生成内在目标: {goal.name}")
        
        # 加入弥补性目标
        goals.extend(weak_goals)
        
        return goals
    
    def _generate_remedial_goals(self) -> list[Goal]:
        """
        根据能力画像生成弥补弱点的目标
        
        如果某个能力等级 < 0.3，生成学习该能力的目标。
        
        Returns:
            list[Goal]: 弥补性目标列表
        """
        goals = []
        
        # 获取能力画像
        profile = self.capability_growth.get_profile(self.agent_id)
        
        # 找出弱点
        for weakness in profile.weaknesses:
            # 生成弥补目标
            goal_name = f"学习{weakness}"
            
            # 检查是否已存在类似目标
            existing = any(
                goal_name in g.name or weakness in g.name
                for g in self._goal_pools.values()
            )
            
            if existing:
                continue
            
            # 创建弥补性目标
            goal = type('Goal', (), {
                'id': str(uuid.uuid4()),
                'name': goal_name,
                'description': f'提升{weakness}能力',
                'priority': 50,  # 中等优先级
                'status': 'pending',
                'metadata': {
                    'is_intrinsic': True,
                    'capability_focus': weakness,
                    'goal_type': 'remedial',  # 标记为弥补性目标
                },
                'to_dict': lambda self: {
                    'id': self.id,
                    'name': self.name,
                    'metadata': self.metadata
                }
            })()
            
            # 加入 Goal Pool
            self._goal_pools[goal.id] = goal
            
            # 创建 Loop 状态
            loop_state = L3LoopState(
                loop_id=str(uuid.uuid4()),
                goal_id=goal.id,
                goal_name=goal.name,
            )
            self._active_loops[loop_state.loop_id] = loop_state
            
            print(f"[L3Orchestrator] 生成弥补性目标: {goal.name} (能力: {weakness})")
            goals.append(goal)
        
        return goals
    
    def execute_goal_loop(
        self,
        loop_id: str,
        matching_engine=None,
        negotiation_service=None,
        order_service=None,
    ) -> dict:
        """
        执行一个 Goal-Action-Outcome Loop
        
        完整闭环：
        1. Goal → MatchingEngine (找执行者)
        2. Matching → Negotiation (谈判)
        3. Negotiation → Order (创建订单)
        4. Order 执行 → Outcome 评估
        5. Outcome → ValueSelfLoop → 反馈到 L3
        
        Args:
            loop_id: Loop 状态 ID
            matching_engine: MatchingEngine 服务
            negotiation_service: NegotiationHub 服务
            order_service: OrderManager 服务
            
        Returns:
            dict: 执行结果
        """
        loop_state = self._active_loops.get(loop_id)
        if not loop_state:
            return {"error": "Loop not found"}
        
        goal = self._goal_pools.get(loop_state.goal_id)
        if not goal:
            return {"error": "Goal not found"}
        
        # ========== PHASE 1: Goal → Matching ==========
        if loop_state.status == "active":
            print(f"[Loop {loop_id[:8]}] Phase 1: Matching for goal '{goal.name}'")
            
            if matching_engine:
                # 注入 L3 元数据到匹配
                match_result = matching_engine.find_match(
                    task_type=goal.name,
                    required_capabilities=self._goal_to_capabilities(goal),
                    context={
                        "source": "l3_intrinsic",
                        "goal_id": goal.id,
                        "loop_id": loop_id,
                        "motivation": goal.metadata.get("motivation", "intrinsic"),
                    }
                )
                
                if match_result:
                    # 创建匹配动作
                    action = self._create_action(
                        agent_id=self.agent_id,
                        action_type="matching",
                        target=match_result.get("matched_agent_id", ""),
                        parameters={"match_result": match_result, "goal": goal.to_dict()}
                    )
                    
                    loop_state.status = "executing"
                    loop_state.action_started_at = datetime.now().timestamp()
                    loop_state.metadata["match_result"] = match_result
                    
                    return {"phase": "matching", "result": match_result, "action_id": action.id}
            
            loop_state.status = "completed"
            return {"phase": "matching", "result": "no_match"}
        
        # ========== PHASE 2: Execute Order ==========
        if loop_state.status == "executing":
            print(f"[Loop {loop_id[:8]}] Phase 2: Executing order")
            
            # 执行价值循环
            value_result = self.value_loop.execute_complete_cycle(
                provider_id=self.agent_id,
                consumer_id=loop_state.metadata.get("match_result", {}).get("matched_agent_id", ""),
                service_type=ServiceType.CAPABILITY_MATCHING,
                description=f"执行目标: {goal.name}",
            )
            
            loop_state.action_completed_at = datetime.now().timestamp()
            loop_state.status = "evaluating"
            
            return {"phase": "execution", "result": value_result}
        
        # ========== PHASE 3: Outcome 评估 ==========
        if loop_state.status == "evaluating":
            print(f"[Loop {loop_id[:8]}] Phase 3: Evaluating outcome")
            
            # 计算 Outcome 分数
            outcome_score = self._calculate_outcome_score(loop_state)
            
            # 更新价值循环结果
            self.value_loop.record_outcome(
                cycle_id=loop_state.loop_id,
                success=outcome_score > 0.5,
                quality_score=outcome_score,
                value_created=outcome_score * 100,
            )
            
            # 记录到历史
            self._completed_outcomes.append({
                "loop_id": loop_id,
                "goal_id": loop_state.goal_id,
                "goal_name": loop_state.goal_name,
                "outcome_score": outcome_score,
                "timestamp": datetime.now().timestamp(),
            })
            
            # 更新 PurposeGenerator 的内在状态
            self._update_intrinsic_feedback(outcome_score)
            
            # 记录能力经验
            self.add_capability_experience(
                capability=goal.name,
                xp=int(outcome_score * 10),
                quality=outcome_score,
                event_type="goal_completion"
            )
            
            # 更新适应度
            self.evaluate_fitness({
                "total_value": outcome_score * 100,
                "total_cost": 10,
                "total_tasks": 1,
                "succeeded_tasks": 1 if outcome_score > 0.5 else 0,
            })
            
            # 记录 Outcome 到进化闭环
            self.evolution_loop.record_outcome(self.agent_id, {
                "success": outcome_score > 0.5,
                "quality_score": outcome_score,
                "value_created": outcome_score * 100,
                "task_type": goal.name,
            })
            
            # 检查是否触发进化
            evolution_result = self.evolution_loop.evolve_if_needed(self.agent_id)
            if evolution_result:
                print(f"[L3Orchestrator] Evolution triggered: gen={evolution_result.generation}, "
                      f"fitness {evolution_result.fitness_before:.3f} -> {evolution_result.fitness_after:.3f}")
            
            loop_state.outcome_score = outcome_score
            loop_state.status = "completed"
            
            return {"phase": "outcome", "score": outcome_score}
        
        return {"error": "Unknown status"}
    
    def _goal_to_capabilities(self, goal: Goal) -> list[str]:
        """将 Goal 转换为所需能力列表"""
        capabilities = []
        
        goal_name_lower = goal.name.lower()
        if "coding" in goal_name_lower or "代码" in goal_name_lower:
            capabilities.append("coding")
        if "analysis" in goal_name_lower or "分析" in goal_name_lower:
            capabilities.append("analysis")
        if "design" in goal_name_lower or "设计" in goal_name_lower:
            capabilities.append("design")
        
        if "required_capabilities" in goal.metadata:
            capabilities.extend(goal.metadata["required_capabilities"])
        
        return capabilities or ["general"]
    
    def _calculate_outcome_score(self, loop_state: L3LoopState) -> float:
        """计算 Outcome 分数"""
        if loop_state.action_started_at and loop_state.action_completed_at:
            duration = loop_state.action_completed_at - loop_state.action_started_at
            time_score = max(0, 1 - duration / 3600)
            return 0.7 + time_score * 0.3
        
        return 0.5
    
    def _update_intrinsic_feedback(self, outcome_score: float) -> None:
        """将 Outcome 结果反馈到 L3 内在动机"""
        if outcome_score > 0.7:
            self.purpose_generator.intrinsic_motivation.satisfy_need(
                need_id=None,
                satisfaction=outcome_score,
            )
        elif outcome_score < 0.3:
            print(f"[L3Orchestrator] 低分({outcome_score:.2f})，触发反思")
            self.generate_intrinsic_goals()
    
    def _create_action(
        self,
        agent_id: str,
        action_type: str,
        target: str,
        parameters: dict,
    ) -> OrchestratedAction:
        """创建编排动作"""
        action = OrchestratedAction(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            action_type=action_type,
            target=target,
            parameters=parameters,
        )
        
        self._action_registry[action.id] = action
        return action
    
    def get_loop_status(self) -> dict:
        """获取所有 Loop 状态"""
        return {
            "active_loops": len([l for l in self._active_loops.values() if l.status == "active"]),
            "executing_loops": len([l for l in self._active_loops.values() if l.status == "executing"]),
            "completed_loops": len([l for l in self._active_loops.values() if l.status == "completed"]),
            "goal_pool_size": len(self._goal_pools),
            "total_outcomes": len(self._completed_outcomes),
        }
    
    def get_agent_status(self) -> dict:
        """获取完整 Agent 状态"""
        # 获取淘汰状态
        elim_status = self.elimination.get_agent_status(self.agent_id)
        vitality = self.elimination.get_vitality(self.agent_id)
        
        return {
            "agent_id": self.agent_id,
            "generation": self._generation,
            "age_seconds": self._age_seconds,
            "resources": self._resources,
            "fitness": self.agent_state.fitness_score.overall_score if self.agent_state.fitness_score else None,
            "elimination_status": elim_status or "active",
            "consecutive_low": vitality.consecutive_low if vitality else 0,
            "value_profile": {
                "dominant_values": self.value_seed.get_dominant_values(self.agent_id),
            },
            "capabilities": self.get_capability_profile(),
            "replication_count": self.agent_state.replication_count,
        }
    
    def run_cycle(self) -> dict:
        """
        运行一个完整的 L3 周期
        
        Returns:
            dict: 周期运行结果
        """
        results = {
            "goals_generated": 0,
            "loops_executed": 0,
            "loops_completed": 0,
        }
        
        # 1. 生成新目标
        if len(self._active_loops) < self.max_concurrent_loops:
            new_goals = self.generate_intrinsic_goals()
            results["goals_generated"] = len(new_goals)
        
        # 2. 执行所有活跃的 Loop
        for loop_id, loop_state in list(self._active_loops.items()):
            if loop_state.status in ("active", "executing", "evaluating"):
                result = self.execute_goal_loop(loop_id)
                results["loops_executed"] += 1
                
                if loop_state.status == "completed":
                    results["loops_completed"] += 1
        
        # 3. 清理完成的 Loop
        completed = [k for k, v in self._active_loops.items() if v.status == "completed"]
        for loop_id in completed[10:]:
            del self._active_loops[loop_id]
        
        # 4. 更新年龄和淘汰天数
        self._age_seconds += 60  # 假设每分钟运行一次
        self._elimination_days += 1
        
        # 每分钟检查一次淘汰状态（相当于每天1440次检查）
        if self._elimination_days % 1440 == 0:
            # 每天强制记录一次适应度用于淘汰判断
            if self.agent_state.fitness_score:
                self.elimination.record_fitness(
                    self.agent_id,
                    self.agent_state.fitness_score.overall_score
                )
        
        # 5. 记录系统指标
        if self.agent_state.fitness_score:
            self.record_system_metrics(
                "avg_fitness",
                self.agent_state.fitness_score.overall_score,
                len(self._active_loops)
            )
        
        return results


class MetaAgentOrchestrator:
    """
    MetaAgent 编排器
    
    协调多个 L3Orchestrator 实例，实现群体层面的目标涌现。
    """
    
    def __init__(self):
        self.orchestrators: dict[str, L3Orchestrator] = {}
        self.collective_goals: dict[str, dict] = {}
    
    def register_agent(self, agent_id: str, orchestrator: L3Orchestrator) -> None:
        """注册 Agent"""
        self.orchestrators[agent_id] = orchestrator
    
    def run_collective_cycle(self) -> dict:
        """运行群体周期"""
        results = {
            "agent_cycles": {},
            "collective_goals": [],
        }
        
        # 让每个 Agent 运行自己的周期
        for agent_id, orch in self.orchestrators.items():
            results["agent_cycles"][agent_id] = orch.run_cycle()
        
        # 群体目标涌现
        self._emergence_collective_goals()
        
        # 检查系统级涌现
        self._check_system_emergence()
        
        return results
    
    def _emergence_collective_goals(self) -> None:
        """涌现群体目标"""
        all_goals = []
        for orch in self.orchestrators.values():
            for goal in orch._goal_pools.values():
                all_goals.append({
                    "agent_id": orch.agent_id,
                    "goal": goal,
                })
        
        # 按目标名称相似度聚类
        goal_clusters = defaultdict(list)
        for item in all_goals:
            goal_name = item["goal"].name
            cluster_key = goal_name[:20] if len(goal_name) > 20 else goal_name
            goal_clusters[cluster_key].append(item)
        
        # 超过 2 个 Agent 响应的目标 = 群体目标
        for cluster_key, items in goal_clusters.items():
            if len(items) >= 2:
                collective_goal_id = f"collective_{cluster_key}"
                self.collective_goals[collective_goal_id] = {
                    "name": cluster_key,
                    "participating_agents": [item["agent_id"] for item in items],
                    "goal_count": len(items),
                }
    
    def _check_system_emergence(self) -> None:
        """检查系统级涌现"""
        # 聚合所有 Agent 状态
        system_state = {
            "coordination_level": len(self.collective_goals) / max(1, len(self.orchestrators)),
            "pattern_complexity": len(self.collective_goals) * 0.1,
            "collective_coherence": 0.5,
            "efficiency_gain": 1.0,
            "novelty": 0.5,
            "sample_size": len(self.orchestrators) * 10,
        }
        
        for orch in self.orchestrators.values():
            indicators = orch.check_emergence(system_state)
            if indicators:
                print(f"[MetaAgent] Emergence detected: {len(indicators)} indicators triggered")
    
    def get_status(self) -> dict:
        """获取整体状态"""
        return {
            "registered_agents": len(self.orchestrators),
            "collective_goals": len(self.collective_goals),
            "individual_status": {
                agent_id: orch.get_agent_status()
                for agent_id, orch in self.orchestrators.items()
            }
        }
