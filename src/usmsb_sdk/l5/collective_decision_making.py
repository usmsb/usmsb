# -*- coding: utf-8 -*-
"""
CollectiveDecisionMaking - L5 集体决策

多个 Agent 协作做出决策的系统。

核心能力：
- 提案收集：从多个 Agent 收集提案
- 多轮协商：迭代优化提案
- 共识达成：达到集体共识
- 支持度计算：评估决策质量
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable


class DecisionStatus(Enum):
    """决策状态"""
    PENDING = "pending"          # 待处理
    DELIBERATING = "deliberating"  # 协商中
    CONSENSUS = "consensus"      # 达成共识
    VOTING = "voting"            # 投票中
    DECIDED = "decided"          # 已决定
    FAILED = "failed"            # 失败


class ConsensusType(Enum):
    """共识类型"""
    UNANIMOUS = "unanimous"      # 全票一致
    STRONG = "strong"           # 强共识 (>75%)
    WEAK = "weak"               # 弱共识 (>50%)
    MAJORITY = "majority"       # 多数 (>50%)


@dataclass
class DecisionTopic:
    """决策话题"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    proposer: str = ""  # 提出者
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    deadline: float | None = None
    urgency: float = 0.5  # 0.0 - 1.0
    tags: list[str] = field(default_factory=list)


@dataclass
class Proposal:
    """提案"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic_id: str = ""
    proposer: str = ""
    content: Any = None
    rationale: str = ""
    support_score: float = 0.0
    opposition_score: float = 0.0
    votes_for: list[str] = field(default_factory=list)
    votes_against: list[str] = field(default_factory=list)
    abstentions: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    round: int = 0  # 协商轮次
    evolution_history: list[dict] = field(default_factory=list)  # 演化历史


@dataclass
class Evaluation:
    """评估"""
    evaluator: str
    proposal_id: str
    score: float  # -1.0 到 1.0
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class CollectiveDecision:
    """集体决策"""
    topic: DecisionTopic
    proposal: Proposal
    support_rate: float  # 支持率
    consensus_type: ConsensusType
    rounds_needed: int
    participating_agents: list[str]
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    
    # 额外信息
    rejected_proposals: list[Proposal] = field(default_factory=list)
    final_suggestions: list[str] = field(default_factory=list)


@dataclass
class SupportMatrix:
    """支持矩阵"""
    matrix: dict[str, dict[str, float]] = field(default_factory=dict)  # agent -> proposal -> support
    
    def add_support(self, agent: str, proposal: str, score: float) -> None:
        if agent not in self.matrix:
            self.matrix[agent] = {}
        self.matrix[agent][proposal] = score
    
    def get_proposal_support(self, proposal: str) -> float:
        scores = [s for s in self.matrix.values() if proposal in s]
        if not scores:
            return 0.0
        return sum(s[proposal] for s in scores) / len(scores)
    
    def get_agent_support(self, agent: str) -> dict[str, float]:
        return self.matrix.get(agent, {})


class CollectiveDecisionMaking:
    """
    集体决策引擎
    
    通过多轮协商达成集体决策。
    """
    
    def __init__(
        self,
        collective_id: str = "collective_001",
        max_rounds: int = 10,
        consensus_threshold: float = 0.75
    ):
        self.collective_id = collective_id
        self.max_rounds = max_rounds
        self.consensus_threshold = consensus_threshold
        
        # 活跃决策
        self.active_decisions: dict[str, dict] = {}
        
        # 支持矩阵
        self.support_matrix = SupportMatrix()
        
        # 历史决策
        self.decision_history: list[CollectiveDecision] = []
        
        # 统计
        self.stats = {
            "total_decisions": 0,
            "consensus_reached": 0,
            "failed_decisions": 0,
            "avg_rounds": 0.0,
        }
        
        print(f"[CollectiveDecisionMaking] Initialized for {collective_id}")
    
    async def reach_consensus(
        self,
        topic: DecisionTopic,
        agents: list[Any],  # Agent objects
        evaluate_fn: Callable[[Any, Proposal], Evaluation] | None = None
    ) -> CollectiveDecision:
        """
        达成共识
        
        Args:
            topic: 决策话题
            agents: 参与的 Agent 列表
            evaluate_fn: 评估函数
            
        Returns:
            CollectiveDecision: 集体决策
        """
        print(f"[CollectiveDecisionMaking] Starting consensus for: {topic.title}")
        
        # 收集提案
        proposals = await self._collect_proposals(topic, agents)
        
        if not proposals:
            return await self._create_failed_decision(topic, agents, "No proposals")
        
        # 多轮协商
        for round_num in range(self.max_rounds):
            topic.round = round_num + 1
            print(f"[CollectiveDecisionMaking] Round {round_num + 1}/{self.max_rounds}")
            
            # 收集评估
            evaluations = await self._collect_evaluations(proposals, agents, evaluate_fn)
            
            # 更新支持矩阵
            await self._update_support_matrix(proposals, evaluations)
            
            # 计算支持率
            support_rates = self._calculate_support_rates(proposals)
            
            # 检查是否达成共识
            leading_proposal_id, support_rate = self._get_leading_proposal(proposals, support_rates)
            
            if support_rate >= self.consensus_threshold:
                # 达成共识
                leading_proposal = next(p for p in proposals if p.id == leading_proposal_id)
                decision = CollectiveDecision(
                    topic=topic,
                    proposal=leading_proposal,
                    support_rate=support_rate,
                    consensus_type=ConsensusType.STRONG if support_rate > 0.9 else ConsensusType.CONSENSUS,
                    rounds_needed=round_num + 1,
                    participating_agents=[a.agent_id for a in agents],
                )
                self._finalize_decision(decision)
                return decision
            
            # 演化提案
            proposals = await self._evolve_proposals(
                proposals,
                evaluations,
                support_rates
            )
        
        # 未达成强共识，返回最接受的
        leading_proposal_id, support_rate = self._get_leading_proposal(proposals, support_rates)
        leading_proposal = next(p for p in proposals if p.id == leading_proposal_id)
        
        decision = CollectiveDecision(
            topic=topic,
            proposal=leading_proposal,
            support_rate=support_rate,
            consensus_type=ConsensusType.WEAK,
            rounds_needed=self.max_rounds,
            participating_agents=[a.agent_id for a in agents],
        )
        
        self._finalize_decision(decision)
        return decision
    
    async def _collect_proposals(
        self,
        topic: DecisionTopic,
        agents: list[Any]
    ) -> list[Proposal]:
        """收集提案"""
        proposals = []
        
        for agent in agents:
            try:
                # 尝试让 Agent 生成提案
                if hasattr(agent, 'generate_proposal'):
                    proposal_content = await agent.generate_proposal(topic)
                else:
                    # 简化：生成随机提案
                    proposal_content = {
                        "action": f"Action by {agent.agent_id}",
                        "resource_allocation": 0.5
                    }
                
                proposal = Proposal(
                    topic_id=topic.id,
                    proposer=agent.agent_id,
                    content=proposal_content,
                    rationale=f"Proposal from {agent.agent_id}",
                    round=0
                )
                proposals.append(proposal)
                
            except Exception as e:
                print(f"[CollectiveDecisionMaking] Error collecting proposal from {agent.agent_id}: {e}")
        
        return proposals
    
    async def _collect_evaluations(
        self,
        proposals: list[Proposal],
        agents: list[Any],
        evaluate_fn: Callable | None
    ) -> list[Evaluation]:
        """收集评估"""
        evaluations = []
        
        for agent in agents:
            for proposal in proposals:
                try:
                    if evaluate_fn:
                        evaluation = await evaluate_fn(agent, proposal)
                    else:
                        # 简化评估
                        evaluation = Evaluation(
                            evaluator=agent.agent_id,
                            proposal_id=proposal.id,
                            score=0.5,  # 中立
                            strengths=["Clear intent"],
                            weaknesses=["Needs more detail"]
                        )
                    evaluations.append(evaluation)
                except Exception as e:
                    print(f"[CollectiveDecisionMaking] Error evaluating: {e}")
        
        return evaluations
    
    async def _update_support_matrix(
        self,
        proposals: list[Proposal],
        evaluations: list[Evaluation]
    ) -> None:
        """更新支持矩阵"""
        for eval in evaluations:
            self.support_matrix.add_support(
                eval.evaluator,
                eval.proposal_id,
                (eval.score + 1) / 2  # 转换到 0-1
            )
    
    def _calculate_support_rates(self, proposals: list[Proposal]) -> dict[str, float]:
        """计算支持率"""
        rates = {}
        for proposal in proposals:
            rates[proposal.id] = self.support_matrix.get_proposal_support(proposal.id)
        return rates
    
    def _get_leading_proposal(
        self,
        proposals: list[Proposal],
        support_rates: dict[str, float]
    ) -> tuple[str, float]:
        """获取领先提案"""
        if not proposals:
            return "", 0.0
        
        best = max(proposals, key=lambda p: support_rates.get(p.id, 0))
        return best.id, support_rates.get(best.id, 0)
    
    async def _evolve_proposals(
        self,
        proposals: list[Proposal],
        evaluations: list[Evaluation],
        support_rates: dict[str, float]
    ) -> list[Proposal]:
        """基于反馈演化提案"""
        evolved = []
        
        for proposal in proposals:
            # 收集反馈
            proposal_evals = [e for e in evaluations if e.proposal_id == proposal.id]
            
            if not proposal_evals:
                evolved.append(proposal)
                continue
            
            # 提取建议
            all_suggestions = []
            for eval in proposal_evals:
                all_suggestions.extend(eval.suggestions)
            
            # 创建演化版本
            evolved_proposal = Proposal(
                topic_id=proposal.topic_id,
                proposer=proposal.proposer,
                content={
                    **({} if isinstance(proposal.content, dict) else {"content": proposal.content}),
                    "evolved_from": proposal.id,
                    "improvements": all_suggestions[:3]
                },
                rationale=f"{proposal.rationale} (evolved round {proposal.round + 1})",
                support_score=support_rates.get(proposal.id, 0),
                round=proposal.round + 1,
                evolution_history=proposal.evolution_history + [
                    {"round": proposal.round, "score": support_rates.get(proposal.id, 0)}
                ]
            )
            evolved.append(evolved_proposal)
        
        return evolved
    
    async def _create_failed_decision(
        self,
        topic: DecisionTopic,
        agents: list[Any],
        reason: str
    ) -> CollectiveDecision:
        """创建失败决策"""
        self.stats["failed_decisions"] += 1
        
        return CollectiveDecision(
            topic=topic,
            proposal=Proposal(
                topic_id=topic.id,
                content={"error": reason}
            ),
            support_rate=0.0,
            consensus_type=ConsensusType.WEAK,
            rounds_needed=0,
            participating_agents=[a.agent_id for a in agents],
        )
    
    def _finalize_decision(self, decision: CollectiveDecision) -> None:
        """最终化决策"""
        self.decision_history.append(decision)
        self.stats["total_decisions"] += 1
        self.stats["consensus_reached"] += 1
        
        if self.decision_history:
            total_rounds = sum(d.rounds_needed for d in self.decision_history)
            self.stats["avg_rounds"] = total_rounds / len(self.decision_history)
        
        print(f"[CollectiveDecisionMaking] Decision reached: {decision.consensus_type.value} ({decision.support_rate:.2%})")
    
    def get_active_decisions(self) -> list[dict]:
        """获取活跃决策"""
        return list(self.active_decisions.values())
    
    def get_decision_history(self) -> list[CollectiveDecision]:
        """获取决策历史"""
        return self.decision_history
    
    def get_statistics(self) -> dict:
        """获取统计"""
        return {
            "collective_id": self.collective_id,
            "total_decisions": self.stats["total_decisions"],
            "consensus_reached": self.stats["consensus_reached"],
            "failed": self.stats["failed_decisions"],
            "avg_rounds": self.stats["avg_rounds"],
            "active_decisions": len(self.active_decisions),
        }
    
    def to_dict(self) -> dict:
        return self.get_statistics()
