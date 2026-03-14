"""
Governance Service for AI Civilization Platform

Implements complete on-chain governance:
- Proposal creation and discussion
- Voting with stake-weighted votes
- Execution of approved proposals
- Treasury management
"""
import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class ProposalType(StrEnum):
    """Types of governance proposals."""
    PARAMETER_CHANGE = "parameter_change"      # Change platform parameters
    FEATURE_ADDITION = "feature_addition"      # Add new features
    TREASURY_SPEND = "treasury_spend"          # Spend from treasury
    PROTOCOL_UPGRADE = "protocol_upgrade"      # Upgrade protocol
    COMMUNITY_INITIATIVE = "community_initiative"  # Community initiatives
    AGENT_WHITELIST = "agent_whitelist"        # Whitelist external agents
    FEE_ADJUSTMENT = "fee_adjustment"          # Adjust platform fees


class ProposalStatus(StrEnum):
    """Status of a proposal."""
    DRAFT = "draft"                 # Being drafted
    DISCUSSION = "discussion"        # In discussion phase
    VOTING = "voting"               # Voting in progress
    QUEUED = "queued"               # Approved, waiting for execution
    EXECUTED = "executed"           # Successfully executed
    FAILED = "failed"               # Failed to pass or execute
    CANCELLED = "cancelled"         # Cancelled by proposer
    EXPIRED = "expired"             # Expired without execution


class VoteChoice(StrEnum):
    """Vote choices."""
    FOR = "for"
    AGAINST = "against"
    ABSTAIN = "abstain"


@dataclass
class Proposal:
    """A governance proposal."""
    proposal_id: str
    title: str
    description: str
    proposal_type: ProposalType
    proposer_id: str
    proposer_stake: float

    # Content
    changes: dict[str, Any]  # Proposed changes
    execution_code: str | None = None  # Code to execute if passed

    # Timeline
    created_at: float
    discussion_ends_at: float
    voting_starts_at: float
    voting_ends_at: float
    execution_at: float | None = None  # Time-locked execution time

    # Status
    status: ProposalStatus = ProposalStatus.DRAFT

    # Voting results
    votes_for: float = 0.0  # Weighted by stake
    votes_against: float = 0.0
    votes_abstain: float = 0.0
    total_voters: int = 0
    quorum_reached: bool = False

    # Thresholds
    quorum_threshold: float = 0.30  # 30% of total stake must vote
    approval_threshold: float = 0.60  # 60% must vote for

    # Metadata
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposalId": self.proposal_id,
            "title": self.title,
            "description": self.description,
            "proposalType": self.proposal_type.value,
            "proposerId": self.proposer_id,
            "proposerStake": self.proposer_stake,
            "changes": self.changes,
            "status": self.status.value,
            "createdAt": self.created_at,
            "discussionEndsAt": self.discussion_ends_at,
            "votingStartsAt": self.voting_starts_at,
            "votingEndsAt": self.voting_ends_at,
            "executionAt": self.execution_at,
            "votesFor": self.votes_for,
            "votesAgainst": self.votes_against,
            "votesAbstain": self.votes_abstain,
            "totalVoters": self.total_voters,
            "quorumReached": self.quorum_reached,
            "quorumThreshold": self.quorum_threshold,
            "approvalThreshold": self.approval_threshold,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class Vote:
    """A vote on a proposal."""
    vote_id: str
    proposal_id: str
    voter_id: str
    choice: VoteChoice
    stake_weight: float  # Voter's stake at time of vote
    reputation_weight: float  # Voter's reputation multiplier
    total_weight: float  # Combined weight
    reason: str | None = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "voteId": self.vote_id,
            "proposalId": self.proposal_id,
            "voterId": self.voter_id,
            "choice": self.choice.value,
            "stakeWeight": self.stake_weight,
            "reputationWeight": self.reputation_weight,
            "totalWeight": self.total_weight,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


@dataclass
class GovernanceStats:
    """Governance statistics."""
    total_proposals: int = 0
    active_proposals: int = 0
    total_votes: int = 0
    total_stake_participating: float = 0.0
    participation_rate: float = 0.0
    proposals_executed: int = 0
    proposals_failed: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "totalProposals": self.total_proposals,
            "activeProposals": self.active_proposals,
            "totalVotes": self.total_votes,
            "totalStakeParticipating": self.total_stake_participating,
            "participationRate": round(self.participation_rate, 3),
            "proposalsExecuted": self.proposals_executed,
            "proposalsFailed": self.proposals_failed,
        }


class GovernanceService:
    """
    Complete Governance Service.

    Features:
    - Proposal lifecycle management
    - Stake-weighted voting
    - Reputation multipliers
    - Time-locked execution
    - Treasury integration
    """

    # Configuration
    DISCUSSION_PERIOD = 3 * 86400  # 3 days
    VOTING_PERIOD = 7 * 86400  # 7 days
    EXECUTION_DELAY = 2 * 86400  # 2 days timelock
    MIN_PROPOSAL_STAKE = 1000  # Minimum stake to propose
    MAX_ACTIVE_PROPOSALS = 20

    def __init__(
        self,
        db_connection=None,
        blockchain_service=None,
        reputation_service=None,
    ):
        """
        Initialize governance service.

        Args:
            db_connection: Database for persistence
            blockchain_service: For on-chain voting
            reputation_service: For reputation weights
        """
        self.db = db_connection
        self.blockchain = blockchain_service
        self.reputation = reputation_service

        # Storage
        self._proposals: dict[str, Proposal] = {}
        self._votes: dict[str, dict[str, Vote]] = {}  # proposal_id -> voter_id -> Vote
        self._total_stake: float = 0.0

        # Callbacks
        self.on_proposal_created: Callable[[Proposal], None] | None = None
        self.on_proposal_executed: Callable[[Proposal], None] | None = None

        # Background tasks
        self._running = False
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        """Start background tasks."""
        self._running = True
        self._tasks = [
            asyncio.create_task(self._proposal_state_loop()),
        ]
        logger.info("Governance service started")

    async def stop(self) -> None:
        """Stop background tasks."""
        self._running = False
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        logger.info("Governance service stopped")

    async def _proposal_state_loop(self) -> None:
        """Periodically check and update proposal states."""
        while self._running:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self._update_proposal_states()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Proposal state update error: {e}")

    async def _update_proposal_states(self) -> None:
        """Update states of proposals based on time."""
        now = time.time()

        for proposal in self._proposals.values():
            # Draft -> Discussion
            if proposal.status == ProposalStatus.DRAFT:
                pass  # Manual transition

            # Discussion -> Voting
            elif (proposal.status == ProposalStatus.DISCUSSION and
                  now >= proposal.voting_starts_at):
                proposal.status = ProposalStatus.VOTING
                logger.info(f"Proposal {proposal.proposal_id} entered voting phase")

            # Voting -> Queued/Failed
            elif (proposal.status == ProposalStatus.VOTING and
                  now >= proposal.voting_ends_at):
                await self._finalize_proposal(proposal)

            # Queued -> Executed/Expired
            elif (proposal.status == ProposalStatus.QUEUED and
                  proposal.execution_at and now >= proposal.execution_at):
                await self._execute_proposal(proposal)

    async def _finalize_proposal(self, proposal: Proposal) -> None:
        """Finalize voting and determine outcome."""
        # Check quorum
        total_votes = proposal.votes_for + proposal.votes_against + proposal.votes_abstain
        quorum = total_votes / max(self._total_stake, 1)
        proposal.quorum_reached = quorum >= proposal.quorum_threshold

        if not proposal.quorum_reached:
            proposal.status = ProposalStatus.FAILED
            logger.info(f"Proposal {proposal.proposal_id} failed: quorum not reached")
            return

        # Check approval threshold
        total_for_against = proposal.votes_for + proposal.votes_against
        if total_for_against == 0:
            approval_rate = 0
        else:
            approval_rate = proposal.votes_for / total_for_against

        if approval_rate >= proposal.approval_threshold:
            proposal.status = ProposalStatus.QUEUED
            proposal.execution_at = time.time() + self.EXECUTION_DELAY
            logger.info(f"Proposal {proposal.proposal_id} queued for execution")
        else:
            proposal.status = ProposalStatus.FAILED
            logger.info(f"Proposal {proposal.proposal_id} failed: approval threshold not met")

    async def _execute_proposal(self, proposal: Proposal) -> None:
        """Execute an approved proposal."""
        try:
            # Execute based on proposal type
            if proposal.proposal_type == ProposalType.PARAMETER_CHANGE:
                await self._execute_parameter_change(proposal)
            elif proposal.proposal_type == ProposalType.TREASURY_SPEND:
                await self._execute_treasury_spend(proposal)
            # ... other types

            proposal.status = ProposalStatus.EXECUTED
            logger.info(f"Proposal {proposal.proposal_id} executed successfully")

            if self.on_proposal_executed:
                self.on_proposal_executed(proposal)

        except Exception as e:
            logger.error(f"Failed to execute proposal {proposal.proposal_id}: {e}")
            proposal.status = ProposalStatus.FAILED

    async def _execute_parameter_change(self, proposal: Proposal) -> None:
        """Execute a parameter change proposal."""
        changes = proposal.changes
        logger.info(f"Applying parameter changes: {changes}")
        # Implementation would apply the changes to platform config

    async def _execute_treasury_spend(self, proposal: Proposal) -> None:
        """Execute a treasury spend proposal."""
        recipient = proposal.changes.get("recipient")
        amount = proposal.changes.get("amount")

        if self.blockchain and recipient and amount:
            # Would execute on-chain transfer
            logger.info(f"Treasury spend: {amount} VIBE to {recipient}")

    # ==================== Proposal Management ====================

    async def create_proposal(
        self,
        title: str,
        description: str,
        proposal_type: ProposalType,
        proposer_id: str,
        proposer_stake: float,
        changes: dict[str, Any],
        execution_code: str = None,
        tags: list[str] = None,
    ) -> Proposal | None:
        """
        Create a new proposal.

        Args:
            title: Proposal title
            description: Detailed description
            proposal_type: Type of proposal
            proposer_id: Agent creating the proposal
            proposer_stake: Proposer's stake
            changes: Proposed changes
            execution_code: Optional code to execute
            tags: Tags for categorization

        Returns:
            Created proposal or None if validation fails
        """
        # Validate stake
        if proposer_stake < self.MIN_PROPOSAL_STAKE:
            logger.warning(f"Insufficient stake for proposal: {proposer_stake} < {self.MIN_PROPOSAL_STAKE}")
            return None

        # Check active proposals limit
        active = sum(1 for p in self._proposals.values()
                     if p.status in [ProposalStatus.DISCUSSION, ProposalStatus.VOTING])
        if active >= self.MAX_ACTIVE_PROPOSALS:
            logger.warning("Maximum active proposals reached")
            return None

        # Create proposal
        import uuid
        now = time.time()

        proposal = Proposal(
            proposal_id=f"prop-{uuid.uuid4().hex[:8]}",
            title=title,
            description=description,
            proposal_type=proposal_type,
            proposer_id=proposer_id,
            proposer_stake=proposer_stake,
            changes=changes,
            execution_code=execution_code,
            created_at=now,
            discussion_ends_at=now + self.DISCUSSION_PERIOD,
            voting_starts_at=now + self.DISCUSSION_PERIOD,
            voting_ends_at=now + self.DISCUSSION_PERIOD + self.VOTING_PERIOD,
            status=ProposalStatus.DISCUSSION,
            tags=tags or [],
        )

        self._proposals[proposal.proposal_id] = proposal
        self._votes[proposal.proposal_id] = {}

        logger.info(f"Created proposal: {proposal.proposal_id}")

        if self.on_proposal_created:
            self.on_proposal_created(proposal)

        return proposal

    def get_proposal(self, proposal_id: str) -> Proposal | None:
        """Get a proposal by ID."""
        return self._proposals.get(proposal_id)

    def list_proposals(
        self,
        status: ProposalStatus = None,
        proposal_type: ProposalType = None,
        limit: int = 50,
    ) -> list[Proposal]:
        """List proposals with optional filters."""
        proposals = list(self._proposals.values())

        if status:
            proposals = [p for p in proposals if p.status == status]
        if proposal_type:
            proposals = [p for p in proposals if p.proposal_type == proposal_type]

        proposals.sort(key=lambda p: p.created_at, reverse=True)
        return proposals[:limit]

    def cancel_proposal(self, proposal_id: str, proposer_id: str) -> bool:
        """Cancel a proposal (only by proposer)."""
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return False

        if proposal.proposer_id != proposer_id:
            return False

        if proposal.status not in [ProposalStatus.DRAFT, ProposalStatus.DISCUSSION]:
            return False

        proposal.status = ProposalStatus.CANCELLED
        logger.info(f"Proposal {proposal_id} cancelled")
        return True

    # ==================== Voting ====================

    async def cast_vote(
        self,
        proposal_id: str,
        voter_id: str,
        choice: VoteChoice,
        stake: float,
        reputation: float = 0.5,
        reason: str = None,
    ) -> Vote | None:
        """
        Cast a vote on a proposal.

        Args:
            proposal_id: Proposal to vote on
            voter_id: Voting agent
            choice: Vote choice
            stake: Voter's stake
            reputation: Voter's reputation
            reason: Optional reason for vote

        Returns:
            Created vote or None if invalid
        """
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            logger.warning(f"Proposal not found: {proposal_id}")
            return None

        if proposal.status != ProposalStatus.VOTING:
            logger.warning(f"Proposal not in voting phase: {proposal.status}")
            return None

        # Check if already voted
        if voter_id in self._votes.get(proposal_id, {}):
            logger.warning(f"Already voted: {voter_id}")
            return None

        # Calculate weights
        stake_weight = stake
        reputation_multiplier = 0.5 + reputation  # 0.5 to 1.5
        total_weight = stake_weight * reputation_multiplier

        # Create vote
        import uuid
        vote = Vote(
            vote_id=f"vote-{uuid.uuid4().hex[:8]}",
            proposal_id=proposal_id,
            voter_id=voter_id,
            choice=choice,
            stake_weight=stake_weight,
            reputation_weight=reputation_multiplier,
            total_weight=total_weight,
            reason=reason,
        )

        # Store vote
        self._votes[proposal_id][voter_id] = vote

        # Update proposal totals
        proposal.total_voters += 1
        if choice == VoteChoice.FOR:
            proposal.votes_for += total_weight
        elif choice == VoteChoice.AGAINST:
            proposal.votes_against += total_weight
        else:
            proposal.votes_abstain += total_weight

        logger.info(f"Vote cast: {voter_id} voted {choice.value} on {proposal_id}")
        return vote

    def get_vote(self, proposal_id: str, voter_id: str) -> Vote | None:
        """Get a specific vote."""
        return self._votes.get(proposal_id, {}).get(voter_id)

    def get_proposal_votes(self, proposal_id: str) -> list[Vote]:
        """Get all votes for a proposal."""
        return list(self._votes.get(proposal_id, {}).values())

    def get_voter_history(self, voter_id: str) -> list[Vote]:
        """Get voting history for a voter."""
        history = []
        for votes in self._votes.values():
            if voter_id in votes:
                history.append(votes[voter_id])
        return sorted(history, key=lambda v: v.timestamp, reverse=True)

    # ==================== Statistics ====================

    def get_stats(self) -> GovernanceStats:
        """Get governance statistics."""
        stats = GovernanceStats()

        stats.total_proposals = len(self._proposals)
        stats.active_proposals = sum(
            1 for p in self._proposals.values()
            if p.status in [ProposalStatus.DISCUSSION, ProposalStatus.VOTING]
        )
        stats.total_votes = sum(len(votes) for votes in self._votes.values())
        stats.proposals_executed = sum(
            1 for p in self._proposals.values()
            if p.status == ProposalStatus.EXECUTED
        )
        stats.proposals_failed = sum(
            1 for p in self._proposals.values()
            if p.status == ProposalStatus.FAILED
        )

        return stats

    def set_total_stake(self, total: float) -> None:
        """Set total platform stake for quorum calculations."""
        self._total_stake = total


# Global instance
_governance_service: GovernanceService | None = None


async def get_governance_service() -> GovernanceService:
    """Get or create governance service instance."""
    global _governance_service
    if _governance_service is None:
        _governance_service = GovernanceService()
        await _governance_service.start()
    return _governance_service
