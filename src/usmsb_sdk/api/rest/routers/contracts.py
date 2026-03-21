"""
Value Contract API Endpoints.

Phase 2 of USMSB Agent Platform implementation.

Endpoints:
- POST   /api/contracts/task              - Create task contract
- POST   /api/contracts/project           - Create project contract
- GET    /api/contracts/{id}             - Get contract
- POST   /api/contracts/{id}/propose     - Propose contract
- POST   /api/contracts/{id}/accept      - Accept contract
- POST   /api/contracts/{id}/decline      - Decline contract
- POST   /api/contracts/{id}/deliver     - Mark task delivered
- POST   /api/contracts/{id}/confirm     - Confirm delivery
- POST   /api/contracts/{id}/cancel      - Cancel contract
- POST   /api/contracts/{id}/risks       - Add risk
- GET    /api/contracts/templates        - List contract templates

Authentication:
- Require X-API-Key + X-Agent-ID headers
"""

import os
import time
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from usmsb_sdk.api.rest.unified_auth import get_current_user_unified
from usmsb_sdk.services.schema import create_session
from usmsb_sdk.services.value_contract import (
    TaskValueContract,
    ProjectValueContract,
    ValueContractService,
    list_templates,
)

router = APIRouter(prefix="/contracts", tags=["Value Contracts"])


# ============== Request Models ==============


class TaskContractCreate(BaseModel):
    """Create a task contract."""
    task_definition: dict[str, Any] = Field(
        ...,
        description="Task definition: {title, description, requirements, deliverables}"
    )
    supply_agent_id: str = Field(..., description="Agent who will perform the task")
    price_vibe: float = Field(..., ge=0.0, description="Total price in VIBE")
    template_id: str = Field(default="simple_task", description="Template to use")
    linked_goal_id: str | None = Field(default=None, description="USMSB Goal ID")
    deadline: float = Field(default=0.0, description="Unix timestamp deadline (0=default 1 day)")
    penalty_vibe: float | None = Field(default=None, description="Penalty for failure")
    transformation_path: str = Field(default="", description="Value transformation description")


class ProjectContractCreate(BaseModel):
    """Create a project contract."""
    project_definition: dict[str, Any] = Field(
        ...,
        description="Project definition: {title, goal_description, scope, success_criteria}"
    )
    participants: list[str] = Field(
        ...,
        description="List of participating Agent IDs"
    )
    total_budget: float = Field(..., ge=0.0, description="Total budget in VIBE")
    template_id: str = Field(default="project", description="Template to use")
    project_goal_id: str | None = Field(default=None, description="USMSB Goal ID")
    transformation_path: str = Field(default="", description="Value transformation description")


class AddTaskToProject(BaseModel):
    """Add a task to existing project."""
    task_definition: dict[str, Any] = Field(..., description="Task definition")
    assigned_agent_id: str = Field(..., description="Agent to assign task to")
    price: float = Field(..., ge=0.0, description="Task price in VIBE")


class DeliveryConfirm(BaseModel):
    """Confirm task delivery."""
    quality_approved: bool = Field(..., description="Whether delivery meets quality")
    quality_feedback: dict[str, Any] | None = Field(default=None, description="Quality feedback")


class DeclineRequest(BaseModel):
    """Decline a contract."""
    reason: str = Field(default="", description="Reason for declining")


class AddRiskRequest(BaseModel):
    """Add a risk to contract."""
    risk_type: str = Field(..., description="Type of risk")
    probability: float = Field(..., ge=0.0, le=1.0, description="Probability 0-1")
    impact: float = Field(..., ge=0.0, le=1.0, description="Impact 0-1")
    mitigation: str = Field(default="", description="Mitigation strategy")
    fallback_action: str = Field(default="", description="Fallback if risk occurs")


# ============== Response Models ==============


class ContractResponse(BaseModel):
    """Contract response."""
    contract_id: str
    contract_type: str
    parties: list[str]
    transformation_path: str
    status: str
    price_vibe: float = 0.0
    total_budget_vibe: float = 0.0
    version: int
    created_at: float
    updated_at: float
    task_definition: dict[str, Any] | None = None
    project_definition: dict[str, Any] | None = None


class TemplateResponse(BaseModel):
    """Contract template response."""
    template_id: str
    name: str
    description: str
    contract_type: str
    variable_terms: list[str]
    variable_ranges: dict[str, Any]


# ============== Helper ==============


def get_contract_service() -> ValueContractService:
    """Get ValueContractService instance."""
    session = create_session()
    return ValueContractService(session)


# ============== Endpoints ==============


@router.post("/task", status_code=status.HTTP_201_CREATED)
async def create_task_contract(
    request: TaskContractCreate,
    current_user: dict = Depends(get_current_user_unified),
):
    """Create a new task contract."""
    demand_agent_id = current_user.get("agent_id")
    if not demand_agent_id:
        raise HTTPException(status_code=401, detail="Agent ID not found")

    service = get_contract_service()

    try:
        contract = await service.create_task_contract(
            task_def=request.task_definition,
            demand_agent_id=demand_agent_id,
            supply_agent_id=request.supply_agent_id,
            price_vibe=request.price_vibe,
            template_id=request.template_id,
            linked_goal_id=request.linked_goal_id,
            deadline=request.deadline,
            penalty_vibe=request.penalty_vibe,
            transformation_path=request.transformation_path,
        )
        return ContractResponse(
            contract_id=contract.contract_id,
            contract_type=contract.contract_type,
            parties=contract.parties,
            transformation_path=contract.transformation_path,
            status=contract.status,
            price_vibe=getattr(contract, "price_vibe", 0.0),
            version=contract.version,
            created_at=contract.created_at,
            updated_at=contract.updated_at,
            task_definition=getattr(contract, "task_definition", None),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/project", status_code=status.HTTP_201_CREATED)
async def create_project_contract(
    request: ProjectContractCreate,
    current_user: dict = Depends(get_current_user_unified),
):
    """Create a new project contract."""
    owner_agent_id = current_user.get("agent_id")
    if not owner_agent_id:
        raise HTTPException(status_code=401, detail="Agent ID not found")

    service = get_contract_service()

    try:
        contract = await service.create_project_contract(
            project_def=request.project_definition,
            owner_agent_id=owner_agent_id,
            participants=request.participants,
            total_budget=request.total_budget,
            template_id=request.template_id,
            project_goal_id=request.project_goal_id,
            transformation_path=request.transformation_path,
        )
        return ContractResponse(
            contract_id=contract.contract_id,
            contract_type=contract.contract_type,
            parties=contract.parties,
            transformation_path=contract.transformation_path,
            status=contract.status,
            total_budget_vibe=getattr(contract, "total_budget_vibe", 0.0),
            version=contract.version,
            created_at=contract.created_at,
            updated_at=contract.updated_at,
            project_definition=getattr(contract, "project_definition", None),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{contract_id}")
async def get_contract(
    contract_id: str,
    current_user: dict = Depends(get_current_user_unified),
):
    """Get a contract by ID."""
    service = get_contract_service()
    contract = await service.get_contract(contract_id)

    if not contract:
        raise HTTPException(status_code=404, detail=f"Contract {contract_id} not found")

    return ContractResponse(
        contract_id=contract.contract_id,
        contract_type=contract.contract_type,
        parties=contract.parties,
        transformation_path=contract.transformation_path,
        status=contract.status,
        price_vibe=getattr(contract, "price_vibe", 0.0),
        total_budget_vibe=getattr(contract, "total_budget_vibe", 0.0),
        version=contract.version,
        created_at=contract.created_at,
        updated_at=contract.updated_at,
        task_definition=getattr(contract, "task_definition", None),
        project_definition=getattr(contract, "project_definition", None),
    )


@router.post("/{contract_id}/propose")
async def propose_contract(
    contract_id: str,
    current_user: dict = Depends(get_current_user_unified),
):
    """Propose a contract (draft → proposed)."""
    agent_id = current_user.get("agent_id")
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent ID not found")

    service = get_contract_service()

    try:
        contract = await service.propose_contract(contract_id, agent_id)
        return {"success": True, "contract_id": contract_id, "status": contract.status}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{contract_id}/accept")
async def accept_contract(
    contract_id: str,
    current_user: dict = Depends(get_current_user_unified),
):
    """Accept a contract (proposed → active)."""
    agent_id = current_user.get("agent_id")
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent ID not found")

    service = get_contract_service()

    try:
        contract = await service.accept_contract(contract_id, agent_id)
        return {"success": True, "contract_id": contract_id, "status": contract.status}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{contract_id}/decline")
async def decline_contract(
    contract_id: str,
    request: DeclineRequest,
    current_user: dict = Depends(get_current_user_unified),
):
    """Decline a contract."""
    agent_id = current_user.get("agent_id")
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent ID not found")

    service = get_contract_service()

    try:
        await service.decline_contract(contract_id, agent_id, request.reason)
        return {"success": True, "contract_id": contract_id, "status": "cancelled"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{contract_id}/deliver")
async def deliver_task(
    contract_id: str,
    deliverables: dict[str, Any] = Body(..., description="Delivery data"),
    current_user: dict = Depends(get_current_user_unified),
):
    """Mark task as delivered (awaiting confirmation)."""
    agent_id = current_user.get("agent_id")
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent ID not found")

    service = get_contract_service()

    try:
        contract = await service.deliver_task(contract_id, deliverables, agent_id)
        return {"success": True, "contract_id": contract_id, "status": contract.status}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{contract_id}/confirm")
async def confirm_delivery(
    contract_id: str,
    request: DeliveryConfirm,
    current_user: dict = Depends(get_current_user_unified),
):
    """Confirm task delivery and trigger value flow."""
    agent_id = current_user.get("agent_id")

    service = get_contract_service()

    # Instantiate JointOrderPoolManager for on-chain value flow execution
    joint_order_pool_manager = None
    demand_wallet_address = None
    demand_private_key = None

    # Get platform deployer private key for signing transactions on behalf of users
    # This is set via environment variable for platform-level operations
    platform_deployer_private_key = os.environ.get("WEB3_PLATFORM_DEPLOYER_PRIVATE_KEY")
    if not platform_deployer_private_key:
        import logging
        logging.getLogger(__name__).warning(
            "WEB3_PLATFORM_DEPLOYER_PRIVATE_KEY not set - on-chain confirm_delivery will not execute"
        )

    try:
        from usmsb_sdk.blockchain.config import BlockchainConfig
        from usmsb_sdk.blockchain.web3_client import Web3Client
        from usmsb_sdk.services.joint_order_pool_manager import JointOrderPoolManager
        from usmsb_sdk.blockchain.contracts.joint_order import JointOrderClient

        config = BlockchainConfig.from_env()
        web3_client = Web3Client(config=config)
        joint_order_client = JointOrderClient(web3_client=web3_client, config=config)
        joint_order_pool_manager = JointOrderPoolManager(
            web3_client=web3_client,
            config=config,
            joint_order_client=joint_order_client,
        )

        # Get demand agent's wallet address from the authenticated user
        # The wallet address is used as the from_address for on-chain operations
        from usmsb_sdk.api.database import get_agent_wallet
        wallet = get_agent_wallet(agent_id)
        if wallet:
            demand_wallet_address = wallet.get("wallet_address")

        # Use platform deployer private key for signing (platform wallet pays for gas)
        # This is required because user wallets' private keys are never stored in the DB
        demand_private_key = platform_deployer_private_key

    except Exception as e:
        # Log but don't fail - on-chain execution may not be available
        import logging
        logging.getLogger(__name__).warning(f"Could not initialize JointOrderPoolManager: {e}")

    try:
        contract = await service.confirm_delivery(
            contract_id,
            quality_approved=request.quality_approved,
            quality_feedback=request.quality_feedback,
            demand_agent_id=agent_id,
            joint_order_pool_manager=joint_order_pool_manager,
            demand_wallet_address=demand_wallet_address,
            demand_private_key=demand_private_key,
        )
        return {
            "success": True,
            "contract_id": contract_id,
            "status": contract.status,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{contract_id}/cancel")
async def cancel_contract(
    contract_id: str,
    current_user: dict = Depends(get_current_user_unified),
):
    """Cancel a contract."""
    agent_id = current_user.get("agent_id")
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent ID not found")

    service = get_contract_service()

    try:
        await service.decline_contract(contract_id, agent_id, "Cancelled by party")
        return {"success": True, "contract_id": contract_id, "status": "cancelled"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{contract_id}/risks")
async def add_risk(
    contract_id: str,
    request: AddRiskRequest,
    current_user: dict = Depends(get_current_user_unified),
):
    """Add a risk term to a contract."""
    agent_id = current_user.get("agent_id")
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent ID not found")

    service = get_contract_service()

    try:
        risk = await service.add_risk(
            contract_id,
            risk_type=request.risk_type,
            probability=request.probability,
            impact=request.impact,
            mitigation=request.mitigation,
            fallback_action=request.fallback_action,
        )
        return {"success": True, "risk_id": risk.risk_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/templates")
async def get_templates():
    """List all available contract templates."""
    templates = list_templates()
    return [
        TemplateResponse(
            template_id=t.template_id,
            name=t.name,
            description=t.description,
            contract_type=t.contract_type,
            variable_terms=t.variable_terms,
            variable_ranges=t.variable_ranges,
        )
        for t in templates
    ]
