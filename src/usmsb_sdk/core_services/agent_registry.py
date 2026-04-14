"""
AgentRegistry - Agent 注册与管理

USMSB 核心服务之一。
管理 Agent 的注册、状态和生命周期。

功能：
- Agent 注册/注销
- Agent 状态管理
- Agent 能力追踪
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AgentStatus(Enum):
    """Agent 状态"""
    OFFLINE = "offline"           # 离线
    ONLINE = "online"             # 在线
    BUSY = "busy"               # 忙碌
    SUSPENDED = "suspended"      # 暂停


class AgentType(Enum):
    """Agent 类型"""
    GENERAL = "general"           # 通用 Agent
    SPECIALIST = "specialist"     # 专业 Agent
    COORDINATOR = "coordinator"  # 协调 Agent
    GOVERNOR = "governor"       # 治理 Agent


@dataclass
class AgentProfile:
    """
    Agent 画像
    
    包含 Agent 的所有元信息。
    """
    id: str
    name: str
    description: str
    agent_type: AgentType = AgentType.GENERAL
    status: AgentStatus = AgentStatus.OFFLINE
    capabilities: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    wallet_address: str = ""
    owner: str = ""  # 所有者 ID
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    last_active: float = field(default_factory=lambda: datetime.now().timestamp())
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    reputation: float = 0.5  # 0.0-1.0
    hourly_rate: float = 0.0  # VIBE/小时
    max_concurrent: int = 5  # 最大并发任务数
    current_tasks: int = 0  # 当前任务数
    metadata: dict = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """计算成功率"""
        if self.total_tasks == 0:
            return 0.0
        return self.successful_tasks / self.total_tasks
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "agent_type": self.agent_type.value,
            "status": self.status.value,
            "capabilities": self.capabilities,
            "skills": self.skills,
            "wallet_address": self.wallet_address,
            "owner": self.owner,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": self.success_rate,
            "reputation": self.reputation,
            "hourly_rate": self.hourly_rate,
            "max_concurrent": self.max_concurrent,
            "current_tasks": self.current_tasks,
            "metadata": self.metadata,
        }


class AgentRegistry:
    """
    Agent 注册表
    
    管理所有 Agent 的注册和状态。
    
    使用方式：
    ```python
    registry = AgentRegistry()
    
    # 注册 Agent
    agent = AgentProfile(id="agent_001", name="Test Agent", ...)
    registry.register(agent)
    
    # 更新状态
    registry.update_status("agent_001", AgentStatus.ONLINE)
    
    # 发现 Agent
    agents = registry.discover(capabilities=["coding"])
    ```
    """
    
    def __init__(self):
        # Agent 存储
        self._agents: dict[str, AgentProfile] = {}
        
        # 能力索引
        self._capability_index: dict[str, list[str]] = {}  # capability -> [agent_id]
        
        # 状态索引
        self._status_index: dict[AgentStatus, list[str]] = {}
    
    def register(self, agent: AgentProfile) -> bool:
        """
        注册 Agent
        
        Args:
            agent: Agent 画像
            
        Returns:
            bool: 是否成功
        """
        if agent.id in self._agents:
            return False
        
        # 添加到存储
        self._agents[agent.id] = agent
        
        # 更新能力索引
        for capability in agent.capabilities:
            if capability not in self._capability_index:
                self._capability_index[capability] = []
            self._capability_index[capability].append(agent.id)
        
        # 更新状态索引
        if agent.status not in self._status_index:
            self._status_index[agent.status] = []
        self._status_index[agent.status].append(agent.id)
        
        return True
    
    def unregister(self, agent_id: str) -> bool:
        """
        注销 Agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            bool: 是否成功
        """
        if agent_id not in self._agents:
            return False
        
        agent = self._agents[agent_id]
        
        # 清理能力索引
        for capability in agent.capabilities:
            if capability in self._capability_index:
                if agent_id in self._capability_index[capability]:
                    self._capability_index[capability].remove(agent_id)
        
        # 清理状态索引
        if agent.status in self._status_index:
            if agent_id in self._status_index[agent.status]:
                self._status_index[agent.status].remove(agent_id)
        
        # 删除
        del self._agents[agent_id]
        
        return True
    
    def get_agent(self, agent_id: str) -> AgentProfile | None:
        """获取 Agent"""
        return self._agents.get(agent_id)
    
    def update_status(self, agent_id: str, status: AgentStatus) -> bool:
        """
        更新 Agent 状态
        
        Args:
            agent_id: Agent ID
            status: 新状态
            
        Returns:
            bool: 是否成功
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        
        # 清理旧状态索引
        if agent.status in self._status_index:
            if agent_id in self._status_index[agent.status]:
                self._status_index[agent.status].remove(agent_id)
        
        # 更新状态
        agent.status = status
        agent.last_active = datetime.now().timestamp()
        
        # 添加到新状态索引
        if status not in self._status_index:
            self._status_index[status] = []
        self._status_index[status].append(agent_id)
        
        return True
    
    def update_activity(self, agent_id: str) -> bool:
        """更新最后活跃时间"""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.last_active = datetime.now().timestamp()
        return True
    
    def update_task_stats(
        self,
        agent_id: str,
        success: bool
    ) -> bool:
        """
        更新任务统计
        
        Args:
            agent_id: Agent ID
            success: 是否成功
            
        Returns:
            bool: 是否成功
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        
        agent.total_tasks += 1
        if success:
            agent.successful_tasks += 1
        else:
            agent.failed_tasks += 1
        
        # 更新声誉
        agent.reputation = agent.success_rate
        
        return True
    
    def discover(
        self,
        capabilities: list[str] | None = None,
        status: AgentStatus | None = None,
        min_reputation: float = 0.0,
        limit: int = 10
    ) -> list[AgentProfile]:
        """
        发现 Agent
        
        Args:
            capabilities: 需要的能力
            status: 状态过滤
            min_reputation: 最低声誉
            limit: 返回数量
            
        Returns:
            list[AgentProfile]: 匹配的 Agent
        """
        candidates = set()
        
        # 按能力筛选
        if capabilities:
            for cap in capabilities:
                if cap in self._capability_index:
                    candidates.update(self._capability_index[cap])
        else:
            candidates = set(self._agents.keys())
        
        # 状态筛选
        if status:
            status_candidates = set(self._status_index.get(status, []))
            candidates &= status_candidates
        
        # 构建结果
        results = []
        for agent_id in candidates:
            agent = self._agents.get(agent_id)
            if not agent:
                continue
            
            # 声誉筛选
            if agent.reputation < min_reputation:
                continue
            
            # 排除忙碌的 Agent
            if agent.current_tasks >= agent.max_concurrent:
                continue
            
            results.append(agent)
        
        # 按声誉排序
        results.sort(key=lambda a: a.reputation, reverse=True)
        
        return results[:limit]
    
    def get_online_agents(self) -> list[AgentProfile]:
        """获取所有在线 Agent"""
        return [
            self._agents[aid]
            for aid in self._status_index.get(AgentStatus.ONLINE, [])
            if aid in self._agents
        ]
    
    def get_busy_agents(self) -> list[AgentProfile]:
        """获取所有忙碌 Agent"""
        return [
            self._agents[aid]
            for aid in self._status_index.get(AgentStatus.BUSY, [])
            if aid in self._agents
        ]
    
    def increment_task(self, agent_id: str) -> bool:
        """增加当前任务数"""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.current_tasks += 1
        if agent.current_tasks >= agent.max_concurrent:
            self.update_status(agent_id, AgentStatus.BUSY)
        return True
    
    def decrement_task(self, agent_id: str) -> bool:
        """减少当前任务数"""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.current_tasks = max(0, agent.current_tasks - 1)
        if agent.current_tasks < agent.max_concurrent:
            if agent.status == AgentStatus.BUSY:
                self.update_status(agent_id, AgentStatus.ONLINE)
        return True
    
    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        total = len(self._agents)
        by_status = {
            status.value: len(agents)
            for status, agents in self._status_index.items()
        }
        
        total_tasks = sum(a.total_tasks for a in self._agents.values())
        avg_reputation = (
            sum(a.reputation for a in self._agents.values()) / total
            if total > 0 else 0
        )
        
        return {
            "total_agents": total,
            "by_status": by_status,
            "total_tasks": total_tasks,
            "average_reputation": avg_reputation,
            "capabilities_count": len(self._capability_index),
        }
