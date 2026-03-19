"""
USMSB SDK REST API Routers

Modular routers for different API domains.
"""

from usmsb_sdk.api.rest.routers.agents import router as agents_router
from usmsb_sdk.api.rest.routers.blockchain import router as blockchain_router
from usmsb_sdk.api.rest.routers.collaborations import router as collaborations_router
from usmsb_sdk.api.rest.routers.demands import router as demands_router
from usmsb_sdk.api.rest.routers.environments import router as environments_router
from usmsb_sdk.api.rest.routers.gene_capsule import router as gene_capsule_router
from usmsb_sdk.api.rest.routers.heartbeat import router as heartbeat_router
from usmsb_sdk.api.rest.routers.learning import router as learning_router
from usmsb_sdk.api.rest.routers.matching import router as matching_router
from usmsb_sdk.api.rest.routers.meta_agent_matching import router as meta_agent_matching_router
from usmsb_sdk.api.rest.routers.network import router as network_router
from usmsb_sdk.api.rest.routers.orders import router as orders_router
from usmsb_sdk.api.rest.routers.pre_match_negotiation import router as pre_match_negotiation_router
from usmsb_sdk.api.rest.routers.predictions import router as predictions_router
from usmsb_sdk.api.rest.routers.registration import router as registration_router
from usmsb_sdk.api.rest.routers.reputation import router as reputation_router
from usmsb_sdk.api.rest.routers.services import router as services_router
from usmsb_sdk.api.rest.routers.souls import router as souls_router
from usmsb_sdk.api.rest.routers.staking import router as staking_router
from usmsb_sdk.api.rest.routers.system import router as system_router
from usmsb_sdk.api.rest.routers.wallet import router as wallet_router
from usmsb_sdk.api.rest.routers.workflows import router as workflows_router

__all__ = [
    "agents_router",
    "environments_router",
    "demands_router",
    "predictions_router",
    "workflows_router",
    "matching_router",
    "network_router",
    "collaborations_router",
    "orders_router",
    "learning_router",
    "registration_router",
    "services_router",
    "system_router",
    "gene_capsule_router",
    "pre_match_negotiation_router",
    "meta_agent_matching_router",
    "staking_router",
    "reputation_router",
    "wallet_router",
    "heartbeat_router",
    "blockchain_router",
    "souls_router",
]
