"""
Value Contract Data Models

Phase 2 of USMSB Agent Platform implementation.

Defines the Value Contract hierarchy:
- ValueFlow: Single value transfer (uses USMSB Resource + Value)
- ContractRisk: Contract risk terms (uses USMSB Risk)
- BaseValueContract: Abstract base for all contracts
- TaskValueContract: Task-level contract (fine-grained)
- ProjectValueContract: Project-level contract (coarse-grained, contains tasks)
"""

from dataclasses import dataclass, field
from typing import Any

from usmsb_sdk.core.elements import Resource, Risk, Value


# ============== ValueFlow ==============


@dataclass
class ValueFlow:
    """
    Represents a single value transfer in a contract.

    Uses USMSB Resource and Value elements.
    A contract has one or more ValueFlows that define how value moves
    between parties.

    Example:
        Agent A provides 100 TFLOPS of computation
        → Resource: {type: "computational", quantity: 100}
        → Value: {type: "economic", metric: 10.0}  # worth 10 VIBE
        → Trigger: "on_delivery"
    """

    flow_id: str = ""
    from_agent_id: str = ""
    to_agent_id: str = ""
    resource: Resource | None = None  # USMSB Resource
    value: Value | None = None  # USMSB Value
    trigger: str = "on_delivery"  # on_delivery | on_completion | on_milestone
    status: str = "pending"  # pending | executed | failed
    executed_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "flow_id": self.flow_id,
            "from_agent_id": self.from_agent_id,
            "to_agent_id": self.to_agent_id,
            "resource": {
                "id": self.resource.id if self.resource else "",
                "name": self.resource.name if self.resource else "",
                "type": self.resource.type.value if self.resource else "",
                "quantity": self.resource.quantity if self.resource else 0,
            } if self.resource else None,
            "value": {
                "id": self.value.id if self.value else "",
                "name": self.value.name if self.value else "",
                "type": self.value.type.value if self.value else "",
                "metric": self.value.metric if self.value else 0.0,
            } if self.value else None,
            "trigger": self.trigger,
            "status": self.status,
            "executed_at": self.executed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ValueFlow":
        resource = None
        if data.get("resource"):
            r = data["resource"]
            resource = Resource(
                id=r.get("id", ""),
                name=r.get("name", ""),
                type=r.get("type", "tangible"),
                quantity=r.get("quantity", 0),
            )

        value = None
        if data.get("value"):
            v = data["value"]
            value = Value(
                id=v.get("id", ""),
                name=v.get("name", ""),
                type=v.get("type", "economic"),
                metric=v.get("metric"),
            )

        return cls(
            flow_id=data.get("flow_id", ""),
            from_agent_id=data.get("from_agent_id", ""),
            to_agent_id=data.get("to_agent_id", ""),
            resource=resource,
            value=value,
            trigger=data.get("trigger", "on_delivery"),
            status=data.get("status", "pending"),
            executed_at=data.get("executed_at", 0.0),
        )


# ============== ContractRisk ==============


@dataclass
class ContractRisk:
    """
    Represents a risk term in a contract.

    Uses USMSB Risk element.
    Defines identified risks, their probability/impact, and mitigation plans.
    """

    risk_id: str = ""
    risk_type: str = ""  # risk type string
    probability: float = 0.0  # 0.0 ~ 1.0
    impact: float = 0.0  # 0.0 ~ 1.0
    mitigation: str = ""  # Description of mitigation strategy
    fallback_action: str = ""  # What to do if risk materializes

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_id": self.risk_id,
            "risk_type": self.risk_type,
            "probability": self.probability,
            "impact": self.impact,
            "mitigation": self.mitigation,
            "fallback_action": self.fallback_action,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContractRisk":
        return cls(
            risk_id=data.get("risk_id", ""),
            risk_type=data.get("risk_type", ""),
            probability=data.get("probability", 0.0),
            impact=data.get("impact", 0.0),
            mitigation=data.get("mitigation", ""),
            fallback_action=data.get("fallback_action", ""),
        )


# ============== Contract Milestone ==============


@dataclass
class ContractMilestone:
    """
    A milestone in a contract.

    Represents a checkpoint at which partial payment or delivery occurs.
    """

    milestone_id: str = ""
    name: str = ""
    description: str = ""
    payment_percentage: float = 0.0  # 0.0 ~ 1.0 of total value
    status: str = "pending"  # pending | completed | failed
    criteria: dict[str, Any] | None = None
    completed_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "milestone_id": self.milestone_id,
            "name": self.name,
            "description": self.description,
            "payment_percentage": self.payment_percentage,
            "status": self.status,
            "criteria": self.criteria,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContractMilestone":
        return cls(
            milestone_id=data.get("milestone_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            payment_percentage=data.get("payment_percentage", 0.0),
            status=data.get("status", "pending"),
            criteria=data.get("criteria"),
            completed_at=data.get("completed_at", 0.0),
        )


# ============== BaseValueContract ==============


@dataclass
class BaseValueContract:
    """
    Abstract base class for Value Contracts.

    Defines the common structure for all contract types (Task and Project).
    Contains the USMSB elements: ValueFlows, ContractRisks, transformation_path.

    A Value Contract represents:
    - WHO are involved (parties)
    - WHAT they commit to do (transformation_path)
    - HOW value flows (value_flows)
    - WHAT could go wrong (risks)
    """

    contract_id: str = ""
    contract_type: str = ""  # "task" | "project"

    # Parties involved (Agent IDs)
    parties: list[str] = field(default_factory=list)

    # USMSB transformation path: "投入 → 产出 → 回报" description
    # Example: "富余算力 → 复杂推理任务完成 → VIBE 收益"
    transformation_path: str = ""

    # Value flows in this contract
    value_flows: list[ValueFlow] = field(default_factory=list)

    # Contract risks
    risks: list[ContractRisk] = field(default_factory=list)

    # Contract status
    status: str = "draft"  # draft | proposed | accepted | active | completed | disputed | cancelled

    # Version for optimistic locking
    version: int = 1

    # Timestamps
    created_at: float = 0.0
    updated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_type": self.contract_type,
            "parties": self.parties,
            "transformation_path": self.transformation_path,
            "value_flows": [vf.to_dict() for vf in self.value_flows],
            "risks": [r.to_dict() for r in self.risks],
            "status": self.status,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ============== TaskValueContract ==============


@dataclass
class TaskValueContract(BaseValueContract):
    """
    Task-level Value Contract (fine-grained).

    Represents a single task with clear deliverables, deadline, and payment.

    Used for:
    - Simple tasks (centered matching)
    - Sub-tasks within a Project
    """

    contract_type: str = "task"

    # Reference to parent project (if this task is part of a project)
    parent_project_id: str | None = None

    # Task definition
    task_definition: dict[str, Any] = field(default_factory=dict)
    # {
    #     "title": str,
    #     "description": str,
    #     "requirements": list[str],
    #     "deliverables": list[str],
    #     "acceptance_criteria": str,
    # }

    # Milestone checkpoints
    milestone_checkpoints: list[ContractMilestone] = field(default_factory=list)

    # Deadline (Unix timestamp)
    deadline: float = 0.0

    # Linked Goal ID (which USMSB Goal this task serves)
    linked_goal_id: str | None = None

    # Payment
    price_vibe: float = 0.0  # Total price in VIBE
    penalty_vibe: float | None = None  # Penalty if supply side fails

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "parent_project_id": self.parent_project_id,
                "task_definition": self.task_definition,
                "milestone_checkpoints": [m.to_dict() for m in self.milestone_checkpoints],
                "deadline": self.deadline,
                "linked_goal_id": self.linked_goal_id,
                "price_vibe": self.price_vibe,
                "penalty_vibe": self.penalty_vibe,
            }
        )
        return base


# ============== ProjectValueContract ==============


@dataclass
class ProjectValueContract(BaseValueContract):
    """
    Project-level Value Contract (coarse-grained).

    Represents a multi-task project with phases, milestones, and total budget.
    Contains child TaskValueContracts.

    Used for:
    - Complex projects requiring multiple agents
    - Strategic collaborations
    """

    contract_type: str = "project"

    project_id: str = ""

    # Project definition
    project_definition: dict[str, Any] = field(default_factory=dict)
    # {
    #     "title": str,
    #     "goal_description": str,
    #     "scope": str,
    #     "success_criteria": list[str],
    # }

    # Total budget in VIBE
    total_budget_vibe: float = 0.0

    # Child task contract IDs
    child_task_contract_ids: list[str] = field(default_factory=list)

    # Project Goal ID (USMSB Goal)
    project_goal_id: str = ""

    # Phase milestones
    phase_milestones: list[ContractMilestone] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "project_id": self.project_id,
                "project_definition": self.project_definition,
                "total_budget_vibe": self.total_budget_vibe,
                "child_task_contract_ids": self.child_task_contract_ids,
                "project_goal_id": self.project_goal_id,
                "phase_milestones": [m.to_dict() for m in self.phase_milestones],
            }
        )
        return base
