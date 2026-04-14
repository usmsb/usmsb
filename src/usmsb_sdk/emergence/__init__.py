# -*- coding: utf-8 -*-
"""
Phase 4: Emergence System Layer

USMSB 涌现系统模块。

功能：
- Gossip 协议
- 动态组队
- 模式检测
- 全局协调
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class GossipMessage:
    """Gossip 消息"""
    id: str
    sender_id: str
    message_type: str  # capability, opportunity, state
    content: dict
    ttl: int = 3
    visited: list[str] = field(default_factory=list)


class GossipNode:
    """Gossip 节点"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.peers: list[str] = []
        self._messages: list[GossipMessage] = []
    
    def add_peer(self, peer_id: str) -> None:
        self.peers.append(peer_id)
    
    def broadcast(self, msg_type: str, content: dict) -> GossipMessage:
        msg = GossipMessage(
            id=str(uuid.uuid4()),
            sender_id=self.agent_id,
            message_type=msg_type,
            content=content,
            ttl=3,
            visited=[self.agent_id]
        )
        self._messages.append(msg)
        return msg


class EmergenceMonitor:
    """涌现监控"""
    
    def __init__(self):
        self._patterns: list[dict] = []
        self._teams: list[dict] = []
    
    def detect_pattern(self, agent_ids: list[str], pattern_type: str) -> dict:
        """检测模式"""
        pattern = {
            "id": str(uuid.uuid4()),
            "pattern_type": pattern_type,
            "agents": agent_ids,
            "detected_at": datetime.now().timestamp()
        }
        self._patterns.append(pattern)
        return pattern
    
    def get_patterns(self) -> list[dict]:
        return self._patterns


class TeamFormation:
    """动态组队"""
    
    def __init__(self):
        self._teams: list[dict] = []
    
    def form_team(self, leader_id: str, member_ids: list[str], task: str) -> dict:
        """形成团队"""
        team = {
            "id": str(uuid.uuid4()),
            "leader_id": leader_id,
            "members": [leader_id] + member_ids,
            "task": task,
            "status": "forming",
            "created_at": datetime.now().timestamp()
        }
        self._teams.append(team)
        return team
    
    def get_teams(self) -> list[dict]:
        return self._teams


class GlobalCoordination:
    """全局协调（涌现）"""
    
    def __init__(self):
        self._coordinations: list[dict] = []
    
    def coordinate(self, agents: list[str], action: str) -> dict:
        """协调行动"""
        coord = {
            "id": str(uuid.uuid4()),
            "agents": agents,
            "action": action,
            "created_at": datetime.now().timestamp()
        }
        self._coordinations.append(coord)
        return coord
    
    def get_coordinations(self) -> list[dict]:
        return self._coordinations


class EmergenceSystem:
    """
    涌现系统
    
    整合所有涌现功能。
    """
    
    def __init__(self):
        self.gossip = GossipNode("system")
        self.team_formation = TeamFormation()
        self.emergence_monitor = EmergenceMonitor()
        self.global_coord = GlobalCoordination()
    
    def get_stats(self) -> dict:
        return {
            "teams": len(self.team_formation.get_teams()),
            "patterns": len(self.emergence_monitor.get_patterns()),
            "coordinations": len(self.global_coord.get_coordinations())
        }
