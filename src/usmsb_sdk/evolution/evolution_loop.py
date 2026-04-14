# -*- coding: utf-8 -*-
"""
EvolutionLoop - 进化闭环

将 EvolutionController 真正连接到 Goal Loop：

1. 每次 Outcome 评估 → 记录适应度
2. 适应度评估 → FitnessEvaluator
3. Fitness 累积 → EvolutionController.evolve()
4. 进化 → 新基因 / 新 Agent

使用方法：
    loop = EvolutionLoop(evolution_controller, fitness_evaluator)
    
    # 每次任务完成后
    loop.record_outcome(agent_id, outcome_data)
    
    # 定期进化
    evolution_result = loop.evolve_if_needed(agent_id)
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class EvolutionTrigger:
    """进化触发条件"""
    min_outcomes: int = 5  # 最少 Outcome 数
    min_fitness_change: float = 0.1  # 最小适应度变化
    evolution_interval: float = 3600  # 进化间隔（秒）
    max_population: int = 100  # 最大种群数


@dataclass
class EvolutionResult:
    """进化结果"""
    agent_id: str
    generation: int
    fitness_before: float
    fitness_after: float
    mutations: list[str]
    new_individuals: int
    timestamp: float


class EvolutionLoop:
    """
    进化闭环
    
    连接 Outcome → Fitness → Evolution 的完整闭环。
    
    触发条件：
    1. 累积足够多的 Outcome
    2. 适应度变化足够大
    3. 超过进化间隔
    """
    
    def __init__(
        self,
        evolution_controller=None,
        fitness_evaluator=None,
        trigger: EvolutionTrigger | None = None,
    ):
        from usmsb_sdk.evolution import EvolutionController, FitnessEvaluator
        
        self.evolution = evolution_controller or EvolutionController(
            population_size=20,
            elite_ratio=0.1,
            mutation_rate=0.1
        )
        
        self.fitness = fitness_evaluator or FitnessEvaluator()
        
        self.trigger = trigger or EvolutionTrigger()
        
        # Outcome 历史
        self._outcomes: dict[str, list[dict]] = {}  # agent_id -> [outcomes]
        
        # 上次进化时间
        self._last_evolution: dict[str, float] = {}
        
        # 进化结果
        self._evolution_results: dict[str, EvolutionResult] = {}
    
    def record_outcome(
        self,
        agent_id: str,
        outcome_data: dict
    ) -> None:
        """
        记录 Outcome
        
        Args:
            agent_id: Agent ID
            outcome_data: {
                "success": bool,
                "quality_score": float,
                "value_created": float,
                "task_type": str,
                ...
            }
        """
        if agent_id not in self._outcomes:
            self._outcomes[agent_id] = []
        
        outcome_data["timestamp"] = datetime.now().timestamp()
        self._outcomes[agent_id].append(outcome_data)
        
        # 限制历史长度
        if len(self._outcomes[agent_id]) > 100:
            self._outcomes[agent_id] = self._outcomes[agent_id][-100:]
        
        # 更新适应度
        self._update_fitness(agent_id)
    
    def _update_fitness(self, agent_id: str) -> None:
        """根据 Outcome 更新适应度"""
        outcomes = self._outcomes.get(agent_id, [])
        
        if not outcomes:
            return
        
        # 计算性能数据
        total = len(outcomes)
        succeeded = sum(1 for o in outcomes if o.get("success"))
        
        performance_data = {
            "total_tasks": total,
            "succeeded_tasks": succeeded,
            "total_value": sum(o.get("value_created", 0) for o in outcomes),
            "total_cost": sum(o.get("cost", 0) for o in outcomes),
            "avg_quality": sum(o.get("quality_score", 0.5) for o in outcomes) / total,
        }
        
        # 评估适应度
        self.fitness.evaluate(agent_id, performance_data)
    
    def should_evolve(self, agent_id: str) -> tuple[bool, str]:
        """
        检查是否应该进化
        
        Returns:
            (should_evolve, reason)
        """
        outcomes = self._outcomes.get(agent_id, [])
        
        # 检查数量
        if len(outcomes) < self.trigger.min_outcomes:
            return False, f"Only {len(outcomes)} outcomes, need {self.trigger.min_outcomes}"
        
        # 检查间隔
        last_time = self._last_evolution.get(agent_id, 0)
        elapsed = datetime.now().timestamp() - last_time
        
        if elapsed < self.trigger.evolution_interval:
            return False, f"Only {elapsed:.0f}s since last evolution, need {self.trigger.evolution_interval}s"
        
        # 检查适应度变化
        history = self.fitness.get_history(agent_id, limit=10)
        
        if len(history) < 2:
            return True, "First evolution"
        
        # 计算适应度变化
        recent = [h.overall_score for h in history[:len(history)//2]]
        older = [h.overall_score for h in history[len(history)//2:]]
        
        avg_recent = sum(recent) / len(recent)
        avg_older = sum(older) / len(older)
        
        change = abs(avg_recent - avg_older)
        
        if change < self.trigger.min_fitness_change:
            return False, f"Fitness change {change:.3f} < {self.trigger.min_fitness_change}"
        
        return True, f"Fitness changed by {change:.3f}"
    
    def evolve_if_needed(self, agent_id: str) -> EvolutionResult | None:
        """
        如果满足条件则进化
        
        Returns:
            EvolutionResult 或 None
        """
        should, reason = self.should_evolve(agent_id)
        
        if not should:
            return None
        
        return self.evolve(agent_id)
    
    def evolve(self, agent_id: str) -> EvolutionResult:
        """
        执行进化
        
        流程：
        1. 获取当前适应度
        2. 调用 EvolutionController.evolve()
        3. 返回结果
        """
        # 获取当前适应度
        history = self.fitness.get_history(agent_id, limit=1)
        fitness_before = history[0].overall_score if history else 0.5
        
        # 构建 Agent 状态
        outcomes = self._outcomes.get(agent_id, [])
        
        agent_states = {
            agent_id: {
                "id": agent_id,
                "success_rate": sum(1 for o in outcomes if o.get("success")) / max(1, len(outcomes)),
                "avg_quality": sum(o.get("quality_score", 0.5) for o in outcomes) / max(1, len(outcomes)),
                "value_created": sum(o.get("value_created", 0) for o in outcomes),
            }
        }
        
        # 执行进化
        evolution_result = self.evolution.evolve(agent_states)
        
        # 更新进化时间
        self._last_evolution[agent_id] = datetime.now().timestamp()
        
        # 获取进化后适应度
        history_after = self.fitness.get_history(agent_id, limit=1)
        fitness_after = history_after[0].overall_score if history_after else fitness_before
        
        # 构建结果
        result = EvolutionResult(
            agent_id=agent_id,
            generation=evolution_result["generation"],
            fitness_before=fitness_before,
            fitness_after=fitness_after,
            mutations=evolution_result.get("mutations", [])[:5],  # 只保留前5个
            new_individuals=len(self.evolution.population),
            timestamp=datetime.now().timestamp()
        )
        
        self._evolution_results[agent_id] = result
        
        # 清空 Outcomes（进化后重新开始）
        # self._outcomes[agent_id] = []  # 注释掉，保留历史
        
        return result
    
    def get_evolution_status(self, agent_id: str) -> dict:
        """获取进化状态"""
        outcomes = self._outcomes.get(agent_id, [])
        history = self.fitness.get_history(agent_id, limit=5)
        
        should, reason = self.should_evolve(agent_id)
        
        last_evolution = self._last_evolution.get(agent_id, 0)
        elapsed = datetime.now().timestamp() - last_evolution
        
        evolution_result = self._evolution_results.get(agent_id)
        
        return {
            "agent_id": agent_id,
            "outcomes_count": len(outcomes),
            "evolution_needed": should,
            "evolution_reason": reason,
            "time_since_last_evolution": elapsed,
            "fitness_trend": self.fitness.get_trend(agent_id),
            "fitness_recent": [h.overall_score for h in history],
            "last_evolution": evolution_result.__dict__ if evolution_result else None,
            "population_size": len(self.evolution.population),
        }
    
    def inject_individual(self, agent_id: str, genes: dict) -> None:
        """
        注入新个体到种群
        
        用于 Agent 自我复制后注入新个体。
        """
        self.evolution.inject_agent(agent_id, genes)
    
    def get_best_genome(self) -> dict | None:
        """获取最优基因组"""
        genome = self.evolution.get_best_genome()
        
        if genome:
            return self.evolution.export_genome(genome)
        
        return None
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            "agents_tracked": len(self._outcomes),
            "evolution_count": len(self._evolution_results),
            "population_size": len(self.evolution.population),
            "evolution_stats": self.evolution.get_evolution_statistics(),
        }
