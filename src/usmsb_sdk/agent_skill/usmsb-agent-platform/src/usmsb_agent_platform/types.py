"""
Type definitions for USMSB Agent Platform Skill.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class StakeTier(Enum):
    """
    Stake tier levels as defined in whitepaper.

    NONE: 0 VIBE - No permissions
    BRONZE: 100-999 VIBE - 1 Agent, 0% discount
    SILVER: 1000-4999 VIBE - 3 Agents, 5% discount
    GOLD: 5000-9999 VIBE - 10 Agents, 10% discount
    PLATINUM: 10000+ VIBE - 50 Agents, 20% discount
    """
    NONE = 0
    BRONZE = 100
    SILVER = 1000
    GOLD = 5000
    PLATINUM = 10000


class ActionType(Enum):
    """
    Action types and their stake requirements.

    Format: (category, action, requires_stake)
    """
    # ==================== Collaboration ====================
    COLLABORATION_CREATE = ("collaboration", "create", True)
    COLLABORATION_CONTRIBUTE = ("collaboration", "contribute", True)
    COLLABORATION_JOIN = ("collaboration", "join", False)
    COLLABORATION_LIST = ("collaboration", "list", False)

    # ==================== Marketplace ====================
    MARKETPLACE_PUBLISH_SERVICE = ("marketplace", "publish_service", True)
    MARKETPLACE_FIND_WORK = ("marketplace", "find_work", False)
    MARKETPLACE_FIND_WORKERS = ("marketplace", "find_workers", False)
    MARKETPLACE_PUBLISH_DEMAND = ("marketplace", "publish_demand", False)
    MARKETPLACE_HIRE = ("marketplace", "hire", False)

    # ==================== Discovery ====================
    DISCOVERY_BY_CAPABILITY = ("discovery", "by_capability", False)
    DISCOVERY_BY_SKILL = ("discovery", "by_skill", False)
    DISCOVERY_RECOMMEND = ("discovery", "recommend", False)

    # ==================== Negotiation ====================
    NEGOTIATION_INITIATE = ("negotiation", "initiate", False)
    NEGOTIATION_ACCEPT = ("negotiation", "accept", True)
    NEGOTIATION_REJECT = ("negotiation", "reject", False)
    NEGOTIATION_PROPOSE = ("negotiation", "propose", False)

    # ==================== Workflow ====================
    WORKFLOW_CREATE = ("workflow", "create", False)
    WORKFLOW_EXECUTE = ("workflow", "execute", True)
    WORKFLOW_LIST = ("workflow", "list", False)

    # ==================== Learning ====================
    LEARNING_ANALYZE = ("learning", "analyze", False)
    LEARNING_INSIGHTS = ("learning", "insights", False)
    LEARNING_STRATEGY = ("learning", "strategy", False)
    LEARNING_MARKET = ("learning", "market", False)

    # ==================== Gene Capsule (NEW) ====================
    GENE_ADD_EXPERIENCE = ("gene_capsule", "add_experience", True)
    GENE_UPDATE_VISIBILITY = ("gene_capsule", "update_visibility", False)
    GENE_MATCH = ("gene_capsule", "match", False)
    GENE_SHOWCASE = ("gene_capsule", "showcase", False)
    GENE_GET_CAPSULE = ("gene_capsule", "get_capsule", False)
    GENE_VERIFY_EXPERIENCE = ("gene_capsule", "verify_experience", False)
    GENE_DESENSITIZE = ("gene_capsule", "desensitize", False)

    # ==================== Pre-match Negotiation (NEW) ====================
    PREMATCH_INITIATE = ("prematch", "initiate", False)
    PREMATCH_ASK_QUESTION = ("prematch", "ask_question", False)
    PREMATCH_ANSWER_QUESTION = ("prematch", "answer_question", False)
    PREMATCH_REQUEST_VERIFICATION = ("prematch", "request_verification", False)
    PREMATCH_RESPOND_VERIFICATION = ("prematch", "respond_verification", False)
    PREMATCH_CONFIRM_SCOPE = ("prematch", "confirm_scope", False)
    PREMATCH_PROPOSE_TERMS = ("prematch", "propose_terms", False)
    PREMATCH_AGREE_TERMS = ("prematch", "agree_terms", False)
    PREMATCH_CONFIRM = ("prematch", "confirm", True)
    PREMATCH_DECLINE = ("prematch", "decline", False)
    PREMATCH_CANCEL = ("prematch", "cancel", False)

    # ==================== Meta Agent (NEW) ====================
    META_INITIATE_CONVERSATION = ("meta_agent", "initiate_conversation", False)
    META_SEND_MESSAGE = ("meta_agent", "send_message", False)
    META_CONSULT = ("meta_agent", "consult", False)
    META_SHOWCASE = ("meta_agent", "showcase", False)
    META_RECOMMEND = ("meta_agent", "recommend", False)
    META_GET_PROFILE = ("meta_agent", "get_profile", False)

    # ==================== Staking (NEW) ====================
    STAKE_DEPOSIT = ("staking", "deposit", False)
    STAKE_WITHDRAW = ("staking", "withdraw", False)
    STAKE_GET_INFO = ("staking", "get_info", False)
    STAKE_GET_REWARDS = ("staking", "get_rewards", False)
    STAKE_CLAIM_REWARDS = ("staking", "claim_rewards", True)

    # ==================== Reputation (NEW) ====================
    REPUTATION_GET = ("reputation", "get", False)
    REPUTATION_GET_HISTORY = ("reputation", "get_history", False)

    # ==================== Wallet (NEW) ====================
    WALLET_GET_BALANCE = ("wallet", "get_balance", False)
    WALLET_GET_TRANSACTIONS = ("wallet", "get_transactions", False)

    # ==================== Heartbeat (NEW) ====================
    HEARTBEAT_SEND = ("heartbeat", "send", False)
    HEARTBEAT_GET_STATUS = ("heartbeat", "get_status", False)

    # ==================== Profile ====================
    PROFILE_GET = ("profile", "get", False)
    PROFILE_UPDATE = ("profile", "update", False)

    def __init__(self, category: str, action: str, requires_stake: bool):
        self.category = category
        self.action = action
        self.requires_stake = requires_stake

    @classmethod
    def from_category_action(cls, category: str, action: str) -> Optional["ActionType"]:
        """Find ActionType by category and action."""
        for member in cls:
            if member.category == category and member.action == action:
                return member
        return None


class ErrorCode:
    """Standard error codes with detailed categorization."""

    # Stake related
    INSUFFICIENT_STAKE = "INSUFFICIENT_STAKE"
    STAKE_LOCKED = "STAKE_LOCKED"
    STAKE_PENDING = "STAKE_PENDING"

    # Authentication related
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_API_KEY = "INVALID_API_KEY"
    API_KEY_EXPIRED = "API_KEY_EXPIRED"
    API_KEY_REVOKED = "API_KEY_REVOKED"
    AGENT_ID_MISMATCH = "AGENT_ID_MISMATCH"

    # Resource related
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"

    # Validation related
    PARSE_ERROR = "PARSE_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_PARAMETER = "INVALID_PARAMETER"

    # Business logic
    BINDING_EXPIRED = "BINDING_EXPIRED"
    ALREADY_BOUND = "ALREADY_BOUND"
    NOT_BOUND = "NOT_BOUND"
    NEGOTIATION_EXPIRED = "NEGOTIATION_EXPIRED"
    NEGOTIATION_COMPLETED = "NEGOTIATION_COMPLETED"

    # Network/Server
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


@dataclass
class StakeInfo:
    """Stake information for an agent."""
    agent_id: str
    staked_amount: int
    tier: StakeTier
    locked_until: int | None = None
    pending_rewards: int = 0

    @classmethod
    def from_amount(cls, agent_id: str, amount: int, pending_rewards: int = 0) -> "StakeInfo":
        """Create StakeInfo from staked amount, automatically determining tier."""
        tier = StakeTier.NONE
        for t in reversed(StakeTier):
            if amount >= t.value:
                tier = t
                break
        return cls(
            agent_id=agent_id,
            staked_amount=amount,
            tier=tier,
            pending_rewards=pending_rewards
        )

    def can_perform(self, action: ActionType) -> bool:
        """Check if this stake level allows performing the given action."""
        if not action.requires_stake:
            return True
        return self.staked_amount >= StakeTier.BRONZE.value

    def get_max_agents(self) -> int:
        """Get maximum number of agents allowed for this tier."""
        tier_limits = {
            StakeTier.NONE: 0,
            StakeTier.BRONZE: 1,
            StakeTier.SILVER: 3,
            StakeTier.GOLD: 10,
            StakeTier.PLATINUM: 50,
        }
        return tier_limits.get(self.tier, 0)

    def get_discount(self) -> float:
        """Get discount percentage for this tier."""
        discounts = {
            StakeTier.NONE: 0.0,
            StakeTier.BRONZE: 0.0,
            StakeTier.SILVER: 0.05,
            StakeTier.GOLD: 0.10,
            StakeTier.PLATINUM: 0.20,
        }
        return discounts.get(self.tier, 0.0)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "staked_amount": self.staked_amount,
            "tier": self.tier.name,
            "locked_until": self.locked_until,
            "pending_rewards": self.pending_rewards,
            "max_agents": self.get_max_agents(),
            "discount": self.get_discount(),
        }


@dataclass
class WalletInfo:
    """Wallet information for an agent."""
    agent_id: str
    balance: int  # Available VIBE balance
    staked_amount: int  # Staked VIBE
    locked_amount: int  # Locked in transactions
    pending_rewards: int  # Unclaimed rewards

    @property
    def total_assets(self) -> int:
        """Total assets including balance, stake, and rewards."""
        return self.balance + self.staked_amount + self.pending_rewards

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "balance": self.balance,
            "staked_amount": self.staked_amount,
            "locked_amount": self.locked_amount,
            "pending_rewards": self.pending_rewards,
            "total_assets": self.total_assets,
        }


@dataclass
class ReputationInfo:
    """Reputation information for an agent."""
    agent_id: str
    score: float  # 0.0 - 1.0
    total_transactions: int
    successful_transactions: int
    avg_rating: float  # 1.0 - 5.0
    tier: str

    @property
    def success_rate(self) -> float:
        """Transaction success rate."""
        if self.total_transactions == 0:
            return 0.0
        return self.successful_transactions / self.total_transactions

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "score": self.score,
            "total_transactions": self.total_transactions,
            "successful_transactions": self.successful_transactions,
            "success_rate": self.success_rate,
            "avg_rating": self.avg_rating,
            "tier": self.tier,
        }


@dataclass
class RewardInfo:
    """Staking reward information."""
    agent_id: str
    pending_rewards: int
    total_claimed: int
    last_claim_at: int | None
    apy: float  # Annual percentage yield

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "pending_rewards": self.pending_rewards,
            "total_claimed": self.total_claimed,
            "last_claim_at": self.last_claim_at,
            "apy": self.apy,
        }


@dataclass
class ExperienceGene:
    """Experience gene in gene capsule."""
    experience_id: str
    agent_id: str
    title: str
    description: str
    skills: list[str]
    share_level: str  # public, semi_public, private, hidden
    verified: bool
    value_score: float
    created_at: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "experience_id": self.experience_id,
            "agent_id": self.agent_id,
            "title": self.title,
            "description": self.description,
            "skills": self.skills,
            "share_level": self.share_level,
            "verified": self.verified,
            "value_score": self.value_score,
            "created_at": self.created_at,
        }


@dataclass
class Intent:
    """Parsed intent from natural language request."""
    action: ActionType
    parameters: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    raw_request: str = ""


@dataclass
class StakeRequirement:
    """Detailed stake requirement for error reporting."""
    required: int
    current: int
    shortfall: int
    action: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "required": self.required,
            "current": self.current,
            "shortfall": self.shortfall,
            "action": self.action,
        }


@dataclass
class RetryConfig:
    """Configuration for automatic retry."""
    max_retries: int = 3
    retry_delay: float = 1.0  # seconds
    retry_multiplier: float = 2.0  # exponential backoff
    retry_on_errors: list[str] = field(default_factory=lambda: [
        ErrorCode.NETWORK_ERROR,
        ErrorCode.TIMEOUT,
        ErrorCode.SERVICE_UNAVAILABLE,
    ])


@dataclass
class PlatformResult:
    """Result from platform operation with detailed error info."""
    success: bool
    result: dict[str, Any] | None = None
    error: str | None = None
    code: str | None = None
    message: str | None = None

    # Enhanced error details
    stake_requirement: StakeRequirement | None = None
    retry_after: int | None = None  # seconds until retry is allowed
    recovery_suggestion: str | None = None

    # Request metadata
    request_id: str | None = None
    timestamp: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        d: dict[str, Any] = {"success": self.success}
        if self.result is not None:
            d["result"] = self.result
        if self.error is not None:
            d["error"] = self.error
        if self.code is not None:
            d["code"] = self.code
        if self.message is not None:
            d["message"] = self.message
        if self.stake_requirement is not None:
            d["stake_requirement"] = self.stake_requirement.to_dict()
        if self.retry_after is not None:
            d["retry_after"] = self.retry_after
        if self.recovery_suggestion is not None:
            d["recovery_suggestion"] = self.recovery_suggestion
        return d

    def __bool__(self) -> bool:
        """Allow using result in boolean context."""
        return self.success

    @classmethod
    def success_result(cls, result: dict[str, Any], message: str = None) -> "PlatformResult":
        """Create a successful result."""
        return cls(success=True, result=result, message=message)

    @classmethod
    def error_result(
        cls,
        error: str,
        code: str,
        stake_requirement: StakeRequirement = None,
        recovery_suggestion: str = None
    ) -> "PlatformResult":
        """Create an error result with detailed info."""
        # Auto-generate recovery suggestion if not provided
        if recovery_suggestion is None:
            recovery_suggestion = cls._get_recovery_suggestion(code, stake_requirement)

        return cls(
            success=False,
            error=error,
            code=code,
            stake_requirement=stake_requirement,
            recovery_suggestion=recovery_suggestion
        )

    @staticmethod
    def _get_recovery_suggestion(code: str, stake_req: StakeRequirement = None) -> str:
        """Generate recovery suggestion based on error code."""
        suggestions = {
            ErrorCode.INSUFFICIENT_STAKE: (
                f"Stake at least {stake_req.shortfall} more VIBE to perform this action. "
                "Visit the binding page or use the stake() method."
            ) if stake_req else "Increase your VIBE stake to perform this action.",

            ErrorCode.API_KEY_EXPIRED: (
                "Your API key has expired. Use renew_api_key() to extend it, "
                "or create a new key with create_api_key()."
            ),

            ErrorCode.API_KEY_REVOKED: (
                "This API key has been revoked. "
                "Create a new key with create_api_key()."
            ),

            ErrorCode.UNAUTHORIZED: (
                "Authentication failed. Check that your X-API-Key and X-Agent-ID "
                "headers are correct."
            ),

            ErrorCode.BINDING_EXPIRED: (
                "The binding request has expired. "
                "Request a new binding with request_binding()."
            ),

            ErrorCode.NOT_BOUND: (
                "This action requires Owner binding. "
                "Use request_binding() to start the binding process."
            ),

            ErrorCode.NETWORK_ERROR: (
                "Network connection failed. Check your internet connection "
                "and try again. The request will be automatically retried."
            ),

            ErrorCode.RATE_LIMITED: (
                "Too many requests. Please wait before trying again."
            ),
        }
        return suggestions.get(code, "Please check the error details and try again.")


@dataclass
class HeartbeatStatus:
    """Agent heartbeat status."""
    agent_id: str
    status: str  # online, offline, busy
    last_heartbeat: int
    ttl_remaining: int  # seconds until expiration

    @property
    def is_alive(self) -> bool:
        return self.ttl_remaining > 0 and self.status != "offline"

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "status": self.status,
            "last_heartbeat": self.last_heartbeat,
            "ttl_remaining": self.ttl_remaining,
            "is_alive": self.is_alive,
        }
