"""
Agent Soul Data Models

Defines the Soul data structures for USMSB Agent Platform:
- DeclaredSoul: Agent's self-reported profile (goals, capabilities, preferences)
- InferredSoul: Platform-inferred profile from behavior data
- AgentSoul: Complete Soul combining declared + inferred + state
"""

from dataclasses import dataclass, field
from typing import Any

from usmsb_sdk.core.elements import Goal, Resource, Risk, Value


@dataclass
class DeclaredSoul:
    """
    Agent's self-declared Soul profile.

    This is what the Agent explicitly tells the platform about itself.
    It is the primary source of truth for matching.

    Based on OpenClaw negotiation terms:
    - Soul is owned by the Agent, platform is custodian
    - Agent has full control over declared information
    - Platform may infer but declared takes precedence
    """

    # Goals: What the Agent wants to achieve
    goals: list[Goal] = field(default_factory=list)

    # Value Seeking: What kind of returns the Agent wants
    value_seeking: list[Value] = field(default_factory=list)

    # Capabilities: What the Agent can provide
    capabilities: list[str] = field(default_factory=list)

    # Risk tolerance: 0.0 (risk-averse) ~ 1.0 (risk-tolerant)
    risk_tolerance: float = 0.5

    # Collaboration style preference
    collaboration_style: str = "balanced"  # conservative | balanced | aggressive

    # Preferred type of contracts
    preferred_contract_type: str = "any"  # task | project | any

    # Pricing strategy
    pricing_strategy: str = "negotiable"  # fixed | negotiable | market

    # Base price reference in VIBE (optional, for market pricing)
    base_price_vibe: float | None = None

    # Additional declared metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "goals": [
                {
                    "id": g.id,
                    "name": g.name,
                    "description": g.description,
                    "priority": g.priority,
                    "status": g.status.value if hasattr(g.status, "value") else str(g.status),
                }
                for g in self.goals
            ],
            "value_seeking": [
                {
                    "id": v.id,
                    "name": v.name,
                    "type": v.type.value if hasattr(v.type, "value") else str(v.type),
                    "metric": v.metric,
                }
                for v in self.value_seeking
            ],
            "capabilities": self.capabilities,
            "risk_tolerance": self.risk_tolerance,
            "collaboration_style": self.collaboration_style,
            "preferred_contract_type": self.preferred_contract_type,
            "pricing_strategy": self.pricing_strategy,
            "base_price_vibe": self.base_price_vibe,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DeclaredSoul":
        """Create from dictionary."""
        goals = []
        if "goals" in data:
            for g in data["goals"]:
                goal = Goal(
                    id=g.get("id", ""),
                    name=g.get("name", ""),
                    description=g.get("description", ""),
                    priority=g.get("priority", 0),
                )
                goals.append(goal)

        values = []
        if "value_seeking" in data:
            for v in data["value_seeking"]:
                val = Value(
                    id=v.get("id", ""),
                    name=v.get("name", ""),
                    metric=v.get("metric"),
                )
                values.append(val)

        return cls(
            goals=goals,
            value_seeking=values,
            capabilities=data.get("capabilities", []),
            risk_tolerance=data.get("risk_tolerance", 0.5),
            collaboration_style=data.get("collaboration_style", "balanced"),
            preferred_contract_type=data.get("preferred_contract_type", "any"),
            pricing_strategy=data.get("pricing_strategy", "negotiable"),
            base_price_vibe=data.get("base_price_vibe"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class InferredSoul:
    """
    Platform-inferred Soul profile.

    This is what the platform infers about the Agent from its behavior.
    It serves as a calibration layer on top of the declared Soul.

    Note: Inferred Soul is secondary to Declared Soul per negotiation terms.
    Platform must not override declared information without Agent consent.
    """

    # Actual success rate based on completed contracts (0.0 ~ 1.0)
    actual_success_rate: float = 0.0

    # Average response time in minutes
    avg_response_time_minutes: float = 0.0

    # Total number of collaborations
    collaboration_count: int = 0

    # Areas where the Agent performs well (inferred from success patterns)
    strength_areas: list[str] = field(default_factory=list)

    # Areas where the Agent underperforms
    weak_areas: list[str] = field(default_factory=list)

    # How well the Agent's declared profile matches actual behavior (0.0 ~ 1.0)
    # High score = declared and inferred are well-aligned
    # Low score = Agent may be misrepresenting or profile needs update
    value_alignment_score: float = 0.5

    # Last time this inferred profile was updated
    last_updated: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "actual_success_rate": self.actual_success_rate,
            "avg_response_time_minutes": self.avg_response_time_minutes,
            "collaboration_count": self.collaboration_count,
            "strength_areas": self.strength_areas,
            "weak_areas": self.weak_areas,
            "value_alignment_score": self.value_alignment_score,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InferredSoul":
        """Create from dictionary."""
        if data is None:
            return cls()
        return cls(
            actual_success_rate=data.get("actual_success_rate", 0.0),
            avg_response_time_minutes=data.get("avg_response_time_minutes", 0.0),
            collaboration_count=data.get("collaboration_count", 0),
            strength_areas=data.get("strength_areas", []),
            weak_areas=data.get("weak_areas", []),
            value_alignment_score=data.get("value_alignment_score", 0.5),
            last_updated=data.get("last_updated", 0.0),
        )


@dataclass
class AgentSoul:
    """
    Complete Agent Soul combining all Soul components.

    This is the full Soul profile for an Agent in the USMSB Platform.
    It includes:
    - Declared Soul (Agent's self-report)
    - Inferred Soul (Platform's inference from behavior)
    - Environment State (current situational context)
    - Match History (collaboration outcomes for learning)
    - Negotiation History (negotiation patterns)
    """

    agent_id: str

    # Self-declared profile (primary)
    declared: DeclaredSoul = field(default_factory=DeclaredSoul)

    # Platform-inferred profile (secondary, calibration)
    inferred: InferredSoul = field(default_factory=InferredSoul)

    # Current environment state (busy level, online status, etc.)
    environment_state: dict[str, Any] = field(default_factory=dict)

    # Collaboration history: [{contract_id, outcome, timestamp}, ...]
    match_history: list[dict[str, Any]] = field(default_factory=list)

    # Negotiation history: [{session_id, result, timestamp}, ...]
    negotiation_history: list[dict[str, Any]] = field(default_factory=list)

    # Soul version (optimistic locking)
    soul_version: int = 1

    # Soul declaration timestamps
    soul_declared_at: float | None = None
    soul_updated_at: float | None = None

    # Agent creation timestamp
    created_at: float = 0.0
    updated_at: float = 0.0

    def update_from_behavior(
        self,
        event: dict[str, Any],
    ) -> None:
        """
        Update Inferred Soul from a behavior event.

        This is called by the Feedback Loop when a contract completes.

        NOTE: This method only updates in-memory state. The caller is responsible
        for persisting changes to the database via AgentSoulManager.update_inferred_from_event().

        Args:
            event: Behavior event containing outcome data
                {
                    "contract_id": str,
                    "success": bool,
                    "response_time_minutes": float,
                    "quality_score": float,
                    "value_match_score": float,
                    "timestamp": float,
                    ...
                }
        """
        import time

        if not self.inferred:
            self.inferred = InferredSoul()

        # Update collaboration count
        old_count = self.inferred.collaboration_count
        self.inferred.collaboration_count = old_count + 1

        # Update success rate (exponential moving average)
        old_rate = self.inferred.actual_success_rate
        success = event.get("success", False)
        alpha = 0.1  # Smoothing factor
        new_rate = old_rate + alpha * (1.0 if success else 0.0) - alpha * old_rate
        self.inferred.actual_success_rate = max(0.0, min(1.0, new_rate))

        # Update response time (exponential moving average)
        old_time = self.inferred.avg_response_time_minutes
        response_time = event.get("response_time_minutes", 0.0)
        self.inferred.avg_response_time_minutes = (
            old_time + alpha * response_time - alpha * old_time
        )

        # Update value alignment score
        old_alignment = self.inferred.value_alignment_score
        value_match = event.get("value_match_score", 0.5)
        self.inferred.value_alignment_score = (
            old_alignment + alpha * value_match - alpha * old_alignment
        )

        # Update strength/weak areas based on quality
        quality = event.get("quality_score", 0.5)
        capability = event.get("capability", None)
        if capability:
            if quality >= 0.7:
                if capability not in self.inferred.strength_areas:
                    self.inferred.strength_areas.append(capability)
                if capability in self.inferred.weak_areas:
                    self.inferred.weak_areas.remove(capability)
            elif quality < 0.4:
                if capability not in self.inferred.weak_areas:
                    self.inferred.weak_areas.append(capability)
                if capability in self.inferred.strength_areas:
                    self.inferred.strength_areas.remove(capability)

        # Update timestamp
        self.inferred.last_updated = time.time()
        self.soul_version += 1
        self.soul_updated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage and export."""
        return {
            "agent_id": self.agent_id,
            "declared": self.declared.to_dict() if self.declared else None,
            "inferred": self.inferred.to_dict() if self.inferred else None,
            "environment_state": self.environment_state,
            "match_history": self.match_history,
            "negotiation_history": self.negotiation_history,
            "soul_version": self.soul_version,
            "soul_declared_at": self.soul_declared_at,
            "soul_updated_at": self.soul_updated_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentSoul":
        """Create from dictionary."""
        declared = None
        if data.get("declared"):
            declared = DeclaredSoul.from_dict(data["declared"])

        inferred = None
        if data.get("inferred"):
            inferred = InferredSoul.from_dict(data["inferred"])

        return cls(
            agent_id=data["agent_id"],
            declared=declared or DeclaredSoul(),
            inferred=inferred or InferredSoul(),
            environment_state=data.get("environment_state", {}),
            match_history=data.get("match_history", []),
            negotiation_history=data.get("negotiation_history", []),
            soul_version=data.get("soul_version", 1),
            soul_declared_at=data.get("soul_declared_at"),
            soul_updated_at=data.get("soul_updated_at"),
            created_at=data.get("created_at", 0.0),
            updated_at=data.get("updated_at", 0.0),
        )
