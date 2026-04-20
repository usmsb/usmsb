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

# Governance contract address (from blockchain/contracts.py)
VIBGOVERNANCE_ADDRESS = "0x27475aea1eEba485005B1717a35a7D411d144a1d"
VIBGOVERNANCE_ABI = [
    {"name": "getProposalCount", "type": "function", "inputs": [],
     "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view"},
    {"name": "getProposal", "type": "function", "inputs": [{"name": "proposalId", "type": "uint256"}],
     "outputs": [{"name": "", "type": "tuple",
                  "components": [
                      {"name": "id", "type": "uint256"},
                      {"name": "proposer", "type": "address"},
                      {"name": "title", "type": "string"},
                      {"name": "description", "type": "string"},
                      {"name": "forVotes", "type": "uint256"},
                      {"name": "againstVotes", "type": "uint256"},
                      {"name": "startTime", "type": "uint256"},
                      {"name": "endTime", "type": "uint256"},
                      {"name": "executed", "type": "bool"},
                      {"name": "cancelled", "type": "bool"},
                  ]}],
     "stateMutability": "view"},
    {"name": "castVote", "type": "function",
     "inputs": [{"name": "proposalId", "type": "uint256"}, {"name": "support", "type": "bool"}],
     "outputs": [], "stateMutability": "nonpayable"},
    {"name": "getVotes", "type": "function", "inputs": [{"name": "account", "type": "address"}],
     "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view"},
]

# Staking contract address and ABI (from blockchain/contracts.py)
VIBSTAKING_ADDRESS = "0x1901Ab56eA38cBeFc7a3F0Ed188B7108d27f4c05"
VIBSTAKING_ABI = [
    {"name": "stake", "type": "function",
     "inputs": [{"name": "amount", "type": "uint256"}, {"name": "lockPeriod", "type": "uint256"}],
     "outputs": [], "stateMutability": "nonpayable"},
    {"name": "unstake", "type": "function", "inputs": [], "outputs": [],
     "stateMutability": "nonpayable"},
    {"name": "claimReward", "type": "function", "inputs": [], "outputs": [],
     "stateMutability": "nonpayable"},
    {"name": "getStakeInfo", "type": "function", "inputs": [{"name": "user", "type": "address"}],
     "outputs": [{"name": "amount", "type": "uint256"}, {"name": "startTime", "type": "uint256"},
                 {"name": "lockPeriod", "type": "uint256"}, {"name": "isActive", "type": "bool"}],
     "stateMutability": "view"},
    {"name": "getPendingReward", "type": "function", "inputs": [{"name": "user", "type": "address"}],
     "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view"},
]

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
    "VIBGOVERNANCE_ADDRESS",
    "VIBGOVERNANCE_ABI",
    "VIBSTAKING_ADDRESS",
    "VIBSTAKING_ABI",
]
