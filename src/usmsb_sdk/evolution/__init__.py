# -*- coding: utf-8 -*-
"""
Phase 5: Self-Evolution Layer

USMSB 自我进化模块。

功能：
- 适应度评估
- 性能追踪
- 自我改进
- 基因突变
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class FitnessResult:
    """适应度评估结果"""
    agent_id: str
    fitness_score: float  # 0.0-1.0
    dimensions: dict  # 各维度分数
    rank: int  # 排名
    percentile: float  # 百分位


@dataclass
class PerformanceRecord:
    """性能记录"""
    id: str
    agent_id: str
    metric_name: str
    metric_value: float
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


class FitnessEvaluator:
    """适应度评估"""
    
    # 适应度维度权重
    WEIGHTS = {
        "value_created": 0.30,
        "task_success": 0.25,
        "efficiency": 0.20,
        "reputation": 0.15,
        "collaboration": 0.10
    }
    
    def evaluate(self, agent_id: str, metrics: dict) -> FitnessResult:
        """评估适应度"""
        scores = {}
        total = 0.0
        
        for dim, weight in self.WEIGHTS.items():
            value = metrics.get(dim, 0.5)
            scores[dim] = min(1.0, value)
            total += scores[dim] * weight
        
        return FitnessResult(
            agent_id=agent_id,
            fitness_score=total,
            dimensions=scores,
            rank=0,
            percentile=total * 100
        )


class PerformanceTracker:
    """性能追踪"""
    
    def __init__(self):
        self._records: list[PerformanceRecord] = []
    
    def record(
        self,
        agent_id: str,
        metric_name: str,
        metric_value: float
    ) -> None:
        """记录性能指标"""
        record = PerformanceRecord(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            metric_name=metric_name,
            metric_value=metric_value
        )
        self._records.append(record)
    
    def get_metrics(
        self,
        agent_id: str,
        metric_name: str | None = None
    ) -> list[PerformanceRecord]:
        """获取指标历史"""
        results = [r for r in self._records if r.agent_id == agent_id]
        if metric_name:
            results = [r for r in results if r.metric_name == metric_name]
        return results


class SelfImprover:
    """自我改进器"""
    
    def __init__(self):
        self._improvements: list[dict] = []
    
    def suggest_improvement(
        self,
        agent_id: str,
        weakness: str,
        current_state: dict
    ) -> dict:
        """建议改进"""
        suggestion = {
            "agent_id": agent_id,
            "weakness": weakness,
            "suggested_action": f"Improve {weakness}",
            "expected_gain": 0.1,
            "timestamp": datetime.now().timestamp()
        }
        self._improvements.append(suggestion)
        return suggestion


class GeneMutator:
    """基因突变器"""
    
    MUTATION_RATE = 0.10  # 10% 变异率
    
    def mutate_capability(self, capability: str, intensity: float = 1.0) -> str:
        """突变能力"""
        import random
        if random.random() > self.MUTATION_RATE:
            return capability
        
        # 简化：能力增强/削弱
        mutations = [f"{capability}_enhanced", f"{capability}_variant"]
        return random.choice(mutations)


class EvolutionController:
    """进化控制器"""
    
    def __init__(self):
        self.fitness_evaluator = FitnessEvaluator()
        self.performance_tracker = PerformanceTracker()
        self.self_improver = SelfImprover()
        self.gene_mutator = GeneMutator()
    
    def evolve_agent(
        self,
        agent_id: str,
        current_state: dict
    ) -> dict:
        """进化 Agent"""
        # 1. 评估适应度
        fitness = self.fitness_evaluator.evaluate(agent_id, current_state)
        
        # 2. 如果适应度低，建议改进
        suggestions = []
        if fitness.fitness_score < 0.5:
            for dim, score in fitness.dimensions.items():
                if score < 0.3:
                    suggestion = self.self_improver.suggest_improvement(
                        agent_id, dim, current_state
                    )
                    suggestions.append(suggestion)
        
        # 3. 基因突变
        mutated_genes = []
        for cap in current_state.get("capabilities", []):
            mutated = self.gene_mutator.mutate_capability(cap)
            if mutated != cap:
                mutated_genes.append(mutated)
        
        return {
            "agent_id": agent_id,
            "fitness": fitness,
            "suggestions": suggestions,
            "mutations": mutated_genes,
            "timestamp": datetime.now().timestamp()
        }
    
    def get_evolution_stats(self) -> dict:
        """获取进化统计"""
        return {
            "tracked_agents": len(set(r.agent_id for r in self.performance_tracker._records)),
            "total_improvements": len(self.self_improver._improvements),
        }
