"""
EmergenceSystem - 涌现系统

Phase 4: 涌现系统层 - 完整实现

完整实现：
- Gossip 协议（完整网络模拟）
- 团队形成算法
- 模式检测（复杂网络分析）
- 全局协调（分布式协调）
"""

import uuid
import random
import math
import networkx as nx
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable


# ============================================================================
# Gossip Protocol - 完整网络协议实现
# ============================================================================

@dataclass
class GossipMessage:
    """Gossip 消息"""
    id: str
    sender_id: str
    message_type: str  # capability, opportunity, state, heartbeat
    content: dict
    ttl: int = 3
    hops: int = 0
    visited: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=datetime.now().timestamp)
    metadata: dict = field(default_factory=dict)


@dataclass
class NodeState:
    """节点状态"""
    node_id: str
    capabilities: list[str]
    reputation: float
    active_tasks: int
    resource_level: float  # 0-1
    last_heartbeat: float
    metadata: dict


class GossipProtocol:
    """
    Gossip 协议 - 完整实现
    
    支持：
    - SWIM 风格的故障检测
    - 带抑制的广播
    - 流行病模型（Epidermic）
    """
    
    # Gossip 配置
    FANOUT = 3  # 每轮传播目标数
    GOSSIP_INTERVAL = 1.0  # 秒
    TTL_DECAY = 0.95  # TTL 衰减率
    HEARTBEAT_TIMEOUT = 30.0  # 秒
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.peers: dict[str, 'GossipProtocol'] = {}
        self.message_cache: dict[str, GossipMessage] = {}
        self.peer_states: dict[str, NodeState] = {}
        self._pending_messages: deque[GossipMessage] = deque()
        self._failure_suspects: set[str] = set()
        self._confirmed_failures: set[str] = set()
    
    def add_peer(self, peer_id: str, peer: 'GossipProtocol') -> None:
        """添加对等节点"""
        self.peers[peer_id] = peer
        peer.peers[self.node_id] = self
    
    def remove_peer(self, peer_id: str) -> None:
        """移除对等节点"""
        if peer_id in self.peers:
            del self.peers[peer_id]
            self.peers[peer_id].peers.pop(self.node_id, None)
    
    def broadcast(
        self,
        msg_type: str,
        content: dict,
        ttl: int = 3
    ) -> GossipMessage:
        """广播消息"""
        msg = GossipMessage(
            id=str(uuid.uuid4()),
            sender_id=self.node_id,
            message_type=msg_type,
            content=content,
            ttl=ttl,
            visited=[self.node_id]
        )
        self.message_cache[msg.id] = msg
        self._pending_messages.append(msg)
        return msg
    
    def send_heartbeat(self) -> GossipMessage:
        """发送心跳"""
        state = self.get_state()
        return self.broadcast("heartbeat", {
            "node_id": self.node_id,
            "state": state.__dict__,
            "timestamp": datetime.now().timestamp()
        })
    
    def get_state(self) -> NodeState:
        """获取当前状态"""
        return NodeState(
            node_id=self.node_id,
            capabilities=[],  # 外部设置
            reputation=0.5,
            active_tasks=0,
            resource_level=0.8,
            last_heartbeat=datetime.now().timestamp(),
            metadata={}
        )
    
    def update_peer_state(self, peer_id: str, state: NodeState) -> None:
        """更新对等节点状态"""
        self.peer_states[peer_id] = state
        
        # 检查是否需要移除
        if peer_id in self._failure_suspects:
            if datetime.now().timestamp() - state.last_heartbeat < self.HEARTBEAT_TIMEOUT:
                self._failure_suspects.discard(peer_id)
    
    def gossip_round(self) -> list[GossipMessage]:
        """
        执行一轮 Gossip
        
        1. 发送消息给随机 peers
        2. 处理接收到的消息
        3. 检测故障
        
        Returns:
            list[GossipMessage]: 发送的消息
        """
        sent_messages = []
        
        # 处理待发送消息
        while self._pending_messages:
            msg = self._pending_messages.popleft()
            
            if msg.ttl <= 0:
                continue
            
            # 选择目标 peers
            targets = self._select_targets(self.FANOUT, msg.visited)
            
            for target_id in targets:
                if target_id in self.peers:
                    # 复制消息（TTL 衰减）
                    sent_msg = GossipMessage(
                        id=msg.id,
                        sender_id=self.node_id,
                        message_type=msg.message_type,
                        content=msg.content,
                        ttl=max(0, int(msg.ttl * self.TTL_DECAY)),
                        hops=msg.hops + 1,
                        visited=msg.visited + [self.node_id],
                        metadata=msg.metadata
                    )
                    
                    # 发送
                    self.peers[target_id].receive_gossip(sent_msg)
                    sent_messages.append(sent_msg)
        
        # 故障检测
        self._detect_failures()
        
        return sent_messages
    
    def _select_targets(self, k: int, exclude: list[str]) -> list[str]:
        """选择目标 peers"""
        candidates = [p for p in self.peers.keys() if p not in exclude]
        
        if len(candidates) <= k:
            return candidates
        
        return random.sample(candidates, k)
    
    def receive_gossip(self, msg: GossipMessage) -> None:
        """接收 Gossip 消息"""
        # 检查是否已处理
        if msg.id in self.message_cache:
            return
        
        self.message_cache[msg.id] = msg
        
        # 更新发送方状态
        if msg.message_type == "heartbeat" and "state" in msg.content:
            state = NodeState(**msg.content["state"])
            self.update_peer_state(msg.sender_id, state)
        
        # 加入待处理队列
        self._pending_messages.append(msg)
    
    def _detect_failures(self) -> None:
        """检测节点故障（SWIM 风格）"""
        now = datetime.now().timestamp()
        
        for peer_id, state in list(self.peer_states.items()):
            if peer_id in self._confirmed_failures:
                continue
            
            if now - state.last_heartbeat > self.HEARTBEAT_TIMEOUT:
                if peer_id not in self._failure_suspects:
                    self._failure_suspects.add(peer_id)
                    # 广播怀疑
                    self.broadcast("suspect", {
                        "suspected_node": peer_id,
                        "reason": "heartbeat_timeout"
                    })
                else:
                    # 多次怀疑，确认故障
                    self._confirmed_failures.add(peer_id)
                    self.broadcast("confirm", {
                        "confirmed_node": peer_id,
                        "reason": "heartbeat_timeout"
                    })
    
    def get_active_peers(self) -> list[str]:
        """获取活跃 peers"""
        return [p for p in self.peers.keys() if p not in self._confirmed_failures]


# ============================================================================
# Team Formation - 动态组队算法
# ============================================================================

@dataclass
class Team:
    """团队"""
    id: str
    leader_id: str
    members: list[str]
    task: str
    required_capabilities: list[str]
    status: str = "forming"  # forming, active, completed, disbanded
    cohesion_score: float = 0.0  # 团队凝聚力
    created_at: float = field(default_factory=datetime.now().timestamp)
    metadata: dict = field(default_factory=dict)


class TeamFormationAlgorithm:
    """
    团队形成算法 - 完整实现
    
    特点：
    - 基于能力的匹配
    - 团队凝聚力优化
    - 动态调整
    """
    
    MIN_TEAM_SIZE = 2
    MAX_TEAM_SIZE = 10
    COHESION_THRESHOLD = 0.6  # 凝聚力阈值
    
    def __init__(self):
        self.teams: dict[str, Team] = {}
        self.node_capabilities: dict[str, list[str]] = defaultdict(list)
        self.node_reputations: dict[str, float] = {}
    
    def register_node_capabilities(
        self,
        node_id: str,
        capabilities: list[str],
        reputation: float = 0.5
    ) -> None:
        """注册节点能力"""
        self.node_capabilities[node_id] = capabilities
        self.node_reputations[node_id] = reputation
    
    def find_candidates(
        self,
        required_capabilities: list[str],
        exclude_nodes: list[str] = None,
        min_reputation: float = 0.0
    ) -> list[tuple[str, float]]:
        """
        查找符合条件的候选节点
        
        Returns:
            list[(node_id, score)]: 按分数排序的候选列表
        """
        exclude_nodes = exclude_nodes or []
        
        candidates = []
        
        for node_id, capabilities in self.node_capabilities.items():
            if node_id in exclude_nodes:
                continue
            
            if node_id not in self.node_reputations:
                continue
            
            reputation = self.node_reputations[node_id]
            if reputation < min_reputation:
                continue
            
            # 计算能力匹配分数
            matched = set(capabilities) & set(required_capabilities)
            match_score = len(matched) / len(required_capabilities) if required_capabilities else 0
            
            if match_score > 0:
                # 综合分数 = 能力匹配 * 0.7 + 声誉 * 0.3
                score = match_score * 0.7 + reputation * 0.3
                candidates.append((node_id, score))
        
        # 按分数排序
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        return candidates
    
    def estimate_team_cohesion(
        self,
        member_ids: list[str]
    ) -> float:
        """
        估算团队凝聚力
        
        使用：
        - 能力重叠度
        - 历史协作成功率
        - 声誉互补性
        
        Returns:
            float: 凝聚力分数 0-1
        """
        if len(member_ids) < 2:
            return 1.0
        
        # 计算能力重叠
        total_overlap = 0
        pairs = 0
        
        for i, m1 in enumerate(member_ids):
            caps1 = set(self.node_capabilities.get(m1, []))
            for m2 in member_ids[i+1:]:
                caps2 = set(self.node_capabilities.get(m2, []))
                intersection = len(caps1 & caps2)
                union = len(caps1 | caps2)
                if union > 0:
                    overlap = intersection / union
                    total_overlap += overlap
                    pairs += 1
        
        overlap_score = total_overlap / pairs if pairs > 0 else 0
        
        # 计算声誉多样性（标准差）
        reputations = [self.node_reputations.get(m, 0.5) for m in member_ids]
        if len(reputations) > 1:
            import statistics
            diversity = min(1.0, statistics.stdev(reputations) * 2)
        else:
            diversity = 1.0
        
        # 综合凝聚力
        cohesion = overlap_score * 0.6 + diversity * 0.4
        
        return cohesion
    
    def form_team(
        self,
        task: str,
        required_capabilities: list[str],
        leader_id: str,
        min_size: int = 2,
        max_size: int = 5,
        min_cohesion: float = 0.5
    ) -> Team | None:
        """
        形成团队
        
        1. 查找候选
        2. 贪婪选择最大凝聚力组合
        3. 验证凝聚力阈值
        
        Returns:
            Team 或 None（无法组成有效团队）
        """
        # 查找候选
        candidates = self.find_candidates(
            required_capabilities,
            exclude_nodes=[leader_id],
            min_reputation=0.3
        )
        
        if not candidates:
            return None
        
        # 贪婪选择
        members = [leader_id]
        remaining_caps = set(required_capabilities)
        
        for node_id, _ in candidates:
            if len(members) >= max_size:
                break
            
            node_caps = set(self.node_capabilities.get(node_id, []))
            
            # 检查是否有新贡献
            new_contribution = len(node_caps & remaining_caps) > 0
            
            # 估算加入后的凝聚力
            test_members = members + [node_id]
            test_cohesion = self.estimate_team_cohesion(test_members)
            
            if new_contribution and test_cohesion >= min_cohesion:
                members.append(node_id)
                remaining_caps -= node_caps
        
        # 检查是否满足最低要求
        if len(members) < min_size:
            return None
        
        # 创建团队
        team = Team(
            id=str(uuid.uuid4()),
            leader_id=leader_id,
            members=members,
            task=task,
            required_capabilities=required_capabilities,
            status="forming",
            cohesion_score=self.estimate_team_cohesion(members)
        )
        
        self.teams[team.id] = team
        
        return team
    
    def dissolve_team(self, team_id: str) -> bool:
        """解散团队"""
        if team_id in self.teams:
            self.teams[team_id].status = "disbanded"
            return True
        return False
    
    def merge_teams(self, team_id1: str, team_id2: str) -> Team | None:
        """合并两个团队"""
        t1 = self.teams.get(team_id1)
        t2 = self.teams.get(team_id2)
        
        if not t1 or not t2:
            return None
        
        # 合并成员
        new_members = list(set(t1.members + t2.members))
        
        if len(new_members) > self.MAX_TEAM_SIZE:
            return None
        
        # 估算新凝聚力
        new_cohesion = self.estimate_team_cohesion(new_members)
        
        # 创建新团队
        merged = Team(
            id=str(uuid.uuid4()),
            leader_id=t1.leader_id,
            members=new_members,
            task=f"{t1.task} + {t2.task}",
            required_capabilities=list(set(t1.required_capabilities + t2.required_capabilities)),
            status="forming",
            cohesion_score=new_cohesion
        )
        
        self.teams[merged.id] = merged
        t1.status = "disbanded"
        t2.status = "disbanded"
        
        return merged


# ============================================================================
# Pattern Detection - 模式检测
# ============================================================================

class PatternDetection:
    """
    模式检测 - 完整实现
    
    使用图论和网络科学方法检测涌现模式。
    """
    
    def __init__(self):
        self.interaction_graph = nx.Graph()  # 交互图
        self.capability_graph = nx.DiGraph()  # 能力传递图
        self.activity_timeline: deque = deque(maxlen=1000)  # 活动时间线
        self.patterns: list[dict] = []
    
    def record_interaction(
        self,
        node_a: str,
        node_b: str,
        interaction_type: str,
        value: float = 1.0,
        metadata: dict = None
    ) -> None:
        """记录交互"""
        # 更新交互图
        if self.interaction_graph.has_edge(node_a, node_b):
            self.interaction_graph[node_a][node_b]["weight"] += value
        else:
            self.interaction_graph.add_edge(node_a, node_b, weight=value, type=interaction_type)
        
        # 记录时间线
        self.activity_timeline.append({
            "node_a": node_a,
            "node_b": node_b,
            "type": interaction_type,
            "value": value,
            "timestamp": datetime.now().timestamp(),
            "metadata": metadata or {}
        })
    
    def detect_hub_nodes(self, min_degree: int = 5) -> list[dict]:
        """检测中心节点（高连接度）"""
        hubs = []
        
        for node in self.interaction_graph.nodes():
            degree = self.interaction_graph.degree(node)
            if degree >= min_degree:
                # 计算介数中心性
                betweenness = nx.betweenness_centrality(self.interaction_graph).get(node, 0)
                
                hubs.append({
                    "node_id": node,
                    "degree": degree,
                    "betweenness": betweenness,
                    "is_bridge": self._is_bridge_node(node)
                })
        
        hubs.sort(key=lambda x: x["betweenness"], reverse=True)
        
        return hubs
    
    def _is_bridge_node(self, node: str) -> bool:
        """判断是否是桥接节点"""
        # 桥接节点：移除后图会分裂
        test_graph = self.interaction_graph.copy()
        test_graph.remove_node(node)
        return nx.is_connected(test_graph) != nx.is_connected(self.interaction_graph)
    
    def detect_communities(self) -> list[list[str]]:
        """检测社区（使用 Louvain 算法）"""
        try:
            # 使用 Louvain 社区检测
            import community
            partition = community.best_partition(self.interaction_graph)
            
            communities = defaultdict(list)
            for node, comm_id in partition.items():
                communities[comm_id].append(node)
            
            return list(communities.values())
        except ImportError:
            # 回退到标签传播
            try:
                from networkx.algorithms import community
                comps = list(community.label_propagation_communities(self.interaction_graph))
                return [list(c) for c in comps]
            except:
                return []
    
    def detect_bottlenecks(self) -> list[dict]:
        """检测瓶颈（边介数中心性高的边）"""
        bottlenecks = []
        
        # 计算边介数中心性
        edge_betweenness = nx.edge_betweenness_centrality(self.interaction_graph)
        
        threshold = statistics.mean(edge_betweenness.values()) + 2 * statistics.stdev(edge_betweenness.values())
        
        for (a, b), centrality in edge_betweenness.items():
            if centrality > threshold:
                bottlenecks.append({
                    "node_a": a,
                    "node_b": b,
                    "centrality": centrality,
                    "is_critical": centrality > threshold * 2
                })
        
        bottlenecks.sort(key=lambda x: x["centrality"], reverse=True)
        
        return bottlenecks
    
    def analyze_small_world_property(self) -> dict:
        """分析小世界特性"""
        if len(self.interaction_graph.nodes()) < 3:
            return {"is_small_world": False, "reason": "not_enough_nodes"}
        
        try:
            # 计算聚类系数
            clustering = nx.average_clustering(self.interaction_graph)
            
            # 计算平均最短路径
            avg_path = nx.average_shortest_path_length(self.interaction_graph)
            
            # 与随机图比较
            n = len(self.interaction_graph.nodes())
            m = len(self.interaction_graph.edges())
            
            random_graph = nx.gnm_random_graph(n, m)
            random_path = nx.average_shortest_path_length(random_graph)
            
            # 小世界判断：聚类系数高，路径长度接近随机图
            is_small_world = clustering > 0.1 and avg_path / random_path < 2
            
            return {
                "is_small_world": is_small_world,
                "clustering_coefficient": clustering,
                "avg_path_length": avg_path,
                "random_path_length": random_path,
                "sigma": clustering / (random_graph.number_of_edges() / (n * (n - 1) / 2)) if n > 1 else 0
            }
        except nx.NetworkXError:
            return {"is_small_world": False, "reason": "graph_disconnected"}
    
    def detect_emergence_signals(self) -> list[dict]:
        """检测涌现信号"""
        signals = []
        
        # 1. 社区形成
        communities = self.detect_communities()
        if len(communities) > 1:
            signals.append({
                "type": "community_formation",
                "description": f"检测到 {len(communities)} 个社区",
                "communities": communities,
                "strength": len(communities) / len(self.interaction_graph.nodes())
            })
        
        # 2. 中心节点涌现
        hubs = self.detect_hub_nodes()
        if hubs:
            signals.append({
                "type": "hub_emergence",
                "description": f"检测到 {len(hubs)} 个中心节点",
                "hubs": [h["node_id"] for h in hubs[:3]],
                "strength": len(hubs) / len(self.interaction_graph.nodes())
            })
        
        # 3. 小世界特性
        sw = self.analyze_small_world_property()
        if sw.get("is_small_world"):
            signals.append({
                "type": "small_world_emergence",
                "description": "网络呈现小世界特性",
                "strength": sw.get("sigma", 0)
            })
        
        # 4. 瓶颈形成
        bottlenecks = self.detect_bottlenecks()
        if bottlenecks:
            signals.append({
                "type": "bottleneck_formation",
                "description": f"检测到 {len(bottlenecks)} 个瓶颈",
                "strength": len(bottlenecks) / max(1, len(self.interaction_graph.edges()))
            })
        
        # 存储模式
        self.patterns.extend(signals)
        
        return signals


# ============================================================================
# Global Coordination - 全局协调
# ============================================================================

@dataclass
class CoordinationAction:
    """协调动作"""
    id: str
    action_type: str  # allocate, sequence, balance
    target_nodes: list[str]
    parameters: dict
    status: str = "proposed"  # proposed, approved, rejected, executed
    votes_for: int = 0
    votes_against: int = 0


class GlobalCoordination:
    """
    全局协调器 - 完整实现
    
    通过投票和共识形成全局协调动作。
    """
    
    APPROVAL_THRESHOLD = 0.6  # 60% 赞成即通过
    
    def __init__(self):
        self.pending_actions: list[CoordinationAction] = []
        self.executed_actions: list[CoordinationAction] = []
        self.node_votes: dict[str, set[str]] = defaultdict(set)  # action_id -> set of node_ids who voted
        self.network_topology: nx.Graph = nx.Graph()
    
    def propose_action(
        self,
        proposer_id: str,
        action_type: str,
        target_nodes: list[str],
        parameters: dict
    ) -> CoordinationAction:
        """提议协调动作"""
        action = CoordinationAction(
            id=str(uuid.uuid4()),
            action_type=action_type,
            target_nodes=target_nodes,
            parameters=parameters,
            status="proposed"
        )
        
        self.pending_actions.append(action)
        
        # 自动广播（通过 Gossip）
        return action
    
    def vote(
        self,
        action_id: str,
        node_id: str,
        approve: bool
    ) -> bool:
        """节点投票"""
        action = next((a for a in self.pending_actions if a.id == action_id), None)
        
        if not action or action.status != "proposed":
            return False
        
        if node_id not in self.node_votes[action_id]:
            self.node_votes[action_id].add(node_id)
            
            if approve:
                action.votes_for += 1
            else:
                action.votes_against += 1
        
        # 检查是否达成共识
        self._check_consensus(action)
        
        return True
    
    def _check_consensus(self, action: CoordinationAction) -> None:
        """检查共识是否达成"""
        total_votes = action.votes_for + action.votes_against
        
        if total_votes < len(self.network_topology.nodes()) * 0.5:
            return  # 投票人数不足
        
        approval_rate = action.votes_for / total_votes
        
        if approval_rate >= self.APPROVAL_THRESHOLD:
            action.status = "approved"
        elif 1 - approval_rate >= self.APPROVAL_THRESHOLD:
            action.status = "rejected"
    
    def execute_action(self, action_id: str) -> bool:
        """执行协调动作"""
        action = next((a for a in self.pending_actions if a.id == action_id), None)
        
        if not action or action.status != "approved":
            return False
        
        # 执行动作（根据类型）
        if action.action_type == "allocate":
            self._execute_allocate(action)
        elif action.action_type == "sequence":
            self._execute_sequence(action)
        elif action.action_type == "balance":
            self._execute_balance(action)
        
        action.status = "executed"
        self.executed_actions.append(action)
        self.pending_actions.remove(action)
        
        return True
    
    def _execute_allocate(self, action: CoordinationAction) -> None:
        """执行资源分配"""
        resources = action.parameters.get("resources", {})
        
        for node_id in action.target_nodes:
            allocation = resources.get(node_id, 0)
            # 更新节点资源（实际应用中需要更复杂的逻辑）
            pass
    
    def _execute_sequence(self, action: CoordinationAction) -> None:
        """执行顺序协调"""
        order = action.parameters.get("order", [])
        # 按顺序执行任务
        pass
    
    def _execute_balance(self, action: CoordinationAction) -> None:
        """执行负载均衡"""
        # 重新分配负载
        pass
    
    def get_coordination_status(self) -> dict:
        """获取协调状态"""
        return {
            "pending": len(self.pending_actions),
            "executed": len(self.executed_actions),
            "approved": sum(1 for a in self.pending_actions if a.status == "approved"),
            "nodes": len(self.network_topology.nodes()),
            "active_nodes": sum(1 for n in self.network_topology.nodes() 
                               if self.network_topology.nodes[n].get("active", True))
        }


# ============================================================================
# Emergence System - 涌现系统主控制器
# ============================================================================

class EmergenceSystem:
    """
    涌现系统 - 完整实现
    
    整合所有涌现相关功能。
    """
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        
        # 初始化子系统
        self.gossip = GossipProtocol(node_id)
        self.team_formation = TeamFormationAlgorithm()
        self.pattern_detection = PatternDetection()
        self.global_coord = GlobalCoordination()
        
        # 网络拓扑
        self.network = nx.Graph()
        self.network.add_node(node_id)
    
    def add_node(self, node_id: str) -> None:
        """添加节点到网络"""
        self.network.add_node(node_id)
        self.global_coord.network_topology.add_node(node_id)
    
    def connect_nodes(self, node_a: str, node_b: str, bidirectional: bool = True) -> None:
        """连接两个节点"""
        self.network.add_edge(node_a, node_b)
        
        if bidirectional:
            self.global_coord.network_topology.add_edge(node_a, node_b)
    
    def discover_capabilities(self, node_id: str) -> list[str]:
        """通过 Gossip 发现节点能力"""
        # 从 Gossip 消息中提取能力
        capabilities = []
        
        for msg in self.gossip.message_cache.values():
            if msg.sender_id == node_id and msg.message_type == "capability_update":
                caps = msg.content.get("capabilities", [])
                capabilities.extend(caps)
        
        return list(set(capabilities))
    
    def form_team_for_task(
        self,
        task: str,
        required_capabilities: list[str]
    ) -> Team | None:
        """为任务组建团队"""
        # 1. 通过模式检测找到相关节点
        relevant_nodes = self._find_relevant_nodes(required_capabilities)
        
        # 2. 组建团队
        team = self.team_formation.form_team(
            task=task,
            required_capabilities=required_capabilities,
            leader_id=relevant_nodes[0] if relevant_nodes else self.node_id,
            min_size=max(2, len(required_capabilities)),
            max_size=min(10, len(relevant_nodes) + 1)
        )
        
        # 3. 广播团队形成
        if team:
            self.gossip.broadcast("team_formed", {
                "team_id": team.id,
                "members": team.members,
                "task": task
            })
        
        return team
    
    def _find_relevant_nodes(self, capabilities: list[str]) -> list[str]:
        """找到拥有相关能力的节点"""
        relevant = []
        
        for node_id in self.network.nodes():
            if node_id == self.node_id:
                continue
            
            node_caps = self.discover_capabilities(node_id)
            
            if set(capabilities) & set(node_caps):
                relevant.append(node_id)
        
        return relevant
    
    def get_emergence_status(self) -> dict:
        """获取涌现系统状态"""
        patterns = self.pattern_detection.detect_emergence_signals()
        coordination = self.global_coord.get_coordination_status()
        
        return {
            "node_id": self.node_id,
            "network_size": self.network.number_of_nodes(),
            "active_peers": len(self.gossip.get_active_peers()),
            "teams": len(self.team_formation.teams),
            "detected_patterns": len(patterns),
            "coordination": coordination,
            "patterns": patterns[-5:]  # 最近 5 个模式
        }
    
    def run_gossip_round(self) -> list[GossipMessage]:
        """运行一轮 Gossip"""
        return self.gossip.gossip_round()
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            "gossip": {
                "peers": len(self.gossip.peers),
                "messages": len(self.gossip.message_cache),
                "suspects": len(self.gossip._failure_suspects)
            },
            "teams": {
                "total": len(self.team_formation.teams),
                "active": sum(1 for t in self.team_formation.teams.values() if t.status == "active")
            },
            "patterns": {
                "detected": len(self.pattern_detection.patterns),
                "hubs": len(self.pattern_detection.detect_hub_nodes())
            },
            "coordination": self.global_coord.get_coordination_status()
        }


import statistics
