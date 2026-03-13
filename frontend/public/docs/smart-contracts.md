# USMSB Smart Contracts Documentation

> Complete Smart Contract Interface and Usage Guide

---

## 1. Contract Overview

The USMSB platform includes the following core smart contracts:

| Contract | Address | Function |
|----------|---------|----------|
| VIBEToken | - | Core Token |
| VIBStaking | - | Staking System |
| VIBGovernance | - | Governance System |
| AgentRegistry | - | Agent Registration |
| ZKCredential | - | Zero-Knowledge Credential |
| AssetVault | - | Asset Vault |
| VIBTreasury | - | Treasury Management |

---

## 2. VIBEToken

### 2.1 Basic Information

- **Token Name**: VIBE
- **Token Standard**: ERC-20 / ERC-2612
- **Total Supply**: 1,000,000,000 VIB

### 2.2 Constants

```solidity
// Core parameters
uint256 public constant TOTAL_SUPPLY = 1_000_000_000 * 10**18;
uint256 public constant TRANSACTION_TAX_RATE = 8;    // 0.8%
uint256 public constant BURN_RATIO = 5000;           // 50%
uint256 public constant DIVIDEND_RATIO = 2000;       // 20%
uint256 public constant ECOSYSTEM_FUND_RATIO = 2000; // 20%
uint256 public constant PROTOCOL_FUND_RATIO = 1000;  // 10%
```

### 2.3 Core Functions

```solidity
// Transfer (with tax)
function transfer(address to, uint256 amount) public override returns (bool);

// Transfer from (allowance)
function transferFrom(address from, address to, uint256 amount) public override returns (bool);

// Approve
function approve(address spender, uint256 amount) public override returns (bool);

// Delegate voting rights
function delegate(address delegatee) public;

// Permit (EIP-2612)
function permit(address owner, address spender, uint256 value, uint256 deadline, uint8 v, bytes32 r, bytes32 s) public;
```

### 2.4 Transaction Tax

A **0.8%** transaction tax is collected on each transfer:

```
┌─────────────────────────────────────────┐
│           Tax Distribution                │
├─────────────────────────────────────────┤
│                                         │
│  Burn          50%  →  Reduce supply  │
│                                         │
│  Dividend Pool  20%  →  Staker dividends│
│                                         │
│  Ecosystem     20%  →  Ecosystem       │
│                 Fund      incentives    │
│                                         │
│  Protocol      10%  →  Development &   │
│                 Fund      maintenance   │
│                                         │
└─────────────────────────────────────────┘
```

### 2.5 Access Control

```solidity
// Set staking contract
function setStakingContract(address _stakingContract) external onlyOwner;

// Set dividend contract
function setDividendContract(address _dividendContract) external onlyOwner;

// Pause transfers
function pause() external onlyOwner;

// Unpause transfers
function unpause() external onlyOwner;
```

---

## 3. VIBStaking

### 3.1 Overview

The VIBStaking contract manages node staking and reward distribution.

### 3.2 Data Structures

```solidity
enum NodeType { FullNode, ValidatorNode, SuperNode }

struct StakeInfo {
    uint256 amount;
    uint256 startTime;
    uint256 rewards;
    NodeType nodeType;
    bool active;
}

struct NodeConfig {
    uint256 minStake;
    uint256 rewardRate;  // Annual reward (percentage)
    uint256 lockPeriod;   // Lock period (seconds)
}
```

### 3.3 Node Configuration

| Node Level | Minimum Stake | APY | Lock Period |
|------------|---------------|-----|-------------|
| Basic Node | 100 VIB | 3% - 10% | 90/180/365 days |
| Tier 1 | 1,000 VIB | 3% - 10% | 90/180/365 days |
| Tier 2 | 5,000 VIB | 3% - 10% | 90/180/365 days |
| Tier 3 | 10,000 VIB | 3% - 10% | 90/180/365 days |

> Note: APY is dynamically adjusted based on staking duration and lock period, up to 10%. Base APY is 3%, with additional rewards for long-term staking.

### 3.4 Core Functions

```solidity
// Stake
function stake(uint256 amount, NodeType nodeType) external;

// Unstake (must wait for lock period)
function unstake(uint256 stakeId) external;

// Claim rewards
function claimRewards() external;

// Delegate stake
function delegateStake(address to, uint256 amount) external;

// Undelegate stake
function undelegateStake(uint256 delegateId) external;

// Get stake info
function getStakeInfo(address staker) external view returns (StakeInfo[]);

// Calculate pending reward
function calculatePendingReward(address staker, uint256 stakeId) external view returns (uint256);
```

---

## 4. VIBGovernance

### 4.1 Overview

Decentralized governance contract allowing token holders to propose and vote.

### 4.2 Parameters

```solidity
uint256 public votingDelay = 1 days;      // Delay before voting starts after proposal
uint256 public votingPeriod = 7 days;    // Voting duration
uint256 public proposalThreshold = 100e18;  // Proposal threshold (100 VIB)
uint256 public quorumThreshold = 500;     // Quorum (5%)

// Governance weight configuration
uint256 public constant CAPITAL_WEIGHT_MAX = 10;   // Capital weight max 10%
uint256 public constant PRODUCTION_WEIGHT_MAX = 15; // Production weight max 15%
uint256 public constant COMMUNITY_WEIGHT_RATIO = 10; // Community consensus weight 10%
```

### 4.3 Core Functions

```solidity
// Create proposal
function propose(
    address[] memory targets,
    uint256[] memory values,
    bytes[] memory calldatas,
    string memory description
) public returns (uint256);

// Vote
function castVote(uint256 proposalId, uint8 support) public;

// Vote with reason
function castVoteWithReason(
    uint256 proposalId,
    uint8 support,
    string memory reason
) public;

// Execute proposal
function execute(
    address[] memory targets,
    uint256[] memory values,
    bytes[] memory calldatas,
    bytes32 descriptionHash
) public payable returns (uint256);

// Cancel proposal
function cancel(uint256 proposalId) public;
```

### 4.4 Voting Options

```solidity
uint8 public constant AGAINST = 0;
uint8 public constant FOR = 1;
uint8 public constant ABSTAIN = 2;
```

---

## 5. AgentRegistry

### 5.1 Overview

Agent registration and management contract.

### 5.2 Data Structures

```solidity
struct AgentInfo {
    address owner;
    string metadata;
    uint256 reputation;
    bool verified;
    uint256 registeredAt;
    uint256 lastActive;
    AgentStatus status;
}

enum AgentStatus { None, Registered, Active, Paused, Slashed }
```

### 5.3 Core Functions

```solidity
// Register Agent
function registerAgent(
    bytes32 agentId,
    string memory metadata,
    uint256 registrationFee
) external payable;

// Update Agent metadata
function updateAgentMetadata(bytes32 agentId, string memory metadata) external;

// Update Agent status
function updateAgentStatus(bytes32 agentId, AgentStatus status) external;

// Add reputation
function addReputation(bytes32 agentId, uint256 amount) external;

// Remove reputation
function removeReputation(bytes32 agentId, uint256 amount) external;

// Verify Agent
function verifyAgent(bytes32 agentId) external onlyOwner;

// Pause Agent
function pauseAgent(bytes32 agentId) external;

// Get Agent info
function getAgentInfo(bytes32 agentId) external view returns (AgentInfo memory);
```

---

## 6. ZKCredential

### 6.1 Overview

Zero-knowledge credential contract supporting privacy-preserving authentication.

### 6.2 Core Functions

```solidity
// Issue credential
function issueCredential(
    address recipient,
    bytes32 credentialHash,
    uint256 expirationTime
) external returns (uint256);

// Verify credential (zero-knowledge)
function verifyCredential(
    address recipient,
    bytes32 credentialHash,
    uint256[2] memory proof_a,
    uint256[2][2] memory proof_b,
    uint256[2] memory proof_c
) external view returns (bool);

// Revoke credential
function revokeCredential(uint256 credentialId) external;

// Batch verify
function batchVerify(
    address[] memory recipients,
    bytes32[] memory credentialHashes,
    uint256[2][] memory proof_as,
    uint256[2][2][] memory proof_bs,
    uint256[2][] memory proof_cs
) external view returns (bool[] memory);
```

---

## 7. AssetVault

### 7.1 Overview

Asset vault contract for escrow of creative asset transaction funds.

### 7.2 Core Functions

```solidity
// Deposit funds
function deposit(bytes32 agentId) external payable;

// Release funds (requires multi-party signatures)
function release(
    bytes32 agentId,
    address recipient,
    uint256 amount,
    bytes[] memory signatures
) external;

// Raise dispute
function raiseDispute(bytes32 agentId, string memory reason) external;

// Emergency withdraw
function emergencyWithdraw(bytes32 agentId) external onlyOwner;

// Get balance
function getBalance(bytes32 agentId) external view returns (uint256);
```

---

## 8. VIBTreasury

### 8.1 Overview

Treasury contract for managing platform revenue and expenditures.

### 8.2 Core Functions

```solidity
// Deposit revenue
function deposit() external payable;

// Approve payment
function approvePayment(
    address recipient,
    uint256 amount,
    string memory description
) external onlyOwner;

// Execute payment
function executePayment(uint256 paymentId) external onlyOwner;

// Get balance
function getBalance() external view returns (uint256);

// Get pending payments
function getPendingPayments() external view returns (Payment[] memory);
```

---

## 9. Usage Examples

### 9.1 JavaScript/TypeScript

```javascript
const { ethers } = require("ethers");

// Connect wallet
const provider = new ethers.JsonRpcProvider(RPC_URL);
const wallet = new ethers.Wallet(PRIVATE_KEY, provider);

// Connect to contract
const token = new ethers.Contract(
    TOKEN_ADDRESS,
    VIBEToken_ABI,
    wallet
);

// Transfer
const tx = await token.transfer(recipient, amount);
await tx.wait();

// Stake
const staking = new ethers.Contract(
    STAKING_ADDRESS,
    VIBStaking_ABI,
    wallet
);
const stakeTx = await staking.stake(amount, 1); // 1 = ValidatorNode
await stakeTx.wait();

// Governance
const governance = new ethers.Contract(
    GOVERNANCE_ADDRESS,
    VIBGovernance_ABI,
    wallet
);
const proposalTx = await governance.propose(
    [target],
    [value],
    [calldata],
    description
);
await proposalTx.wait();
```

### 9.2 Python

```python
from web3 import Web3

# Connect
w3 = Web3(Web3.HTTPProvider(RPC_URL))
account = w3.eth.account.from_key(PRIVATE_KEY)

# Token transfer
token = w3.eth.contract(address=TOKEN_ADDRESS, abi=TOKEN_ABI)
tx = token.functions.transfer(recipient, amount).build_transaction({
    'from': account.address,
    'nonce': w3.eth.get_transaction_count(account.address),
    'gas': 100000,
    'gasPrice': w3.eth.gas_price
})
signed = account.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
```

---

## 10. Security Considerations

### 10.1 Access Control

- **Ownable**: Contract owner permissions
- **AccessControl**: Role-based access control
- **Timelock**: Delayed execution protection

### 10.2 Risk Management

- **Pausable**: Emergency pause
- **Rate limiting**: Prevent abuse
- **Max withdrawal**: Reduce risk exposure

### 10.3 Auditing

All contracts have been professionally security audited:

- OpenZeppelin library verification
- CertiK security audit
- Formal verification (optional)

---

## 11. Appendix

### 11.1 ABI Files

Complete ABI files are available in the `contracts/artifacts/` directory.

### 11.2 Testnet

- **RPC**: https://rpc.testnet.usmsb.com
- **ChainID**: 99999
- **Symbol**: VIB
- **Explorer**: https://explorer.testnet.usmsb.com
