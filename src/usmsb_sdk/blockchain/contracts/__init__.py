"""
合约客户端模块

导出所有合约相关的类和函数。
"""

from .abi_loader import (
    ABILoader,
    get_abi_loader,
    load_abi,
    load_abi_and_bytecode,
    load_bytecode,
)
from .agent_registry import AgentRegistryClient
from .agent_wallet import (
    AgentWalletClient,
    AgentWalletFactory,
)
from .base import (
    BaseContractClient,
    ContractError,
    TransactionError,
)
from .joint_order import JointOrderClient, PoolStatus
from .vib_collaboration import VIBCollaborationClient
from .vib_dividend import VIBDividendClient
from .vib_governance import ProposalState, ProposalType, VetoType, VIBGovernanceClient
from .vib_identity import IdentityType, VIBIdentityClient
from .vib_staking import LockPeriod, StakeTier, VIBStakingClient
from .vibe_token import VIBETokenClient

__all__ = [
    "BaseContractClient",
    "TransactionError",
    "ContractError",
    "ABILoader",
    "get_abi_loader",
    "load_abi",
    "load_bytecode",
    "load_abi_and_bytecode",
    "VIBETokenClient",
    "AgentWalletFactory",
    "AgentWalletClient",
    "AgentRegistryClient",
    "VIBStakingClient",
    "StakeTier",
    "LockPeriod",
    "VIBIdentityClient",
    "IdentityType",
    "VIBDividendClient",
    "VIBGovernanceClient",
    "ProposalType",
    "ProposalState",
    "VetoType",
    "VIBCollaborationClient",
    "JointOrderClient",
    "PoolStatus",
]
