"""
CollectiveGoalEmergence - 集体目标涌现

从多个 Agent 的局部目标中涌现出集体目标。

核心功能：
- 目标聚合
- 共识形成
- 集体行动规划
- 目标优先级动态调整
"""

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ConsensusState(Enum):
    """共识状态"""
    PROPOSING = "proposing"       # 提议中
    VOTING = "voting"           # 投票中
    CONSENSUS_REACHED = "consensus_reached"  # 达成共识
    REJECTED = "rejected"       # 被拒绝


@dataclass
class IndividualGoal:
    """个体目标"""
    id: str
    agent_id: str
    goal_type: str
    description: str
    priority: int
    effort_required: float
    expected_value: float
    created_at: float
    votes_for: list[str] = field(default_factory=list)
    votes_against: list[str] = field(default_factory=list)


@dataclass
class CollectiveGoal:
    """集体目标"""
    id: str
    name: str
    description: str
    priority: int
    participating_agents: list[str]
    sub_goals: list[str]  # 子目标 ID 列表
    consensus_state: ConsensusState
    total_effort: float
    expected_value: float
    created_at: float
    consensus_at: float | None = None
    votes_for: list[str] = field(default_factory=list)
    votes_against: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class GoalAggregator:
    """
    目标聚合器
    
    将多个 Agent 的局部目标聚合成集体目标。
    
    使用方式：
    ```python
    aggregator = GoalAggregator()
    
    # 提交个体目标
    aggregator.submit_goal(
        agent_id="agent_001",
        goal_type="exploration",
        description="探索新领域",
        priority=70
    )
    
    # 获取聚合结果
    collective_goals = aggregator.aggregate_goals()
    ```
    """
    
    def __init__(self, similarity_threshold: float = 0.6):
        self.similarity_threshold = similarity_threshold
        
        # 个体目标存储
        self._individual_goals: dict[str, IndividualGoal] = {}
        
        # Agent 目标映射
        self._agent_goals: dict[str, list[str]] = defaultdict(list)
        
        # 聚合的集体目标
        self._collective_goals: dict[str, CollectiveGoal] = {}
    
    def submit_goal(
        self,
        agent_id: str,
        goal_type: str,
        description: str,
        priority: int,
        effort_required: float = 10.0,
        expected_value: float = 10.0
    ) -> IndividualGoal:
        """
        提交个体目标
        
        Args:
            agent_id: Agent ID
            goal_type: 目标类型
            description: 目标描述
            priority: 优先级 (0-100)
            effort_required: 所需努力
            expected_value: 预期价值
            
        Returns:
            IndividualGoal: 创建的目标
        """
        goal = IndividualGoal(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            goal_type=goal_type,
            description=description,
            priority=priority,
            effort_required=effort_required,
            expected_value=expected_value,
            created_at=datetime.now().timestamp()
        )
        
        self._individual_goals[goal.id] = goal
        self._agent_goals[agent_id].append(goal.id)
        
        return goal
    
    def aggregate_goals(
        self,
        min_similar_goals: int = 2,
        min_priority: int = 50
    ) -> list[CollectiveGoal]:
        """
        聚合相似的个体目标为集体目标
        
        Args:
            min_similar_goals: 最少相似目标数
            min_priority: 最低优先级
            
        Returns:
            list[CollectiveGoal]: 集体目标列表
        """
        # 按类型分组
        goals_by_type = defaultdict(list)
        for goal in self._individual_goals.values():
            if goal.priority >= min_priority:
                goals_by_type[goal.goal_type].append(goal)
        
        collective_goals = []
        
        for goal_type, goals in goals_by_type.items():
            if len(goals) >= min_similar_goals:
                collective = self._create_collective_goal(goal_type, goals)
                if collective:
                    collective_goals.append(collective)
                    self._collective_goals[collective.id] = collective
        
        return collective_goals
    
    def _create_collective_goal(
        self,
        goal_type: str,
        goals: list[IndividualGoal]
    ) -> CollectiveGoal | None:
        """创建集体目标"""
        if not goals:
            return None
        
        # 计算平均优先级
        avg_priority = sum(g.priority for g in goals) / len(goals)
        
        # 计算总努力和总价值
        total_effort = sum(g.effort_required for g in goals)
        total_value = sum(g.expected_value for g in goals)
        
        # 收集参与者
        participants = list(set(g.agent_id for g in goals))
        
        collective = CollectiveGoal(
            id=str(uuid.uuid4()),
            name=f"{goal_type}_collective",
            description=f"集体目标: {goal_type}",
            priority=int(avg_priority),
            participating_agents=participants,
            sub_goals=[g.id for g in goals],
            consensus_state=ConsensusState.PROPOSING,
            total_effort=total_effort,
            expected_value=total_value,
            created_at=datetime.now().timestamp()
        )
        
        return collective
    
    def vote(
        self,
        collective_goal_id: str,
        agent_id: str,
        approve: bool
    ) -> bool:
        """
        对集体目标投票
        
        Args:
            collective_goal_id: 集体目标 ID
            agent_id: 投票 Agent ID
            approve: 是否赞成
            
        Returns:
            bool: 投票是否成功
        """
        if collective_goal_id not in self._collective_goals:
            return False
        
        collective = self._collective_goals[collective_goal_id]
        
        if agent_id not in collective.participating_agents:
            return False
        
        if approve:
            if agent_id not in collective.participating_agents:
                collective.votes_for.append(agent_id)
            else:
                if agent_id in collective.votes_against:
                    collective.votes_against.remove(agent_id)
                collective.votes_for.append(agent_id)
        else:
            if agent_id in collective.votes_for:
                collective.votes_for.remove(agent_id)
            collective.votes_against.append(agent_id)
        
        return True
    
    def check_consensus(self, collective_goal_id: str) -> bool:
        """
        检查共识是否达成
        
        Args:
            collective_goal_id: 集体目标 ID
            
        Returns:
            bool: 是否达成共识
        """
        if collective_goal_id not in self._collective_goals:
            return False
        
        collective = self._collective_goals[collective_goal_id]
        participants = set(collective.participating_agents)
        
        # 计算投票
        votes_for = set(collective.votes_for)
        votes_against = set(collective.votes_against)
        
        # 共识条件：> 50% 赞成，且没有人反对超过 30%
        total_votes = len(votes_for) + len(votes_against)
        if total_votes < len(participants) * 0.5:
            return False  # 投票人数不足
        
        approval_rate = len(votes_for) / len(participants)
        rejection_rate = len(votes_against) / len(participants)
        
        if approval_rate > 0.5 and rejection_rate < 0.3:
            collective.consensus_state = ConsensusState.CONSENSUS_REACHED
            collective.consensus_at = datetime.now().timestamp()
            return True
        
        if rejection_rate >= 0.3:
            collective.consensus_state = ConsensusState.REJECTED
        
        return False
    
    def get_collective_goals(
        self,
        state: ConsensusState | None = None
    ) -> list[CollectiveGoal]:
        """获取集体目标列表"""
        if state:
            return [
                g for g in self._collective_goals.values()
                if g.consensus_state == state
            ]
        return list(self._collective_goals.values())


class CollectiveGoalEmergence:
    """
    集体目标涌现主控制器
    
    使用方式：
    ```python
    emergence = CollectiveGoalEmergence()
    
    # Agent 提交目标
    emergence.submit_goal(agent_id="a1", goal_type="explore", ...)
    emergence.submit_goal(agent_id="a2", goal_type="explore", ...)
    
    # 聚合目标
    collective = emergence.aggregate_and_form_consensus()
    
    # 投票
    emergence.vote(collective.id, "a1", True)
    ```
    """
    
    def __init__(self):
        self.aggregator = GoalAggregator()
    
    def submit_goal(
        self,
        agent_id: str,
        goal_type: str,
        description: str,
        priority: int,
        effort_required: float = 10.0,
        expected_value: float = 10.0
    ) -> IndividualGoal:
        """提交个体目标"""
        return self.aggregator.submit_goal(
            agent_id=agent_id,
            goal_type=goal_type,
            description=description,
            priority=priority,
            effort_required=effort_required,
            expected_value=expected_value
        )
    
    def aggregate_and_form_consensus(
        self,
        min_similar_goals: int = 2
    ) -> list[CollectiveGoal]:
        """
        聚合目标并形成共识
        
        Args:
            min_similar_goals: 最少相似目标数
            
        Returns:
            list[CollectiveGoal]: 形成共识的集体目标
        """
        # 聚合目标
        collective_goals = self.aggregator.aggregate_goals(
            min_similar_goals=min_similar_goals
        )
        
        # 检查共识
        for collective in collective_goals:
            self.aggregator.check_consensus(collective.id)
        
        # 返回达成共识的目标
        return [
            g for g in collective_goals
            if g.consensus_state == ConsensusState.CONSENSUS_REACHED
        ]
    
    def vote(
        self,
        collective_goal_id: str,
        agent_id: str,
        approve: bool
    ) -> bool:
        """对集体目标投票"""
        result = self.aggregator.vote(collective_goal_id, agent_id, approve)
        if result:
            self.aggregator.check_consensus(collective_goal_id)
        return result
    
    def get_pending_consensus(self) -> list[CollectiveGoal]:
        """获取待达成共识的目标"""
        return self.aggregator.get_collective_goals(ConsensusState.PROPOSING)
    
    def get_reached_consensus(self) -> list[CollectiveGoal]:
        """获取已达成共识的目标"""
        return self.aggregator.get_collective_goals(ConsensusState.CONSENSUS_REACHED)
