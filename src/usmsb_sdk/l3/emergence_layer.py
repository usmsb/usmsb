"""
EmergenceLayer - 涌现层

实现 Agent 群体涌现智能。

核心功能：
- Gossip 协议：状态传播、能力发现
- Team Formation：自组织团队形成
- Pattern Detection：模式检测
- Global Coordination：全局协调（涌现）
"""

import random
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class GossipMessageType(Enum):
    """Gossip 消息类型"""
    CAPABILITY_UPDATE = "capability_update"    # 能力更新
    GOAL_ANNOUNCEMENT = "goal_announcement"    # 目标公告
    RESOURCE_OFFER = "resource_offer"         # 资源提供
    COLLABORATION_REQUEST = "collab_request"  # 协作请求
    PATTERN_DISCOVERY = "pattern_discovery"    # 模式发现
    HEARTBEAT = "heartbeat"                   # 心跳


@dataclass
class GossipMessage:
    """Gossip 消息"""
    id: str
    sender_id: str
    message_type: GossipMessageType
    content: dict
    timestamp: float
    ttl: int = 3  # 传播跳数
    visited: list[str] = field(default_factory=list)  # 已访问节点


@dataclass
class AgentCapability:
    """Agent 能力描述"""
    agent_id: str
    capabilities: list[str]
    reputation: float
    resource_amount: float
    current_goals: list[str]
    last_active: float


@dataclass
class Team:
    """自组织团队"""
    id: str
    name: str
    leader_id: str | None
    member_ids: list[str]
    task: str
    status: str = "forming"
    created_at: float = field(default_factory=lambda: time.time())


class GossipProtocol:
    """
    Gossip 协议实现
    
    特点：
    - 最终一致性
    - 去中心化
    - 容错性强
    - 延迟较高
    
    使用方式：
    ```python
    gossip = GossipProtocol(agent_id="agent_001")
    
    # 广播消息
    gossip.broadcast(
        message_type=GossipMessageType.CAPABILITY_UPDATE,
        content={"capabilities": ["coding", "reasoning"]}
    )
    
    # 获取邻居
    neighbors = gossip.get_active_neighbors()
    ```
    """
    
    def __init__(
        self,
        agent_id: str,
        peers: list[str] | None = None,
        gossip_interval: float = 5.0,
        fanout: int = 3
    ):
        self.agent_id = agent_id
        self.peers = peers or []
        self.gossip_interval = gossip_interval
        self.fanout = fanout  # 每次传播的邻居数量
        
        # 消息缓存
        self._message_cache: dict[str, GossipMessage] = {}
        
        # 能力注册表
        self._capability_registry: dict[str, AgentCapability] = {}
        
        # 最后 gossip 时间
        self._last_gossip_time: float = 0
    
    def add_peer(self, peer_id: str) -> None:
        """添加对等节点"""
        if peer_id not in self.peers:
            self.peers.append(peer_id)
    
    def remove_peer(self, peer_id: str) -> None:
        """移除对等节点"""
        if peer_id in self.peers:
            self.peers.remove(peer_id)
    
    def broadcast(
        self,
        message_type: GossipMessageType,
        content: dict
    ) -> GossipMessage:
        """
        广播消息
        
        Args:
            message_type: 消息类型
            content: 消息内容
            
        Returns:
            GossipMessage: 创建的消息
        """
        message = GossipMessage(
            id=str(uuid.uuid4()),
            sender_id=self.agent_id,
            message_type=message_type,
            content=content,
            timestamp=time.time(),
            ttl=3,
            visited=[self.agent_id]
        )
        
        self._message_cache[message.id] = message
        
        return message
    
    def receive_message(self, message: GossipMessage) -> bool:
        """
        接收消息
        
        Args:
            message: 收到的消息
            
        Returns:
            bool: 是否是新的消息（未处理过）
        """
        if message.id in self._message_cache:
            return False
        
        self._message_cache[message.id] = message
        
        # 处理不同类型的消息
        if message.message_type == GossipMessageType.CAPABILITY_UPDATE:
            self._update_capability(message)
        elif message.message_type == GossipMessageType.HEARTBEAT:
            pass  # 心跳消息不需要特殊处理
        
        return True
    
    def _update_capability(self, message: GossipMessage) -> None:
        """更新能力注册表"""
        content = message.content
        capability = AgentCapability(
            agent_id=message.sender_id,
            capabilities=content.get("capabilities", []),
            reputation=content.get("reputation", 0.5),
            resource_amount=content.get("resource_amount", 0.0),
            current_goals=content.get("current_goals", []),
            last_active=message.timestamp
        )
        self._capability_registry[message.sender_id] = capability
    
    def get_active_neighbors(self) -> list[str]:
        """
        获取活跃的邻居节点
        
        从 peers 中随机选择 fanout 个节点
        
        Returns:
            list[str]: 邻居节点 ID 列表
        """
        if not self.peers:
            return []
        
        # 随机选择
        k = min(self.fanout, len(self.peers))
        return random.sample(self.peers, k)
    
    def propagate_message(
        self,
        message: GossipMessage,
        neighbors: list[str] | None = None
    ) -> list[str]:
        """
        传播消息到邻居
        
        Args:
            message: 要传播的消息
            neighbors: 指定邻居（可选，默认随机选择）
            
        Returns:
            list[str]: 传播到的邻居 ID 列表
        """
        if message.ttl <= 0:
            return []
        
        if neighbors is None:
            neighbors = self.get_active_neighbors()
        
        # 过滤已访问的节点
        to_send = [n for n in neighbors if n not in message.visited]
        
        # 减少 TTL
        message.ttl -= 1
        message.visited.extend(to_send)
        
        return to_send
    
    def search_capabilities(
        self,
        required_capabilities: list[str],
        min_reputation: float = 0.0
    ) -> list[AgentCapability]:
        """
        搜索具有特定能力的 Agent
        
        Args:
            required_capabilities: 需要的能力列表
            min_reputation: 最低声誉要求
            
        Returns:
            list[AgentCapability]: 匹配的 Agent 能力列表
        """
        results = []
        
        for agent_id, capability in self._capability_registry.items():
            if agent_id == self.agent_id:
                continue
            
            if capability.reputation < min_reputation:
                continue
            
            # 检查是否包含所需能力
            if all(cap in capability.capabilities for cap in required_capabilities):
                results.append(capability)
        
        # 按声誉排序
        results.sort(key=lambda x: x.reputation, reverse=True)
        
        return results
    
    def get_capability(self, agent_id: str) -> AgentCapability | None:
        """获取特定 Agent 的能力"""
        return self._capability_registry.get(agent_id)
    
    def should_gossip(self) -> bool:
        """检查是否应该发起 gossip"""
        now = time.time()
        if now - self._last_gossip_time >= self.gossip_interval:
            self._last_gossip_time = now
            return True
        return False


class TeamFormation:
    """
    自组织团队形成
    
    无需中央调度，Agent 自主协商形成团队。
    
    使用方式：
    ```python
    formation = TeamFormation()
    
    # 发布任务需求
    task_id = formation.announce_task(
        task="需要数据分析能力",
        required_capabilities=["analysis", "visualization"]
    )
    
    # Agent 报名加入
    formation.join_team(task_id, "agent_001")
    
    # 获取形成的团队
    team = formation.get_team(task_id)
    ```
    """
    
    def __init__(self):
        self._pending_tasks: dict[str, dict] = {}
        self._teams: dict[str, Team] = {}
        self._task_members: dict[str, list[str]] = defaultdict(list)
    
    def announce_task(
        self,
        announcer_id: str,
        task: str,
        required_capabilities: list[str],
        max_members: int = 5
    ) -> str:
        """
        发布任务需求
        
        Args:
            announcer_id: 发布者 ID
            task: 任务描述
            required_capabilities: 所需能力
            max_members: 最大成员数
            
        Returns:
            str: 任务 ID
        """
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        self._pending_tasks[task_id] = {
            "id": task_id,
            "announcer_id": announcer_id,
            "task": task,
            "required_capabilities": required_capabilities,
            "max_members": max_members,
            "status": "open",
            "created_at": time.time()
        }
        
        return task_id
    
    def join_team(self, task_id: str, agent_id: str) -> bool:
        """
        加入任务团队
        
        Args:
            task_id: 任务 ID
            agent_id: Agent ID
            
        Returns:
            bool: 是否加入成功
        """
        if task_id not in self._pending_tasks:
            return False
        
        task = self._pending_tasks[task_id]
        
        if task["status"] != "open":
            return False
        
        if agent_id in self._task_members[task_id]:
            return False  # 已加入
        
        if len(self._task_members[task_id]) >= task["max_members"]:
            return False  # 已满
        
        self._task_members[task_id].append(agent_id)
        
        # 如果达到最大成员数，锁定团队
        if len(self._task_members[task_id]) >= task["max_members"]:
            self._finalize_team(task_id)
        
        return True
    
    def leave_team(self, task_id: str, agent_id: str) -> bool:
        """离开团队"""
        if task_id not in self._task_members:
            return False
        
        if agent_id in self._task_members[task_id]:
            self._task_members[task_id].remove(agent_id)
            return True
        
        return False
    
    def _finalize_team(self, task_id: str) -> None:
        """完成团队组建"""
        task = self._pending_tasks[task_id]
        members = self._task_members[task_id]
        
        team = Team(
            id=task_id,
            name=task["task"],
            leader_id=members[0] if members else None,
            member_ids=members,
            task=task["task"],
            status="formed"
        )
        
        self._teams[task_id] = team
        task["status"] = "formed"
    
    def get_team(self, task_id: str) -> Team | None:
        """获取团队信息"""
        return self._teams.get(task_id)
    
    def get_pending_task(self, task_id: str) -> dict | None:
        """获取待处理任务"""
        return self._pending_tasks.get(task_id)
    
    def get_open_tasks(self) -> list[dict]:
        """获取所有开放的任务"""
        return [
            task for task in self._pending_tasks.values()
            if task["status"] == "open"
        ]


class PatternDetection:
    """
    模式检测
    
    从局部交互中检测全局模式。
    
    使用方式：
    ```python
    detector = PatternDetection()
    
    # 记录交互
    detector.record_interaction(
        agent_a="agent_001",
        agent_b="agent_002",
        interaction_type="collaboration",
        outcome="success"
    )
    
    # 检测模式
    patterns = detector.detect_patterns()
    ```
    """
    
    def __init__(self):
        # 交互记录
        self._interactions: list[dict] = []
        
        # 交互统计
        self._interaction_counts: dict[str, dict] = defaultdict(lambda: defaultdict(int))
        
        # 成功/失败统计
        self._outcome_stats: dict[str, dict] = defaultdict(lambda: {"success": 0, "failure": 0})
    
    def record_interaction(
        self,
        agent_a: str,
        agent_b: str,
        interaction_type: str,
        outcome: str
    ) -> None:
        """
        记录交互
        
        Args:
            agent_a: Agent A ID
            agent_b: Agent B ID
            interaction_type: 交互类型
            outcome: 结果 (success/failure)
        """
        interaction = {
            "id": str(uuid.uuid4()),
            "agent_a": agent_a,
            "agent_b": agent_b,
            "type": interaction_type,
            "outcome": outcome,
            "timestamp": time.time()
        }
        
        self._interactions.append(interaction)
        
        # 更新统计
        pair = tuple(sorted([agent_a, agent_b]))
        self._interaction_counts[interaction_type][f"{pair[0]}-{pair[1]}"] += 1
        
        if outcome == "success":
            self._outcome_stats[agent_a]["success"] += 1
            self._outcome_stats[agent_b]["success"] += 1
        else:
            self._outcome_stats[agent_a]["failure"] += 1
            self._outcome_stats[agent_b]["failure"] += 1
    
    def detect_hub_agents(self, min_interactions: int = 10) -> list[str]:
        """
        检测中心节点（高度连接的 Agent）
        
        Args:
            min_interactions: 最小交互次数
            
        Returns:
            list[str]: 中心节点 ID 列表
        """
        hub_counts = defaultdict(int)
        
        for interaction in self._interactions:
            hub_counts[interaction["agent_a"]] += 1
            hub_counts[interaction["agent_b"]] += 1
        
        return [
            agent_id for agent_id, count in hub_counts.items()
            if count >= min_interactions
        ]
    
    def detect_successful_pairs(self) -> list[tuple[str, str]]:
        """
        检测成功协作对
        
        Returns:
            list[tuple]: 成功的 Agent 对
        """
        pairs = []
        
        for pair_key, counts in self._interaction_counts.get("collaboration", {}).items():
            agent_a, agent_b = pair_key.split("-")
            
            # 计算成功率
            total = counts
            successes = min(
                self._outcome_stats[agent_a]["success"],
                self._outcome_stats[agent_b]["success"]
            )
            
            if total >= 3 and successes / total > 0.7:
                pairs.append((agent_a, agent_b))
        
        return pairs
    
    def detect_patterns(self) -> dict[str, Any]:
        """
        检测全局模式
        
        Returns:
            dict: 检测到的模式
        """
        return {
            "hub_agents": self.detect_hub_agents(),
            "successful_pairs": self.detect_successful_pairs(),
            "total_interactions": len(self._interactions),
            "interaction_types": list(self._interaction_counts.keys()),
        }


class EmergenceLayer:
    """
    涌现层主控制器
    
    整合 Gossip、TeamFormation、PatternDetection。
    
    使用方式：
    ```python
    emergence = EmergenceLayer(agent_id="agent_001")
    
    # 广播能力
    emergence.announce_capability(["coding", "analysis"])
    
    # 发布任务
    task_id = emergence.publish_task("需要设计支持", ["design", "creative"])
    
    # 检测模式
    patterns = emergence.detect_global_patterns()
    ```
    """
    
    def __init__(self, agent_id: str, peers: list[str] | None = None):
        self.agent_id = agent_id
        
        # 初始化子模块
        self.gossip = GossipProtocol(agent_id=agent_id, peers=peers)
        self.team_formation = TeamFormation()
        self.pattern_detection = PatternDetection()
        
        # 注册自身能力
        self._register_self_capability()
    
    def _register_self_capability(self) -> None:
        """注册自身能力到 Gossip"""
        # 后续可以通过 update_capability 更新
        pass
    
    def update_capability(
        self,
        capabilities: list[str],
        reputation: float,
        resource_amount: float,
        current_goals: list[str]
    ) -> None:
        """
        更新自身能力并广播
        
        Args:
            capabilities: 能力列表
            reputation: 声誉
            resource_amount: 资源量
            current_goals: 当前目标
        """
        self.gossip.broadcast(
            message_type=GossipMessageType.CAPABILITY_UPDATE,
            content={
                "capabilities": capabilities,
                "reputation": reputation,
                "resource_amount": resource_amount,
                "current_goals": current_goals
            }
        )
    
    def announce_goal(self, goal: str) -> GossipMessage:
        """
        广播目标
        
        Args:
            goal: 目标描述
            
        Returns:
            GossipMessage: 广播的消息
        """
        return self.gossip.broadcast(
            message_type=GossipMessageType.GOAL_ANNOUNCEMENT,
            content={"goal": goal, "agent_id": self.agent_id}
        )
    
    def publish_task(
        self,
        task: str,
        required_capabilities: list[str],
        max_members: int = 5
    ) -> str:
        """
        发布任务并广播
        
        Args:
            task: 任务描述
            required_capabilities: 所需能力
            max_members: 最大成员数
            
        Returns:
            str: 任务 ID
        """
        # 发布任务
        task_id = self.team_formation.announce_task(
            announcer_id=self.agent_id,
            task=task,
            required_capabilities=required_capabilities,
            max_members=max_members
        )
        
        # 广播任务
        self.gossip.broadcast(
            message_type=GossipMessageType.COLLABORATION_REQUEST,
            content={
                "task_id": task_id,
                "task": task,
                "required_capabilities": required_capabilities
            }
        )
        
        return task_id
    
    def search_for_collaborators(
        self,
        required_capabilities: list[str]
    ) -> list[AgentCapability]:
        """
        搜索具有特定能力的协作方
        
        Args:
            required_capabilities: 所需能力
            
        Returns:
            list[AgentCapability]: 匹配的 Agent
        """
        return self.gossip.search_capabilities(required_capabilities)
    
    def join_task(self, task_id: str) -> bool:
        """
        加入任务团队
        
        Args:
            task_id: 任务 ID
            
        Returns:
            bool: 是否加入成功
        """
        return self.team_formation.join_team(task_id, self.agent_id)
    
    def record_interaction(
        self,
        collaborator_id: str,
        interaction_type: str,
        outcome: str
    ) -> None:
        """
        记录与协作方的交互
        
        Args:
            collaborator_id: 协作方 ID
            interaction_type: 交互类型
            outcome: 结果
        """
        self.pattern_detection.record_interaction(
            agent_a=self.agent_id,
            agent_b=collaborator_id,
            interaction_type=interaction_type,
            outcome=outcome
        )
    
    def detect_global_patterns(self) -> dict[str, Any]:
        """
        检测全局模式
        
        Returns:
            dict: 检测到的模式
        """
        return self.pattern_detection.detect_patterns()
    
    def get_active_teams(self) -> list[Team]:
        """获取所有活跃团队"""
        return list(self.team_formation._teams.values())
    
    def get_open_tasks(self) -> list[dict]:
        """获取所有开放任务"""
        return self.team_formation.get_open_tasks()
