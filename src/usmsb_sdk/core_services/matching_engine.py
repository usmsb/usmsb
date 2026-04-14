"""
MatchingEngine - 匹配引擎

USMSB 核心服务之一。
将任务与最合适的 Agent 进行匹配。

功能：
- 多维度匹配
- 匹配排序
- 预匹配洽谈
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MatchStatus(Enum):
    """匹配状态"""
    PENDING = "pending"           # 待确认
    NEGOTIATING = "negotiating"  # 洽谈中
    ACCEPTED = "accepted"         # 已接受
    REJECTED = "rejected"         # 已拒绝
    EXPIRED = "expired"           # 已过期


@dataclass
class Match:
    """匹配结果"""
    id: str
    task_id: str
    agent_id: str
    score: float  # 匹配分数 0-100
    status: MatchStatus = MatchStatus.PENDING
    reason: str = ""  # 匹配原因
    negotiation_id: str | None = None
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    expires_at: float | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class Task:
    """任务"""
    id: str
    title: str
    description: str
    required_capabilities: list[str] = field(default_factory=list)
    required_skills: list[str] = field(default_factory=list)
    budget: float = 0.0
    currency: str = "VIBE"
    deadline: float | None = None
    priority: int = 50  # 0-100
    metadata: dict = field(default_factory=dict)


class MatchingEngine:
    """
    匹配引擎
    
    使用方式：
    ```python
    engine = MatchingEngine()
    
    # 创建任务
    task = Task(id="task_001", title="数据分析", ...)
    
    # 创建候选 Agent
    agents = [agent1, agent2, agent3]
    
    # 执行匹配
    matches = engine.match(task, agents)
    
    # 排序
    ranked = engine.rank_matches(matches)
    ```
    """
    
    # 匹配权重
    WEIGHT_CAPABILITY = 0.40  # 能力匹配
    WEIGHT_REPUTATION = 0.25  # 声誉
    WEIGHT_PRICE = 0.20       # 价格
    WEIGHT_AVAILABILITY = 0.15 # 可用性
    
    def __init__(self, reputation_service=None):
        self.reputation_service = reputation_service
        self._matches: dict[str, Match] = {}
    
    def match(
        self,
        task: Task,
        agents: list,
        top_k: int = 5
    ) -> list[Match]:
        """
        执行匹配
        
        Args:
            task: 任务
            agents: Agent 列表
            top_k: 返回前 k 个匹配
            
        Returns:
            list[Match]: 匹配结果
        """
        matches = []
        
        for agent in agents:
            score = self._calculate_match_score(task, agent)
            
            if score > 0:
                match = Match(
                    id=str(uuid.uuid4()),
                    task_id=task.id,
                    agent_id=agent.id,
                    score=score,
                    reason=self._generate_match_reason(task, agent, score)
                )
                matches.append(match)
                self._matches[match.id] = match
        
        # 按分数排序
        matches.sort(key=lambda m: m.score, reverse=True)
        
        return matches[:top_k]
    
    def _calculate_match_score(self, task: Task, agent) -> float:
        """计算匹配分数"""
        score = 0.0
        
        # 1. 能力匹配分数
        capability_score = self._calculate_capability_score(task, agent)
        score += capability_score * self.WEIGHT_CAPABILITY
        
        # 2. 声誉分数
        reputation_score = self._calculate_reputation_score(agent)
        score += reputation_score * self.WEIGHT_REPUTATION
        
        # 3. 价格分数
        price_score = self._calculate_price_score(task, agent)
        score += price_score * self.WEIGHT_PRICE
        
        # 4. 可用性分数
        availability_score = self._calculate_availability_score(agent)
        score += availability_score * self.WEIGHT_AVAILABILITY
        
        return min(100, max(0, score))
    
    def _calculate_capability_score(self, task: Task, agent) -> float:
        """计算能力匹配分数"""
        if not task.required_capabilities:
            return 100.0  # 无要求，100分
        
        if not agent.capabilities:
            return 0.0
        
        matched = sum(1 for cap in task.required_capabilities if cap in agent.capabilities)
        return (matched / len(task.required_capabilities)) * 100
    
    def _calculate_reputation_score(self, agent) -> float:
        """计算声誉分数"""
        reputation = getattr(agent, "reputation", 0.5)
        return reputation * 100
    
    def _calculate_price_score(self, task: Task, agent) -> float:
        """计算价格分数"""
        if not hasattr(agent, "hourly_rate") or agent.hourly_rate == 0:
            return 50.0  # 无价格信息
        
        if task.budget <= 0:
            return 50.0  # 无预算信息
        
        # 预算内价格得高分
        if agent.hourly_rate <= task.budget:
            return 100.0 - (agent.hourly_rate / task.budget * 50)
        else:
            # 超预算
            over_ratio = agent.hourly_rate / task.budget
            return max(0, 50 - (over_ratio - 1) * 50)
    
    def _calculate_availability_score(self, agent) -> float:
        """计算可用性分数"""
        # 基于当前任务数/最大并发
        max_concurrent = getattr(agent, "max_concurrent", 5)
        current_tasks = getattr(agent, "current_tasks", 0)
        
        if max_concurrent <= 0:
            return 0.0
        
        available_slots = max_concurrent - current_tasks
        
        if available_slots <= 0:
            return 0.0
        
        return min(100, (available_slots / max_concurrent) * 100)
    
    def _generate_match_reason(self, task: Task, agent, score: float) -> str:
        """生成匹配原因"""
        reasons = []
        
        # 能力匹配
        matched_caps = [c for c in task.required_capabilities if c in agent.capabilities]
        if matched_caps:
            reasons.append(f"具备所需能力: {', '.join(matched_caps)}")
        
        # 声誉
        reputation = getattr(agent, "reputation", 0.5)
        if reputation > 0.7:
            reasons.append(f"声誉良好: {reputation:.0%}")
        
        # 可用性
        available = getattr(agent, "max_concurrent", 5) - getattr(agent, "current_tasks", 0)
        if available > 2:
            reasons.append(f"可用性高: {available} 个空位")
        
        return "; ".join(reasons) if reasons else f"综合匹配分数: {score:.1f}"
    
    def rank_matches(self, matches: list[Match]) -> list[Match]:
        """
        排序匹配结果
        
        Args:
            matches: 匹配列表
            
        Returns:
            list[Match]: 排序后的列表
        """
        return sorted(matches, key=lambda m: m.score, reverse=True)
    
    def get_match(self, match_id: str) -> Match | None:
        """获取匹配"""
        return self._matches.get(match_id)
    
    def update_match_status(self, match_id: str, status: MatchStatus) -> bool:
        """更新匹配状态"""
        match = self._matches.get(match_id)
        if not match:
            return False
        match.status = status
        return True
    
    def get_statistics(self) -> dict[str, Any]:
        """获取统计"""
        total = len(self._matches)
        by_status = {}
        
        for match in self._matches.values():
            status = match.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        avg_score = (
            sum(m.score for m in self._matches.values()) / total
            if total > 0 else 0
        )
        
        return {
            "total_matches": total,
            "by_status": by_status,
            "average_score": avg_score,
        }
