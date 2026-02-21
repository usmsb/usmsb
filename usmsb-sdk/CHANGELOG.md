# Changelog

All notable changes to the USMSB SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.0-alpha] - 2025-02-19

### Added

#### Agent SDK HTTP Server
- New `HTTPServer` class for serving agents via HTTP REST API
- `run_agent_with_http()` helper function for quick agent deployment
- Standard endpoints: `/health`, `/`, `/invoke`, `/chat`, `/heartbeat`, `/skills`
- Async lifespan management with graceful startup/shutdown
- CORS middleware support for frontend integration
- Location: `src/usmsb_sdk/agent_sdk/http_server.py`

#### Unified Protocol Layer
- New `usmsb_sdk.protocol` module consolidating all protocol implementations
- HTTP protocol with server and client support (`protocol/http/`)
- WebSocket protocol with server and client support (`protocol/websocket/`)
- MCP (Model Context Protocol) with adapter and handler (`protocol/mcp/`)
- A2A (Agent-to-Agent) protocol with server and client (`protocol/a2a/`)
- P2P protocol handler (`protocol/p2p/`)
- gRPC protocol handler (`protocol/grpc/`)
- Base protocol handler and common types (`protocol/base.py`)
- Factory function `create_protocol_handler()` for easy handler creation

#### Platform Internal Node Module
- New `usmsb_sdk.platform.internal.node` module for platform-level node management
- `NodeManager`: Node lifecycle and connection management
- `NodeDiscoveryService`: Node discovery with health checking
- `NodeBroadcastService`: Message broadcasting with acknowledgment
- `SyncService`: Data synchronization with conflict resolution
- Comprehensive configuration classes: `NodeConfig`, `NetworkConfig`, `SyncConfig`, `SecurityConfig`

#### API REST Refactoring
- Modular router architecture with separate files per domain
- `routers/` directory with 12 domain-specific routers:
  - `agents.py`: Agent management endpoints
  - `environments.py`: Environment management
  - `demands.py`: Demand/supply endpoints
  - `predictions.py`: Behavior prediction
  - `workflows.py`: Workflow management
  - `matching.py`: Supply-demand matching
  - `collaborations.py`: Agent collaboration
  - `learning.py`: Learning and improvement
  - `registration.py`: Agent registration
  - `services.py`: Service discovery
  - `network.py`: Network status
  - `system.py`: System health and info
- `schemas/` directory with Pydantic models for validation
- `services/` directory with business logic layer

### Changed

#### Directory Structure
- Created `usmsb_sdk/protocol/` as the unified protocol layer
- Created `usmsb_sdk/platform/internal/` for internal platform components
- Moved node management from `platform/external/node/` to `platform/internal/node/`
- API layer restructured from single `main.py` (2267 lines) to modular architecture

#### Module Exports
- Updated `usmsb_sdk/__init__.py` with comprehensive exports
- Updated `usmsb_sdk/agent_sdk/__init__.py` to export `HTTPServer`
- Updated `usmsb_sdk/node/__init__.py` with clear module responsibilities
- Added `usmsb_sdk/api/rest/__init__.py` for API module exports
- All protocol modules have complete `__init__.py` exports

#### BaseAgent Enhancements
- Demo `BaseAgent` now inherits from SDK `BaseAgent`
- Unified communication interface across all agents
- Consistent skill definition and publishing

### Deprecated

- `usmsb_sdk/platform/external/protocol/` - use `usmsb_sdk/protocol/` instead
- `usmsb_sdk/platform/protocols/` - use `usmsb_sdk/protocol/mcp/` for MCP
- Demo `p2p_server.py` - use `HTTPServer` from agent SDK instead
- Old import paths will show deprecation warnings

### Fixed

- Clarified communication relationships between Platform and Agent
- Unified MCP implementation (was duplicated in two directories)
- Clear separation of node core (P2P) vs. node management (platform)

### Architecture

```
usmsb_sdk/
├── core/                    # Core USMSB elements
├── node/                    # Core P2P node (independent)
├── protocol/                # Unified protocol layer
│   ├── http/               # HTTP server & client
│   ├── websocket/          # WebSocket server & client
│   ├── mcp/                # Model Context Protocol
│   ├── a2a/                # Agent-to-Agent
│   ├── p2p/                # Peer-to-Peer
│   └── grpc/               # gRPC
├── agent_sdk/              # Agent development framework
│   ├── base_agent.py       # BaseAgent abstract class
│   ├── http_server.py      # HTTP REST server (NEW)
│   ├── communication.py    # Multi-protocol communication
│   └── ...
├── platform/
│   ├── internal/           # Platform internal components
│   │   └── node/          # Node management layer
│   └── external/          # External integrations
└── api/
    └── rest/              # REST API
        ├── main.py        # Entry point (simplified)
        ├── routers/       # Domain routers
        ├── schemas/       # Pydantic models
        └── services/      # Business logic
```

### Migration Guide

#### For Agent Developers
```python
# Old way
from usmsb_sdk.agent_sdk import BaseAgent

# Still works, but now with HTTP support
from usmsb_sdk.agent_sdk import BaseAgent, HTTPServer, run_agent_with_http

# Quick start
agent = MyAgent(config)
await run_agent_with_http(agent, port=5001)
```

#### For Protocol Users
```python
# Old way
from usmsb_sdk.platform.external.protocol.http_handler import HTTPProtocolHandler

# New way
from usmsb_sdk.protocol import HTTPClient, HTTPServer

# Or use factory
from usmsb_sdk.protocol import create_protocol_handler
handler = create_protocol_handler("http")
```

#### For API Users
```python
# Routers are now in dedicated modules
from usmsb_sdk.api.rest.routers import (
    agents_router,
    predictions_router,
)

# Schemas are in schemas/
from usmsb_sdk.api.rest.schemas import (
    AgentCreate,
    PredictionRequest,
)
```

---

## [0.2.0] - 2025-01-15

### Added
- Initial Agent SDK with BaseAgent
- Multi-protocol communication support
- Agent registration and discovery
- WebSocket server support

## [0.1.0] - 2024-12-01

### Added
- Initial release
- Core USMSB elements (Agent, Object, Goal, Resource, etc.)
- Basic Python API
- Project structure
