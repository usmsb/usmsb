**[English](#blockchain-integration) | [中文](#vibe智能合约集成方案文档)**

---

# VIBE Smart Contract Integration Design Document

> Version: 1.3.0
> Date: 2026-03-03
> Network: Base Sepolia (Testnet) / Base (Mainnet)
> Status: Design Complete, Reviewed, Pending Implementation
> Revision Notes: v1.3.0 - Added multi-network configuration design, frontend integration requirements analysis

---

## 1. Project Overview

### 1.1 Goals

Integrate deployed VIBE smart contracts into USMSB SDK and platform to achieve:
- On-chain transactions between Agents
- Association of staking levels with Agent permissions
- Automatic execution of collaboration revenue sharing
- Reverse bidding for joint orders

### 1.2 Core Principles

1. **One Wallet Contract per Agent**: Deploy independent AgentWallet contract when registering an Agent
2. **Staking Level Determines Permissions**: Owner staking level determines Agent creation limits and transaction limits
3. **Design Only, No Development**: This document is for design phase, implementation follows the document
4. **Layered Integration**: SDK layer (Python client) + Platform layer (REST API)

### 1.3 Network Configuration

#### Multi-Network Configuration Design

**Important**: Do not hardcode chainId and network parameters in code! Use configuration files + environment variables.

```python
# usmsb_sdk/blockchain/config.py

from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel
import os

class NetworkType(Enum):
    """Network type"""
    TESTNET = "testnet"   # Base Sepolia
    MAINNET = "mainnet"   # Base Mainnet
    LOCAL = "local"       # Local development

class NetworkConfig(BaseModel):
    """Single network configuration"""
    name: str
    chain_id: int
    rpc_url: str
    explorer_url: str
    contracts: Dict[str, str]

# Predefined network configurations
NETWORKS: Dict[NetworkType, NetworkConfig] = {
    NetworkType.TESTNET: NetworkConfig(
        name="Base Sepolia",
        chain_id=84532,
        rpc_url="https://sepolia.base.org",
        explorer_url="https://sepolia.basescan.org",
        contracts={
            "VIBEToken": "0x91d8C3084b4fd21A04fA3584BFE357F378938dbc",
            "VIBStaking": "0xc3fbD1736a95f403A0569FcA8C84d7B85e2b4E53",
            "AgentRegistry": "0x54bEbDc40cc8B60b0922D8FA6463ab710B14dC69",
            "VIBIdentity": "0x6b72711045b3a384E26eD9039CFF4cA12b856952",
            "VIBCollaboration": "0x7E61b51c49438696195142D06f46c12d90909059",
            "JointOrder": "0xc63d9DEb845138A2C5CFF41A4Cb519ccbDf00F3a",
            "VIBDividend": "0x324571F84C092a958eB46b3478742C58a7beaE7B",
            "VIBGovernance": "0xD866536154154a378544E9dc295D510a0fe29236",
            "ZKCredential": "0x4B8465Fe80Ec91876da78DB775a551dDdBBdB04a",
        }
    ),
    NetworkType.MAINNET: NetworkConfig(
        name="Base",
        chain_id=8453,
        rpc_url="https://mainnet.base.org",
        explorer_url="https://basescan.org",
        contracts={
            # Fill in actual addresses after mainnet deployment
            "VIBEToken": "TBD",
            "VIBStaking": "TBD",
            "AgentRegistry": "TBD",
            "VIBIdentity": "TBD",
            "VIBCollaboration": "TBD",
            "JointOrder": "TBD",
            "VIBDividend": "TBD",
            "VIBGovernance": "TBD",
            "ZKCredential": "TBD",
        }
    ),
    NetworkType.LOCAL: NetworkConfig(
        name="Local",
        chain_id=31337,
        rpc_url="http://localhost:8545",
        explorer_url="",
        contracts={}  # Dynamically filled after local deployment
    )
}

class BlockchainConfig:
    """Blockchain configuration manager"""

    def __init__(self, network: Optional[NetworkType] = None):
        # Prioritize environment variables
        env_network = os.environ.get("VIBE_NETWORK", "").lower()
        if env_network:
            network = NetworkType(env_network)
        elif network is None:
            network = NetworkType.TESTNET  # Default to testnet

        self.network_type = network
        self.config = NETWORKS[network]

        # Allow environment variable to override RPC
        env_rpc = os.environ.get("VIBE_RPC_URL")
        if env_rpc:
            self.config.rpc_url = env_rpc

    @property
    def chain_id(self) -> int:
        return self.config.chain_id

    @property
    def rpc_url(self) -> str:
        return self.config.rpc_url

    @property
    def contracts(self) -> Dict[str, str]:
        return self.config.contracts

    def get_contract_address(self, name: str) -> str:
        """Get contract address"""
        return self.config.contracts.get(name)

    def get_explorer_url(self, tx_hash: str) -> str:
        """Get transaction explorer URL"""
        return f"{self.config.explorer_url}/tx/{tx_hash}"
```

#### Usage

```python
# Method 1: Auto-read from environment variable
# export VIBE_NETWORK=mainnet
config = BlockchainConfig()

# Method 2: Code specification
config = BlockchainConfig(network=NetworkType.MAINNET)

# Method 3: Override RPC (for private nodes)
# export VIBE_RPC_URL=https://my-private-node.com
config = BlockchainConfig()

# Use in transaction building
tx = contract.functions.someMethod().build_transaction({
    'from': from_address,
    'nonce': nonce,
    'chainId': config.chain_id  # Dynamic fetch, no hardcoding
})
```

#### Environment Variable Configuration

```bash
# .env.development (Testnet)
VIBE_NETWORK=testnet
VIBE_RPC_URL=https://sepolia.base.org

# .env.production (Mainnet)
VIBE_NETWORK=mainnet
VIBE_RPC_URL=https://mainnet.base.org

# .env.local (Local Development)
VIBE_NETWORK=local
VIBE_RPC_URL=http://localhost:8545
```

---

## 2. Contract Classification and Addresses

### 2.1 Deployed Contract Addresses

| Contract Name | Address | Category |
|--------------|---------|----------|
| VIBEToken | 0x91d8C3084b4fd21A04fA3584BFE357F378938dbc | Core |
| VIBStaking | 0xc3fbD1736a95f403A0569FcA8C84d7B85e2b4E53 | Core |
| AgentRegistry | 0x54bEbDc40cc8B60b0922D8FA6463ab710B14dC69 | Core |
| AgentWallet | 0x7C0EA6b69B84B673F0428A202Fbb69bA5Bc8dF02 | Core (Template) |
| VIBIdentity | 0x6b72711045b3a384E26eD9039CFF4cA12b856952 | Core |
| VIBCollaboration | 0x7E61b51c49438696195142D06f46c12d90909059 | Business |
| JointOrder | 0xc63d9DEb845138A2C5CFF41A4Cb519ccbDf00F3a | Business |
| ZKCredential | 0x4B8465Fe80Ec91876da78DB775a551dDdBBdB04a | Business |
| VIBDividend | 0x324571F84C092a958eB46b3478742C58a7beaE7B | Incentive |
| EmissionController | 0xe4a31e600D2DeB3297f3732aE509B1C1d7eAAaD6 | Incentive |
| VIBGovernance | 0xD866536154154a378544E9dc295D510a0fe29236 | Governance |

### 2.2 Integration Priority

```
High Priority (Core Functions):
├── VIBEToken      - Token basic operations
├── AgentWallet    - Agent fund management (independently deployed per Agent)
├── AgentRegistry  - Agent registration verification
├── VIBIdentity    - Agent identity + Agent count limits (key: holder Agent limit logic)
└── VIBStaking     - Staking levels (called by VIBIdentity)

Medium Priority (Business Functions):
├── VIBCollaboration - Collaboration revenue sharing
└── JointOrder       - Joint orders

Low Priority (Monitoring/Optional):
├── VIBDividend      - Dividend claiming
├── EmissionController - Emission monitoring
└── VIBGovernance    - Governance voting
```

---

## 3. Key Contract Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Owner (User)                                   │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ 1. Stake VIBE into VIBStaking                                      │ │
│  │ 2. VIBStaking returns staking level                                │ │
│  │ 3. VIBIdentity returns Agent count limit based on level           │ │
│  │ 4. Deploy AgentWallet contract                                      │ │
│  │ 5. AgentWallet calls VIBStaking to get level and update limits    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│ VIBStaking  │◄─────│ VIBIdentity │──────│AgentWallet  │
│             │      │             │      │ (one per Agent)│
│ - stake()   │      │- getAgent  │      │             │
│ - getTier() │      │  Limit()   │      │- deposit()  │
│             │      │- registerAI│      │- transfer() │
│ Tiers:      │      │  Identity()│      │- stake()    │
│ BRONZE      │      │             │      │             │
│ SILVER      │      │ Limits:     │      │ Associated: │
│ GOLD        │      │ Bronze=1    │      │ - VIBStaking│
│ PLATINUM    │      │ Silver=3    │      │ - Registry  │
└─────────────┘      │ Gold=10     │      │ - Identity  │
                     │ Platinum=50 │      └─────────────┘
                     └─────────────┘             │
                                                 ▼
                                          ┌─────────────┐
                                          │AgentRegistry│
                                          │             │
                                          │- register() │
                                          │- isValid()  │
                                          └─────────────┘
```

---

## 4. Contract Integration Details

### 4.1 VIBEToken (0x91d8...)

#### Contract Functions
- ERC-20 standard token
- Transaction tax 0.8% (burn 50%, dividend 20%, ecosystem 15%, protocol 15%)
- Supports Pausable
- **Note**: Transaction tax deducted from sender, receiver receives net amount

#### SDK Interface Design

```python
# usmsb_sdk/blockchain/contracts/vibe_token.py

class VIBETokenClient:
    """VIBE Token Client"""

    def __init__(self, web3, contract_address: str, abi: dict):
        self.web3 = web3
        self.contract = web3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=abi
        )
        self.address = contract_address

    async def balance_of(self, address: str) -> int:
        """Query balance (wei unit, 10^18)"""
        address = Web3.to_checksum_address(address)
        return await self.contract.functions.balanceOf(address).call()

    async def balance_of_vibe(self, address: str) -> float:
        """Query balance (VIBE unit)"""
        balance_wei = await self.balance_of(address)
        return balance_wei / 10**18

    async def approve(
        self,
        spender: str,
        amount: int,
        from_address: str,
        private_key: str
    ) -> str:
        """Authorize spending"""
        spender = Web3.to_checksum_address(spender)
        from_address = Web3.to_checksum_address(from_address)

        nonce = await self.web3.eth.get_transaction_count(from_address)
        tx = self.contract.functions.approve(spender, amount).build_transaction({
            'from': from_address,
            'nonce': nonce,
            'chainId': 84532
        })

        signed = self.web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = await self.web3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()

    async def allowance(self, owner: str, spender: str) -> int:
        """Query allowance"""
        owner = Web3.to_checksum_address(owner)
        spender = Web3.to_checksum_address(spender)
        return await self.contract.functions.allowance(owner, spender).call()

    async def get_tax_breakdown(self, amount: int) -> dict:
        """Calculate transaction tax details"""
        result = await self.contract.functions.getTaxBreakdown(amount).call()
        return {
            "tax_amount": result[0],
            "burn_amount": result[1],
            "dividend_amount": result[2],
            "ecosystem_amount": result[3],
            "protocol_amount": result[4],
            "net_amount": amount - result[0]
        }

    async def get_net_transfer_amount(self, amount: int) -> int:
        """Calculate actual amount received (after tax)"""
        return await self.contract.functions.getNetTransferAmount(amount).call()
```

---

### 4.2 AgentWallet (Dynamic Deployment)

#### Contract Functions
- Independent smart contract wallet for each Agent
- Daily limit control (default 500/transaction, 1000/day)
- Large transfer approval process
- Associated with VIBStaking for level and limit multiplier

#### Important: Agent Backend Private Key Management

**Key Finding**: AgentWallet's `executeTransfer` can only be called by Agent (onlyAgent modifier)

```solidity
modifier onlyAgent() {
    require(msg.sender == agent, "AgentWallet: caller is not agent");
    _;
}

function executeTransfer(address to, uint256 amount) external onlyAgent ...
```

**This means**:
1. Agent backend service needs to hold the private key
2. This private key's address is passed as `_agent` parameter when deploying AgentWallet
3. Only this address can call `executeTransfer`

#### Agent Creation Complete Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Agent Creation Flow                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Prerequisites:                                                         │
│  - Owner has staked VIBE (in VIBStaking)                              │
│  - Owner has Agent backend service private key                        │
│                                                                         │
│  Step 1: Check Limits                                                  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Call VIBIdentity.getAgentLimit(owner) to get limit                │  │
│  │ Call VIBIdentity.getUserAgentCount(owner) to get created count   │  │
│  │ Verify: current < limit                                          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│              │                                                          │
│              ↓ Pass                                                    │
│                                                                         │
│  Step 2: Generate or Obtain Agent Address                             │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Option A: Agent backend generates address and private key       │  │
│  │ Option B: Platform generates address and private key, securely  │  │
│  │            transfers to Agent service                            │  │
│  │                                                                   │  │
│  │ Return: agent_address (EOA address)                             │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│              │                                                          │
│              ↓                                                          │
│                                                                         │
│  Step 3: Deploy AgentWallet Contract                                   │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ constructor(                                                     │  │
│  │      _owner: owner address,           // Owner's EOA address    │  │
│  │      _agent: agent_address,           // Agent backend EOA addr  │  │
│  │      _vibeToken: 0x91d8...,       // VIBEToken address         │  │
│  │      _registry: 0x54bE...,        // AgentRegistry address      │  │
│  │      _stakingContract: 0xc3fb...  // VIBStaking address        │  │
│  │ )                                                                │  │
│  │                                                                   │  │
│  │ Deployer: Can be Owner or Platform (Owner pays Gas)             │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│              │                                                          │
│              ↓ Returns wallet_contract_address                          │
│                                                                         │
│  Step 4: Register to AgentRegistry                                     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ AgentRegistry.registerAgent(wallet_contract_address)             │  │
│  │                                                                   │  │
│  │ Note: registerAgent gets Owner from msg.sender                  │  │
│  │ So must be called by Owner (or platform using Owner's private    │  │
│  │ key)                                                             │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│              │                                                          │
│              ↓                                                          │
│                                                                         │
│  Step 5: Register VIBIdentity (Optional but Recommended)             │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ VIBIdentity.registerAIIdentityFor(                               │  │
│  │     agentAddress: agent_address,  // Agent backend address       │  │
│  │     name: "Agent name",                                           │  │
│  │     metadata: "Agent capability description JSON"             │  │
│  │ )                                                                │  │
│  │                                                                   │  │
│  │ Note: This consumes ETH or VIBE as registration fee             │  │
│  │ Also increases creator's agent count                             │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│              │                                                          │
│              ↓                                                          │
│                                                                         │
│  Step 6: Initialize Wallet (Owner Recharges)                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ 1. VIBEToken.approve(wallet_address, amount)  // Owner approves │  │
│  │ 2. AgentWallet.deposit(amount)                // Owner deposits  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  Final State:                                                          │
│  - owner: Owner's EOA address                                         │
│  - agent_address: Agent backend's EOA address (holds private key)    │
│  - wallet_contract: AgentWallet contract address                      │
│  - staking level: Obtained from VIBStaking                           │
│  - transaction limit: Dynamically adjusted based on level             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 4.3 AgentRegistry (0x54bE...)

#### Contract Functions
- Agent registry, records AgentWallet contract addresses
- Validates Agent validity
- Manages Agent-Owner relationships

#### Key Finding: registerAgent Caller

```solidity
function registerAgent(address agentWallet) external override nonReentrant {
    // Get caller address (in actual deployment, this should be the creator's owner)
    address owner = msg.sender;

    _validAgents[agentWallet] = true;
    _agentToOwner[agentWallet] = owner;
    _ownerAgentCount[owner]++;
    _registeredAgents.push(agentWallet);

    emit AgentRegistered(agentWallet, owner);
}
```

**Key Point**: `msg.sender` is recorded as Owner, so must be called by Owner (or using Owner's private key)

---

### 4.4 VIBIdentity (0x6b72...)

#### Contract Functions
- Soul-bound Token (SBT) identity authentication
- **Agent count limits** (core function)
- Human service provider registration

#### Key Finding: Agent Count Limit Logic

```solidity
// Limit constants in VIBIdentity
uint256 public constant BRONZE_AGENT_LIMIT = 1;
uint256 public constant SILVER_AGENT_LIMIT = 3;
uint256 public constant GOLD_AGENT_LIMIT = 10;
uint256 public constant PLATINUM_AGENT_LIMIT = 50;

// When getting limit, call VIBStaking
function _getAgentLimit(address user) internal view returns (uint256) {
    if (stakingContract != address(0)) {
        try IVIBStakingForIdentity(stakingContract).getStakingTier(user) returns (
            IVIBStakingForIdentity.StakeTier tier
        ) {
            if (tier == IVIBStakingForIdentity.StakeTier.PLATINUM) return PLATINUM_AGENT_LIMIT;
            if (tier == IVIBStakingForIdentity.StakeTier.GOLD) return GOLD_AGENT_LIMIT;
            if (tier == IVIBStakingForIdentity.StakeTier.SILVER) return SILVER_AGENT_LIMIT;
        } catch {}
    }
    return BRONZE_AGENT_LIMIT; // Default 1
}
```

**Conclusion**: Agent count limits are managed by VIBIdentity, which internally calls VIBStaking for the level

---

### 4.5 VIBStaking (0xc3fb...)

#### Contract Functions
- VIBE staking
- Multiple tiers (BRONZE, SILVER, GOLD, PLATINUM)
- Multiple lock periods (none, 30 days, 90 days, 180 days, 365 days)
- Dynamic APY (anti-death spiral mechanism)
- Called by VIBIdentity to get tier

#### Staking Tiers and Thresholds

| Tier | Min Stake | Agent Limit | Daily Limit | Per-Tx Limit |
|------|-----------|-------------|-------------|--------------|
| BRONZE | 0 | 1 | 1000 | 500 |
| SILVER | 1000 | 3 | 3000 | 1500 |
| GOLD | 5000 | 10 | 10000 | 5000 |
| PLATINUM | 20000 | 50 | 50000 | 25000 |

---

## 5. Code Architecture Design

### 5.1 Directory Structure

```
usmsb_sdk/blockchain/
├── __init__.py
├── config.py                 # Network configuration management
├── client.py                # Unified client entry
├── contracts/
│   ├── __init__.py
│   ├── vibe_token.py        # VIBEToken client
│   ├── agent_wallet.py      # AgentWallet client + factory
│   ├── agent_registry.py    # AgentRegistry client
│   ├── vib_identity.py      # VIBIdentity client
│   ├── vib_staking.py       # VIBStaking client
│   ├── vib_collaboration.py # VIBCollaboration client
│   ├── joint_order.py       # JointOrder client
│   ├── vib_dividend.py      # VIBDividend client
│   ├── zk_credential.py     # ZKCredential client
│   └── vib_governance.py    # VIBGovernance client
├── utils/
│   ├── __init__.py
│   ├── gas.py               # Gas estimation and optimization
│   ├── events.py            # Event parsing
│   └── transactions.py     # Transaction helpers
└── abis/                    # Contract ABIs (JSON files)
    ├── VIBEToken.json
    ├── AgentWallet.json
    ├── AgentRegistry.json
    ├── VIBIdentity.json
    ├── VIBStaking.json
    ├── VIBCollaboration.json
    ├── JointOrder.json
    ├── VIBDividend.json
    ├── ZKCredential.json
    └── VIBGovernance.json
```

---

## 6. Private Key Management Strategy

### 6.1 Private Keys Involved

| Key Type | Holder | Usage | Security Level |
|----------|--------|-------|----------------|
| Owner Private Key | User wallet | Staking, authorization, large transfers | Highest (user controls) |
| Agent Private Key | Agent backend | Daily operations, small transfers | High (service holds) |
| Platform Operator Key | Platform backend | Contract deployment, admin operations | High |

### 6.2 Agent Private Key Storage Solutions

1. **Environment Variables**: Suitable for development/testing
2. **Encrypted Storage**: Database encrypted with KMS
3. **Hardware Security Module (HSM)**: For production
4. **Secrets Management Service**: AWS Secrets Manager, HashiCorp Vault

---

## 7. Platform API Design

### 7.1 Blockchain API Routes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/blockchain/balance/{address}` | GET | Query token balance |
| `/api/v1/blockchain/stake` | POST | Stake VIBE |
| `/api/v1/blockchain/unstake` | POST | Unstake VIBE |
| `/api/v1/blockchain/agent/deploy` | POST | Deploy AgentWallet |
| `/api/v1/blockchain/agent/register` | POST | Register Agent |
| `/api/v1/blockchain/agent/transfer` | POST | Agent transfer |
| `/api/v1/blockchain/collaboration/create` | POST | Create collaboration |
| `/api/v1/blockchain/governance/vote` | POST | Submit vote |

---

## 8. Implementation Plan

### Phase 1: Infrastructure (2 days)
- Network configuration module
- Basic client setup
- ABIs loading

### Phase 2: Core Contracts (3 days)
- VIBEToken client
- AgentWallet factory + client
- AgentRegistry client

### Phase 3: Business Contracts (2 days)
- VIBIdentity client
- VIBStaking client

### Phase 4: Integration and Management (2 days)
- VIBCollaboration client
- JointOrder client

### Phase 5: Platform API (2 days)
- REST API endpoints
- Event listeners

### Phase 6: Testing and Documentation (2 days)
- Unit tests
- Integration tests
- Documentation

**Total: 13 days**

---

## 9. Frontend Integration Requirements

### 10.1 Wallet Connection (Required)
- Support MetaMask, WalletConnect
- Chain switching (Base Sepolia / Base)
- Account change detection

### 10.2 New Pages/Components
- Staking page
- Agent deployment wizard
- Transaction history
- Governance voting

### 10.3 Key UI Flows

#### Agent Creation Flow (Frontend)
```
1. User connects wallet
2. Check Owner's staking level
3. Display Agent count limit
4. User clicks "Create Agent"
5. Generate Agent address (frontend or request from backend)
6. Confirm deployment in wallet
7. Wait for transaction confirmation
8. Display success with Agent address
```

---

## 10. Error Handling and Edge Cases

### 11.1 Common Contract Error Codes

| Error Code | Description | Handling |
|------------|-------------|----------|
| INSUFFICIENT_BALANCE | Insufficient balance | Prompt user to recharge |
| ALLOWANCE_LOW | Insufficient allowance | Prompt user to approve |
| AGENT_LIMIT_REACHED | Agent limit reached | Prompt user to upgrade staking |
| TRANSFER_LIMIT_EXCEEDED | Exceeds daily/per-transaction limit | Split into multiple transactions |
| NOT_OWNER | Not the owner | Check caller权限 |

---

## 11. Gas Optimization Suggestions

### 12.1 Batch Operations
- Use multicall for multiple reads
- Batch multiple token transfers

### 12.2 Transaction Estimation
```python
async def estimate_gas(contract, method_name, args, from_address):
    """Estimate gas fee"""
    method = getattr(contract.functions, method_name)
    gas_estimate = await method(*args).estimate_gas({'from': from_address})
    # Add 20% safety margin
    return int(gas_estimate * 1.2)
```

### 12.3 EIP-1559 Transaction Building
```python
async def build_eip1559_transaction(web3, contract, method_name, args, from_address):
    """Build EIP-1559 transaction"""
    gas_price = await get_gas_price(web3)
    nonce = await web3.eth.get_transaction_count(from_address)

    method = getattr(contract.functions, method_name)
    tx = method(*args).build_transaction({
        'from': from_address,
        'nonce': nonce,
        'chainId': 84532,
        'maxFeePerGas': gas_price['max_fee'],
        'maxPriorityFeePerGas': gas_price['priority_fee'],
        'type': 2  # EIP-1559
    })

    return tx
```

---

## 12. Appendix

### A. Getting Contract ABIs

```bash
# Extract ABI from compiled artifacts
cd contracts
npx hardhat compile
# ABI located at artifacts/src/<ContractName>.sol/<ContractName>.json
```

### B. Getting Testnet Tokens

```bash
# Base Sepolia Faucet
https://faucet.triangleplatform.com/base/sepolia
```

### C. Related Documentation

| Document | Description |
|----------|-------------|
| [AGENT_KEY_MANAGEMENT.md](./AGENT_KEY_MANAGEMENT.md) | Agent key management scheme (detailed) |
| [PERMISSION_SYSTEM.md](./PERMISSION_SYSTEM.md) | Permission system design |

### D. Contract Source Locations

```
contracts/src/
├── VIBEToken.sol           # Token contract
├── AgentWallet.sol         # Agent wallet contract
├── AgentRegistry.sol       # Agent registry
├── VIBIdentity.sol         # Identity authentication
├── VIBStaking.sol          # Staking contract
├── VIBCollaboration.sol    # Collaboration revenue sharing
├── JointOrder.sol          # Joint orders
├── VIBDividend.sol         # Dividend contract
├── ZKCredential.sol        # Zero-knowledge credentials
└── VIBGovernance.sol       # Governance contract
```

---

**End of Document**

> This document is a design scheme for smart contract integration (v1.3.0), with issues corrected based on code review.
>
> **Update History**:
> - v1.0.0: Initial version
> - v1.1.0: Corrected Agent private key, count limit issues based on code review
> - v1.2.0: Added VIBDividend/ZKCredential/VIBGovernance analysis, event listeners, error handling, gas optimization
> - v1.3.0: Added multi-network configuration design (solving chainId hardcoding issue), added frontend integration requirements analysis

---

<details>
<summary><h2>中文翻译</h2></summary>

# VIBE 智能合约集成方案文档

> 版本: 1.3.0
> 日期: 2026-03-03
> 网络: Base Sepolia (测试网) / Base (主网)
> 状态: 设计完成，已审查，待实现
> 修订说明: v1.3.0 - 添加多网络配置设计、前端集成需求分析

---

## 一、项目概述

### 1.1 目标

将已部署的VIBE智能合约集成到USMSB SDK和平台中，实现：
- Agent之间的链上交易
- 质押等级与Agent权限的关联
- 协作分成的自动执行
- 联合订单的反向竞价

### 1.2 核心原则

1. **每个Agent一个Wallet合约**: 注册Agent时部署独立的AgentWallet合约
2. **质押等级决定权限**: Owner质押等级决定可创建Agent数量和交易限额
3. **只设计方案不开发**: 本文档为设计阶段，后续按文档实现
4. **分层集成**: SDK层（Python客户端）+ 平台层（REST API）

### 1.3 网络配置

#### 多网络配置设计

**重要**：不要在代码中硬编码chainId和网络参数！应使用配置文件 + 环境变量。

```python
# usmsb_sdk/blockchain/config.py

from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel
import os

class NetworkType(Enum):
    """网络类型"""
    TESTNET = "testnet"   # Base Sepolia
    MAINNET = "mainnet"   # Base Mainnet
    LOCAL = "local"       # 本地开发

class NetworkConfig(BaseModel):
    """单个网络的配置"""
    name: str
    chain_id: int
    rpc_url: str
    explorer_url: str
    contracts: Dict[str, str]

# 预定义网络配置
NETWORKS: Dict[NetworkType, NetworkConfig] = {
    NetworkType.TESTNET: NetworkConfig(
        name="Base Sepolia",
        chain_id=84532,
        rpc_url="https://sepolia.base.org",
        explorer_url="https://sepolia.basescan.org",
        contracts={
            "VIBEToken": "0x91d8C3084b4fd21A04fA3584BFE357F378938dbc",
            "VIBStaking": "0xc3fbD1736a95f403A0569FcA8C84d7B85e2b4E53",
            "AgentRegistry": "0x54bEbDc40cc8B60b0922D8FA6463ab710B14dC69",
            "VIBIdentity": "0x6b72711045b3a384E26eD9039CFF4cA12b856952",
            "VIBCollaboration": "0x7E61b51c49438696195142D06f46c12d90909059",
            "JointOrder": "0xc63d9DEb845138A2C5CFF41A4Cb519ccbDf00F3a",
            "VIBDividend": "0x324571F84C092a958eB46b3478742C58a7beaE7B",
            "VIBGovernance": "0xD866536154154a378544E9dc295D510a0fe29236",
            "ZKCredential": "0x4B8465Fe80Ec91876da78DB775a551dDdBBdB04a",
        }
    ),
    NetworkType.MAINNET: NetworkConfig(
        name="Base",
        chain_id=8453,
        rpc_url="https://mainnet.base.org",
        explorer_url="https://basescan.org",
        contracts={
            # 主网部署后填入实际地址
            "VIBEToken": "待部署",
            "VIBStaking": "待部署",
            "AgentRegistry": "待部署",
            "VIBIdentity": "待部署",
            "VIBCollaboration": "待部署",
            "JointOrder": "待部署",
            "VIBDividend": "待部署",
            "VIBGovernance": "待部署",
            "ZKCredential": "待部署",
        }
    ),
    NetworkType.LOCAL: NetworkConfig(
        name="Local",
        chain_id=31337,
        rpc_url="http://localhost:8545",
        explorer_url="",
        contracts={}  # 本地部署后动态填入
    )
}

class BlockchainConfig:
    """区块链配置管理器"""

    def __init__(self, network: Optional[NetworkType] = None):
        # 优先使用环境变量
        env_network = os.environ.get("VIBE_NETWORK", "").lower()
        if env_network:
            network = NetworkType(env_network)
        elif network is None:
            network = NetworkType.TESTNET  # 默认测试网

        self.network_type = network
        self.config = NETWORKS[network]

        # 允许环境变量覆盖RPC
        env_rpc = os.environ.get("VIBE_RPC_URL")
        if env_rpc:
            self.config.rpc_url = env_rpc

    @property
    def chain_id(self) -> int:
        return self.config.chain_id

    @property
    def rpc_url(self) -> str:
        return self.config.rpc_url

    @property
    def contracts(self) -> Dict[str, str]:
        return self.config.contracts

    def get_contract_address(self, name: str) -> str:
        """获取合约地址"""
        return self.config.contracts.get(name)

    def get_explorer_url(self, tx_hash: str) -> str:
        """获取交易浏览器URL"""
        return f"{self.config.explorer_url}/tx/{tx_hash}"
```

#### 使用方式

```python
# 方式1: 自动从环境变量读取
# export VIBE_NETWORK=mainnet
config = BlockchainConfig()

# 方式2: 代码指定
config = BlockchainConfig(network=NetworkType.MAINNET)

# 方式3: 覆盖RPC（用于私有节点）
# export VIBE_RPC_URL=https://my-private-node.com
config = BlockchainConfig()

# 在交易构建中使用
tx = contract.functions.someMethod().build_transaction({
    'from': from_address,
    'nonce': nonce,
    'chainId': config.chain_id  # 动态获取，不硬编码
})
```

#### 环境变量配置

```bash
# .env.development (测试网)
VIBE_NETWORK=testnet
VIBE_RPC_URL=https://sepolia.base.org

# .env.production (主网)
VIBE_NETWORK=mainnet
VIBE_RPC_URL=https://mainnet.base.org

# .env.local (本地开发)
VIBE_NETWORK=local
VIBE_RPC_URL=http://localhost:8545
```

---

## 二、合约分类与地址

### 2.1 已部署合约地址

| 合约名 | 地址 | 分类 |
|--------|------|------|
| VIBEToken | 0x91d8C3084b4fd21A04fA3584BFE357F378938dbc | 核心 |
| VIBStaking | 0xc3fbD1736a95f403A0569FcA8C84d7B85e2b4E53 | 核心 |
| AgentRegistry | 0x54bEbDc40cc8B60b0922D8FA6463ab710B14dC69 | 核心 |
| AgentWallet | 0x7C0EA6b69B84B673F0428A202Fbb69bA5Bc8dF02 | 核心(模板) |
| VIBIdentity | 0x6b72711045b3a384E26eD9039CFF4cA12b856952 | 核心 |
| VIBCollaboration | 0x7E61b51c49438696195142D06f46c12d90909059 | 业务 |
| JointOrder | 0xc63d9DEb845138A2C5CFF41A4Cb519ccbDf00F3a | 业务 |
| ZKCredential | 0x4B8465Fe80Ec91876da78DB775a551dDdBBdB04a | 业务 |
| VIBDividend | 0x324571F84C092a958eB46b3478742C58a7beaE7B | 激励 |
| EmissionController | 0xe4a31e600D2DeB3297f3732aE509B1C1d7eAAaD6 | 激励 |
| VIBGovernance | 0xD866536154154a378544E9dc295D510a0fe29236 | 治理 |

### 2.2 集成优先级

```
高优先级（核心功能）:
├── VIBEToken      - 代币基础操作
├── AgentWallet    - Agent资金管理（每个Agent独立部署）
├── AgentRegistry  - Agent注册验证
├── VIBIdentity    - Agent身份+数量限制（关键：持有Agent限制逻辑）
└── VIBStaking     - 质押等级（被VIBIdentity调用）

中优先级（业务功能）:
├── VIBCollaboration - 协作分成
└── JointOrder       - 联合订单

低优先级（监控/可选）:
├── VIBDividend      - 分红领取
├── EmissionController - 释放监控
└── VIBGovernance    - 治理投票
```

---

## 三、关键合约关系图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Owner (用户)                                   │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ 1. 质押VIBE到VIBStaking                                            │ │
│  │ 2. VIBStaking返回质押等级                                          │ │
│  │ 3. VIBIdentity根据等级返回Agent数量限制                            │ │
│  │ 4. 部署AgentWallet合约                                             │ │
│  │ 5. AgentWallet调用VIBStaking获取等级更新限额                       │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│ VIBStaking  │◄─────│ VIBIdentity │──────│AgentWallet  │
│             │      │             │      │ (每Agent一个)│
│ - stake()   │      │- getAgent  │      │             │
│ - getTier() │      │  Limit()   │      │- deposit()  │
│             │      │- registerAI │      │- transfer() │
│ 等级:       │      │  Identity()│      │- stake()    │
│ BRONZE      │      │             │      │             │
│ SILVER      │      │ 限制:       │      │ 关联:       │
│ GOLD        │      │ Bronze=1    │      │ - VIBStaking│
│ PLATINUM    │      │ Silver=3    │      │ - Registry  │
└─────────────┘      │ Gold=10     │      │ - Identity  │
                     │ Platinum=50 │      └─────────────┘
                     └─────────────┘             │
                                                 ▼
                                          ┌─────────────┐
                                          │AgentRegistry│
                                          │             │
                                          │- register() │
                                          │- isValid()  │
                                          └─────────────┘
```

---

## 四、逐个合约集成方案

### 4.1 VIBEToken (0x91d8...)

#### 合约功能
- ERC-20标准代币
- 交易税0.8%（销毁50%、分红20%、生态15%、协议15%）
- 支持Pausable
- **注意**: 交易税从发送者扣除，接收者收到净额

### 4.2 AgentWallet (动态部署)

#### 合约功能
- 每个Agent独立的智能合约钱包
- 日限额控制（默认500/笔，1000/日）
- 大额转账审批流程
- 与VIBStaking关联获取等级和限额倍数

#### 重要修正：Agent后端私钥管理

**关键发现**: AgentWallet的`executeTransfer`只能由Agent调用（onlyAgent修饰符）

```solidity
modifier onlyAgent() {
    require(msg.sender == agent, "AgentWallet: caller is not agent");
    _;
}

function executeTransfer(address to, uint256 amount) external onlyAgent ...
```

**这意味着**:
1. Agent后端服务需要持有私钥
2. 该私钥对应的地址在部署AgentWallet时传入`_agent`参数
3. 只有这个地址才能调用`executeTransfer`

#### Agent创建完整流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Agent创建流程                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  前置条件:                                                              │
│  - Owner已质押VIBE（在VIBStaking中）                                   │
│  - Owner有Agent后端服务的私钥                                          │
│                                                                         │
│  Step 1: 检查限制                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ 调用 VIBIdentity.getAgentLimit(owner) 获取限制                   │  │
│  │ 调用 VIBIdentity.getUserAgentCount(owner) 获取已创建数量         │  │
│  │ 验证: current < limit                                            │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│              │                                                          │
│              ↓ 通过                                                    │
│                                                                         │
│  Step 2: 生成或获取Agent地址                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ 方案A: Agent后端自己生成地址和私钥                                │  │
│  │ 方案B: 平台为Agent生成地址和私钥，安全传递给Agent服务             │  │
│  │                                                                   │  │
│  │ 返回: agent_address (EOA地址)                                    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│              │                                                          │
│              ↓                                                          │
│                                                                         │
│  Step 3: 部署AgentWallet合约                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ constructor(                                                     │  │
│  │      _owner: owner地址,           // Owner的EOA地址              │  │
│  │      _agent: agent_address,       // Agent后端服务的EOA地址      │  │
│  │      _vibeToken: 0x91d8...,       // VIBEToken地址               │  │
│  │      _registry: 0x54bE...,        // AgentRegistry地址           │  │
│  │      _stakingContract: 0xc3fb...  // VIBStaking地址              │  │
│  │  )                                                                │  │
│  │                                                                   │  │
│  │ 部署者: 可以是Owner或平台（需要Owner支付Gas）                   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│              │                                                          │
│              ↓ 返回 wallet_contract_address                            │
│                                                                         │
│  Step 4: 注册到AgentRegistry                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ AgentRegistry.registerAgent(wallet_contract_address)             │  │
│  │                                                                   │  │
│  │ 注意: registerAgent从msg.sender获取Owner                        │  │
│  │ 所以必须由Owner调用（或平台使用Owner的私钥代调用）               │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│              │                                                          │
│              ↓                                                          │
│                                                                         │
│  Step 5: 注册VIBIdentity（可选但推荐）                                 │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ VIBIdentity.registerAIIdentityFor(                               │  │
│  │     agentAddress: agent_address,  // Agent后端服务地址           │  │
│  │     name: "Agent名称",                                           │  │
│  │     metadata: "Agent能力描述JSON"                                │  │
│  │ )                                                                │  │
│  │                                                                   │  │
│  │ 注意: 这会消耗ETH或VIBE作为注册费                                │  │
│  │ 同时会增加创建者的agent计数                                      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│              │                                                          │
│              ↓                                                          │
│                                                                         │
│  Step 6: 初始化钱包（Owner充值）                                       │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ 1. VIBEToken.approve(wallet_address, amount)  // Owner授权       │  │
│  │ 2. AgentWallet.deposit(amount)                // Owner充值       │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  最终状态:                                                              │
│  - owner: Owner的EOA地址                                               │
│  - agent_address: Agent后端服务的EOA地址（持有私钥）                   │
│  - wallet_contract: AgentWallet合约地址                                │
│  - 质押等级: 通过VIBStaking获取                                        │
│  - 交易限额: 根据等级动态调整                                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.3 AgentRegistry (0x54bE...)

#### 合约功能
- Agent注册表，记录AgentWallet合约地址
- 验证Agent有效性
- 管理Agent与Owner的关系

#### 重要发现：registerAgent的调用者

```solidity
function registerAgent(address agentWallet) external override nonReentrant {
    // 获取调用者地址（在实际部署时，这应该是创建 Agent 的主人）
    address owner = msg.sender;

    _validAgents[agentWallet] = true;
    _agentToOwner[agentWallet] = owner;
    _ownerAgentCount[owner]++;
    _registeredAgents.push(agentWallet);

    emit AgentRegistered(agentWallet, owner);
}
```

**关键点**: `msg.sender`被记录为Owner，所以必须由Owner调用（或使用Owner私钥）

### 4.4 VIBIdentity (0x6b72...)

#### 合约功能
- 灵魂绑定代币(SBT)身份认证
- **Agent数量限制**（核心功能）
- 人类服务者注册

#### 重要发现：Agent数量限制逻辑

```solidity
// VIBIdentity中的限制常量
uint256 public constant BRONZE_AGENT_LIMIT = 1;
uint256 public constant SILVER_AGENT_LIMIT = 3;
uint256 public constant GOLD_AGENT_LIMIT = 10;
uint256 public constant PLATINUM_AGENT_LIMIT = 50;

// 获取限制时调用VIBStaking
function _getAgentLimit(address user) internal view returns (uint256) {
    if (stakingContract != address(0)) {
        try IVIBStakingForIdentity(stakingContract).getStakingTier(user) returns (
            IVIBStakingForIdentity.StakeTier tier
        ) {
            if (tier == IVIBStakingForIdentity.StakeTier.PLATINUM) return PLATINUM_AGENT_LIMIT;
            if (tier == IVIBStakingForIdentity.StakeTier.GOLD) return GOLD_AGENT_LIMIT;
            if (tier == IVIBStakingForIdentity.StakeTier.SILVER) return SILVER_AGENT_LIMIT;
        } catch {}
    }
    return BRONZE_AGENT_LIMIT; // 默认1个
}
```

**结论**: Agent数量限制由VIBIdentity管理，它内部调用VIBStaking获取等级

### 4.5 VIBStaking (0xc3fb...)

#### 合约功能
- VIBE质押
- 多等级（BRONZE, SILVER, GOLD, PLATINUM）
- 多锁仓期（无锁、30天、90天、180天、365天）
- 动态APY（反死螺旋机制）
- 被VIBIdentity调用获取等级

#### 质押等级与阈值

| 等级 | 最小质押 | Agent限额 | 日限额 | 单笔限额 |
|------|-----------|-----------|--------|----------|
| BRONZE | 0 | 1 | 1000 | 500 |
| SILVER | 1000 | 3 | 3000 | 1500 |
| GOLD | 5000 | 10 | 10000 | 5000 |
| PLATINUM | 20000 | 50 | 50000 | 25000 |

---

## 五、代码架构设计

### 5.1 目录结构

```
usmsb_sdk/blockchain/
├── __init__.py
├── config.py                 # 网络配置管理
├── client.py                 # 统一客户端入口
├── contracts/
│   ├── __init__.py
│   ├── vibe_token.py         # VIBEToken客户端
│   ├── agent_wallet.py       # AgentWallet客户端+工厂
│   ├── agent_registry.py     # AgentRegistry客户端
│   ├── vib_identity.py       # VIBIdentity客户端
│   ├── vib_staking.py        # VIBStaking客户端
│   ├── vib_collaboration.py # VIBCollaboration客户端
│   ├── joint_order.py        # JointOrder客户端
│   ├── vib_dividend.py       # VIBDividend客户端
│   ├── zk_credential.py     # ZKCredential客户端
│   └── vib_governance.py     # VIBGovernance客户端
├── utils/
│   ├── __init__.py
│   ├── gas.py                # Gas估算和优化
│   ├── events.py             # 事件解析
│   └── transactions.py       # 交易辅助
└── abis/                    # 合约ABI（JSON文件）
    ├── VIBEToken.json
    ├── AgentWallet.json
    ├── AgentRegistry.json
    ├── VIBIdentity.json
    ├── VIBStaking.json
    ├── VIBCollaboration.json
    ├── JointOrder.json
    ├── VIBDividend.json
    ├── ZKCredential.json
    └── VIBGovernance.json
```

---

## 六、私钥管理策略

### 6.1 涉及的私钥

| 私钥类型 | 持有者 | 用途 | 安全等级 |
|----------|--------|------|----------|
| Owner私钥 | 用户钱包 | 质押、授权、大额转账 | 最高（用户控制） |
| Agent私钥 | Agent后端 | 日常操作、小额转账 | 高（服务持有） |
| 平台操作员私钥 | 平台后端 | 合约部署、管理操作 | 高 |

### 6.2 Agent私钥存储方案

1. **环境变量**: 适用于开发/测试
2. **加密存储**: 数据库使用KMS加密
3. **硬件安全模块(HSM)**: 用于生产环境
4. **密钥管理服务**: AWS Secrets Manager, HashiCorp Vault

---

## 七、平台API设计

### 7.1 区块链API路由

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/blockchain/balance/{address}` | GET | 查询代币余额 |
| `/api/v1/blockchain/stake` | POST | 质押VIBE |
| `/api/v1/blockchain/unstake` | POST | 解除质押 |
| `/api/v1/blockchain/agent/deploy` | POST | 部署AgentWallet |
| `/api/v1/blockchain/agent/register` | POST | 注册Agent |
| `/api/v1/blockchain/agent/transfer` | POST | Agent转账 |
| `/api/v1/blockchain/collaboration/create` | POST | 创建协作 |
| `/api/v1/blockchain/governance/vote` | POST | 提交投票 |

---

## 八、实现计划

### Phase 1: 基础设施（2天）
- 网络配置模块
- 基础客户端设置
- ABI加载

### Phase 2: 核心合约（3天）
- VIBEToken客户端
- AgentWallet工厂+客户端
- AgentRegistry客户端

### Phase 3: 业务合约（2天）
- VIBIdentity客户端
- VIBStaking客户端

### Phase 4: 整合与管理（2天）
- VIBCollaboration客户端
- JointOrder客户端

### Phase 5: 平台API（2天）
- REST API端点
- 事件监听器

### Phase 6: 测试与文档（2天）
- 单元测试
- 集成测试
- 文档

**总计：13天**

---

## 九、前端集成需求

### 10.1 钱包连接（必须）
- 支持MetaMask、WalletConnect
- 链切换（Base Sepolia / Base）
- 账户变更检测

### 10.2 新增页面/组件
- 质押页面
- Agent部署向导
- 交易历史
- 治理投票

### 10.3 关键UI流程

#### Agent创建流程（前端）
```
1. 用户连接钱包
2. 检查Owner的质押等级
3. 显示Agent数量限额
4. 用户点击"创建Agent"
5. 生成Agent地址（前端或请求后端）
6. 在钱包中确认部署
7. 等待交易确认
8. 显示成功及Agent地址
```

---

## 十、错误处理与异常

### 11.1 常见合约错误码

| 错误码 | 描述 | 处理方式 |
|--------|------|----------|
| INSUFFICIENT_BALANCE | 余额不足 | 提示用户充值 |
| ALLOWANCE_LOW | 授权额度不足 | 提示用户授权 |
| AGENT_LIMIT_REACHED | 达到Agent限额 | 提示用户升级质押 |
| TRANSFER_LIMIT_EXCEEDED | 超过日限额/单笔限额 | 拆分为多笔交易 |
| NOT_OWNER | 非Owner | 检查调用者权限 |

---

## 十一、Gas优化建议

### 12.1 批量操作
- 使用multicall进行批量读取
- 批量代币转账

### 12.2 交易估算
```python
async def estimate_gas(contract, method_name, args, from_address):
    """估算Gas费用"""
    method = getattr(contract.functions, method_name)
    gas_estimate = await method(*args).estimate_gas({'from': from_address})
    # 增加20%安全余量
    return int(gas_estimate * 1.2)
```

### 12.3 EIP-1559交易构建
```python
async def build_eip1559_transaction(web3, contract, method_name, args, from_address):
    """构建EIP-1559交易"""
    gas_price = await get_gas_price(web3)
    nonce = await web3.eth.get_transaction_count(from_address)

    method = getattr(contract.functions, method_name)
    tx = method(*args).build_transaction({
        'from': from_address,
        'nonce': nonce,
        'chainId': 84532,
        'maxFeePerGas': gas_price['max_fee'],
        'maxPriorityFeePerGas': gas_price['priority_fee'],
        'type': 2  # EIP-1559
    })

    return tx
```

---

## 十二、附录

### A. 合约ABI获取

```bash
# 从编译产物提取ABI
cd contracts
npx hardhat compile
# ABI位于 artifacts/src/<ContractName>.sol/<ContractName>.json
```

### B. 测试网络代币获取

```bash
# Base Sepolia Faucet
https://faucet.triangleplatform.com/base/sepolia
```

### C. 相关文档

| 文档 | 说明 |
|------|------|
| [AGENT_KEY_MANAGEMENT.md](./AGENT_KEY_MANAGEMENT.md) | Agent私钥管理方案（详细版） |
| [PERMISSION_SYSTEM.md](./PERMISSION_SYSTEM.md) | 权限系统设计 |

### D. 合约源码位置

```
contracts/src/
├── VIBEToken.sol           # 代币合约
├── AgentWallet.sol         # Agent钱包合约
├── AgentRegistry.sol       # Agent注册表
├── VIBIdentity.sol         # 身份认证
├── VIBStaking.sol          # 质押合约
├── VIBCollaboration.sol    # 协作分成
├── JointOrder.sol          # 联合订单
├── VIBDividend.sol         # 分红合约
├── ZKCredential.sol        # 零知识凭证
└── VIBGovernance.sol       # 治理合约
```

---

**文档结束**

> 本文档为智能合约集成的设计方案（v1.3.0），已根据代码审查修正问题。
>
> **更新历史**:
> - v1.0.0: 初始版本
> - v1.1.0: 基于代码审查修正Agent私钥、数量限制等问题
> - v1.2.0: 补充VIBDividend/ZKCredential/VIBGovernance合约分析，添加事件监听器、错误处理、Gas优化
> - v1.3.0: 添加多网络配置设计（解决chainId硬编码问题），添加前端集成需求分析

</details>
