"""
EmergentGovernance - 涌现治理

从 Agent 交互中涌现出治理规则。

核心功能：
- 规则提案
- 规则投票
- 规则执行
- 规则演化
"""

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class RuleState(Enum):
    """规则状态"""
    PROPOSED = "proposed"       # 提议中
    ACTIVE = "active"           # 生效中
    REJECTED = "rejected"       # 被拒绝
    EXPIRED = "expired"         # 已过期
    SUPERSEDED = "superseded"  # 被取代


class RuleType(Enum):
    """规则类型"""
    RESOURCE_ALLOCATION = "resource_allocation"  # 资源分配
    CONFLICT_RESOLUTION = "conflict_resolution"  # 冲突解决
    REPUTATION = "reputation"  # 声誉规则
    REPLICATION = "replication"  # 复制规则
    COLLABORATION = "collaboration"  # 协作规则
    CUSTOM = "custom"  # 自定义规则


@dataclass
class Rule:
    """治理规则"""
    id: str
    name: str
    description: str
    rule_type: RuleType
    content: dict  # 规则内容
    proposer_id: str
    state: RuleState
    votes_for: list[str] = field(default_factory=list)
    votes_against: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    activated_at: float | None = None
    expires_at: float | None = None
    superseded_by: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class GovernanceEvent:
    """治理事件"""
    id: str
    event_type: str  # proposal, vote, activation, violation, etc.
    rule_id: str | None
    agent_id: str | None
    description: str
    timestamp: float


class RuleRegistry:
    """规则注册表"""
    
    def __init__(self):
        self._rules: dict[str, Rule] = {}
        self._rules_by_type: dict[RuleType, list[str]] = defaultdict(list)
    
    def register_rule(self, rule: Rule) -> None:
        """注册规则"""
        self._rules[rule.id] = rule
        self._rules_by_type[rule.rule_type].append(rule.id)
    
    def get_rule(self, rule_id: str) -> Rule | None:
        """获取规则"""
        return self._rules.get(rule_id)
    
    def get_active_rules(self) -> list[Rule]:
        """获取所有活跃规则"""
        return [
            rule for rule in self._rules.values()
            if rule.state == RuleState.ACTIVE
        ]
    
    def get_rules_by_type(self, rule_type: RuleType) -> list[Rule]:
        """按类型获取规则"""
        return [
            self._rules[rid] for rid in self._rules_by_type.get(rule_type, [])
            if rid in self._rules
        ]
    
    def update_rule_state(
        self,
        rule_id: str,
        new_state: RuleState
    ) -> bool:
        """更新规则状态"""
        if rule_id not in self._rules:
            return False
        
        rule = self._rules[rule_id]
        rule.state = new_state
        
        if new_state == RuleState.ACTIVE:
            rule.activated_at = datetime.now().timestamp()
        
        return True


class VotingMechanism:
    """投票机制"""
    
    def __init__(
        self,
        approval_threshold: float = 0.6,
        participation_threshold: float = 0.5
    ):
        self.approval_threshold = approval_threshold  # 60% 赞成
        self.participation_threshold = participation_threshold  # 50% 参与
    
    def count_votes(self, rule: Rule, total_eligible: int) -> tuple[bool, float]:
        """
        统计投票
        
        Args:
            rule: 规则
            total_eligible: 符合资格的投票者总数
            
        Returns:
            (passed, participation_rate)
        """
        total_votes = len(rule.votes_for) + len(rule.votes_against)
        
        # 计算参与率
        participation = total_votes / total_eligible if total_eligible > 0 else 0
        
        # 检查参与率
        if participation < self.participation_threshold:
            return False, participation
        
        # 计算赞成率
        approval_rate = len(rule.votes_for) / total_votes if total_votes > 0 else 0
        
        passed = approval_rate >= self.approval_threshold
        
        return passed, participation


class RuleEvolution:
    """规则演化"""
    
    def __init__(self):
        self._rule_history: dict[str, list[str]] = defaultdict(list)
    
    def should_evolve(
        self,
        rule: Rule,
        violation_count: int,
        age_seconds: float
    ) -> bool:
        """
        判断规则是否应该演化
        
        Args:
            rule: 规则
            violation_count: 违规次数
            age_seconds: 规则年龄（秒）
            
        Returns:
            bool: 是否应该演化
        """
        # 规则太新，不演化
        if age_seconds < 86400:  # 不到 1 天
            return False
        
        # 违规率过高，需要演化
        if age_seconds > 0:
            violation_rate = violation_count / (age_seconds / 86400)  # 每天违规数
            if violation_rate > 5:  # 每天超过 5 次违规
                return True
        
        # 规则太老，需要更新
        if age_seconds > 30 * 86400:  # 超过 30 天
            return True
        
        return False
    
    def propose_evolution(
        self,
        original_rule: Rule,
        proposer_id: str,
        changes: dict
    ) -> Rule:
        """
        提出规则演化
        
        Args:
            original_rule: 原规则
            proposer_id: 提议者 ID
            changes: 变更内容
            
        Returns:
            Rule: 新规则
        """
        new_rule = Rule(
            id=str(uuid.uuid4()),
            name=f"{original_rule.name}_v2",
            description=original_rule.description,
            rule_type=original_rule.rule_type,
            content={**original_rule.content, **changes},
            proposer_id=proposer_id,
            state=RuleState.PROPOSED,
            metadata={
                "evolved_from": original_rule.id,
                "changes": changes
            }
        )
        
        # 记录历史
        self._rule_history[original_rule.id].append(new_rule.id)
        
        return new_rule


class EmergentGovernance:
    """
    涌现治理主控制器
    
    从 Agent 交互中涌现出治理规则。
    
    使用方式：
    ```python
    governance = EmergentGovernance()
    
    # 提案新规则
    rule_id = governance.propose_rule(
        proposer_id="agent_001",
        rule_type=RuleType.RESOURCE_ALLOCATION,
        name="资源分配规则",
        content={"max_resource_request": 100}
    )
    
    # Agent 投票
    governance.vote(rule_id, "agent_002", True)
    governance.vote(rule_id, "agent_003", True)
    
    # 检查是否通过
    if governance.check_approval(rule_id):
        governance.activate_rule(rule_id)
    ```
    """
    
    def __init__(
        self,
        approval_threshold: float = 0.6,
        participation_threshold: float = 0.5
    ):
        self.registry = RuleRegistry()
        self.voting = VotingMechanism(approval_threshold, participation_threshold)
        self.evolution = RuleEvolution()
        
        # 事件日志
        self._events: list[GovernanceEvent] = []
        
        # 违规记录
        self._violations: dict[str, list[GovernanceEvent]] = defaultdict(list)
        
        # 注册的 Agent
        self._registered_agents: set[str] = set()
    
    def register_agent(self, agent_id: str) -> None:
        """注册 Agent"""
        self._registered_agents.add(agent_id)
    
    def unregister_agent(self, agent_id: str) -> None:
        """注销 Agent"""
        self._registered_agents.discard(agent_id)
    
    def propose_rule(
        self,
        proposer_id: str,
        rule_type: RuleType,
        name: str,
        description: str,
        content: dict,
        expires_in: float | None = None
    ) -> str:
        """
        提案新规则
        
        Args:
            proposer_id: 提议者 ID
            rule_type: 规则类型
            name: 规则名称
            description: 规则描述
            content: 规则内容
            expires_in: 过期时间（秒）
            
        Returns:
            str: 规则 ID
        """
        rule_id = str(uuid.uuid4())
        
        rule = Rule(
            id=rule_id,
            name=name,
            description=description,
            rule_type=rule_type,
            content=content,
            proposer_id=proposer_id,
            state=RuleState.PROPOSED,
        )
        
        if expires_in:
            rule.expires_at = datetime.now().timestamp() + expires_in
        
        self.registry.register_rule(rule)
        
        # 记录事件
        self._log_event(
            event_type="proposal",
            rule_id=rule_id,
            agent_id=proposer_id,
            description=f"Proposed rule: {name}"
        )
        
        return rule_id
    
    def vote(self, rule_id: str, voter_id: str, approve: bool) -> bool:
        """
        投票
        
        Args:
            rule_id: 规则 ID
            voter_id: 投票者 ID
            approve: 是否赞成
            
        Returns:
            bool: 投票是否成功
        """
        rule = self.registry.get_rule(rule_id)
        if not rule:
            return False
        
        if rule.state != RuleState.PROPOSED:
            return False
        
        # 移除之前的投票
        if voter_id in rule.votes_for:
            rule.votes_for.remove(voter_id)
        if voter_id in rule.votes_against:
            rule.votes_against.remove(voter_id)
        
        # 记录新投票
        if approve:
            rule.votes_for.append(voter_id)
        else:
            rule.votes_against.append(voter_id)
        
        # 记录事件
        self._log_event(
            event_type="vote",
            rule_id=rule_id,
            agent_id=voter_id,
            description=f"Voted {'for' if approve else 'against'}: {rule.name}"
        )
        
        return True
    
    def check_approval(self, rule_id: str) -> bool:
        """
        检查规则是否通过
        
        Args:
            rule_id: 规则 ID
            
        Returns:
            bool: 是否通过
        """
        rule = self.registry.get_rule(rule_id)
        if not rule:
            return False
        
        passed, participation = self.voting.count_votes(
            rule,
            len(self._registered_agents)
        )
        
        if passed:
            rule.state = RuleState.ACTIVE
            rule.activated_at = datetime.now().timestamp()
            
            self._log_event(
                event_type="activation",
                rule_id=rule_id,
                agent_id=None,
                description=f"Rule activated: {rule.name}"
            )
        
        return passed
    
    def activate_rule(self, rule_id: str) -> bool:
        """激活规则"""
        rule = self.registry.get_rule(rule_id)
        if not rule:
            return False
        
        rule.state = RuleState.ACTIVE
        rule.activated_at = datetime.now().timestamp()
        
        self._log_event(
            event_type="activation",
            rule_id=rule_id,
            agent_id=None,
            description=f"Rule activated: {rule.name}"
        )
        
        return True
    
    def check_violation(self, rule_id: str, agent_id: str) -> bool:
        """
        检查违规
        
        Args:
            rule_id: 规则 ID
            agent_id: Agent ID
            
        Returns:
            bool: 是否违规
        """
        rule = self.registry.get_rule(rule_id)
        if not rule or rule.state != RuleState.ACTIVE:
            return False
        
        # 记录违规事件
        self._violations[rule_id].append(GovernanceEvent(
            id=str(uuid.uuid4()),
            event_type="violation",
            rule_id=rule_id,
            agent_id=agent_id,
            description=f"Violation of rule: {rule.name}",
            timestamp=datetime.now().timestamp()
        ))
        
        return True
    
    def get_violation_count(self, rule_id: str) -> int:
        """获取违规次数"""
        return len(self._violations.get(rule_id, []))
    
    def evolve_rule_if_needed(self, rule_id: str) -> str | None:
        """
        如果需要，演化规则
        
        Args:
            rule_id: 规则 ID
            
        Returns:
            str: 新规则 ID 或 None
        """
        rule = self.registry.get_rule(rule_id)
        if not rule:
            return None
        
        age = datetime.now().timestamp() - rule.created_at
        violation_count = self.get_violation_count(rule_id)
        
        if self.evolution.should_evolve(rule, violation_count, age):
            # 建议修改（简化版：直接创建新规则）
            new_content = rule.content.copy()
            new_content["version"] = new_content.get("version", 1) + 1
            
            new_rule_id = self.propose_rule(
                proposer_id="governance_system",
                rule_type=rule.rule_type,
                name=f"{rule.name}_evolved",
                description=rule.description,
                content=new_content
            )
            
            # 标记旧规则为被取代
            rule.state = RuleState.SUPERSEDED
            rule.superseded_by = new_rule_id
            
            return new_rule_id
        
        return None
    
    def get_active_rules(self) -> list[Rule]:
        """获取活跃规则"""
        return self.registry.get_active_rules()
    
    def get_rules_by_type(self, rule_type: RuleType) -> list[Rule]:
        """按类型获取规则"""
        return self.registry.get_rules_by_type(rule_type)
    
    def get_proposed_rules(self) -> list[Rule]:
        """获取提议中的规则"""
        return [
            rule for rule in self.registry._rules.values()
            if rule.state == RuleState.PROPOSED
        ]
    
    def get_events(
        self,
        rule_id: str | None = None,
        limit: int = 100
    ) -> list[GovernanceEvent]:
        """获取治理事件"""
        events = self._events
        if rule_id:
            events = [e for e in events if e.rule_id == rule_id]
        return events[-limit:]
    
    def _log_event(
        self,
        event_type: str,
        rule_id: str | None,
        agent_id: str | None,
        description: str
    ) -> None:
        """记录事件"""
        event = GovernanceEvent(
            id=str(uuid.uuid4()),
            event_type=event_type,
            rule_id=rule_id,
            agent_id=agent_id,
            description=description,
            timestamp=datetime.now().timestamp()
        )
        self._events.append(event)
