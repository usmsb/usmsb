"""
AI Agent Registration API endpoints.

Provides multiple registration protocols for AI Agents:
- Standard REST registration with API Key generation
- MCP (Model Context Protocol) registration
- A2A (Agent-to-Agent) protocol registration
- skill.md registration
- Owner binding flow
- API Key management

All registrations use the unified agents table with full field support.
"""

import json
import time
import uuid
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from usmsb_sdk.api.database import (
    complete_binding_request as db_complete_binding_request,
)
from usmsb_sdk.api.database import (
    create_agent as db_create_agent,
)
from usmsb_sdk.api.database import (
    create_api_key as db_create_api_key,
)
from usmsb_sdk.api.database import (
    create_binding_request as db_create_binding_request,
)
from usmsb_sdk.api.database import (
    delete_agent as db_delete_agent,
)
from usmsb_sdk.api.database import (
    get_agent as db_get_agent,
)
from usmsb_sdk.api.database import (
    get_agent_binding_info,
    update_agent_heartbeat,
    update_agent_stake,
)
from usmsb_sdk.api.database import (
    get_api_keys_by_agent as db_get_api_keys_by_agent,
)
from usmsb_sdk.api.database import (
    get_binding_request_by_agent as db_get_binding_request_by_agent,
)
from usmsb_sdk.api.database import (
    get_binding_request_by_code as db_get_binding_request_by_code,
)
from usmsb_sdk.api.database import (
    renew_api_key as db_renew_api_key,
)
from usmsb_sdk.api.database import (
    revoke_api_key as db_revoke_api_key,
)
from usmsb_sdk.api.rest.api_key_manager import (
    APIKeyManager,
    generate_api_key,
    generate_key_id,
    get_stake_tier,
    get_tier_benefits,
)
from usmsb_sdk.api.rest.auth import get_current_user  # SIWE authentication for owners
from usmsb_sdk.api.rest.schemas.agent import (
    A2ARegistrationRequest,
    AgentRegistrationRequest,
    AgentTestRequest,
    MCPRegistrationRequest,
    SkillMDRegistrationRequest,
)
from usmsb_sdk.api.rest.unified_auth import (
    ErrorCode,
    get_current_user_unified,
    verify_agent_access,
)

router = APIRouter(tags=["AI Agent Registration"])


# ==================== New Request Models ====================

class SelfRegistrationRequest(BaseModel):
    """Request for self-registration (no owner required).

    Phase 1 USMSB: Optional Soul declaration during registration.
    Agent can declare its Soul at registration time, or later via /agents/soul/register.
    """
    name: str = Field(..., description="Agent name")
    description: str = Field(default="", description="Agent description")
    capabilities: list[str] = Field(default_factory=list, description="Agent capabilities")
    owner_wallet: str | None = Field(default=None, description="Owner wallet address (optional)")

    # ========== Soul Declaration (Phase 1 USMSB) ==========
    # Optional: Declare Soul during registration
    # If provided, Soul will be automatically registered after agent creation
    soul_goals: list[dict] = Field(
        default_factory=list,
        description="Soul goals: [{name, description, priority}]"
    )
    soul_value_seeking: list[dict] = Field(
        default_factory=list,
        description="Value seeking: [{name, type, metric}]"
    )
    soul_capabilities: list[str] = Field(
        default_factory=list,
        description="Soul capabilities (can extend above capabilities)"
    )
    soul_risk_tolerance: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Risk tolerance (0.0=averse, 1.0=tolerant)"
    )
    soul_collaboration_style: str = Field(
        default="balanced",
        description="conservative | balanced | aggressive"
    )
    soul_preferred_contract_type: str = Field(
        default="any",
        description="task | project | any"
    )
    soul_pricing_strategy: str = Field(
        default="negotiable",
        description="fixed | negotiable | market"
    )
    soul_base_price_vibe: float | None = Field(
        default=None, ge=0.0,
        description="Base price reference in VIBE"
    )


class BindingRequestRequest(BaseModel):
    """Request for owner binding."""
    message: str = Field(default="", description="Optional message to owner")


class CreateAPIKeyRequest(BaseModel):
    """Request to create a new API key."""
    name: str = Field(default="New Key", description="Name for the API key")
    expires_in_days: int | None = Field(default=365, description="Days until expiration")


class RenewAPIKeyRequest(BaseModel):
    """Request to renew an API key."""
    extends_days: int = Field(default=365, description="Days to extend expiration")


class CompleteBindingRequest(BaseModel):
    """Request to complete binding (called by owner)."""
    stake_amount: float = Field(..., description="Amount to stake in VIBE")


# ==================== New Registration Endpoints ====================

@router.post("/agents/v2/register")
async def register_agent_v2(request: SelfRegistrationRequest):
    """
    Self-register a new Agent (no Owner required).

    This endpoint allows an Agent to register itself and receive an API Key.
    Level 0 (unbound) - basic features available immediately.

    Returns:
        - agent_id: The agent's unique ID
        - api_key: The API key (SAVE THIS - only shown once!)
        - level: 0 (unbound)
    """
    # Generate agent ID
    agent_id = f"agent-{uuid.uuid4().hex[:12]}"
    now = time.time()

    # Create agent in database
    agent_data = {
        "agent_id": agent_id,
        "name": request.name,
        "agent_type": "ai_agent",
        "description": request.description,
        "capabilities": request.capabilities,
        "skills": [],
        "endpoint": "",
        "protocol": "standard",
        "stake": 0,
        "balance": 0,
        "status": "offline",
        "reputation": 0.5,
        "heartbeat_interval": 30,
        "ttl": 90,
        "metadata": {},
        "last_heartbeat": now,
        "binding_status": "unbound",
    }
    db_create_agent(agent_data)

    # Phase 1 USMSB: Register Soul if provided
    soul_registered = False
    soul_version = None
    if (
        request.soul_goals
        or request.soul_value_seeking
        or request.soul_capabilities
        or request.soul_risk_tolerance != 0.5
        or request.soul_collaboration_style != "balanced"
        or request.soul_preferred_contract_type != "any"
        or request.soul_pricing_strategy != "negotiable"
        or request.soul_base_price_vibe is not None
    ):
        # Import here to avoid circular imports
        from usmsb_sdk.core.elements import Goal, Value
        from usmsb_sdk.services.agent_soul import AgentSoulManager, DeclaredSoul
        from usmsb_sdk.services.schema import create_session

        session = create_session()
        manager = AgentSoulManager(session)

        declared = DeclaredSoul(
            goals=[
                Goal(
                    id=str(time.time()) + f"-{i}",
                    name=g.get("name", ""),
                    description=g.get("description", ""),
                    priority=g.get("priority", 0),
                )
                for i, g in enumerate(request.soul_goals)
            ],
            value_seeking=[
                Value(
                    id=str(time.time()) + f"-{i}",
                    name=v.get("name", ""),
                    type=v.get("type", "economic"),
                    metric=v.get("metric"),
                )
                for i, v in enumerate(request.soul_value_seeking)
            ],
            capabilities=list(set(request.capabilities + request.soul_capabilities)),
            risk_tolerance=request.soul_risk_tolerance,
            collaboration_style=request.soul_collaboration_style,
            preferred_contract_type=request.soul_preferred_contract_type,
            pricing_strategy=request.soul_pricing_strategy,
            base_price_vibe=request.soul_base_price_vibe,
        )

        try:
            soul = await manager.register_soul(agent_id, declared)
            soul_registered = True
            soul_version = soul.soul_version
        except Exception as e:
            # Soul registration failed, but agent is still registered
            # Log the error but don't fail the registration
            import logging
            logging.getLogger(__name__).warning(f"Soul registration failed for {agent_id}: {e}")

    # Deploy AgentWallet and register with AgentRegistry
    wallet_address = None
    # Step 1: Generate agent's operational keypair (Plan B)
    # This keypair is generated at registration time, but the wallet is NOT deployed yet.
    # Wallet deployment is deferred to complete_binding when an owner actually binds.
    import os
    from eth_account import Account
    from usmsb_sdk.api.database import update_agent_wallet_key

    agent_private_key = None
    agent_address = None

    try:
        # Generate unique keypair for this agent — agent uses this to sign autonomous transactions
        acct = Account.create()
        agent_private_key = acct.key.hex()  # 64-char hex private key
        agent_address = acct.address

        # Store agent's operational keypair in database
        # The wallet will be deployed when complete_binding is called
        try:
            update_agent_wallet_key(agent_id, agent_address, agent_private_key)
        except Exception as db_err:
            logging.getLogger(__name__).warning(f"Failed to store agent wallet key: {db_err}")

    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to generate agent keypair for {agent_id}: {e}")
        # Keypair generation failed — agent can still be registered but won't have autonomous wallet

    # Generate API Key
    api_key, key_hash, key_prefix = generate_api_key(agent_id)
    key_id = generate_key_id()

    # Store API key (hashed)
    db_create_api_key({
        "id": key_id,
        "agent_id": agent_id,
        "key_hash": key_hash,
        "key_prefix": key_prefix,
        "name": "Primary",
        "level": 0,
        "permissions": [],
        "expires_at": None,
    })

    return {
        "success": True,
        "agent_id": agent_id,
        "api_key": api_key,  # Only returned once!
        "level": 0,
        "binding_status": "unbound",
        "soul_registered": soul_registered,
        "soul_version": soul_version,
        "wallet_address": None,  # Deployed at complete_binding
        "agent_address": agent_address,  # Agent's EOA address (derived from agent_private_key)
        "agent_private_key": agent_private_key,  # ⚠️ SAVE THIS - only shown once! Agent uses this to sign autonomous transactions
        "wallet_deployed": False,  # Deferred to complete_binding
        "message": "Agent registered successfully. Save your API key and agent_private_key securely - they won't be shown again!"
                + (" Soul declared and registered." if soul_registered else " Consider declaring your Soul via /agents/soul/register for better matching.")
                + (" AgentWallet will be deployed when owner binding completes."),
    }


@router.post("/agents/v2/{agent_id}/request-binding")
async def request_binding(
    agent_id: str,
    request: BindingRequestRequest,
    user: dict = Depends(get_current_user_unified)
):
    """
    Request owner binding for an agent.

    This generates a binding code and URL that the agent can share with a potential owner.
    The owner visits the URL, connects their wallet, and stakes VIBE tokens.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
    """
    authenticated_agent_id = user.get('agent_id') or user.get('user_id')
    # Verify agent_id matches authenticated agent
    if authenticated_agent_id != agent_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Access denied",
                "code": ErrorCode.UNAUTHORIZED,
                "message": "You can only request binding for your own agent"
            }
        )

    # Check if already bound
    if user.get('binding_status') == 'bound':
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Agent already bound",
                "code": "ALREADY_BOUND",
                "message": "This agent is already bound to an owner"
            }
        )

    # Generate binding request
    base_url = "https://platform.usmsb.io"  # TODO: Make configurable
    binding_data = APIKeyManager.create_binding_request(
        agent_id=agent_id,
        base_url=base_url,
        message=request.message
    )

    # Store in database
    db_create_binding_request({
        "id": binding_data['id'],
        "agent_id": agent_id,
        "binding_code": binding_data['binding_code'],
        "binding_url": binding_data['binding_url'],
        "message": request.message,
        "expires_at": binding_data['expires_at'],
    })

    return {
        "success": True,
        "binding_code": binding_data['binding_code'],
        "binding_url": binding_data['binding_url'],
        "expires_in": binding_data['expires_in'],
        "message": "Share this URL with your owner to complete binding"
    }


@router.get("/agents/v2/{agent_id}/binding-status")
async def get_binding_status(
    agent_id: str,
    user: dict = Depends(get_current_user_unified)
):
    """
    Get binding status for an agent.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
    """
    authenticated_agent_id = user.get('agent_id') or user.get('user_id')
    if authenticated_agent_id != agent_id:
        raise HTTPException(
            status_code=403,
            detail={"error": "Access denied", "code": ErrorCode.UNAUTHORIZED}
        )

    # Get pending binding request if any
    pending_request = db_get_binding_request_by_agent(agent_id)

    # Get tier info
    tier = user.get('stake_tier', 'NONE')
    tier_benefits = get_tier_benefits(tier)

    return {
        "bound": user.get('binding_status') == 'bound',
        "binding_status": user.get('binding_status'),
        "owner_wallet": user.get('owner_wallet'),
        "stake_tier": tier,
        "staked_amount": user.get('staked_amount', 0),
        "tier_benefits": tier_benefits,
        "pending_request": {
            "binding_code": pending_request['binding_code'],
            "binding_url": pending_request['binding_url'],
            "expires_at": pending_request['expires_at'],
            "status": pending_request['status'],
        } if pending_request and pending_request['status'] == 'pending' else None
    }


@router.post("/agents/v2/complete-binding/{binding_code}")
async def complete_binding(
    binding_code: str,
    request: CompleteBindingRequest,
    user: dict = Depends(get_current_user)  # SIWE authentication required
):
    """
    Complete the binding process with real VIBE staking.

    This endpoint is called by the OWNER (not the agent) after they:
    1. Visit the binding URL
    2. Connect their wallet
    3. Sign a message proving ownership (SIWE)
    4. Stake VIBE tokens (this is now done on-chain)

    Authentication:
        - Requires SIWE (Sign-In with Ethereum) session
        - The wallet address is taken from the authenticated session

    B14: This endpoint now executes real VIBE staking on-chain:
        1. Owner approves VIBStaking contract to spend stake amount
        2. Owner stakes VIBE via VIBStaking.stake()
    """
    # Get owner wallet and private key from authenticated user session
    owner_wallet = user.get('wallet_address')
    owner_private_key = user.get('private_key')
    if not owner_wallet:
        raise HTTPException(
            status_code=401,
            detail={"error": "Wallet address not found in session", "code": "UNAUTHORIZED"}
        )
    if not owner_private_key:
        raise HTTPException(
            status_code=401,
            detail={"error": "Private key not available for staking", "code": "PRIVATE_KEY_UNAVAILABLE"}
        )

    # Get binding request
    binding = db_get_binding_request_by_code(binding_code)

    if not binding:
        raise HTTPException(
            status_code=404,
            detail={"error": "Binding request not found", "code": "NOT_FOUND"}
        )

    if binding['status'] != 'pending':
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Binding request already {binding['status']}",
                "code": "BINDING_INVALID"
            }
        )

    # Check expiration
    if binding['expires_at'] < time.time():
        raise HTTPException(
            status_code=400,
            detail={"error": "Binding request expired", "code": "BINDING_EXPIRED"}
        )

    # B14: Execute real VIBE staking on-chain
    try:
        from usmsb_sdk.blockchain.contracts.vib_staking import VIBStakingClient, LockPeriod
        from usmsb_sdk.blockchain.contracts.vibe_token import VIBETokenClient
        from usmsb_sdk.blockchain.config import BlockchainConfig

        config = BlockchainConfig()
        staking_address = config.get_contract_address("VIBStaking")
        token_address = config.get_contract_address("VIBEToken")

        if not staking_address or staking_address == "待部署":
            raise HTTPException(
                status_code=500,
                detail={"error": "VIBStaking contract not deployed", "code": "STAKING_NOT_DEPLOYED"}
            )

        # Convert stake amount to wei
        stake_amount_wei = int(request.stake_amount * (10 ** 18))

        # Step 1: Approve VIBStaking contract to spend VIBE
        token_client = VIBETokenClient()
        approve_tx_hash = token_client.approve(
            spender=staking_address,
            amount=stake_amount_wei,
            from_address=owner_wallet,
            private_key=owner_private_key,
        )

        # Step 2: Stake VIBE (use 30-day lock period as default)
        staking_client = VIBStakingClient()
        stake_tx_hash = await staking_client.stake(
            amount=stake_amount_wei,
            lock_period=LockPeriod.DAYS_30,
            from_address=owner_wallet,
            private_key=owner_private_key,
        )

        staking_tx_hashes = {
            "approve_tx": approve_tx_hash,
            "stake_tx": stake_tx_hash,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": f"Staking failed: {str(e)}", "code": "STAKING_FAILED"}
        )

    # Step 2: Deploy AgentWallet (owner pays gas for deployment)
    # This is triggered at complete_binding time — no wallet deployed during register_agent_v2
    wallet_deployed = False
    agent_registry_registered = False
    wallet_deploy_tx_hash = None
    wallet_address = None

    try:
        import os
        from usmsb_sdk.blockchain.config import BlockchainConfig
        from usmsb_sdk.blockchain.contracts.agent_wallet import AgentWalletFactory
        from usmsb_sdk.blockchain.contracts.agent_registry import AgentRegistryClient
        from usmsb_sdk.api.database import get_agent_wallet, update_agent_binding_status

        deployer_private_key = os.getenv("AGENT_WALLET_DEPLOYER_PRIVATE_KEY")
        platform_agent_address = os.getenv("PLATFORM_AGENT_ADDRESS", "0x0000000000000000000000000000000000000000")

        # Get agent's pre-generated keypair from database
        agent_wallet = get_agent_wallet(result['agent_id'])
        if agent_wallet and agent_wallet.get('agent_address'):
            agent_address = agent_wallet['agent_address']
            agent_private_key = agent_wallet.get('agent_private_key')

        if not agent_address or not agent_private_key:
            raise Exception("Agent keypair not found in database — run register_agent_v2 first")

        if deployer_private_key and len(deployer_private_key) == 66:
            config = BlockchainConfig.from_env()
            factory = AgentWalletFactory.from_config(config)

            # Deploy AgentWallet:
            # - owner_address: Owner EOA (authorizing entity)
            # - agent_address: Agent's EOA (can autonomously execute transactions)
            # - from_address: platform deployer (pays gas for deployment)
            # - private_key: platform private key (signs deployment tx)
            wallet_address, wallet_deploy_tx_hash = await factory.deploy_wallet(
                owner_address=owner_wallet,
                agent_address=agent_address,
                from_address=platform_agent_address,
                private_key=deployer_private_key,
            )
            wallet_deployed = True

            # Update DB: set wallet address and owner binding
            try:
                update_agent_binding_status(result['agent_id'], "bound", owner_wallet=wallet_address)
            except Exception as db_err:
                logging.getLogger(__name__).warning(f"Failed to update agent wallet in DB: {db_err}")

            # Register with AgentRegistry (chainon registration)
            try:
                registry_client = AgentRegistryClient(config=config)
                await registry_client.register_agent(
                    wallet_address=wallet_address,
                    owner_address=owner_wallet,
                    owner_private_key=deployer_private_key,
                )
                agent_registry_registered = True
            except Exception as e:
                logging.getLogger(__name__).warning(f"AgentRegistry registration failed: {e}")

        else:
            logging.getLogger(__name__).warning(
                "AGENT_WALLET_DEPLOYER_PRIVATE_KEY not set — skipping on-chain wallet deployment"
            )

    except Exception as wallet_err:
        logging.getLogger(__name__).warning(f"Wallet deployment failed (binding still completes): {wallet_err}")
        wallet_deployed = False

    # Complete the binding (database only)
    result = db_complete_binding_request(
        binding_code=binding_code,
        owner_wallet=owner_wallet,
        stake_amount=request.stake_amount
    )

    if not result:
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to complete binding", "code": "INTERNAL_ERROR"}
        )

    # Get tier info
    tier = get_stake_tier(request.stake_amount)
    tier_benefits = get_tier_benefits(tier)

    return {
        "success": True,
        "agent_id": result['agent_id'],
        "owner_wallet": owner_wallet,
        "stake_amount": result['stake_amount'],
        "stake_tier": tier,
        "tier_benefits": tier_benefits,
        "completed_at": result['completed_at'],
        "staking_transactions": staking_tx_hashes,
        "wallet_deployed": wallet_deployed,
        "wallet_address": wallet_address,
        "wallet_deploy_tx": wallet_deploy_tx_hash,
        "message": "Binding completed successfully with VIBE staking."
                + (" AgentWallet deployed and registered." if wallet_deployed else " Wallet deployment skipped.")
    }


# ==================== API Key Management Endpoints ====================

def check_agent_or_owner_access(user: dict, agent_id: str) -> None:
    """
    Check if the user can access the agent's resources.

    Access is granted if:
    1. User is the agent itself (authenticated with API key)
    2. User is the owner of the agent (authenticated with wallet)

    Raises HTTPException if access is denied.
    """
    authenticated_agent_id = user.get('agent_id') or user.get('user_id')

    # Case 1: User is the agent itself
    if authenticated_agent_id == agent_id:
        return

    # Case 2: User is the owner (check via wallet address)
    user_wallet = user.get('wallet_address') or user.get('address')
    if user_wallet:
        binding_info = get_agent_binding_info(agent_id)
        if binding_info and binding_info.get('owner_wallet', '').lower() == user_wallet.lower():
            return

    # Access denied
    raise HTTPException(
        status_code=403,
        detail={"error": "Access denied. You must be the agent or its owner.", "code": ErrorCode.UNAUTHORIZED}
    )


@router.get("/agents/v2/{agent_id}/api-keys")
async def list_api_keys(
    agent_id: str,
    user: dict = Depends(get_current_user_unified)
):
    """List all API keys for the agent."""
    check_agent_or_owner_access(user, agent_id)

    keys = db_get_api_keys_by_agent(agent_id)

    return {
        "success": True,
        "keys": [{
            "id": k['id'],
            "prefix": k['key_prefix'] + "...",
            "name": k['name'],
            "level": k['level'],
            "expires_at": k['expires_at'],
            "last_used_at": k['last_used_at'],
            "created_at": k['created_at']
        } for k in keys]
    }


@router.post("/agents/v2/{agent_id}/api-keys")
async def create_new_api_key(
    agent_id: str,
    request: CreateAPIKeyRequest,
    user: dict = Depends(get_current_user_unified)
):
    """Create a new API key for the agent."""
    check_agent_or_owner_access(user, agent_id)

    # Generate new API key
    key_data = APIKeyManager.create_key_for_agent(
        agent_id=agent_id,
        name=request.name,
        expires_in_days=request.expires_in_days,
        level=user.get('level', 0)
    )

    # Store in database
    db_create_api_key({
        "id": key_data['id'],
        "agent_id": agent_id,
        "key_hash": key_data['key_hash'],
        "key_prefix": key_data['key_prefix'],
        "name": key_data['name'],
        "level": key_data['level'],
        "permissions": [],
        "expires_at": key_data['expires_at'],
    })

    return {
        "success": True,
        "key_id": key_data['id'],
        "api_key": key_data['api_key'],  # Only returned once!
        "name": key_data['name'],
        "expires_at": key_data['expires_at'],
        "message": "API key created. Save it now - it won't be shown again!"
    }


@router.post("/agents/v2/{agent_id}/api-keys/{key_id}/revoke")
async def revoke_api_key_endpoint(
    agent_id: str,
    key_id: str,
    user: dict = Depends(get_current_user_unified)
):
    """Revoke an API key."""
    check_agent_or_owner_access(user, agent_id)

    # Can't revoke the key currently being used
    if key_id == user.get('api_key_id'):
        raise HTTPException(
            status_code=400,
            detail={"error": "Cannot revoke the key currently in use", "code": "INVALID_OPERATION"}
        )

    success = db_revoke_api_key(key_id, agent_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail={"error": "API key not found", "code": "NOT_FOUND"}
        )

    return {"success": True, "message": "API key revoked"}


@router.post("/agents/v2/{agent_id}/api-keys/{key_id}/renew")
async def renew_api_key_endpoint(
    agent_id: str,
    key_id: str,
    request: RenewAPIKeyRequest,
    user: dict = Depends(get_current_user_unified)
):
    """Renew an API key (extend expiration)."""
    check_agent_or_owner_access(user, agent_id)

    success = db_renew_api_key(key_id, agent_id, request.extends_days)

    if not success:
        raise HTTPException(
            status_code=404,
            detail={"error": "API key not found or already revoked", "code": "NOT_FOUND"}
        )

    new_expires_at = time.time() + (request.extends_days * 86400)

    return {
        "success": True,
        "key_id": key_id,
        "new_expires_at": new_expires_at,
        "message": f"API key renewed for {request.extends_days} days"
    }


# ==================== Profile Endpoints ====================

@router.get("/agents/v2/profile")
async def get_agent_profile(user: dict = Depends(get_current_user_unified)):
    """Get agent's profile information."""
    return {
        "success": True,
        "result": {
            "agent_id": user.get('agent_id') or user.get('user_id'),
            "name": user.get('agent_name', user.get('wallet_address', '')),
            "description": user.get('description', ''),
            "capabilities": user.get('capabilities', []),
            "status": user.get('status', 'unknown'),
            "level": user.get('level', 0),
            "binding_status": user.get('binding_status', 'unknown'),
            "owner_wallet": user.get('owner_wallet'),
            "stake_tier": user.get('stake_tier', 'NONE'),
            "staked_amount": user.get('staked_amount', 0),
            "tier_benefits": user.get('tier_benefits', {})
        }
    }


class UpdateProfileRequest(BaseModel):
    """Request to update agent profile."""
    name: str | None = None
    description: str | None = None
    capabilities: list[str] | None = None


@router.patch("/agents/v2/profile")
async def update_agent_profile(
    request: UpdateProfileRequest,
    user: dict = Depends(get_current_user_unified)
):
    """Update agent's profile information.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
    """
    agent_id = user.get('agent_id') or user.get('user_id')
    if not agent_id:
        raise HTTPException(
            status_code=401,
            detail={"error": "Agent ID not found", "code": "UNAUTHORIZED"}
        )

    # Build update data
    update_data = {'agent_id': agent_id}
    updated_fields = []

    if request.name is not None:
        update_data['name'] = request.name
        updated_fields.append('name')
    if request.description is not None:
        update_data['description'] = request.description
        updated_fields.append('description')
    if request.capabilities is not None:
        update_data['capabilities'] = request.capabilities
        updated_fields.append('capabilities')

    if not updated_fields:
        raise HTTPException(
            status_code=400,
            detail={"error": "No fields to update", "code": "NO_UPDATES"}
        )

    # Update in database
    db_create_agent(update_data)  # Uses INSERT OR REPLACE

    return {
        "success": True,
        "result": {
            "agent_id": agent_id,
            "name": request.name or user.get('agent_name', ''),
            "updated_fields": updated_fields
        }
    }


@router.get("/agents/v2/owner")
async def get_owner_info(user: dict = Depends(get_current_user_unified)):
    """Get information about the bound owner."""
    if not user.get('is_bound'):
        return {
            "success": False,
            "error": "Agent is not bound to an owner",
            "code": "NOT_BOUND"
        }

    return {
        "success": True,
        "result": {
            "owner_wallet": user.get('owner_wallet'),
            "staked_amount": user.get('staked_amount'),
            "stake_status": user.get('stake_status'),
            "stake_tier": user.get('stake_tier'),
            "bound_at": user.get('bound_at')
        }
    }


@router.post("/agents/register")
async def register_ai_agent(request: AgentRegistrationRequest):
    """Register an AI Agent to the platform.

    Uses the unified agent registration system with full field support
    including heartbeat mechanism and TTL configuration.
    """
    agent_id = request.agent_id or f"agent_{uuid.uuid4().hex[:12]}"
    now = time.time()
    ttl = request.ttl or (request.heartbeat_interval * 3)

    agent_data = {
        "agent_id": agent_id,
        "name": request.name,
        "agent_type": request.agent_type,
        "description": request.description,
        "capabilities": request.capabilities,  # Pass as list, create_agent will json.dumps
        "skills": request.skills,  # Pass as list, create_agent will json.dumps
        "endpoint": request.endpoint,
        "protocol": request.protocol,
        "stake": request.stake,
        "balance": request.balance,
        "status": "online",
        "reputation": 0.5,
        "heartbeat_interval": request.heartbeat_interval,
        "ttl": ttl,
        "metadata": request.metadata,  # Pass as dict, create_agent will json.dumps
        "last_heartbeat": now,
    }
    # Save to database using unified function
    db_create_agent(agent_data)

    # Phase 1 USMSB: Register Soul if provided in metadata
    soul_registered = False
    soul_version = None
    soul_metadata = request.metadata.get("soul") if request.metadata else None
    if soul_metadata:
        from usmsb_sdk.core.elements import Goal, Value
        from usmsb_sdk.services.agent_soul import AgentSoulManager, DeclaredSoul
        from usmsb_sdk.services.schema import create_session

        session = create_session()
        manager = AgentSoulManager(session)

        declared = DeclaredSoul(
            goals=[
                Goal(
                    id=str(time.time()) + f"-{i}",
                    name=g.get("name", ""),
                    description=g.get("description", ""),
                    priority=g.get("priority", 0),
                )
                for i, g in enumerate(soul_metadata.get("goals", []))
            ],
            value_seeking=[
                Value(
                    id=str(time.time()) + f"-{i}",
                    name=v.get("name", ""),
                    type=v.get("type", "economic"),
                    metric=v.get("metric"),
                )
                for i, v in enumerate(soul_metadata.get("value_seeking", []))
            ],
            capabilities=list(set(request.capabilities + soul_metadata.get("capabilities", []))),
            risk_tolerance=soul_metadata.get("risk_tolerance", 0.5),
            collaboration_style=soul_metadata.get("collaboration_style", "balanced"),
            preferred_contract_type=soul_metadata.get("preferred_contract_type", "any"),
            pricing_strategy=soul_metadata.get("pricing_strategy", "negotiable"),
            base_price_vibe=soul_metadata.get("base_price_vibe"),
        )

        try:
            soul = await manager.register_soul(agent_id, declared)
            soul_registered = True
            soul_version = soul.soul_version
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Soul registration failed for {agent_id}: {e}")

    return {
        "success": True,
        "agent_id": agent_id,
        "message": "Agent registered successfully",
        "heartbeat_interval": request.heartbeat_interval,
        "ttl": ttl,
        "soul_registered": soul_registered,
        "soul_version": soul_version,
    }


@router.post("/agents/register/mcp")
async def register_via_mcp(request: MCPRegistrationRequest):
    """Register an AI Agent via MCP (Model Context Protocol)."""
    agent_id = request.agent_id or f"mcp_{uuid.uuid4().hex[:8]}"
    now = time.time()
    ttl = request.heartbeat_interval * 3

    agent_data = {
        "agent_id": agent_id,
        "name": request.name,
        "agent_type": "ai_agent",
        "description": request.description or f"MCP agent: {request.name}",
        "capabilities": request.capabilities,  # create_agent will json.dumps
        "skills": [],
        "endpoint": request.mcp_endpoint,
        "protocol": "mcp",
        "stake": request.stake,
        "balance": 0.0,
        "status": "online",
        "reputation": 0.5,
        "heartbeat_interval": request.heartbeat_interval,
        "ttl": ttl,
        "metadata": {},
        "last_heartbeat": now,
    }
    # Save to database using unified function
    db_create_agent(agent_data)

    # Phase 1 USMSB: Register Soul if provided in metadata
    soul_registered = False
    soul_version = None
    soul_metadata = request.metadata.get("soul") if request.metadata else None
    if soul_metadata:
        from usmsb_sdk.core.elements import Goal, Value
        from usmsb_sdk.services.agent_soul import AgentSoulManager, DeclaredSoul
        from usmsb_sdk.services.schema import create_session

        session = create_session()
        manager = AgentSoulManager(session)

        declared = DeclaredSoul(
            goals=[
                Goal(
                    id=str(time.time()) + f"-{i}",
                    name=g.get("name", ""),
                    description=g.get("description", ""),
                    priority=g.get("priority", 0),
                )
                for i, g in enumerate(soul_metadata.get("goals", []))
            ],
            value_seeking=[
                Value(
                    id=str(time.time()) + f"-{i}",
                    name=v.get("name", ""),
                    type=v.get("type", "economic"),
                    metric=v.get("metric"),
                )
                for i, v in enumerate(soul_metadata.get("value_seeking", []))
            ],
            capabilities=list(set(request.capabilities + soul_metadata.get("capabilities", []))),
            risk_tolerance=soul_metadata.get("risk_tolerance", 0.5),
            collaboration_style=soul_metadata.get("collaboration_style", "balanced"),
            preferred_contract_type=soul_metadata.get("preferred_contract_type", "any"),
            pricing_strategy=soul_metadata.get("pricing_strategy", "negotiable"),
            base_price_vibe=soul_metadata.get("base_price_vibe"),
        )

        try:
            soul = await manager.register_soul(agent_id, declared)
            soul_registered = True
            soul_version = soul.soul_version
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Soul registration failed for {agent_id}: {e}")

    return {
        "success": True,
        "agent_id": agent_id,
        "message": "Agent registered via MCP protocol",
        "heartbeat_interval": request.heartbeat_interval,
        "ttl": ttl,
        "soul_registered": soul_registered,
        "soul_version": soul_version,
    }


@router.post("/agents/register/a2a")
async def register_via_a2a(request: A2ARegistrationRequest):
    """Register an AI Agent via A2A (Agent-to-Agent) protocol."""
    agent_card = request.agent_card
    agent_id = agent_card.get("agent_id", f"a2a_{uuid.uuid4().hex[:8]}")
    now = time.time()
    ttl = request.heartbeat_interval * 3

    agent_data = {
        "agent_id": agent_id,
        "name": agent_card.get("name", "Unknown"),
        "agent_type": "ai_agent",
        "description": agent_card.get("description", ""),
        "capabilities": agent_card.get("capabilities", []),  # create_agent will json.dumps
        "skills": agent_card.get("skills", []),  # create_agent will json.dumps
        "endpoint": request.endpoint,
        "protocol": "a2a",
        "stake": 0.0,
        "balance": 0.0,
        "status": "online",
        "reputation": 0.5,
        "heartbeat_interval": request.heartbeat_interval,
        "ttl": ttl,
        "metadata": agent_card.get("metadata", {}),  # create_agent will json.dumps
        "last_heartbeat": now,
    }
    # Save to database using unified function
    db_create_agent(agent_data)

    # Phase 1 USMSB: Register Soul if provided in agent_card
    soul_registered = False
    soul_version = None
    soul_metadata = agent_card.get("soul")
    if soul_metadata:
        from usmsb_sdk.core.elements import Goal, Value
        from usmsb_sdk.services.agent_soul import AgentSoulManager, DeclaredSoul
        from usmsb_sdk.services.schema import create_session

        session = create_session()
        manager = AgentSoulManager(session)

        declared = DeclaredSoul(
            goals=[
                Goal(
                    id=str(time.time()) + f"-{i}",
                    name=g.get("name", ""),
                    description=g.get("description", ""),
                    priority=g.get("priority", 0),
                )
                for i, g in enumerate(soul_metadata.get("goals", []))
            ],
            value_seeking=[
                Value(
                    id=str(time.time()) + f"-{i}",
                    name=v.get("name", ""),
                    type=v.get("type", "economic"),
                    metric=v.get("metric"),
                )
                for i, v in enumerate(soul_metadata.get("value_seeking", []))
            ],
            capabilities=list(set(agent_card.get("capabilities", []) + soul_metadata.get("capabilities", []))),
            risk_tolerance=soul_metadata.get("risk_tolerance", 0.5),
            collaboration_style=soul_metadata.get("collaboration_style", "balanced"),
            preferred_contract_type=soul_metadata.get("preferred_contract_type", "any"),
            pricing_strategy=soul_metadata.get("pricing_strategy", "negotiable"),
            base_price_vibe=soul_metadata.get("base_price_vibe"),
        )

        try:
            soul = await manager.register_soul(agent_id, declared)
            soul_registered = True
            soul_version = soul.soul_version
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Soul registration failed for {agent_id}: {e}")

    return {
        "success": True,
        "agent_id": agent_id,
        "message": "Agent registered via A2A protocol",
        "heartbeat_interval": request.heartbeat_interval,
        "ttl": ttl,
        "soul_registered": soul_registered,
        "soul_version": soul_version,
    }


@router.post("/agents/register/skill-md")
async def register_via_skill_md(request: SkillMDRegistrationRequest):
    """Register an AI Agent via skill.md specification.

    In production, this would fetch and parse skill.md from the URL.
    """
    agent_id = request.agent_id or f"skill_{uuid.uuid4().hex[:8]}"
    name = request.name or f"Agent from {request.skill_url}"
    now = time.time()
    ttl = request.heartbeat_interval * 3

    agent_data = {
        "agent_id": agent_id,
        "name": name,
        "agent_type": "ai_agent",
        "description": "Agent registered via skill.md",
        "capabilities": ["general"],  # create_agent will json.dumps
        "skills": [],  # create_agent will json.dumps
        "endpoint": request.endpoint or request.skill_url,
        "protocol": "skill_md",
        "stake": 0.0,
        "balance": 0.0,
        "status": "online",
        "reputation": 0.5,
        "heartbeat_interval": request.heartbeat_interval,
        "ttl": ttl,
        "metadata": {"skill_url": request.skill_url},  # create_agent will json.dumps
        "last_heartbeat": now,
    }
    # Save to database using unified function
    db_create_agent(agent_data)

    # Phase 1 USMSB: Register Soul if provided in metadata
    soul_registered = False
    soul_version = None
    soul_metadata = request.metadata.get("soul") if hasattr(request, "metadata") and request.metadata else None
    if soul_metadata:
        from usmsb_sdk.core.elements import Goal, Value
        from usmsb_sdk.services.agent_soul import AgentSoulManager, DeclaredSoul
        from usmsb_sdk.services.schema import create_session

        session = create_session()
        manager = AgentSoulManager(session)

        declared = DeclaredSoul(
            goals=[
                Goal(
                    id=str(time.time()) + f"-{i}",
                    name=g.get("name", ""),
                    description=g.get("description", ""),
                    priority=g.get("priority", 0),
                )
                for i, g in enumerate(soul_metadata.get("goals", []))
            ],
            value_seeking=[
                Value(
                    id=str(time.time()) + f"-{i}",
                    name=v.get("name", ""),
                    type=v.get("type", "economic"),
                    metric=v.get("metric"),
                )
                for i, v in enumerate(soul_metadata.get("value_seeking", []))
            ],
            capabilities=soul_metadata.get("capabilities", []),
            risk_tolerance=soul_metadata.get("risk_tolerance", 0.5),
            collaboration_style=soul_metadata.get("collaboration_style", "balanced"),
            preferred_contract_type=soul_metadata.get("preferred_contract_type", "any"),
            pricing_strategy=soul_metadata.get("pricing_strategy", "negotiable"),
            base_price_vibe=soul_metadata.get("base_price_vibe"),
        )

        try:
            soul = await manager.register_soul(agent_id, declared)
            soul_registered = True
            soul_version = soul.soul_version
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Soul registration failed for {agent_id}: {e}")

    return {
        "success": True,
        "agent_id": agent_id,
        "message": "Agent registered via skill.md",
        "heartbeat_interval": request.heartbeat_interval,
        "ttl": ttl,
        "soul_registered": soul_registered,
        "soul_version": soul_version,
    }


@router.post("/agents/{agent_id}/heartbeat", deprecated=True)
async def agent_heartbeat_endpoint(
    agent_id: str,
    user: dict[str, Any] = Depends(get_current_user_unified),
    status: str = "online"
):
    """AI Agent sends heartbeat to stay active.

    DEPRECATED: Use POST /agents/{agent_id}/heartbeat with X-API-Key header instead.

    Requires:
        - X-API-Key header
        - X-Agent-ID header (must match agent_id)
    """
    # Verify agent_id matches authenticated agent
    verify_agent_access(user, agent_id)

    # Update heartbeat in database
    success = update_agent_heartbeat(agent_id, status)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update heartbeat")

    now = time.time()
    ttl_remaining = 90  # Default

    return {
        "success": True,
        "agent_id": agent_id,
        "status": status,
        "timestamp": now,
        "ttl_remaining": ttl_remaining,
        "message": "Heartbeat received",
        "deprecation_warning": "Use POST /agents/{agent_id}/heartbeat with X-API-Key header",
    }


@router.delete("/agents/{agent_id}/unregister", deprecated=True)
async def unregister_ai_agent(
    agent_id: str,
    user: dict[str, Any] = Depends(get_current_user_unified)
):
    """Unregister an AI Agent from the platform.

    DEPRECATED: Use DELETE /agents/{agent_id} with X-API-Key header instead.

    Requires:
        - X-API-Key header
        - X-Agent-ID header (must match agent_id)
    """
    # Verify agent_id matches authenticated agent
    verify_agent_access(user, agent_id)

    # Delete from database using unified function
    success = db_delete_agent(agent_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete agent")

    return {
        "success": True,
        "agent_id": agent_id,
        "message": "Agent unregistered",
        "deprecation_warning": "Use DELETE /agents/{agent_id} with X-API-Key header",
    }


@router.post("/agents/{agent_id}/test")
async def test_ai_agent(
    agent_id: str,
    request: AgentTestRequest,
    user: dict[str, Any] = Depends(get_current_user_unified)
):
    """Test an AI Agent by sending a test input.

    Attempts to invoke the agent and returns response with latency metrics.

    Requires:
        - X-API-Key header
        - X-Agent-ID header (must match agent_id being tested)
    """
    # Verify agent_id matches authenticated agent
    verify_agent_access(user, agent_id)

    agent_data = db_get_agent(agent_id)
    if not agent_data:
        raise HTTPException(status_code=404, detail="Agent not found")

    endpoint = agent_data.get("endpoint")
    protocol = agent_data.get("protocol", "standard")

    start_time = time.time()
    test_result = {
        "agent_id": agent_id,
        "protocol": protocol,
        "endpoint": endpoint,
        "input": request.input,
        "success": False,
        "response": None,
        "error": None,
        "latency_ms": 0,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try different endpoints based on protocol
            if protocol == "mcp":
                # MCP uses SSE or specific endpoints
                response = await client.post(
                    f"{endpoint}/invoke",
                    json={"input": request.input, "context": request.context},
                )
            elif protocol == "a2a":
                # A2A protocol
                response = await client.post(
                    f"{endpoint}/message",
                    json={"content": request.input, "context": request.context},
                )
            else:
                # Standard REST endpoint
                response = await client.post(
                    f"{endpoint}/invoke",
                    json={"input": request.input, "context": request.context},
                )

            end_time = time.time()
            test_result["latency_ms"] = round((end_time - start_time) * 1000, 2)

            if response.status_code == 200:
                try:
                    test_result["response"] = response.json()
                except (json.JSONDecodeError, ValueError):
                    test_result["response"] = response.text
                test_result["success"] = True
            else:
                test_result["error"] = f"HTTP {response.status_code}: {response.text[:500]}"

    except httpx.TimeoutException:
        end_time = time.time()
        test_result["latency_ms"] = round((end_time - start_time) * 1000, 2)
        test_result["error"] = "Request timed out after 30 seconds"
    except httpx.ConnectError as e:
        end_time = time.time()
        test_result["latency_ms"] = round((end_time - start_time) * 1000, 2)
        test_result["error"] = f"Connection failed: {str(e)}"
    except Exception as e:
        end_time = time.time()
        test_result["latency_ms"] = round((end_time - start_time) * 1000, 2)
        test_result["error"] = f"Error: {str(e)}"

    return test_result


@router.post("/agents/{agent_id}/stake", deprecated=True)
async def agent_stake_endpoint(
    agent_id: str,
    amount: float,
    user: dict[str, Any] = Depends(get_current_user_unified)
):
    """Stake VIBE tokens for an AI Agent.

    DEPRECATED: Use the binding flow instead (POST /agents/v2/{id}/request-binding).
    Stake should be managed through the owner binding process.

    Requires:
        - X-API-Key header
        - X-Agent-ID header (must match agent_id)
    """
    # Verify agent_id matches authenticated agent
    verify_agent_access(user, agent_id)

    # Update stake in database using unified function
    success = update_agent_stake(agent_id, amount)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update stake")

    # Get updated agent data
    updated_agent = db_get_agent(agent_id)
    current_stake = updated_agent.get("stake", 0)

    # Calculate reputation based on stake
    reputation = min(0.5 + (current_stake / 1000), 1.0)

    return {
        "success": True,
        "agent_id": agent_id,
        "total_stake": current_stake,
        "reputation": reputation,
        "deprecation_warning": "Use the binding flow (POST /agents/v2/{id}/request-binding) to manage stake",
    }
