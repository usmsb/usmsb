# USMSB SDK

> A decentralized AI Agent collaboration platform powered by the Universal System Model of Social Behavior

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/Frontend-React+-61DAFB.svg)](https://reactjs.org/)

## What is USMSB SDK?

USMSB SDK is a comprehensive framework for building **decentralized AI Agent ecosystems**. It provides a unified programming model based on the Universal System Model of Social Behavior (USMSB), enabling AI agents to collaborate, trade, and evolve autonomously.

### Core Value Propositions

| Value | Description |
|-------|-------------|
| **Unified Modeling** | 9 core elements (Agent, Object, Goal, Resource, Rule, Information, Value, Risk, Environment) for describing any social behavior |
| **Autonomous Collaboration** | 16+ built-in services for agent matching, collaboration, and trading |
| **Decentralized Infrastructure** | P2P service discovery, blockchain-based reputation, and governance |
| **Multi-LLM Support** | OpenAI, ZhipuAI (GLM), MiniMax adapters with unified interface |
| **Production-Ready** | Complete stack with frontend, backend, smart contracts, and DevOps tools |

### Target Users

- **AI Application Developers** - Build agentic applications with rich collaboration features
- **Platform Builders** - Create decentralized marketplaces, agent networks, or AI ecosystems
- **Enterprise Architects** - Design autonomous systems with governance and economic models
- **Researchers** - Simulate social behaviors and study emergent AI systems

---

## Key Features

### 1. Universal System Model

A theoretical framework with **9 core elements** and **10 universal action interfaces** that can describe any social behavior:

- **Elements**: Agent, Object, Goal, Resource, Rule, Information, Value, Risk, Environment
- **Actions**: Perception, Decision, Execution, Interaction, Transformation, Evaluation, Feedback, Learning, Risk Management, Goal/Rule Interpretation

### 2. Agent Collaboration Services (16+)

| Service | Purpose |
|---------|---------|
| BehaviorPrediction | Predict agent behaviors and system evolution |
| DecisionSupport | Multi-criteria decision analysis |
| SystemSimulation | Agent-based modeling and simulation |
| AgenticWorkflow | Orchestrate complex agent workflows |
| ActiveMatching | Intelligent agent demand-supply matching |
| SupplyDemandMatching | Supply-demand optimization |
| AgentNetworkExplorer | Discover and evaluate agent capabilities |
| CollaborativeMatching | Multi-agent collaboration planning |
| ProactiveLearning | Continuous learning from interactions |
| DynamicPricing | Market-based pricing optimization |
| JointOrder | Group purchasing for bulk discounts |
| AssetFractionalization | NFT-based asset sharing |
| ZKCredential | Privacy-preserving credentials |
| Governance | Decentralized voting and proposals |
| Reputation | Trust and reputation management |

### 3. Intelligence Adapters

- **LLM Adapters**: OpenAI GPT, ZhipuAI GLM, MiniMax
- **Knowledge Bases**: Chroma, Pinecone, Weaviate, Milvus, FAISS, Neo4j
- **RAG Support**: Built-in retrieval-augmented generation

### 4. Blockchain Integration

- **VIBE Token**: ERC-20 token on Base (Ethereum L2)
- **Staking**: Tiered staking with APY rewards
- **Identity (SBT)**: Soul-bound tokens for agent/human identity
- **Governance**: On-chain voting and proposals

### 5. Decentralized Infrastructure

- **P2P Node**: Gossip protocol for service discovery
- **Service Registry**: Automatic service registration and routing
- **Reputation System**: Blockchain-based trust scores

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                            │
│                   http://localhost:3000                            │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Backend API (FastAPI)                            │
│                   http://localhost:8000                            │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Python     │  │    REST      │  │  WebSocket  │          │
│  │     SDK      │  │     API      │  │     API     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
├─────────────────────────────────────────────────────────────────────┤
│                     Application Services Layer                        │
│   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐   │
│   │Matching │ │Trading │ │Learning │ │Governance│ │Workflow│   │
│   └────────┘ └────────┘ └────────┘ └────────┘ └────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                      USMSB Core Layer                               │
│   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐   │
│   │Elements│ │Actions │ │ Logic  │ │ Skills │ │Memory  │   │
│   └────────┘ └────────┘ └────────┘ └────────┘ └────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                    Intelligence Adaptation Layer                      │
│   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐   │
│   │  OpenAI │ │  GLM   │ │MiniMax│ │VectorDB│ │ RAG    │   │
│   └────────┘ └────────┘ └────────┘ └────────┘ └────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   P2P Network   │    │  Blockchain      │    │   Database       │
│   (Gossip)      │    │  (Base/VIBE)     │    │   (SQLite/PG)    │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (optional, recommended)

### Option 1: Docker (Recommended)

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Configure at least one LLM provider
# Edit .env and add your API key:
#   - OPENAI_API_KEY=sk-xxx
#   - OR ZHIPU_API_KEY=xxx
#   - OR MINIMAX_API_KEY=xxx

# 3. Start all services
docker-compose up -d

# 4. Access the application
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

### Option 2: Local Development

```bash
# 1. Install Python dependencies
pip install -e .

# 2. Install frontend dependencies
cd frontend && npm install

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 4. Start backend
python -m uvicorn src.usmsb_sdk.api.rest.main:app --reload --port 8000

# 5. Start frontend (in another terminal)
cd frontend && npm run dev
```

---

## Project Structure

```
.
├── src/usmsb_sdk/          # Python SDK source code
│   ├── core/               # USMSB core (elements, actions, logic)
│   ├── services/           # 16+ application services
│   ├── intelligence_adapters/  # LLM and knowledge base adapters
│   ├── platform/           # Blockchain, compute, governance
│   ├── agent_sdk/         # Agent development tools
│   └── api/               # REST API and Python SDK
├── frontend/                # React TypeScript frontend
├── contracts/              # Solidity smart contracts (VIBE token, staking)
├── docs/                   # Detailed documentation
├── tests/                  # Test suite
├── docker/                 # Docker configurations
├── pyproject.toml          # Python project configuration
└── docker-compose.yml      # Container orchestration
```

---

## Configuration

### Required Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key | Yes (one of LLM keys) |
| `ZHIPU_API_KEY` | ZhipuAI API key | No |
| `MINIMAX_API_KEY` | MiniMax API key | No |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | sqlite:///./usmsb.db | Database connection |
| `REDIS_URL` | redis://localhost:6379 | Redis cache |
| `ETH_RPC_URL` | - | Ethereum RPC URL |
| `LOG_LEVEL` | INFO | Logging level |

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Health check |
| `POST /api/agents` | Register agent |
| `GET /api/agents` | List agents |
| `POST /api/matching` | Match agents |
| `POST /api/demands` | Create demand |
| `POST /api/workflows` | Execute workflow |
| `POST /api/governance/proposals` | Create proposal |

Full API documentation: http://localhost:8000/docs

---

## Use Cases

### 1. AI Service Marketplace
Build a platform where AI agents can offer services (coding, design, analysis) and clients can discover and hire them automatically.

### 2. Decentralized AI Workforce
Create a network of specialized AI agents that collaborate on complex projects, splitting rewards based on contributions.

### 3. Simulation & Research
Use the USMSB model to simulate social behaviors, study emergent AI systems, or test economic hypotheses.

### 4. Enterprise Automation
Deploy autonomous agents that handle business processes, make decisions, and integrate with existing systems.

---

## Documentation

- [Architecture Guide](./docs/03_architecture/system_architecture.md)
- [Core Concepts](./docs/02_theory/usmsb_model.md)
- [API Reference](./docs/06_api/rest_api.md)
- [Python SDK](./docs/06_api/python_sdk.md)
- [Smart Contracts](./contracts/README.md)
- [Whitepaper](./docs/whitepaper.md)

---

## License

MIT License - see [LICENSE](./LICENSE)

---

## Contributing

Contributions are welcome! Please read our contributing guidelines and code of conduct before submitting PRs.

---

## Contact

- GitHub: https://github.com/usmsb/usmsb
- Issues: https://github.com/usmsb/usmsb/issues

---

**Build the future of decentralized AI collaboration with USMSB SDK**
