"""
RoleNegotiation - 角色协商协议

Phase 4: 涌现系统层 - 核心模块

Agent 团队中的角色协商：
- 角色定义
- 能力匹配
- 协商机制
- 角色分配
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class RoleType(Enum):
    """角色类型"""
    LEADER = "leader"
    COORDINATOR = "coordinator"
    SPECIALIST = "specialist"
    SUPPORTER = "supporter"
    OBSERVER = "observer"


@dataclass
class Role:
    """角色"""
    name: str
    type: RoleType
    required_capabilities: list[str]
    responsibilities: list[str]
    authority_level: int  # 1-10
    max_holder: int = 1  # 最多几个 Agent 持有


@dataclass
class RoleBid:
    """角色竞价"""
    agent_id: str
    role_name: str
    bid_strength: float  # 0-1
    capabilities_match: float  # 0-1
    experience: int
    timestamp: float


@dataclass
class NegotiationResult:
    """协商结果"""
    role_name: str
    assigned_agent: str | None
    all_bids: list[RoleBid]
    winner_bid: RoleBid | None
    round: int


class RoleNegotiationProtocol:
    """
    角色协商协议
    
    在团队形成时协商角色分配：
    1. 定义角色需求
    2. Agent 竞价
    3. 评估竞价
    4. 分配角色
    """
    
    def __init__(self):
        self.roles: dict[str, Role] = {}
        self.pending_negotiations: dict[str, list[RoleBid]] = {}
        self.assigned_roles: dict[str, str] = {}  # role_name -> agent_id
    
    def define_team_roles(
        self,
        team_id: str,
        role_definitions: list[Role]
    ) -> None:
        """定义团队角色"""
        for role in role_definitions:
            self.roles[f"{team_id}:{role.name}"] = role
    
    def submit_bid(
        self,
        team_id: str,
        agent_id: str,
        role_name: str,
        agent_capabilities: list[str],
        experience: int = 0
    ) -> RoleBid:
        """提交角色竞价"""
        full_role_name = f"{team_id}:{role_name}"
        role = self.roles.get(full_role_name)
        
        if not role:
            raise ValueError(f"Role {role_name} not defined in team {team_id}")
        
        # 计算能力匹配度
        required = set(role.required_capabilities)
        available = set(agent_capabilities)
        match = len(required & available) / len(required) if required else 0
        
        # 计算竞价强度
        bid = RoleBid(
            agent_id=agent_id,
            role_name=role_name,
            bid_strength=0.5 + experience * 0.01 + match * 0.3,
            capabilities_match=match,
            experience=experience,
            timestamp=datetime.now().timestamp()
        )
        
        # 记录竞价
        if full_role_name not in self.pending_negotiations:
            self.pending_negotiations[full_role_name] = []
        self.pending_negotiations[full_role_name].append(bid)
        
        return bid
    
    def negotiate(self, team_id: str, role_name: str, max_rounds: int = 3) -> NegotiationResult:
        """执行协商"""
        full_role_name = f"{team_id}:{role_name}"
        bids = self.pending_negotiations.get(full_role_name, [])
        
        if not bids:
            return NegotiationResult(
                role_name=role_name,
                assigned_agent=None,
                all_bids=[],
                winner_bid=None,
                round=0
            )
        
        # 排序竞价（按强度）
        sorted_bids = sorted(bids, key=lambda x: x.bid_strength, reverse=True)
        
        # 选择最强竞价
        winner = sorted_bids[0]
        
        # 分配角色
        self.assigned_roles[full_role_name] = winner.agent_id
        
        return NegotiationResult(
            role_name=role_name,
            assigned_agent=winner.agent_id,
            all_bids=bids,
            winner_bid=winner,
            round=1  # 简化为单轮
        )
    
    def negotiate_all(self, team_id: str) -> list[NegotiationResult]:
        """协商所有角色"""
        team_roles = [k for k in self.roles.keys() if k.startswith(f"{team_id}:")]
        
        results = []
        for full_role_name in team_roles:
            role_name = full_role_name.split(":")[1]
            result = self.negotiate(team_id, role_name)
            results.append(result)
        
        return results
    
    def reassign_role(self, team_id: str, role_name: str, new_agent_id: str) -> bool:
        """重新分配角色"""
        full_role_name = f"{team_id}:{role_name}"
        
        if full_role_name not in self.roles:
            return False
        
        self.assigned_roles[full_role_name] = new_agent_id
        return True
    
    def get_role_assignment(self, team_id: str, role_name: str) -> str | None:
        """获取角色分配"""
        return self.assigned_roles.get(f"{team_id}:{role_name}")
    
    def get_team_assignments(self, team_id: str) -> dict[str, str]:
        """获取团队所有角色分配"""
        return {
            k.split(":")[1]: v
            for k, v in self.assigned_roles.items()
            if k.startswith(f"{team_id}:")
        }


# 预设角色模板
DEFAULT_ROLE_TEMPLATES = {
    "leader": Role(
        name="leader",
        type=RoleType.LEADER,
        required_capabilities=["coordination", "decision_making"],
        responsibilities=["制定目标", "分配任务", "监督进度"],
        authority_level=10,
        max_holder=1
    ),
    "coordinator": Role(
        name="coordinator",
        type=RoleType.COORDINATOR,
        required_capabilities=["communication", "planning"],
        responsibilities=["协调资源", "促进合作", "解决冲突"],
        authority_level=7,
        max_holder=2
    ),
    "specialist": Role(
        name="specialist",
        type=RoleType.SPECIALIST,
        required_capabilities=["expert_knowledge"],
        responsibilities=["提供专业意见", "执行关键任务"],
        authority_level=5,
        max_holder=5
    ),
    "supporter": Role(
        name="supporter",
        type=RoleType.SUPPORTER,
        required_capabilities=["collaboration"],
        responsibilities=["辅助其他角色", "提供支援"],
        authority_level=3,
        max_holder=10
    ),
}
