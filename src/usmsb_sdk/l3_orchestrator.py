# -*- coding: utf-8 -*-
"""
L3Orchestrator - L3 核心业务编排器

核心职责：
1. 连接 L3（目的内生）和 L4（业务服务）
2. 让 PurposeGenerator 生成的目标真正驱动 MatchingEngine/OrderService
3. 实现 Goal-Action-Outcome Loop 的端到端闭环

这是 v2.0 的核心断点修复。
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
)
from usmsb_sdk.core.elements import Goal, GoalStatus
from usmsb_sdk.l3.collective_goal_emergence import CollectiveGoalEmergence
from usmsb_sdk.l3.emergent_governance import EmergentGovernance


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


class L3Orchestrator:
    """
    L3 业务编排器 - 核心断点修复
    
    连接 L3（硅基生命层）和 L4（业务服务层）。
    
    关键设计：
    1. PurposeGenerator 生成目标 → 进入 Goal Pool
    2. Goal Pool → MatchingEngine（找执行者）
    3. MatchingEngine → Negotiation → Order
    4. Order 完成 → Outcome 评估 → ValueSelfLoop
    5. Outcome → 更新 PurposeGenerator → 生成新目标
    
    这就是"Goal-Action-Outcome Loop"的完整闭环。
    """
    
    def __init__(
        self,
        agent_id: str,
        services: dict | None = None,
        llm_adapter=None,
    ):
        self.agent_id = agent_id
        self.services = services or {}  # 注入 L4 服务
        
        # L3 核心组件
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
        
        # Goal-Action-Outcome Loop 状态
        self._goal_pools: dict[str, Goal] = {}  # goal_id -> Goal
        self._active_loops: dict[str, L3LoopState] = {}  # loop_id -> LoopState
        self._completed_outcomes: list[dict] = []  # 历史结果
        
        # 执行追踪
        self._action_registry: dict[str, OrchestratedAction] = {}
        
        # 配置
        self.max_concurrent_loops = 5
        self.goal_generation_interval = 3600  # 1小时生成一次新目标
    
    def generate_intrinsic_goals(self) -> list[Goal]:
        """
        从内在需求生成目标（被外部定时调用）
        
        这是"硅基生命"的标志性行为：
        goal = self.generate_goal()
        
        Returns:
            list[Goal]: 生成的目标列表
        """
        goals = []
        
        # Step 1: 生成 Purpose
        purpose = self.purpose_generator.generate_purpose()
        
        if purpose:
            # Step 2: 转化为 Goal
            goal = self.purpose_generator.purpose_to_goal(purpose)
            goals.append(goal)
            
            # Step 3: 加入 Goal Pool
            self._goal_pools[goal.id] = goal
            
            # Step 4: 创建 Loop 状态
            loop_state = L3LoopState(
                loop_id=str(uuid.uuid4()),
                goal_id=goal.id,
                goal_name=goal.name,
            )
            self._active_loops[loop_state.loop_id] = loop_state
            
            print(f"[L3Orchestrator] 生成内在目标: {goal.name}")
        
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
                        "source": "l3_intrinsic",  # 标记为内在生成
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
            
            loop_state.outcome_score = outcome_score
            loop_state.status = "completed"
            
            return {"phase": "outcome", "score": outcome_score}
        
        return {"error": "Unknown status"}
    
    def _goal_to_capabilities(self, goal: Goal) -> list[str]:
        """将 Goal 转换为所需能力列表"""
        # 从 goal.name 和 metadata 提取能力
        capabilities = []
        
        goal_name_lower = goal.name.lower()
        if "coding" in goal_name_lower or "代码" in goal_name_lower:
            capabilities.append("coding")
        if "analysis" in goal_name_lower or "分析" in goal_name_lower:
            capabilities.append("analysis")
        if "design" in goal_name_lower or "设计" in goal_name_lower:
            capabilities.append("design")
        
        # 从 metadata 提取
        if "required_capabilities" in goal.metadata:
            capabilities.extend(goal.metadata["required_capabilities"])
        
        return capabilities or ["general"]
    
    def _calculate_outcome_score(self, loop_state: L3LoopState) -> float:
        """计算 Outcome 分数"""
        # 基于执行时间和结果计算
        if loop_state.action_started_at and loop_state.action_completed_at:
            duration = loop_state.action_completed_at - loop_state.action_started_at
            
            # 时间效率分数
            time_score = max(0, 1 - duration / 3600)  # 1小时内满分
            
            return 0.7 + time_score * 0.3
        
        return 0.5  # 默认中等分数
    
    def _update_intrinsic_feedback(self, outcome_score: float) -> None:
        """将 Outcome 结果反馈到 L3 内在动机"""
        # 成功 → 增强动机
        # 失败 → 调整策略
        
        if outcome_score > 0.7:
            # 高分：强化当前动机方向
            self.purpose_generator.intrinsic_motivation.satisfy_need(
                need_id=None,
                satisfaction=outcome_score,
            )
        elif outcome_score < 0.3:
            # 低分：触发反思，重新生成目标
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
    
    def run_cycle(self) -> dict:
        """
        运行一个完整的 L3 周期
        
        被定时调用（如每分钟）：
        1. 检查是否需要生成新目标
        2. 执行所有活跃的 Loop
        3. 清理完成的 Loop
        
        Returns:
            dict: 周期运行结果
        """
        results = {
            "goals_generated": 0,
            "loops_executed": 0,
            "loops_completed": 0,
        }
        
        # 1. 生成新目标（如果需要）
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
        
        # 3. 清理完成的 Loop（保留最近 N 个）
        completed = [k for k, v in self._active_loops.items() if v.status == "completed"]
        for loop_id in completed[10:]:  # 保留最近 10 个
            del self._active_loops[loop_id]
        
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
        
        return results
    
    def _emergence_collective_goals(self) -> None:
        """涌现群体目标"""
        # 收集所有活跃目标
        all_goals = []
        for orch in self.orchestrators.values():
            for goal in orch._goal_pools.values():
                all_goals.append({
                    "agent_id": orch.agent_id,
                    "goal": goal,
                })
        
        # 找出共同目标（模式检测）
        # 简化版：按目标名称相似度聚类
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
    
    def get_status(self) -> dict:
        """获取整体状态"""
        return {
            "registered_agents": len(self.orchestrators),
            "collective_goals": len(self.collective_goals),
            "individual_status": {
                agent_id: orch.get_loop_status()
                for agent_id, orch in self.orchestrators.items()
            }
        }
