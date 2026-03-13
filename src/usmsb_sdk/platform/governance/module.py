"""
Governance Module

Module for decentralized governance including proposals, voting,
and decision execution.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ProposalStatus(str, Enum):
    """Status of a governance proposal."""
    DRAFT = "draft"
    ACTIVE = "active"
    PASSED = "passed"
    REJECTED = "rejected"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class VoteType(str, Enum):
    """Types of votes."""
    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"


class ProposalType(str, Enum):
    """Types of proposals."""
    PARAMETER_CHANGE = "parameter_change"
    TREASURY_SPEND = "treasury_spend"
    PROTOCOL_UPGRADE = "protocol_upgrade"
    COMMUNITY_GRANT = "community_grant"
    POLICY_CHANGE = "policy_change"
    GENERAL = "general"


@dataclass
class VotingPower:
    """Voting power for an agent."""
    agent_id: str
    token_balance: float = 0.0
    staked_tokens: float = 0.0
    reputation: float = 0.0
    delegations_received: float = 0.0
    delegations_given: str = ""  # agent_id delegated to

    @property
    def total_power(self) -> float:
        """Calculate total voting power."""
        base = self.token_balance + (self.staked_tokens * 1.5)  # Bonus for staked
        reputation_bonus = base * (self.reputation / 100)  # Up to 100% bonus
        delegated_bonus = self.delegations_received
        return base + reputation_bonus + delegated_bonus


@dataclass
class Vote:
    """A single vote on a proposal."""
    voter_id: str
    proposal_id: str
    vote_type: VoteType
    voting_power: float
    reason: Optional[str] = None
    timestamp: float = field(default_factory=lambda: time.time())


@dataclass
class Proposal:
    """A governance proposal."""
    id: str
    title: str
    description: str
    proposer_id: str
    type: ProposalType
    status: ProposalStatus = ProposalStatus.DRAFT
    parameters: Dict[str, Any] = field(default_factory=dict)
    voting_start: Optional[float] = None
    voting_end: Optional[float] = None
    quorum: float = 0.3  # 30% of total voting power
    threshold: float = 0.5  # 50% of votes must be yes
    votes: List[Vote] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())
    executed_at: Optional[float] = None
    execution_result: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_vote_counts(self) -> Dict[VoteType, float]:
        """Get vote counts by type."""
        counts = {VoteType.YES: 0.0, VoteType.NO: 0.0, VoteType.ABSTAIN: 0.0}
        for vote in self.votes:
            counts[vote.vote_type] += vote.voting_power
        return counts

    def get_total_voting_power(self) -> float:
        """Get total voting power that voted."""
        return sum(v.voting_power for v in self.votes)


class GovernanceModule:
    """
    Governance Module.

    Provides decentralized governance capabilities:
    - Proposal creation and management
    - Voting mechanisms
    - Delegation
    - Execution of passed proposals
    """

    def __init__(
        self,
        voting_period_hours: float = 72.0,
        default_quorum: float = 0.3,
        default_threshold: float = 0.5,
        min_proposal_stake: float = 100.0,
    ):
        """
        Initialize the Governance Module.

        Args:
            voting_period_hours: Default voting period in hours
            default_quorum: Default quorum requirement
            default_threshold: Default pass threshold
            min_proposal_stake: Minimum stake to create proposal
        """
        self.voting_period_hours = voting_period_hours
        self.default_quorum = default_quorum
        self.default_threshold = default_threshold
        self.min_proposal_stake = min_proposal_stake

        self._proposals: Dict[str, Proposal] = {}
        self._voting_powers: Dict[str, VotingPower] = {}
        self._total_voting_power: float = 0.0
        self._delegations: Dict[str, str] = {}  # delegator -> delegatee

        # Callbacks
        self.on_proposal_created: Optional[Callable[[Proposal], None]] = None
        self.on_proposal_passed: Optional[Callable[[Proposal], None]] = None
        self.on_proposal_rejected: Optional[Callable[[Proposal], None]] = None
        self.on_vote_cast: Optional[Callable[[Vote], None]] = None

    def register_voter(
        self,
        agent_id: str,
        token_balance: float = 0.0,
        staked_tokens: float = 0.0,
        reputation: float = 0.0,
    ) -> VotingPower:
        """
        Register a voter with their voting power.

        Args:
            agent_id: Agent ID
            token_balance: Token balance
            staked_tokens: Staked tokens
            reputation: Reputation score (0-100)

        Returns:
            Voting power record
        """
        power = VotingPower(
            agent_id=agent_id,
            token_balance=token_balance,
            staked_tokens=staked_tokens,
            reputation=reputation,
        )

        self._voting_powers[agent_id] = power
        self._recalculate_total_power()

        return power

    def update_voting_power(
        self,
        agent_id: str,
        token_balance: Optional[float] = None,
        staked_tokens: Optional[float] = None,
        reputation: Optional[float] = None,
    ) -> bool:
        """Update voting power for an agent."""
        power = self._voting_powers.get(agent_id)
        if not power:
            return False

        if token_balance is not None:
            power.token_balance = token_balance
        if staked_tokens is not None:
            power.staked_tokens = staked_tokens
        if reputation is not None:
            power.reputation = reputation

        self._recalculate_total_power()
        return True

    def _recalculate_total_power(self) -> None:
        """Recalculate total voting power."""
        self._total_voting_power = sum(
            p.total_power for p in self._voting_powers.values()
            if not p.delegations_given  # Exclude delegated power
        )

    def delegate(
        self,
        delegator_id: str,
        delegatee_id: str,
    ) -> bool:
        """
        Delegate voting power.

        Args:
            delegator_id: Agent delegating
            delegatee_id: Agent receiving delegation

        Returns:
            True if successful
        """
        if delegator_id not in self._voting_powers:
            return False
        if delegatee_id not in self._voting_powers:
            return False

        delegator = self._voting_powers[delegator_id]

        # Remove previous delegation
        if delegator.delegations_given:
            old_delegatee = self._voting_powers.get(delegator.delegations_given)
            if old_delegatee:
                old_delegatee.delegations_received -= delegator.total_power

        # Set new delegation
        delegator.delegations_given = delegatee_id
        delegatee = self._voting_powers[delegatee_id]
        delegatee.delegations_received += delegator.total_power

        self._delegations[delegator_id] = delegatee_id
        self._recalculate_total_power()

        logger.info(f"Voting power delegated: {delegator_id} -> {delegatee_id}")
        return True

    def create_proposal(
        self,
        title: str,
        description: str,
        proposer_id: str,
        type: ProposalType,
        parameters: Optional[Dict[str, Any]] = None,
        quorum: Optional[float] = None,
        threshold: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Proposal:
        """
        Create a new proposal.

        Args:
            title: Proposal title
            description: Proposal description
            proposer_id: Proposer agent ID
            type: Proposal type
            parameters: Proposal parameters
            quorum: Quorum requirement
            threshold: Pass threshold
            metadata: Additional metadata

        Returns:
            Created proposal
        """
        import uuid

        # Check proposer has minimum stake
        proposer_power = self._voting_powers.get(proposer_id)
        if not proposer_power or proposer_power.staked_tokens < self.min_proposal_stake:
            raise ValueError(f"Proposer must have at least {self.min_proposal_stake} staked tokens")

        proposal = Proposal(
            id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            proposer_id=proposer_id,
            type=type,
            parameters=parameters or {},
            quorum=quorum or self.default_quorum,
            threshold=threshold or self.default_threshold,
            metadata=metadata or {},
        )

        self._proposals[proposal.id] = proposal

        if self.on_proposal_created:
            self.on_proposal_created(proposal)

        logger.info(f"Proposal created: {title} (ID: {proposal.id})")
        return proposal

    def activate_proposal(
        self,
        proposal_id: str,
        voting_period_hours: Optional[float] = None,
    ) -> bool:
        """
        Activate a proposal for voting.

        Args:
            proposal_id: Proposal ID
            voting_period_hours: Voting period (uses default if None)

        Returns:
            True if successful
        """
        proposal = self._proposals.get(proposal_id)
        if not proposal or proposal.status != ProposalStatus.DRAFT:
            return False

        voting_hours = voting_period_hours or self.voting_period_hours
        proposal.status = ProposalStatus.ACTIVE
        proposal.voting_start = time.time()
        proposal.voting_end = proposal.voting_start + (voting_hours * 3600)
        proposal.updated_at = time.time()

        logger.info(f"Proposal {proposal_id} activated for voting")
        return True

    def cast_vote(
        self,
        proposal_id: str,
        voter_id: str,
        vote_type: VoteType,
        reason: Optional[str] = None,
    ) -> Optional[Vote]:
        """
        Cast a vote on a proposal.

        Args:
            proposal_id: Proposal ID
            voter_id: Voter ID
            vote_type: Type of vote
            reason: Optional reason

        Returns:
            Created vote or None
        """
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            raise ValueError("Proposal not found")

        if proposal.status != ProposalStatus.ACTIVE:
            raise ValueError("Proposal is not active for voting")

        if time.time() > proposal.voting_end:
            raise ValueError("Voting period has ended")

        # Check if already voted
        for v in proposal.votes:
            if v.voter_id == voter_id:
                raise ValueError("Already voted on this proposal")

        # Get voting power
        power = self._voting_powers.get(voter_id)
        if not power:
            raise ValueError("Voter not registered")

        # Check if delegated
        if power.delegations_given:
            raise ValueError(f"Voting power delegated to {power.delegations_given}")

        vote = Vote(
            voter_id=voter_id,
            proposal_id=proposal_id,
            vote_type=vote_type,
            voting_power=power.total_power,
            reason=reason,
        )

        proposal.votes.append(vote)
        proposal.updated_at = time.time()

        if self.on_vote_cast:
            self.on_vote_cast(vote)

        logger.info(f"Vote cast: {voter_id} voted {vote_type.value} on {proposal_id}")
        return vote

    def finalize_proposal(self, proposal_id: str) -> ProposalStatus:
        """
        Finalize a proposal after voting period.

        Args:
            proposal_id: Proposal ID

        Returns:
            Final status
        """
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            raise ValueError("Proposal not found")

        if proposal.status != ProposalStatus.ACTIVE:
            return proposal.status

        if time.time() < proposal.voting_end:
            raise ValueError("Voting period has not ended")

        counts = proposal.get_vote_counts()
        total_voted = proposal.get_total_voting_power()

        # Check quorum
        quorum_reached = total_voted >= (self._total_voting_power * proposal.quorum)

        if not quorum_reached:
            proposal.status = ProposalStatus.EXPIRED
            logger.info(f"Proposal {proposal_id} expired (quorum not reached)")
        else:
            # Check threshold
            yes_votes = counts[VoteType.YES]
            no_votes = counts[VoteType.NO]
            total_decisive = yes_votes + no_votes

            if total_decisive > 0 and yes_votes / total_decisive >= proposal.threshold:
                proposal.status = ProposalStatus.PASSED
                if self.on_proposal_passed:
                    self.on_proposal_passed(proposal)
                logger.info(f"Proposal {proposal_id} passed")
            else:
                proposal.status = ProposalStatus.REJECTED
                if self.on_proposal_rejected:
                    self.on_proposal_rejected(proposal)
                logger.info(f"Proposal {proposal_id} rejected")

        proposal.updated_at = time.time()
        return proposal.status

    def execute_proposal(self, proposal_id: str) -> bool:
        """
        Execute a passed proposal.

        Args:
            proposal_id: Proposal ID

        Returns:
            True if executed successfully
        """
        proposal = self._proposals.get(proposal_id)
        if not proposal or proposal.status != ProposalStatus.PASSED:
            return False

        try:
            # Execute based on proposal type
            result = self._execute_proposal_action(proposal)
            proposal.execution_result = result
            proposal.status = ProposalStatus.EXECUTED
            proposal.executed_at = time.time()
            proposal.updated_at = time.time()

            logger.info(f"Proposal {proposal_id} executed")
            return True

        except Exception as e:
            logger.error(f"Failed to execute proposal {proposal_id}: {e}")
            proposal.execution_result = {"error": str(e)}
            return False

    def _execute_proposal_action(self, proposal: Proposal) -> Dict[str, Any]:
        """Execute the action defined in the proposal."""
        # This would integrate with actual system components
        return {
            "status": "executed",
            "type": proposal.type.value,
            "parameters": proposal.parameters,
        }

    def get_proposal(self, proposal_id: str) -> Optional[Proposal]:
        """Get proposal by ID."""
        return self._proposals.get(proposal_id)

    def list_proposals(
        self,
        status: Optional[ProposalStatus] = None,
        type: Optional[ProposalType] = None,
        proposer_id: Optional[str] = None,
    ) -> List[Proposal]:
        """List proposals with filters."""
        proposals = list(self._proposals.values())

        if status:
            proposals = [p for p in proposals if p.status == status]

        if type:
            proposals = [p for p in proposals if p.type == type]

        if proposer_id:
            proposals = [p for p in proposals if p.proposer_id == proposer_id]

        return proposals

    def get_voter_info(self, agent_id: str) -> Optional[VotingPower]:
        """Get voter information."""
        return self._voting_powers.get(agent_id)

    def get_governance_stats(self) -> Dict[str, Any]:
        """Get governance statistics."""
        total_proposals = len(self._proposals)
        active_proposals = sum(
            1 for p in self._proposals.values()
            if p.status == ProposalStatus.ACTIVE
        )
        passed_proposals = sum(
            1 for p in self._proposals.values()
            if p.status in (ProposalStatus.PASSED, ProposalStatus.EXECUTED)
        )
        total_voters = len(self._voting_powers)
        total_delegations = len(self._delegations)

        return {
            "total_proposals": total_proposals,
            "active_proposals": active_proposals,
            "passed_proposals": passed_proposals,
            "total_voters": total_voters,
            "total_voting_power": self._total_voting_power,
            "total_delegations": total_delegations,
            "quorum_requirement": self.default_quorum,
            "pass_threshold": self.default_threshold,
        }
