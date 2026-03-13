"""
合约客户端模块

导出所有合约相关的类和函数。
"""

from .base import (
    BaseContractClient,
    TransactionError,
    ContractError,
)
from .abi_loader import (
    ABILoader,
    get_abi_loader,
    load_abi,
    load_bytecode,
    load_abi_and_bytecode,
)
from .vibe_token import VIBETokenClient
from .agent_wallet import (
    AgentWalletFactory,
    AgentWalletClient,
)
from .agent_registry import AgentRegistryClient
from .vib_staking import VIBStakingClient, StakeTier, LockPeriod
from .vib_identity import VIBIdentityClient, IdentityType
from .vib_dividend import VIBDividendClient
from .vib_governance import VIBGovernanceClient, ProposalType, ProposalState, VetoType
from .vib_collaboration import VIBCollaborationClient
from .joint_order import JointOrderClient, PoolStatus

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
