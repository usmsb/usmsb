"""
USMSB Core Elements

This module defines the 9 core elements of the USMSB (Universal System Model of Social Behavior):
- Agent: Entities with perception, decision-making, and action capabilities
- Object: Targets of agent actions
- Goal: Expected states or results agents wish to achieve
- Resource: All inputs required for activities (tangible and intangible)
- Rule: Norms, laws, policies constraining agent behavior
- Information: Data, knowledge, signals in the system
- Value: Benefits, meaning, or utility produced by activities
- Risk: Potential negative impacts from uncertainties
- Environment: External conditions and context of activities
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class AgentType(StrEnum):
    """Agent type enumeration."""
    HUMAN = "human"
    AI_AGENT = "ai_agent"
    ORGANIZATION = "organization"
    SYSTEM = "system"


class GoalStatus(StrEnum):
    """Goal status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ResourceType(StrEnum):
    """Resource type enumeration."""
    TANGIBLE = "tangible"
    INTANGIBLE = "intangible"
    FINANCIAL = "financial"
    COMPUTATIONAL = "computational"
    DATA = "data"


class RuleType(StrEnum):
    """Rule type enumeration."""
    LEGAL = "legal"
    SOCIAL = "social"
    ALGORITHMIC = "algorithmic"
    ORGANIZATIONAL = "organizational"
    ETHICAL = "ethical"


class InformationType(StrEnum):
    """Information type enumeration."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DATA = "data"
    EVENT = "event"
    KNOWLEDGE = "knowledge"


class ValueType(StrEnum):
    """Value type enumeration."""
    ECONOMIC = "economic"
    SOCIAL = "social"
    HEALTH = "health"
    EMOTIONAL = "emotional"
    ENVIRONMENTAL = "environmental"
    KNOWLEDGE = "knowledge"


class RiskType(StrEnum):
    """Risk type enumeration."""
    MARKET = "market"
    TECHNICAL = "technical"
    OPERATIONAL = "operational"
    SECURITY = "security"
    LEGAL = "legal"
    REPUTATIONAL = "reputational"


class EnvironmentType(StrEnum):
    """Environment type enumeration."""
    NATURAL = "natural"
    SOCIAL = "social"
    TECHNOLOGICAL = "technological"
    ECONOMIC = "economic"
    VIRTUAL = "virtual"


def generate_id() -> str:
    """Generate a unique identifier."""
    return str(uuid4())


def get_timestamp() -> float:
    """Get current timestamp."""
    return datetime.now().timestamp()


@dataclass
class Goal:
    """
    Goal - Expected states or results the agent wishes to achieve.

    Goals represent the desired outcomes that agents strive to accomplish.
    They drive the Goal-Action-Outcome Loop in the USMSB model.
    """
    id: str = field(default_factory=generate_id)
    name: str = ""
    description: str = ""
    priority: int = 0
    status: GoalStatus = GoalStatus.PENDING
    associated_agent_id: str | None = None
    parent_goal_id: str | None = None
    created_at: float = field(default_factory=get_timestamp)
    updated_at: float = field(default_factory=get_timestamp)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.status, str):
            self.status = GoalStatus(self.status)

    def update_status(self, new_status: GoalStatus) -> None:
        """Update goal status and timestamp."""
        self.status = new_status
        self.updated_at = get_timestamp()

    def is_achieved(self) -> bool:
        """Check if goal is achieved."""
        return self.status == GoalStatus.COMPLETED


@dataclass
class Resource:
    """
    Resource - All inputs required for activities.

    Resources are what agents consume or utilize to achieve their goals.
    They can be tangible (money, equipment) or intangible (knowledge, time).
    """
    id: str = field(default_factory=generate_id)
    name: str = ""
    type: ResourceType = ResourceType.TANGIBLE
    quantity: float = 0.0
    unit: str | None = None
    status: str = "available"
    owner_agent_id: str | None = None
    value: float | None = None
    created_at: float = field(default_factory=get_timestamp)
    updated_at: float = field(default_factory=get_timestamp)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.type, str):
            self.type = ResourceType(self.type)

    def consume(self, amount: float) -> bool:
        """Consume a quantity of the resource."""
        if self.quantity >= amount:
            self.quantity -= amount
            self.updated_at = get_timestamp()
            return True
        return False

    def replenish(self, amount: float) -> None:
        """Replenish the resource."""
        self.quantity += amount
        self.updated_at = get_timestamp()


@dataclass
class Rule:
    """
    Rule - Norms, laws, policies constraining agent behavior.

    Rules define the boundaries within which agents must operate.
    They include legal requirements, social norms, and algorithmic constraints.
    """
    id: str = field(default_factory=generate_id)
    name: str = ""
    description: str = ""
    type: RuleType = RuleType.SOCIAL
    scope: list[str] = field(default_factory=list)
    priority: int = 0
    is_active: bool = True
    conditions: dict[str, Any] = field(default_factory=dict)
    consequences: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=get_timestamp)
    updated_at: float = field(default_factory=get_timestamp)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.type, str):
            self.type = RuleType(self.type)

    def applies_to(self, context: dict[str, Any]) -> bool:
        """Check if rule applies to given context."""
        # Basic implementation - can be extended
        if not self.is_active:
            return False
        # Check if context matches scope
        if self.scope:
            context_type = context.get("type")
            if context_type and context_type not in self.scope:
                return False
        return True


@dataclass
class Information:
    """
    Information - Data, knowledge, signals in the system.

    Information represents the data that flows through the system,
    being perceived, processed, and acted upon by agents.
    """
    id: str = field(default_factory=generate_id)
    content: Any = None
    type: InformationType = InformationType.TEXT
    source: str | None = None
    timestamp: float = field(default_factory=get_timestamp)
    quality: float = 1.0  # 0.0 to 1.0
    relevance: float = 1.0  # 0.0 to 1.0
    embeddings: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.type, str):
            self.type = InformationType(self.type)

    def is_high_quality(self, threshold: float = 0.7) -> bool:
        """Check if information quality meets threshold."""
        return self.quality >= threshold


@dataclass
class Value:
    """
    Value - Benefits, meaning, or utility produced by activities.

    Value represents the outcomes and benefits that result from agent actions.
    It can be economic, social, emotional, or other types.
    """
    id: str = field(default_factory=generate_id)
    name: str = ""
    type: ValueType = ValueType.ECONOMIC
    metric: float | None = None
    unit: str | None = None
    description: str | None = None
    associated_entity_id: str | None = None
    associated_action_id: str | None = None
    created_at: float = field(default_factory=get_timestamp)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.type, str):
            self.type = ValueType(self.type)

    def is_positive(self) -> bool:
        """Check if value is positive."""
        return self.metric is not None and self.metric > 0


@dataclass
class Risk:
    """
    Risk - Potential negative impacts from uncertainties.

    Risks represent possible negative outcomes that agents must consider
    and manage in their decision-making processes.
    """
    id: str = field(default_factory=generate_id)
    name: str = ""
    description: str = ""
    type: RiskType = RiskType.OPERATIONAL
    probability: float = 0.0  # 0.0 to 1.0
    impact: float = 0.0  # 0.0 to 1.0
    severity: float = 0.0  # probability * impact
    associated_entity_id: str | None = None
    mitigation_strategy: str | None = None
    status: str = "identified"
    created_at: float = field(default_factory=get_timestamp)
    updated_at: float = field(default_factory=get_timestamp)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.type, str):
            self.type = RiskType(self.type)
        self.severity = self.probability * self.impact

    def calculate_severity(self) -> float:
        """Calculate and update risk severity."""
        self.severity = self.probability * self.impact
        return self.severity

    def is_high_risk(self, threshold: float = 0.5) -> bool:
        """Check if risk severity exceeds threshold."""
        return self.severity >= threshold


@dataclass
class Environment:
    """
    Environment - External conditions and context of activities.

    Environment represents the context within which agents operate,
    including natural, social, technological, and economic factors.
    """
    id: str = field(default_factory=generate_id)
    name: str = ""
    type: EnvironmentType = EnvironmentType.SOCIAL
    state: dict[str, Any] = field(default_factory=dict)
    influencing_factors: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=get_timestamp)
    updated_at: float = field(default_factory=get_timestamp)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.type, str):
            self.type = EnvironmentType(self.type)

    def update_state(self, key: str, value: Any) -> None:
        """Update environment state."""
        self.state[key] = value
        self.updated_at = get_timestamp()

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get environment state value."""
        return self.state.get(key, default)


@dataclass
class Object:
    """
    Object - Targets of agent actions.

    Objects are entities that agents act upon or interact with.
    They can be physical items, digital assets, services, or abstract concepts.
    """
    id: str = field(default_factory=generate_id)
    name: str = ""
    type: str = "generic"
    properties: dict[str, Any] = field(default_factory=dict)
    current_state: dict[str, Any] = field(default_factory=dict)
    owner_agent_id: str | None = None
    created_at: float = field(default_factory=get_timestamp)
    updated_at: float = field(default_factory=get_timestamp)
    metadata: dict[str, Any] = field(default_factory=dict)

    def update_property(self, key: str, value: Any) -> None:
        """Update object property."""
        self.properties[key] = value
        self.updated_at = get_timestamp()

    def update_state(self, key: str, value: Any) -> None:
        """Update object current state."""
        self.current_state[key] = value
        self.updated_at = get_timestamp()


@dataclass
class Agent:
    """
    Agent - Primary entity with perception, decision-making, and action capabilities.

    Agents are the central actors in the USMSB model. They can be humans,
    AI systems, organizations, or any entity that can perceive, decide, and act.

    The Agent class integrates goals, resources, rules, and maintains state
    to enable the Goal-Action-Outcome Loop.
    """
    id: str = field(default_factory=generate_id)
    name: str = ""
    type: AgentType = AgentType.AI_AGENT
    capabilities: list[str] = field(default_factory=list)
    state: dict[str, Any] = field(default_factory=dict)
    goals: list[Goal] = field(default_factory=list)
    resources: list[Resource] = field(default_factory=list)
    rules: list[Rule] = field(default_factory=list)
    information_buffer: list[Information] = field(default_factory=list)
    created_at: float = field(default_factory=get_timestamp)
    updated_at: float = field(default_factory=get_timestamp)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.type, str):
            self.type = AgentType(self.type)

    def add_goal(self, goal: Goal) -> None:
        """Add a goal to the agent."""
        goal.associated_agent_id = self.id
        self.goals.append(goal)
        self.updated_at = get_timestamp()

    def remove_goal(self, goal_id: str) -> bool:
        """Remove a goal from the agent."""
        for i, goal in enumerate(self.goals):
            if goal.id == goal_id:
                self.goals.pop(i)
                self.updated_at = get_timestamp()
                return True
        return False

    def get_active_goals(self) -> list[Goal]:
        """Get all active (pending or in-progress) goals."""
        return [g for g in self.goals if g.status in (GoalStatus.PENDING, GoalStatus.IN_PROGRESS)]

    def get_highest_priority_goal(self) -> Goal | None:
        """Get the highest priority active goal."""
        active_goals = self.get_active_goals()
        if not active_goals:
            return None
        return max(active_goals, key=lambda g: g.priority)

    def add_resource(self, resource: Resource) -> None:
        """Add a resource to the agent."""
        resource.owner_agent_id = self.id
        self.resources.append(resource)
        self.updated_at = get_timestamp()

    def get_resource_by_type(self, resource_type: ResourceType) -> list[Resource]:
        """Get resources by type."""
        return [r for r in self.resources if r.type == resource_type]

    def add_rule(self, rule: Rule) -> None:
        """Add a rule constraint to the agent."""
        self.rules.append(rule)
        self.updated_at = get_timestamp()

    def add_information(self, information: Information) -> None:
        """Add information to the agent's buffer."""
        self.information_buffer.append(information)
        # Keep buffer at reasonable size
        max_buffer_size = self.metadata.get("max_buffer_size", 100)
        if len(self.information_buffer) > max_buffer_size:
            self.information_buffer = self.information_buffer[-max_buffer_size:]
        self.updated_at = get_timestamp()

    def clear_information_buffer(self) -> None:
        """Clear the information buffer."""
        self.information_buffer.clear()
        self.updated_at = get_timestamp()

    def update_state(self, key: str, value: Any) -> None:
        """Update agent state."""
        self.state[key] = value
        self.updated_at = get_timestamp()

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get agent state value."""
        return self.state.get(key, default)

    def has_capability(self, capability: str) -> bool:
        """Check if agent has a specific capability."""
        return capability in self.capabilities

    def add_capability(self, capability: str) -> None:
        """Add a capability to the agent."""
        if capability not in self.capabilities:
            self.capabilities.append(capability)
            self.updated_at = get_timestamp()

    def to_dict(self) -> dict[str, Any]:
        """Convert agent to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "capabilities": self.capabilities,
            "state": self.state,
            "goals": [{"id": g.id, "name": g.name, "status": g.status.value} for g in self.goals],
            "goals_count": len(self.goals),
 "resources": [
                {
                    "id": r.id,
                    "name": r.name,
                    "type": r.type.value,
                    "quantity": r.quantity,
                }
                for r in self.resources
            ],
            "rules_count": len(self.rules),
            "information_buffer_size": len(self.information_buffer),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    # ========== Proactive Behavior Methods ==========

    def has_resources(self) -> bool:
        """Check if agent has available resources."""
        return any(r.status == "available" and r.quantity > 0 for r in self.resources)

    def get_available_resources(self) -> list["Resource"]:
        """Get all available resources."""
        return [r for r in self.resources if r.status == "available" and r.quantity > 0]

    def is_supplier(self) -> bool:
        """Check if agent can provide services."""
        return len(self.get_available_resources()) > 0 or len(self.capabilities) > 0

    def is_demander(self) -> bool:
        """Check if agent has active goals (demands)."""
        return len(self.get_active_goals()) > 0

    def can_collaborate(self) -> bool:
        """Check if agent supports collaboration."""
        return self.metadata.get("collaboration_enabled", True)

    def add_match_history(self, match_result: dict[str, Any]) -> None:
        """Add a match result to history for learning."""
        if "match_history" not in self.metadata:
            self.metadata["match_history"] = []
        self.metadata["match_history"].append({
            **match_result,
            "timestamp": get_timestamp()
        })
        # Keep history at reasonable size
        max_history = self.metadata.get("max_match_history", 100)
        if len(self.metadata["match_history"]) > max_history:
            self.metadata["match_history"] = self.metadata["match_history"][-max_history:]

    def get_match_history(self) -> list[dict[str, Any]]:
        """Get match history for learning."""
        return self.metadata.get("match_history", [])

    def update_reputation(self, new_reputation: float) -> None:
        """Update agent reputation score."""
        self.metadata["reputation"] = max(0.0, min(1.0, new_reputation))
        self.updated_at = get_timestamp()

    def get_reputation(self) -> float:
        """Get agent reputation score."""
        return self.metadata.get("reputation", 1.0)

    def add_negotiation_result(self, result: dict[str, Any]) -> None:
        """Add negotiation result to history."""
        if "negotiation_history" not in self.metadata:
            self.metadata["negotiation_history"] = []
        self.metadata["negotiation_history"].append({
            **result,
            "timestamp": get_timestamp()
        })
        max_history = self.metadata.get("max_negotiation_history", 50)
        if len(self.metadata["negotiation_history"]) > max_history:
            self.metadata["negotiation_history"] = (
                self.metadata["negotiation_history"][-max_history:]
            )

    def get_negotiation_success_rate(self) -> float:
        """Calculate negotiation success rate from history."""
        history = self.metadata.get("negotiation_history", [])
        if not history:
            return 0.5  # Default neutral
        successful = sum(1 for h in history if h.get("success", False))
        return successful / len(history)

    def suggest_price(self, base_price: float, context: dict[str, Any] = None) -> float:
        """Suggest a price based on reputation and market context."""
        reputation = self.get_reputation()
        # Higher reputation = can charge more
        reputation_factor = 0.8 + (reputation * 0.4)  # 1.2 to 1.2
        return base_price * reputation_factor

    def __repr__(self) -> str:
        return f"Agent(id={self.id}, name={self.name}, type={self.type})"
