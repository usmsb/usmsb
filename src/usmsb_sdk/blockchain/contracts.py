"""
VIBE Protocol 合约常量 - Base Sepolia 测试网

来源: frontend/src/data/contracts.ts
部署时间: 2026-03-19
网络: Base Sepolia (chainId: 84532)
"""

# ── 主网合约 ────────────────────────────────────────────────────────────────

VIBETOKEN_ADDRESS = "0x93C52dF000317e12F891474B46d8B05652430bDC"
VIBSTAKING_ADDRESS = "0x1901Ab56eA38cBeFc7a3F0Ed188B7108d27f4c05"
VIBGOVERNANCE_ADDRESS = "0x27475aea1eEba485005B1717a35a7D411d144a1d"

# ── ABI 片断 ────────────────────────────────────────────────────────────────

VIBETOKEN_ABI = [
    {"name": "balanceOf", "type": "function", "inputs": [{"name": "account", "type": "address"}],
     "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view"},
    {"name": "transfer", "type": "function",
     "inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}],
     "outputs": [{"name": "", "type": "bool"}], "stateMutability": "nonpayable"},
    {"name": "approve", "type": "function",
     "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}],
     "outputs": [{"name": "", "type": "bool"}], "stateMutability": "nonpayable"},
    {"name": "allowance", "type": "function",
     "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}],
     "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view"},
    {"name": "totalSupply", "type": "function", "inputs": [],
     "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view"},
]

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
