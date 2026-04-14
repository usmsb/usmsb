"""
SelfReplication - 自我复制引擎

硅基生命的"自我复制"能力。

核心功能：
- 适应度计算
- 复制条件检查
- Agent 复制
- 能力继承
- 变异机制
"""

import copy
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from usmsb_sdk.core.elements import Agent, Goal, Resource


class ReplicationType(Enum):
    """复制类型"""
    ASEXUAL = "asexual"    # 无性繁殖：完全复制
    SEXUAL = "sexual"     # 有性繁殖：两个 Agent 交换基因
    CLONING = "cloning"   # 克隆：精确复制
    VARIANT = "variant"    # 变异复制：带有突变的复制


class ReplicationStatus(Enum):
    """复制状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ReplicationRecord:
    """复制记录"""
    id: str
    parent_id: str
    child_id: str | None = None
    replication_type: ReplicationType = ReplicationType.VARIANT
    fitness_at_replication: float = 0.0
    mutation_applied: list[str] = field(default_factory=list)
    inherited_capabilities: list[str] = field(default_factory=list)
    resource_cost: float = 0.0
    status: ReplicationStatus = ReplicationStatus.PENDING
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    error_message: str = ""


@dataclass
class ReplicationTrigger:
    """复制触发条件配置"""
    min_fitness: float = 0.6        # 最低适应度
    min_resource: float = 100.0     # 最低资源
    min_age_seconds: float = 3600    # 最小年龄（1小时）
    cooldown_seconds: float = 86400  # 复制冷却时间（24小时）
    max_population: int = 1000      # 最大种群数量
    replication_cost: float = 50.0   # 复制消耗资源


class FitnessCalculator:
    """
    适应度计算器
    
    适应度 = w1 × value_created + w2 × collaboration_count + 
             w3 × learning_progress + w4 × resource_efficiency
    
    权重：
    - value_created: 30%
    - collaboration_count: 20%
    - learning_progress: 30%
    - resource_efficiency: 20%
    """
    
    # 权重配置
    WEIGHT_VALUE = 0.30
    WEIGHT_COLLABORATION = 0.20
    WEIGHT_LEARNING = 0.30
    WEIGHT_EFFICIENCY = 0.20
    
    def calculate(
        self,
        value_created: float,
        collaboration_count: int,
        learning_progress: float,
        resource_efficiency: float
    ) -> float:
        """
        计算适应度
        
        Args:
            value_created: 创造的价值
            collaboration_count: 协作次数
            learning_progress: 学习进度 (0.0-1.0)
            resource_efficiency: 资源效率 (0.0-1.0)
            
        Returns:
            float: 适应度 (0.0-1.0)
        """
        fitness = (
            self.WEIGHT_VALUE * min(value_created / 1000.0, 1.0) +
            self.WEIGHT_COLLABORATION * min(collaboration_count / 100, 1.0) +
            self.WEIGHT_LEARNING * learning_progress +
            self.WEIGHT_EFFICIENCY * resource_efficiency
        )
        
        # 限制在 0.0-1.0 范围内
        return max(0.0, min(1.0, fitness))
    
    def calculate_from_agent_state(self, state: dict) -> float:
        """
        从 Agent 状态计算适应度
        
        Args:
            state: Agent 状态字典
            
        Returns:
            float: 适应度
        """
        return self.calculate(
            value_created=state.get("value_created", 0.0),
            collaboration_count=state.get("collaboration_count", 0),
            learning_progress=state.get("learning_progress", 0.0),
            resource_efficiency=state.get("resource_efficiency", 0.5)
        )


class MutationEngine:
    """
    变异引擎
    
    变异率：10%
    - 5% 概率：能力增强
    - 5% 概率：能力减弱
    - 90% 概率：能力不变
    """
    
    MUTATION_RATE = 0.10  # 10% 变异率
    
    def __init__(self):
        import random
        self._random = random.Random()
    
    def should_mutate(self) -> bool:
        """是否应该变异"""
        return self._random.random() < self.MUTATION_RATE
    
    def mutate_capability_score(self, score: float) -> float:
        """
        变异能力分数
        
        Args:
            score: 原始分数 (0.0-1.0)
            
        Returns:
            float: 变异后的分数
        """
        if not self.should_mutate():
            return score
        
        roll = self._random.random()
        
        if roll < 0.05:
            # 5% 概率：能力增强（+10-20%）
            boost = self._random.uniform(0.1, 0.2)
            return min(1.0, score + boost)
        elif roll < 0.10:
            # 5% 概率：能力减弱（-10-20%）
            reduction = self._random.uniform(0.1, 0.2)
            return max(0.0, score - reduction)
        else:
            return score
    
    def mutate_goal_priority(self, priority: int) -> int:
        """
        变异目标优先级
        
        Args:
            priority: 原始优先级 (0-100)
            
        Returns:
            int: 变异后的优先级
        """
        if not self.should_mutate():
            return priority
        
        # ±10% 随机调整
        adjustment = self._random.uniform(-0.1, 0.1)
        new_priority = priority * (1 + adjustment)
        
        return max(0, min(100, int(new_priority)))
    
    def mutate_capabilities(self, capabilities: list[str]) -> list[str]:
        """
        变异能力列表
        
        变异后的能力列表可能包含：
        - 原始能力（保持不变）
        - 能力增强（分数提高）
        - 能力减弱（分数降低）
        
        Returns:
            list[str]: 变异后的能力列表
        """
        return capabilities  # 简化版：不做能力列表的增删
    
    def get_mutation_description(self) -> list[str]:
        """获取本次变异描述"""
        if not self.should_mutate():
            return []
        
        mutations = []
        roll = self._random.random()
        
        if roll < 0.05:
            mutations.append("capability_enhanced")
        elif roll < 0.10:
            mutations.append("capability_weakened")
        
        return mutations


class SelfReplication:
    """
    自我复制引擎
    
    核心职责：
    1. 检查复制条件（适应度、资源、年龄等）
    2. 执行复制操作
    3. 继承父 Agent 能力
    4. 应用变异
    5. 记录复制历史
    
    使用方式：
    ```python
    replication = SelfReplication()
    
    # 检查是否可以复制
    can_replicate, reason = replication.can_replicate("agent_001")
    
    if can_replicate:
        # 执行复制
        child = replication.replicate("agent_001")
        print(f"Created child agent: {child.id}")
    ```
    """
    
    def __init__(
        self,
        trigger_config: ReplicationTrigger | None = None,
        fitness_calculator: FitnessCalculator | None = None,
        mutation_engine: MutationEngine | None = None
    ):
        self.trigger_config = trigger_config or ReplicationTrigger()
        self.fitness_calculator = fitness_calculator or FitnessCalculator()
        self.mutation_engine = mutation_engine or MutationEngine()
        
        # 复制记录
        self._replication_records: dict[str, ReplicationRecord] = {}
        
        # Agent 状态存储（外部应该接入真实 Agent 状态）
        self._agent_states: dict[str, dict] = {}
        
        # 父-子关系映射
        self._parent_children: dict[str, list[str]] = {}
        
        # 上次复制时间
        self._last_replication_time: dict[str, float] = {}
    
    def set_agent_state(self, agent_id: str, state: dict) -> None:
        """
        设置 Agent 状态（用于适应度计算）
        
        Args:
            agent_id: Agent ID
            state: Agent 状态字典，包含：
                - value_created: float
                - collaboration_count: int
                - learning_progress: float
                - resource_efficiency: float
                - resource_amount: float
                - age_seconds: float
                - capabilities: list[str]
                - goals: list[dict]
        """
        self._agent_states[agent_id] = state.copy()
    
    def get_agent_state(self, agent_id: str) -> dict | None:
        """获取 Agent 状态"""
        return self._agent_states.get(agent_id)
    
    def can_replicate(self, agent_id: str) -> tuple[bool, str]:
        """
        检查是否可以复制
        
        Args:
            agent_id: Agent ID
            
        Returns:
            (can_replicate, reason)
        """
        state = self._agent_states.get(agent_id)
        if not state:
            return False, f"Agent {agent_id} state not found"
        
        # 1. 适应度检查
        fitness = self.calculate_fitness(agent_id)
        if fitness < self.trigger_config.min_fitness:
            return False, f"Fitness {fitness:.2f} < {self.trigger_config.min_fitness}"
        
        # 2. 资源检查
        resource = state.get("resource_amount", 0.0)
        if resource < self.trigger_config.min_resource:
            return False, f"Resource {resource:.2f} < {self.trigger_config.min_resource}"
        
        # 3. 年龄检查
        age = state.get("age_seconds", 0.0)
        if age < self.trigger_config.min_age_seconds:
            return False, f"Age {age:.0f}s < {self.trigger_config.min_age_seconds}s"
        
        # 4. 冷却检查
        last_time = self._last_replication_time.get(agent_id, 0)
        time_since = datetime.now().timestamp() - last_time
        if time_since < self.trigger_config.cooldown_seconds:
            remaining = self.trigger_config.cooldown_seconds - time_since
            return False, f"Cooldown: {remaining:.0f}s remaining"
        
        # 5. 种群检查
        total_agents = len(self._agent_states)
        if total_agents >= self.trigger_config.max_population:
            return False, f"Population {total_agents} >= {self.trigger_config.max_population}"
        
        return True, "All conditions satisfied"
    
    def calculate_fitness(self, agent_id: str) -> float:
        """
        计算 Agent 的适应度
        
        Args:
            agent_id: Agent ID
            
        Returns:
            float: 适应度 (0.0-1.0)
        """
        state = self._agent_states.get(agent_id)
        if not state:
            return 0.0
        
        return self.fitness_calculator.calculate_from_agent_state(state)
    
    def replicate(
        self,
        parent_id: str,
        replication_type: ReplicationType = ReplicationType.VARIANT,
        child_id: str | None = None
    ) -> dict | None:
        """
        执行自我复制
        
        Args:
            parent_id: 父 Agent ID
            replication_type: 复制类型
            child_id: 子 Agent ID（可选，默认自动生成）
            
        Returns:
            dict: 子 Agent 信息，包含：
                - id: str
                - parent_id: str
                - inherited_capabilities: list[str]
                - mutation_applied: list[str]
                - fitness: float
            或 None（如果复制失败）
        """
        can_replicate, reason = self.can_replicate(parent_id)
        if not can_replicate:
            print(f"Cannot replicate: {reason}")
            return None
        
        state = self._agent_states[parent_id]
        
        # 创建复制记录
        record = ReplicationRecord(
            id=str(uuid.uuid4()),
            parent_id=parent_id,
            replication_type=replication_type,
            fitness_at_replication=self.calculate_fitness(parent_id),
        )
        
        # 生成子 Agent ID
        if child_id is None:
            child_id = f"{parent_id}_child_{len(self._parent_children.get(parent_id, []))}"
        
        record.child_id = child_id
        
        # 1. 创建子 Agent 状态
        child_state = self._create_child_state(parent_id, child_id, replication_type)
        
        # 2. 继承能力
        child_state = self.inherit_capabilities(state, child_state)
        
        # 3. 应用变异
        if replication_type == ReplicationType.VARIANT:
            child_state, mutations = self.apply_mutation(child_state)
            record.mutation_applied = mutations
        
        # 4. 消耗资源
        child_state["resource_amount"] -= self.trigger_config.replication_cost
        record.resource_cost = self.trigger_config.replication_cost
        
        # 5. 保存子 Agent 状态
        self._agent_states[child_id] = child_state
        
        # 6. 更新父子关系
        if parent_id not in self._parent_children:
            self._parent_children[parent_id] = []
        self._parent_children[parent_id].append(child_id)
        
        # 7. 更新上次复制时间
        self._last_replication_time[parent_id] = datetime.now().timestamp()
        
        # 8. 保存复制记录
        record.status = ReplicationStatus.COMPLETED
        self._replication_records[record.id] = record
        
        return {
            "id": child_id,
            "parent_id": parent_id,
            "replication_type": replication_type.value,
            "inherited_capabilities": child_state.get("capabilities", []),
            "mutation_applied": record.mutation_applied,
            "fitness": record.fitness_at_replication,
            "resource_cost": record.resource_cost,
            "generation": self._get_generation_number(parent_id) + 1,
        }
    
    def _create_child_state(
        self,
        parent_id: str,
        child_id: str,
        replication_type: ReplicationType
    ) -> dict:
        """创建子 Agent 初始状态"""
        parent_state = self._agent_states[parent_id]
        
        child_state = {
            "id": child_id,
            "parent_id": parent_id,
            "capabilities": copy.deepcopy(parent_state.get("capabilities", [])),
            "goals": copy.deepcopy(parent_state.get("goals", [])),
            "value_created": 0.0,  # 重置
            "collaboration_count": 0,  # 重置
            "learning_progress": parent_state.get("learning_progress", 0.0),
            "resource_amount": parent_state.get("resource_amount", 100.0) / 2,  # 分一半给子 Agent
            "age_seconds": 0.0,  # 重置年龄
            "generation": self._get_generation_number(parent_id) + 1,
        }
        
        return child_state
    
    def inherit_capabilities(
        self,
        parent_state: dict,
        child_state: dict,
        inheritance_rate: float = 0.8
    ) -> dict:
        """
        继承父 Agent 能力
        
        Args:
            parent_state: 父 Agent 状态
            child_state: 子 Agent 状态
            inheritance_rate: 继承率 (0.0-1.0)
            
        Returns:
            dict: 继承后的子 Agent 状态
        """
        parent_capabilities = parent_state.get("capabilities", [])
        
        # 按继承率继承能力
        inherit_count = int(len(parent_capabilities) * inheritance_rate)
        child_state["capabilities"] = parent_capabilities[:inherit_count]
        
        # 继承目标
        parent_goals = parent_state.get("goals", [])
        inherit_goals_count = int(len(parent_goals) * inheritance_rate)
        child_state["goals"] = parent_goals[:inherit_goals_count]
        
        return child_state
    
    def apply_mutation(self, child_state: dict) -> tuple[dict, list[str]]:
        """
        应用变异
        
        Args:
            child_state: 子 Agent 状态
            
        Returns:
            (mutated_state, mutations_applied)
        """
        mutations = []
        
        # 变异学习进度
        old_progress = child_state.get("learning_progress", 0.5)
        new_progress = self.mutation_engine.mutate_capability_score(old_progress)
        if new_progress != old_progress:
            child_state["learning_progress"] = new_progress
            mutations.append(f"learning_progress: {old_progress:.2f} -> {new_progress:.2f}")
        
        # 变异目标优先级
        for goal in child_state.get("goals", []):
            old_priority = goal.get("priority", 50)
            new_priority = self.mutation_engine.mutate_goal_priority(old_priority)
            if new_priority != old_priority:
                goal["priority"] = new_priority
                mutations.append(f"goal_priority: {old_priority} -> {new_priority}")
        
        # 变异能力列表
        capabilities = child_state.get("capabilities", [])
        if self.mutation_engine.should_mutate():
            child_state["capabilities"] = self.mutation_engine.mutate_capabilities(capabilities)
            if child_state["capabilities"] != capabilities:
                mutations.append("capabilities_mutated")
        
        return child_state, mutations
    
    def _get_generation_number(self, agent_id: str) -> int:
        """获取 Agent 的代数"""
        state = self._agent_states.get(agent_id)
        if not state:
            return 0
        return state.get("generation", 0)
    
    def get_children(self, parent_id: str) -> list[str]:
        """获取父 Agent 的所有子 Agent"""
        return self._parent_children.get(parent_id, [])
    
    def get_replication_record(self, record_id: str) -> ReplicationRecord | None:
        """获取复制记录"""
        return self._replication_records.get(record_id)
    
    def get_replication_history(self, agent_id: str) -> list[ReplicationRecord]:
        """获取 Agent 的复制历史"""
        records = []
        for record in self._replication_records.values():
            if record.parent_id == agent_id or record.child_id == agent_id:
                records.append(record)
        return records
    
    def get_population_stats(self) -> dict:
        """获取种群统计"""
        total = len(self._agent_states)
        generations = {}
        
        for state in self._agent_states.values():
            gen = state.get("generation", 0)
            generations[gen] = generations.get(gen, 0) + 1
        
        return {
            "total_agents": total,
            "max_population": self.trigger_config.max_population,
            "generations": generations,
            "total_replications": len(self._replication_records),
        }
