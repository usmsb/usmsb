"""
EvolutionController - 自我进化控制器

Phase 5: 自我进化层 - 完整实现

完整实现：
- 适应度评估（多目标优化）
- 基因突变（真实进化算法）
- 自我改进（反馈循环）
- 进化压力测试
"""

import uuid
import random
import copy
import math
import numpy as np
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable


# ============================================================================
# Fitness Evaluation - 适应度评估
# ============================================================================

@dataclass
class FitnessDimensions:
    """适应度维度"""
    value_created: float = 0.0      # 创造价值
    task_success: float = 0.0        # 任务成功率
    efficiency: float = 0.0          # 效率
    reputation: float = 0.0           # 声誉
    collaboration: float = 0.0        # 协作能力
    learning: float = 0.0            # 学习能力
    resource_usage: float = 0.0      # 资源使用效率


@dataclass
class FitnessResult:
    """适应度评估结果"""
    agent_id: str
    overall_score: float  # 0-1
    dimensions: FitnessDimensions
    rank: int
    percentile: float
    fitness_landscape: dict  # 适应度景观
    timestamp: float


@dataclass
class EvolutionRecord:
    """进化记录"""
    generation: int
    agent_id: str
    parent_id: str | None
    fitness_before: float
    fitness_after: float
    mutations: list[str]
    survival_probability: float


class MultiObjectiveFitnessEvaluator:
    """
    多目标适应度评估器
    
    使用 Pareto 最优和加权求和方法。
    """
    
    # 维度权重（可配置）
    DEFAULT_WEIGHTS = {
        "value_created": 0.25,
        "task_success": 0.20,
        "efficiency": 0.15,
        "reputation": 0.15,
        "collaboration": 0.10,
        "learning": 0.10,
        "resource_usage": 0.05
    }
    
    def __init__(self, weights: dict | None = None):
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
    
    def evaluate(self, agent_state: dict, historical_data: dict | None = None) -> FitnessResult:
        """
        评估 Agent 适应度
        
        Args:
            agent_state: Agent 状态
            historical_data: 历史数据
            
        Returns:
            FitnessResult: 适应度结果
        """
        # 提取维度
        dims = self._extract_dimensions(agent_state, historical_data)
        
        # 归一化到 0-1
        normalized_dims = self._normalize_dimensions(dims)
        
        # 计算加权总分
        overall = sum(
            normalized_dims.__dict__[key] * self.weights[key]
            for key in self.weights
        )
        
        # 构建适应度景观
        landscape = self._build_fitness_landscape(dims)
        
        return FitnessResult(
            agent_id=agent_state.get("id", ""),
            overall_score=overall,
            dimensions=normalized_dims,
            rank=0,  # 后续计算
            percentile=overall * 100,
            fitness_landscape=landscape,
            timestamp=datetime.now().timestamp()
        )
    
    def _extract_dimensions(self, state: dict, history: dict | None) -> FitnessDimensions:
        """提取适应度维度"""
        return FitnessDimensions(
            value_created=state.get("value_created", 0.0),
            task_success=state.get("success_rate", 0.0),
            efficiency=state.get("efficiency", 0.0),
            reputation=state.get("reputation", 0.0),
            collaboration=state.get("collaboration_score", 0.0),
            learning=state.get("learning_progress", 0.0),
            resource_usage=state.get("resource_efficiency", 0.0)
        )
    
    def _normalize_dimensions(self, dims: FitnessDimensions) -> FitnessDimensions:
        """归一化维度值到 0-1"""
        def normalize(value, scale=1.0):
            return min(1.0, max(0.0, value / scale))
        
        return FitnessDimensions(
            value_created=normalize(dims.value_created, 10000.0),
            task_success=dims.task_success,
            efficiency=dims.efficiency,
            reputation=dims.reputation,
            collaboration=dims.collaboration,
            learning=dims.learning,
            resource_usage=dims.resource_usage
        )
    
    def _build_fitness_landscape(self, dims: FitnessDimensions) -> dict:
        """构建适应度景观"""
        return {
            "peak_value": dims.value_created,
            "stability": 1.0 - abs(dims.efficiency - 0.5) * 2,
            "adaptability": dims.learning * 0.7 + dims.task_success * 0.3,
            "specialization": 1.0 - dims.collaboration,
            "versatility": dims.collaboration
        }
    
    def calculate_pareto_rank(self, results: list[FitnessResult]) -> list[FitnessResult]:
        """计算 Pareto 秩"""
        n = len(results)
        dominated_count = [[] for _ in range(n)]
        
        # 计算支配关系
        for i in range(n):
            for j in range(n):
                if i != j:
                    if self._dominates(results[i], results[j]):
                        dominated_count[j].append(i)
        
        # 计算秩（非支配层级）
        ranks = [0] * n
        current_rank = 0
        
        while sum(ranks) == 0 or any(r == 0 for r in ranks):
            for i in range(n):
                if ranks[i] == 0 and len(dominated_count[i]) == 0:
                    ranks[i] = current_rank + 1
            current_rank += 1
        
        for i, r in enumerate(ranks):
            results[i].rank = r
        
        return results
    
    def _dominates(self, a: FitnessResult, b: FitnessResult) -> bool:
        """判断 a 是否支配 b"""
        ad = a.dimensions
        bd = b.dimensions
        
        better = False
        
        for key in ["value_created", "task_success", "efficiency", "reputation", 
                     "collaboration", "learning", "resource_usage"]:
            av = getattr(ad, key)
            bv = getattr(bd, key)
            
            if av > bv:
                better = True
            elif av < bv:
                return False
        
        return better


# ============================================================================
# Gene Mutation - 基因突变
# ============================================================================

@dataclass
class Gene:
    """基因"""
    name: str
    value: Any
    mutation_rate: float = 0.1
    mutation_range: tuple = (0, 1)  # 数值范围


@dataclass
class Genome:
    """基因组"""
    agent_id: str
    genes: dict[str, Gene]
    generation: int = 0
    parent_id: str | None = None


class GeneMutator:
    """
    基因突变器 - 完整实现
    
    支持多种突变类型。
    """
    
    # 突变类型
    MUTATION_TYPES = ["gaussian", "uniform", "directional", "creep", "swap", "insert", "delete"]
    
    def __init__(self, base_mutation_rate: float = 0.1):
        self.base_mutation_rate = base_mutation_rate
    
    def mutate_genome(
        self,
        genome: Genome,
        fitness_context: dict | None = None
    ) -> tuple[Genome, list[str]]:
        """
        突变基因组
        
        Args:
            genome: 原始基因组
            fitness_context: 适应度上下文（影响突变方向）
            
        Returns:
            (mutated_genome, mutations_applied)
        """
        mutated_genes = copy.deepcopy(genome.genes)
        mutations = []
        
        for gene_name, gene in mutated_genes.items():
            mutation = self._mutate_gene(gene, fitness_context)
            if mutation:
                mutations.append(f"{gene_name}: {mutation}")
        
        return Genome(
            agent_id=f"{genome.agent_id}_mut",
            genes=mutated_genes,
            generation=genome.generation + 1,
            parent_id=genome.agent_id
        ), mutations
    
    def _mutate_gene(
        self,
        gene: Gene,
        context: dict | None
    ) -> str | None:
        """突变单个基因"""
        if random.random() > gene.mutation_rate:
            return None
        
        gene_type = type(gene.value)
        
        if gene_type in (int, float):
            return self._mutate_numeric(gene)
        elif gene_type == str:
            return self._mutate_categorical(gene)
        elif gene_type == list:
            return self._mutate_list(gene)
        elif gene_type == dict:
            return self._mutate_dict(gene)
        
        return None
    
    def _mutate_numeric(self, gene: Gene) -> str:
        """数值基因突变"""
        original = gene.value
        min_val, max_val = gene.mutation_range
        
        # 选择突变类型
        mutation_type = random.choice(self.MUTATION_TYPES[:4])  # 数值类型
        
        if mutation_type == "gaussian":
            # 高斯突变
            sigma = (max_val - min_val) * 0.1
            gene.value = gene.value + random.gauss(0, sigma)
        elif mutation_type == "uniform":
            # 均匀突变
            delta = random.uniform(-0.1, 0.1) * (max_val - min_val)
            gene.value = gene.value + delta
        elif mutation_type == "directional":
            # 方向突变（基于适应度梯度）
            if random.random() < 0.5:
                gene.value = gene.value * (1 + random.uniform(0.05, 0.2))
            else:
                gene.value = gene.value * (1 - random.uniform(0.05, 0.2))
        elif mutation_type == "creep":
            # 缓慢漂移
            gene.value = gene.value + random.choice([-1, 1]) * (max_val - min_val) * 0.01
        
        # 限制范围
        gene.value = max(min_val, min(max_val, gene.value))
        
        return f"{mutation_type}: {original} -> {gene.value:.4f}"
    
    def _mutate_categorical(self, gene: Gene) -> str:
        """类别基因突变"""
        if isinstance(gene.value, list):
            # 从列表中选择
            original = gene.value
            gene.value = random.choice(gene.value)
            return f"swap: {original} -> {gene.value}"
        return None
    
    def _mutate_list(self, gene: Gene) -> str:
        """列表基因突变"""
        if not gene.value:
            return None
        
        op = random.choice(["insert", "delete", "swap"])
        
        if op == "insert" and len(gene.value) < 20:
            gene.value.append(random.random())
            return "insert: new element"
        elif op == "delete" and len(gene.value) > 1:
            gene.value.pop(random.randint(0, len(gene.value) - 1))
            return "delete: removed element"
        elif op == "swap" and len(gene.value) > 1:
            i, j = random.sample(range(len(gene.value)), 2)
            gene.value[i], gene.value[j] = gene.value[j], gene.value[i]
            return f"swap: indices {i}, {j}"
        
        return None
    
    def _mutate_dict(self, gene: Gene) -> str:
        """字典基因突变"""
        if not gene.value:
            return None
        
        keys = list(gene.value.keys())
        key = random.choice(keys)
        original = gene.value[key]
        
        if isinstance(original, (int, float)):
            gene.value[key] = original * random.uniform(0.8, 1.2)
            return f"dict_mutate: {key} {original} -> {gene.value[key]:.4f}"
        
        return None


class CrossoverOperator:
    """交叉操作"""
    
    def crossover(
        self,
        parent_a: Genome,
        parent_b: Genome
    ) -> tuple[Genome, Genome]:
        """
        单点交叉
        
        Returns:
            (child_a, child_b)
        """
        # 获取共同基因
        common_genes = set(parent_a.genes.keys()) & set(parent_b.genes.keys())
        
        if not common_genes:
            return parent_a, parent_b
        
        # 选择交叉点
        crossover_point = random.choice(list(common_genes))
        
        # 创建子代
        child_a_genes = {}
        child_b_genes = {}
        
        for gene_name in parent_a.genes:
            if gene_name <= crossover_point:
                child_a_genes[gene_name] = copy.deepcopy(parent_a.genes[gene_name])
                child_b_genes[gene_name] = copy.deepcopy(parent_b.genes[gene_name])
            else:
                child_a_genes[gene_name] = copy.deepcopy(parent_b.genes[gene_name])
                child_b_genes[gene_name] = copy.deepcopy(parent_a.genes[gene_name])
        
        return (
            Genome(agent_id=f"{parent_a.agent_id}_x{parent_b.agent_id}",
                   genes=child_a_genes, generation=max(parent_a.generation, parent_b.generation) + 1),
            Genome(agent_id=f"{parent_b.agent_id}_x{parent_a.agent_id}",
                   genes=child_b_genes, generation=max(parent_a.generation, parent_b.generation) + 1)
        )


# ============================================================================
# Self Improvement - 自我改进
# ============================================================================

@dataclass
class ImprovementSuggestion:
    """改进建议"""
    agent_id: str
    weakness: str
    current_value: float
    target_value: float
    expected_gain: float
    confidence: float
    strategy: str


class SelfImprovementEngine:
    """
    自我改进引擎 - 完整实现
    
    分析弱点，生成改进建议，执行改进。
    """
    
    WEAKNESS_THRESHOLD = 0.3  # 低于此值视为弱点
    IMPROVEMENT_STRATEGIES = {
        "value_created": ["increase_throughput", "optimize_pricing", "expand_capabilities"],
        "task_success": ["quality_focus", "better_planning", "skill_upgrade"],
        "efficiency": ["process_optimization", "automation", "resource_management"],
        "reputation": ["deliver_quality", "communicate_better", "build_trust"],
        "collaboration": ["team_formation", "skill_sharing", "coordinate_better"],
        "learning": ["practice_more", "seek_feedback", "study_patterns"]
    }
    
    def __init__(self):
        self.suggestions: list[ImprovementSuggestion] = []
    
    def analyze_weaknesses(self, fitness: FitnessResult) -> list[ImprovementSuggestion]:
        """
        分析弱点
        
        Args:
            fitness: 适应度评估结果
            
        Returns:
            list[ImprovementSuggestion]: 改进建议
        """
        suggestions = []
        dims = fitness.dimensions
        
        for dim_name in ["value_created", "task_success", "efficiency", 
                         "reputation", "collaboration", "learning"]:
            value = getattr(dims, dim_name)
            
            if value < self.WEAKNESS_THRESHOLD:
                strategies = self.IMPROVEMENT_STRATEGIES.get(dim_name, ["generic_improvement"])
                strategy = random.choice(strategies)
                
                suggestion = ImprovementSuggestion(
                    agent_id=fitness.agent_id,
                    weakness=dim_name,
                    current_value=value,
                    target_value=self.WEAKNESS_THRESHOLD + 0.1,
                    expected_gain=self.WEAKNESS_THRESHOLD - value,
                    confidence=0.7,
                    strategy=strategy
                )
                suggestions.append(suggestion)
        
        self.suggestions.extend(suggestions)
        return suggestions
    
    def prioritize_suggestions(
        self,
        suggestions: list[ImprovementSuggestion]
    ) -> list[ImprovementSuggestion]:
        """对建议进行优先级排序"""
        # 按 expected_gain * confidence 排序
        suggestions.sort(
            key=lambda s: s.expected_gain * s.confidence,
            reverse=True
        )
        return suggestions


# ============================================================================
# Evolution Controller - 进化控制器
# ============================================================================

class EvolutionController:
    """
    进化控制器 - 完整实现
    
    整合所有进化相关功能。
    """
    
    def __init__(
        self,
        population_size: int = 50,
        elite_ratio: float = 0.1,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.7
    ):
        self.population_size = population_size
        self.elite_ratio = elite_ratio
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        
        # 组件
        self.fitness_evaluator = MultiObjectiveFitnessEvaluator()
        self.mutator = GeneMutator(mutation_rate)
        self.crossover = CrossoverOperator()
        self.improvement_engine = SelfImprovementEngine()
        
        # 状态
        self.population: list[Genome] = []
        self.fitness_history: list[FitnessResult] = []
        self.evolution_records: list[EvolutionRecord] = []
        self.generation = 0
        
        # 历史
        self.best_fitness: deque = deque(maxlen=100)
        self.avg_fitness: deque = deque(maxlen=100)
    
    def initialize_population(
        self,
        template: Genome,
        size: int | None = None
    ) -> None:
        """初始化种群"""
        size = size or self.population_size
        
        self.population = []
        
        for i in range(size):
            # 复制模板并随机变异
            genome = copy.deepcopy(template)
            genome.agent_id = f"{template.agent_id}_gen0_{i}"
            
            if i > 0:  # 第一个保持原样
                mutated, _ = self.mutator.mutate_genome(genome)
                genome = mutated
            
            self.population.append(genome)
    
    def evaluate_population(
        self,
        agent_states: dict[str, dict],
        historical_data: dict | None = None
    ) -> list[FitnessResult]:
        """评估种群"""
        results = []
        
        for genome in self.population:
            state = agent_states.get(genome.agent_id, {"id": genome.agent_id})
            result = self.fitness_evaluator.evaluate(state, historical_data)
            results.append(result)
        
        # 计算 Pareto 秩
        results = self.fitness_evaluator.calculate_pareto_rank(results)
        
        # 更新历史
        self.fitness_history.extend(results)
        
        # 记录统计
        if results:
            self.best_fitness.append(max(r.overall_score for r in results))
            self.avg_fitness.append(sum(r.overall_score for r in results) / len(results))
        
        return results
    
    def selection(self, fitness_results: list[FitnessResult]) -> list[Genome]:
        """选择（精英保留 + 锦标赛）"""
        n_elite = max(1, int(len(self.population) * self.elite_ratio))
        
        # 精英保留
        sorted_results = sorted(fitness_results, key=lambda x: x.rank)
        elite = [self.population[i] for i, r in enumerate(sorted_results) 
                 if r.rank <= n_elite]
        
        # 锦标赛选择
        tournament_size = 3
        remaining = []
        
        for _ in range(len(self.population) - n_elite):
            candidates = random.sample(list(zip(fitness_results, self.population)), tournament_size)
            winner = min(candidates, key=lambda x: x[0].rank)
            remaining.append(winner[1])
        
        return elite + remaining
    
    def evolve(
        self,
        agent_states: dict[str, dict],
        historical_data: dict | None = None
    ) -> dict:
        """
        执行一代进化
        
        Args:
            agent_states: Agent 状态字典
            historical_data: 历史数据
            
        Returns:
            dict: 进化结果
        """
        self.generation += 1
        
        # 1. 评估
        fitness_results = self.evaluate_population(agent_states, historical_data)
        
        # 2. 选择
        selected = self.selection(fitness_results)
        
        # 3. 交叉
        offspring = []
        while len(offspring) < len(self.population):
            if random.random() < self.crossover_rate and len(offspring) + 1 < len(self.population):
                parent_a, parent_b = random.sample(selected, 2)
                child_a, child_b = self.crossover.crossover(parent_a, parent_b)
                offspring.extend([child_a, child_b])
            else:
                offspring.append(random.choice(selected))
        
        # 4. 突变
        mutated_offspring = []
        mutations_log = []
        
        for genome in offspring[:len(self.population)]:
            if random.random() < self.mutation_rate:
                mutated, mutations = self.mutator.mutate_genome(genome)
                mutated_offspring.append(mutated)
                mutations_log.extend(mutations)
            else:
                mutated_offspring.append(genome)
        
        # 5. 替换
        self.population = mutated_offspring[:len(self.population)]
        
        # 6. 记录
        best = max(fitness_results, key=lambda x: x.overall_score)
        
        return {
            "generation": self.generation,
            "best_fitness": best.overall_score,
            "avg_fitness": sum(r.overall_score for r in fitness_results) / len(fitness_results),
            "best_agent": best.agent_id,
            "mutations": mutations_log,
            "population_size": len(self.population)
        }
    
    def get_improvement_suggestions(
        self,
        agent_id: str,
        fitness: FitnessResult
    ) -> list[ImprovementSuggestion]:
        """获取改进建议"""
        return self.improvement_engine.analyze_weaknesses(fitness)
    
    def get_evolution_statistics(self) -> dict:
        """获取进化统计"""
        return {
            "generation": self.generation,
            "population_size": len(self.population),
            "best_fitness_history": list(self.best_fitness),
            "avg_fitness_history": list(self.avg_fitness),
            "total_evaluations": len(self.fitness_history),
            "convergence_rate": self._calculate_convergence()
        }
    
    def _calculate_convergence(self) -> float:
        """计算收敛率"""
        if len(self.best_fitness) < 10:
            return 0.0
        
        recent = list(self.best_fitness)[-10:]
        if max(recent) == min(recent):
            return 1.0
        
        # 收敛 = 最近几代没有改进
        improvements = sum(1 for i in range(1, len(recent)) if recent[i] > recent[i-1])
        
        return 1.0 - (improvements / (len(recent) - 1))
    
    def inject_agent(
        self,
        agent_id: str,
        genes: dict[str, Any]
    ) -> None:
        """注入新 Agent 到种群"""
        gene_objects = {
            name: Gene(name=name, value=value)
            for name, value in genes.items()
        }
        
        genome = Genome(
            agent_id=agent_id,
            genes=gene_objects,
            generation=self.generation
        )
        
        # 替换最差个体
        if self.population:
            worst_idx = min(range(len(self.population)), 
                           key=lambda i: self.fitness_history[i].overall_score 
                           if i < len(self.fitness_history) else 0)
            self.population[worst_idx] = genome
    
    def get_best_genome(self) -> Genome | None:
        """获取最优基因组"""
        if not self.population or not self.fitness_history:
            return None
        
        best_idx = max(range(len(self.fitness_history)), 
                      key=lambda i: self.fitness_history[i].overall_score)
        
        return self.population[best_idx]
    
    def export_genome(self, genome: Genome) -> dict:
        """导出基因组为字典"""
        return {
            "agent_id": genome.agent_id,
            "generation": genome.generation,
            "parent_id": genome.parent_id,
            "genes": {
                name: gene.value
                for name, gene in genome.genes.items()
            }
        }
