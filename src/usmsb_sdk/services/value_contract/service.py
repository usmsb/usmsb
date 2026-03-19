"""
Value Contract Service

Phase 2 of USMSB Agent Platform implementation.

Manages the full lifecycle of Value Contracts:
- Create task or project contracts
- Propose, accept, decline contracts
- Deliver and confirm task completion
- Execute value flows (VIBE transfers)
- Handle disputes

This service replaces the legacy OrderService.
"""

import logging
import time
import uuid
from typing import Any

from sqlalchemy.orm import Session

from usmsb_sdk.core.elements import Goal, Resource, Value
from usmsb_sdk.services.schema import (
    ContractMilestoneDB,
    ContractRiskDB,
    ContractValueFlowDB,
    ValueContractDB,
)
from usmsb_sdk.services.value_contract.models import (
    BaseValueContract,
    ContractMilestone,
    ContractRisk,
    ProjectValueContract,
    TaskValueContract,
    ValueFlow,
)

logger = logging.getLogger(__name__)


class ValueContractService:
    """
    Service for managing Value Contracts.

    Provides CRUD operations and lifecycle management for contracts.
    """

    def __init__(self, db_session: Session):
        self.db = db_session

    # ============== Create ==============

    async def create_task_contract(
        self,
        task_def: dict[str, Any],
        demand_agent_id: str,
        supply_agent_id: str,
        price_vibe: float,
        template_id: str = "simple_task",
        linked_goal_id: str | None = None,
        deadline: float = 0.0,
        penalty_vibe: float | None = None,
        transformation_path: str = "",
        extra_terms: dict[str, Any] | None = None,
    ) -> TaskValueContract:
        """
        Create a new Task Contract.

        Args:
            task_def: Task definition {title, description, requirements, deliverables}
            demand_agent_id: Agent requesting the task
            supply_agent_id: Agent who will perform the task
            price_vibe: Total price in VIBE
            template_id: Contract template to use (default: simple_task)
            linked_goal_id: USMSB Goal this task serves
            deadline: Unix timestamp for deadline
            penalty_vibe: Penalty for failure
            transformation_path: Description of value transformation
            extra_terms: Additional terms to merge with template

        Returns:
            Created TaskValueContract
        """
        contract_id = f"contract-{uuid.uuid4().hex[:12]}"
        now = time.time()

        if deadline == 0.0:
            deadline = now + 86400  # Default 1 day

        # Create ValueFlow for payment
        payment_flow = ValueFlow(
            flow_id=f"flow-{uuid.uuid4().hex[:8]}",
            from_agent_id=demand_agent_id,
            to_agent_id=supply_agent_id,
            resource=Resource(
                id=f"res-{uuid.uuid4().hex[:8]}",
                name="Task Execution",
                type="service",
                quantity=1,
            ),
            value=Value(
                id=f"val-{uuid.uuid4().hex[:8]}",
                name="Task Payment",
                type="economic",
                metric=price_vibe,
            ),
            trigger="on_delivery",
            status="pending",
        )

        # Create base contract
        contract = TaskValueContract(
            contract_id=contract_id,
            contract_type="task",
            parties=[demand_agent_id, supply_agent_id],
            transformation_path=transformation_path or f"Task completion by {supply_agent_id} for {demand_agent_id}",
            value_flows=[payment_flow],
            risks=[],
            status="draft",
            version=1,
            created_at=now,
            updated_at=now,
            task_definition=task_def,
            deadline=deadline,
            linked_goal_id=linked_goal_id,
            price_vibe=price_vibe,
            penalty_vibe=penalty_vibe,
        )

        # Persist to DB
        await self._save_contract(contract)

        logger.info(f"Created TaskContract {contract_id}: {demand_agent_id} -> {supply_agent_id}, {price_vibe} VIBE")
        return contract

    async def create_project_contract(
        self,
        project_def: dict[str, Any],
        owner_agent_id: str,
        participants: list[str],
        total_budget: float,
        template_id: str = "project",
        project_goal_id: str | None = None,
        transformation_path: str = "",
    ) -> ProjectValueContract:
        """
        Create a new Project Contract.

        Args:
            project_def: Project definition {title, goal_description, scope, success_criteria}
            owner_agent_id: Agent who owns the project
            participants: List of participating Agent IDs
            total_budget: Total budget in VIBE
            template_id: Contract template to use
            project_goal_id: USMSB Goal this project serves
            transformation_path: Description of project value transformation

        Returns:
            Created ProjectValueContract
        """
        project_id = f"project-{uuid.uuid4().hex[:12]}"
        contract_id = f"contract-{uuid.uuid4().hex[:12]}"
        now = time.time()

        all_parties = list(set([owner_agent_id] + participants))

        contract = ProjectValueContract(
            contract_id=contract_id,
            contract_type="project",
            parties=all_parties,
            transformation_path=transformation_path or project_def.get("title", "Project collaboration"),
            value_flows=[],
            risks=[],
            status="draft",
            version=1,
            created_at=now,
            updated_at=now,
            project_id=project_id,
            project_definition=project_def,
            total_budget_vibe=total_budget,
            child_task_contract_ids=[],
            project_goal_id=project_goal_id or "",
        )

        await self._save_contract(contract)

        logger.info(f"Created ProjectContract {contract_id}: owner={owner_agent_id}, budget={total_budget} VIBE")
        return contract

    async def add_task_to_project(
        self,
        project_id: str,
        task_def: dict[str, Any],
        assigned_agent_id: str,
        price: float,
    ) -> TaskValueContract:
        """
        Add a Task Contract to an existing Project.

        Args:
            project_id: Parent project's contract_id
            task_def: Task definition
            assigned_agent_id: Agent assigned to perform the task
            price: Task price in VIBE

        Returns:
            Created TaskValueContract linked to project
        """
        # Get parent project
        parent = await self.get_contract(project_id)
        if not parent or parent.contract_type != "project":
            raise ValueError(f"Project {project_id} not found or not a project")

        # Create task contract
        task = await self.create_task_contract(
            task_def=task_def,
            demand_agent_id=parent.parties[0],  # Owner is demand
            supply_agent_id=assigned_agent_id,
            price_vibe=price,
        )
        task.parent_project_id = project_id
        task.status = "draft"

        # Update parent project
        parent.child_task_contract_ids.append(task.contract_id)
        parent.updated_at = time.time()
        await self._save_contract(parent)
        await self._save_contract(task)

        return task

    # ============== Lifecycle ==============

    async def get_contract(self, contract_id: str) -> BaseValueContract | None:
        """Get a contract by ID."""
        db_record = self.db.query(ValueContractDB).filter(
            ValueContractDB.contract_id == contract_id
        ).first()

        if not db_record:
            return None

        return await self._db_to_contract(db_record)

    # Valid state transitions
    STATE_TRANSITIONS = {
        "draft": ["proposed", "cancelled"],
        "proposed": ["accepted", "declined", "cancelled"],
        "accepted": ["active", "cancelled"],
        "active": ["completed", "disputed", "cancelled"],
        "completed": [],  # Terminal state
        "disputed": ["completed", "cancelled"],
        "cancelled": [],  # Terminal state
        "declined": [],  # Terminal state
    }

    def _validate_state_transition(
        self,
        contract_id: str,
        current_status: str,
        target_status: str,
    ) -> None:
        """
        Validate that a state transition is allowed.

        D7 Fix: Added state machine validation.

        Raises ValueError if transition is not allowed.
        """
        valid_targets = self.STATE_TRANSITIONS.get(current_status, [])

        if target_status not in valid_targets:
            raise ValueError(
                f"Invalid state transition for contract {contract_id}: "
                f"{current_status} -> {target_status}. "
                f"Allowed transitions: {valid_targets}"
            )

    async def propose_contract(
        self,
        contract_id: str,
        proposer_agent_id: str,
    ) -> BaseValueContract:
        """
        Propose a contract (change status from draft to proposed).

        Args:
            contract_id: Contract to propose
            proposer_agent_id: Agent proposing the contract

        Returns:
            Updated contract
        """
        contract = await self.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        if proposer_agent_id not in contract.parties:
            raise ValueError(f"Agent {proposer_agent_id} is not a party to contract {contract_id}")

        if contract.status != "draft":
            raise ValueError(f"Contract {contract_id} is not in draft status")

        # D7 Fix: Validate state transition
        self._validate_state_transition(contract_id, contract.status, "proposed")

        contract.status = "proposed"
        contract.updated_at = time.time()
        await self._save_contract(contract)

        logger.info(f"Contract {contract_id} proposed by {proposer_agent_id}")
        return contract

    async def accept_contract(
        self,
        contract_id: str,
        accepting_agent_id: str,
    ) -> BaseValueContract:
        """
        Accept a contract (change status from proposed to active).

        Args:
            contract_id: Contract to accept
            accepting_agent_id: Agent accepting the contract

        Returns:
            Updated contract (now active)
        """
        contract = await self.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        if accepting_agent_id not in contract.parties:
            raise ValueError(f"Agent {accepting_agent_id} is not a party")

        if contract.status != "proposed":
            raise ValueError(f"Contract {contract_id} is not in proposed status")

        # D7 Fix: Validate state transition
        self._validate_state_transition(contract_id, contract.status, "active")

        contract.status = "active"
        contract.updated_at = time.time()
        contract.version += 1
        await self._save_contract(contract)

        logger.info(f"Contract {contract_id} accepted by {accepting_agent_id}, now active")
        return contract

    async def decline_contract(
        self,
        contract_id: str,
        declining_agent_id: str,
        reason: str = "",
    ) -> None:
        """
        Decline a contract (cancel it).

        Args:
            contract_id: Contract to decline
            declining_agent_id: Agent declining
            reason: Optional reason
        """
        contract = await self.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        if contract.status in ("completed", "cancelled"):
            raise ValueError(f"Contract {contract_id} cannot be declined in status {contract.status}")

        # D7 Fix: Validate state transition
        self._validate_state_transition(contract_id, contract.status, "cancelled")

        contract.status = "cancelled"
        contract.updated_at = time.time()
        await self._save_contract(contract)

        logger.info(f"Contract {contract_id} declined by {declining_agent_id}: {reason}")

    async def deliver_task(
        self,
        contract_id: str,
        deliverables: dict[str, Any],
        supply_agent_id: str,
    ) -> BaseValueContract:
        """
        Mark a task as delivered (awaiting confirmation).

        Args:
            contract_id: Contract ID
            deliverables: Delivery data {description, files, links, etc.}
            supply_agent_id: Agent delivering the task

        Returns:
            Updated contract
        """
        contract = await self.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        if supply_agent_id not in contract.parties:
            raise ValueError(f"Agent {supply_agent_id} is not a party")

        if contract.status != "active":
            raise ValueError(f"Contract {contract_id} is not active")

        # D7 Fix: Validate state transition (deliver doesn't change status, just marks delivery)
        # Status stays active until confirmed

        # Store deliverables in task_definition
        if hasattr(contract, "task_definition"):
            contract.task_definition["deliverables"] = deliverables
            contract.task_definition["delivered_at"] = time.time()
            contract.task_definition["delivered_by"] = supply_agent_id

        contract.updated_at = time.time()
        await self._save_contract(contract)

        logger.info(f"Contract {contract_id} delivered by {supply_agent_id}")
        return contract

    async def confirm_delivery(
        self,
        contract_id: str,
        quality_approved: bool,
        quality_feedback: dict[str, Any] | None = None,
        demand_agent_id: str | None = None,
    ) -> BaseValueContract:
        """
        Confirm task delivery (trigger value flow execution).

        Args:
            contract_id: Contract ID
            quality_approved: Whether delivery meets quality standards
            quality_feedback: Feedback on delivery quality
            demand_agent_id: Agent confirming (optional, auto-detected if not provided)

        Returns:
            Updated contract
        """
        contract = await self.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        if contract.status != "active":
            raise ValueError(f"Contract {contract_id} is not active")

        # D7 Fix: Validate state transition
        target_status = "disputed" if not quality_approved else "completed"
        self._validate_state_transition(contract_id, contract.status, target_status)

        if not quality_approved:
            contract.status = "disputed"
            if quality_feedback:
                contract.task_definition["quality_feedback"] = quality_feedback
            await self._save_contract(contract)
            logger.warning(f"Contract {contract_id} disputed by demand side")
            return contract

        # Quality approved - complete the contract
        contract.status = "completed"
        if hasattr(contract, "task_definition"):
            contract.task_definition["confirmed_at"] = time.time()
            contract.task_definition["quality_feedback"] = quality_feedback or {}

        contract.updated_at = time.time()
        contract.version += 1
        await self._save_contract(contract)

        # Execute value flows
        for i, flow in enumerate(contract.value_flows):
            if flow.status == "pending":
                await self.execute_value_flow(contract_id, i)

        logger.info(f"Contract {contract_id} completed, value flows executed")
        return contract

    # ============== Value Flow ==============

    async def execute_value_flow(
        self,
        contract_id: str,
        flow_index: int,
    ) -> ValueFlow | None:
        """
        Execute a value flow (trigger VIBE transfer).

        This method handles the actual VIBE transfer via the blockchain integration.
        Currently stubs the transfer - real implementation would call joint_order_pool_manager.

        Args:
            contract_id: Contract ID
            flow_index: Index of the value_flow to execute

        Returns:
            Updated ValueFlow or None
        """
        contract = await self.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        if flow_index < 0 or flow_index >= len(contract.value_flows):
            raise ValueError(f"Invalid flow index {flow_index}")

        flow = contract.value_flows[flow_index]

        if flow.status != "pending":
            logger.warning(f"Flow {flow.flow_id} is not pending, skipping")
            return flow

        # TODO: Integrate with joint_order_pool_manager for actual VIBE transfer
        # For now, mark as executed
        flow.status = "executed"
        flow.executed_at = time.time()

        # Update contract
        contract.updated_at = time.time()
        await self._save_contract(contract)

        logger.info(f"ValueFlow {flow.flow_id} executed: {flow.from_agent_id} -> {flow.to_agent_id}, {flow.value.metric if flow.value else 0} VIBE")
        return flow

    # ============== Risk Management ==============

    async def add_risk(
        self,
        contract_id: str,
        risk_type: str,
        probability: float,
        impact: float,
        mitigation: str = "",
        fallback_action: str = "",
    ) -> ContractRisk:
        """Add a risk term to a contract."""
        contract = await self.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        risk = ContractRisk(
            risk_id=f"risk-{uuid.uuid4().hex[:8]}",
            risk_type=risk_type,
            probability=probability,
            impact=impact,
            mitigation=mitigation,
            fallback_action=fallback_action,
        )

        contract.risks.append(risk)
        contract.updated_at = time.time()
        await self._save_contract(contract)

        logger.info(f"Risk {risk.risk_id} added to contract {contract_id}")
        return risk

    # ============== Helpers ==============

    async def _save_contract(self, contract: BaseValueContract) -> None:
        """Save or update a contract in the database."""
        existing = self.db.query(ValueContractDB).filter(
            ValueContractDB.contract_id == contract.contract_id
        ).first()

        if existing:
            # Update
            existing.status = contract.status
            existing.contract_type = contract.contract_type
            existing.parties = contract.parties
            existing.transformation_path = contract.transformation_path
            existing.version = contract.version
            existing.updated_at = contract.updated_at
        else:
            # Insert
            db_record = ValueContractDB(
                contract_id=contract.contract_id,
                contract_type=contract.contract_type,
                parties=contract.parties,
                transformation_path=contract.transformation_path,
                status=contract.status,
                version=contract.version,
                contract_data=contract.to_dict(),
                created_at=contract.created_at,
                updated_at=contract.updated_at,
            )
            self.db.add(db_record)

        self.db.commit()

    async def _db_to_contract(self, db_record: ValueContractDB) -> BaseValueContract:
        """Convert DB record to contract object."""
        data = db_record.contract_data or {}

        if db_record.contract_type == "task":
            contract = TaskValueContract(
                contract_id=db_record.contract_id,
                contract_type=db_record.contract_type,
                parties=db_record.parties or [],
                transformation_path=db_record.transformation_path or "",
                status=db_record.status,
                version=db_record.version,
                created_at=float(db_record.created_at.timestamp()) if db_record.created_at else 0.0,
                updated_at=float(db_record.updated_at.timestamp()) if db_record.updated_at else 0.0,
            )
        else:
            contract = ProjectValueContract(
                contract_id=db_record.contract_id,
                contract_type=db_record.contract_type,
                parties=db_record.parties or [],
                transformation_path=db_record.transformation_path or "",
                status=db_record.status,
                version=db_record.version,
                created_at=float(db_record.created_at.timestamp()) if db_record.created_at else 0.0,
                updated_at=float(db_record.updated_at.timestamp()) if db_record.updated_at else 0.0,
            )

        # Parse value flows from contract_data
        if "value_flows" in data:
            contract.value_flows = [ValueFlow.from_dict(vf) for vf in data["value_flows"]]

        # Parse risks
        if "risks" in data:
            contract.risks = [ContractRisk.from_dict(r) for r in data["risks"]]

        # Type-specific fields
        if db_record.contract_type == "task":
            contract.task_definition = data.get("task_definition", {})
            contract.deadline = data.get("deadline", 0.0)
            contract.price_vibe = data.get("price_vibe", 0.0)
            contract.penalty_vibe = data.get("penalty_vibe")
            contract.parent_project_id = data.get("parent_project_id")
            contract.linked_goal_id = data.get("linked_goal_id")
        else:
            contract.project_definition = data.get("project_definition", {})
            contract.total_budget_vibe = data.get("total_budget_vibe", 0.0)
            contract.child_task_contract_ids = data.get("child_task_contract_ids", [])
            contract.project_goal_id = data.get("project_goal_id", "")

        return contract
