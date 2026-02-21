"""
Pytest Fixtures for Integration Tests

This module provides fixtures for creating test resources including:
- Agent configurations and mock agents
- Storage instances (File, SQLite, IPFS)
- Node instances and platform configurations
- Communication managers and discovery managers
- Mock servers for testing protocols
"""

import asyncio
import os
import tempfile
import pytest
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import json
import logging

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
test_logger = logging.getLogger("test_integration")


# ==================== Event Loop ====================

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ==================== Temporary Directories ====================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_db_path(temp_dir):
    """Create a temporary database path."""
    return temp_dir / "test_storage.db"


@pytest.fixture
def temp_file_path(temp_dir):
    """Create a temporary file storage path."""
    return temp_dir / "files"


# ==================== Agent Configuration Fixtures ====================

@pytest.fixture
def basic_agent_config():
    """Create a basic agent configuration for testing."""
    from usmsb_sdk.agent_sdk.agent_config import (
        AgentConfig,
        SkillDefinition,
        CapabilityDefinition,
        NetworkConfig,
        SecurityConfig,
        ProtocolType,
    )

    return AgentConfig(
        name="TestAgent",
        description="A test agent for integration testing",
        version="1.0.0",
        tags=["test", "integration"],
        skills=[
            SkillDefinition(
                name="test_skill",
                description="A test skill",
                parameters=[],
                returns="object",
            ),
            SkillDefinition(
                name="process_data",
                description="Process data skill",
                parameters=[],
                returns="object",
            ),
        ],
        capabilities=[
            CapabilityDefinition(
                name="testing",
                description="Testing capability",
                category="testing",
                level="basic",
            ),
        ],
        network=NetworkConfig(
            platform_endpoints=["http://localhost:8000"],
            p2p_listen_port=9001,
        ),
        security=SecurityConfig(
            auth_enabled=False,
            api_key=None,
        ),
        auto_register=False,
        auto_discover=False,
    )


@pytest.fixture
def multi_protocol_agent_config():
    """Create an agent configuration with multiple protocols enabled."""
    from usmsb_sdk.agent_sdk.agent_config import (
        AgentConfig,
        ProtocolConfig,
        ProtocolType,
    )

    config = AgentConfig(
        name="MultiProtocolAgent",
        description="Agent with multiple protocols",
    )
    config.enable_protocol(ProtocolType.HTTP, ProtocolConfig(
        protocol_type=ProtocolType.HTTP,
        host="0.0.0.0",
        port=8080,
    ))
    config.enable_protocol(ProtocolType.WEBSOCKET, ProtocolConfig(
        protocol_type=ProtocolType.WEBSOCKET,
        host="0.0.0.0",
        port=8765,
    ))
    config.enable_protocol(ProtocolType.A2A, ProtocolConfig(
        protocol_type=ProtocolType.A2A,
        host="0.0.0.0",
        port=8081,
    ))
    config.enable_protocol(ProtocolType.MCP, ProtocolConfig(
        protocol_type=ProtocolType.MCP,
        host="0.0.0.0",
        port=8082,
    ))
    config.enable_protocol(ProtocolType.P2P, ProtocolConfig(
        protocol_type=ProtocolType.P2P,
        host="0.0.0.0",
        port=9002,
    ))
    return config


@pytest.fixture
def agent_configs_list(basic_agent_config, multi_protocol_agent_config):
    """Create a list of agent configurations for multi-agent tests."""
    return [basic_agent_config, multi_protocol_agent_config]


# ==================== Storage Fixtures ====================

@pytest.fixture
async def file_storage(temp_file_path):
    """Create a file storage instance for testing."""
    from usmsb_sdk.platform.external.storage.file_storage import FileStorage

    storage = FileStorage(base_path=temp_file_path, cache_enabled=True)
    yield storage


@pytest.fixture
async def sqlite_storage(temp_db_path):
    """Create a SQLite storage instance for testing."""
    from usmsb_sdk.platform.external.storage.sqlite_storage import SQLiteStorage

    storage = SQLiteStorage(database_path=temp_db_path)
    yield storage


@pytest.fixture
def ipfs_storage_mock():
    """Create a mocked IPFS storage instance."""
    from usmsb_sdk.platform.external.storage.ipfs_storage import (
        IPFSStorage,
        IPFSConnectionConfig,
    )

    # Create with disabled connection for testing
    config = IPFSConnectionConfig(
        api_host=None,
        gateway_url="https://ipfs.io",
    )
    storage = IPFSStorage(config=config)

    # Mock the IPFS operations
    storage._connected = False

    yield storage


@pytest.fixture
async def storage_manager(temp_file_path, temp_db_path, ipfs_storage_mock):
    """Create a storage manager with all layers for testing."""
    from usmsb_sdk.platform.external.storage.file_storage import FileStorage
    from usmsb_sdk.platform.external.storage.sqlite_storage import SQLiteStorage
    from usmsb_sdk.platform.external.storage.storage_manager import (
        StorageManager,
        CacheStrategy,
        SyncStrategy,
    )

    file_storage = FileStorage(base_path=temp_file_path, cache_enabled=True)
    sqlite_storage = SQLiteStorage(database_path=temp_db_path)

    manager = StorageManager(
        file_storage=file_storage,
        sqlite_storage=sqlite_storage,
        ipfs_storage=ipfs_storage_mock,
        cache_strategy=CacheStrategy.WRITE_THROUGH,
        sync_strategy=SyncStrategy.HYBRID,
        sync_interval_seconds=5,
    )

    await manager.initialize()
    yield manager

    await manager.close()


# ==================== Node Fixtures ====================

@pytest.fixture
def node_config():
    """Create a P2P node configuration for testing."""
    return {
        "address": "127.0.0.1",
        "port": 19000,
        "bootstrap_peers": [],
        "capabilities": ["testing", "storage"],
        "metadata": {"test": True},
    }


@pytest.fixture
async def p2p_node(node_config):
    """Create a P2P node for testing."""
    from usmsb_sdk.node.decentralized_node import P2PNode

    node = P2PNode(config=node_config)
    started = await node.start()

    if not started:
        pytest.skip("Could not start P2P node")

    yield node

    await node.stop()


@pytest.fixture
def service_registry(p2p_node):
    """Get the service registry from a P2P node."""
    return p2p_node.registry


# ==================== Broadcast Service Fixtures ====================

@pytest.fixture
async def broadcast_service():
    """Create an environment broadcast service for testing."""
    from usmsb_sdk.platform.environment.broadcast_service import (
        EnvironmentBroadcastService,
    )

    service = EnvironmentBroadcastService(max_history=100)
    await service.start()

    yield service

    await service.stop()


# ==================== Protocol Adapter Fixtures ====================

@pytest.fixture
def mcp_adapter():
    """Create an MCP adapter for testing."""
    from usmsb_sdk.platform.protocols.mcp_adapter import MCPAdapter

    adapter = MCPAdapter(
        server_url="http://localhost:8080/mcp",
        api_key=None,
    )
    yield adapter


@pytest.fixture
async def mcp_adapter_started(mcp_adapter):
    """Create and start an MCP adapter for testing."""
    # Note: start() may fail without actual server, which is expected
    try:
        await mcp_adapter.start()
    except Exception:
        pass  # Expected if no MCP server is running

    yield mcp_adapter

    await mcp_adapter.stop()


# ==================== Agent SDK Fixtures ====================

class MockAgent:
    """Mock agent implementation for testing."""

    def __init__(self, config):
        from usmsb_sdk.agent_sdk.agent_config import AgentConfig

        self.config = config if isinstance(config, AgentConfig) else config
        self.agent_id = self.config.agent_id
        self.name = self.config.name
        self._running = False
        self._skills = {s.name: s for s in self.config.skills}
        self.logger = test_logger

        # Track calls
        self.messages_received = []
        self.skills_executed = []

    async def initialize(self):
        """Initialize the mock agent."""
        self.logger.info(f"MockAgent {self.name} initialized")

    async def handle_message(self, message, session=None):
        """Handle incoming message."""
        self.messages_received.append(message)
        self.logger.info(f"MockAgent {self.name} received message: {message}")
        return {"status": "handled", "agent": self.name}

    async def execute_skill(self, skill_name, params):
        """Execute a skill."""
        self.skills_executed.append((skill_name, params))
        self.logger.info(f"MockAgent {self.name} executing skill: {skill_name}")

        if skill_name == "test_skill":
            return {"result": "success", "params": params}
        elif skill_name == "process_data":
            return {"processed": True, "data": params}

        raise ValueError(f"Unknown skill: {skill_name}")

    async def shutdown(self):
        """Shutdown the mock agent."""
        self.logger.info(f"MockAgent {self.name} shutdown")

    async def start(self):
        """Start the mock agent."""
        await self.initialize()
        self._running = True

    async def stop(self):
        """Stop the mock agent."""
        await self.shutdown()
        self._running = False

    @property
    def is_running(self):
        return self._running

    @property
    def skills(self):
        return list(self._skills.values())


@pytest.fixture
def mock_agent(basic_agent_config):
    """Create a mock agent for testing."""
    return MockAgent(basic_agent_config)


@pytest.fixture
def mock_agents_list(agent_configs_list):
    """Create a list of mock agents for multi-agent testing."""
    return [MockAgent(config) for config in agent_configs_list]


# ==================== Communication Fixtures ====================

@pytest.fixture
async def communication_manager(basic_agent_config):
    """Create a communication manager for testing."""
    from usmsb_sdk.agent_sdk.communication import CommunicationManager

    async def message_handler(message, session=None):
        return {"status": "received", "message_id": message.message_id}

    manager = CommunicationManager(
        agent_id=basic_agent_config.agent_id,
        agent_config=basic_agent_config,
        message_handler=message_handler,
        logger=test_logger,
    )

    await manager.initialize()
    yield manager

    await manager.close()


@pytest.fixture
async def discovery_manager(basic_agent_config, communication_manager):
    """Create a discovery manager for testing."""
    from usmsb_sdk.agent_sdk.discovery import DiscoveryManager

    manager = DiscoveryManager(
        agent_id=basic_agent_config.agent_id,
        agent_config=basic_agent_config,
        communication_manager=communication_manager,
        logger=test_logger,
    )

    await manager.initialize()
    yield manager

    await manager.close()


@pytest.fixture
async def registration_manager(basic_agent_config):
    """Create a registration manager for testing."""
    from usmsb_sdk.agent_sdk.registration import RegistrationManager

    manager = RegistrationManager(
        agent_id=basic_agent_config.agent_id,
        agent_config=basic_agent_config,
        logger=test_logger,
    )

    yield manager

    await manager.close()


# ==================== Mock HTTP Server Fixtures ====================

@pytest.fixture
async def mock_platform_server():
    """Create a mock HTTP server that simulates the platform API."""
    from aiohttp import web

    registered_agents = {}
    messages_sent = []

    async def health_check(request):
        return web.json_response({
            "node_id": "test-platform-node",
            "status": "healthy",
            "load": 0.5,
            "priority": 50,
        })

    async def register_agent(request):
        data = await request.json()
        agent_id = data.get("agent_id")
        registered_agents[agent_id] = {
            **data,
            "registered_at": datetime.now().isoformat(),
            "status": "online",
        }
        return web.json_response({
            "registration_id": f"reg-{agent_id}",
            "agent_id": agent_id,
            "status": "registered",
            "token": f"token-{agent_id}",
        }, status=201)

    async def get_agent(request):
        agent_id = request.match_info["agent_id"]
        if agent_id in registered_agents:
            return web.json_response(registered_agents[agent_id])
        return web.json_response({"error": "Not found"}, status=404)

    async def discover_agents(request):
        return web.json_response({
            "agents": list(registered_agents.values()),
        })

    async def send_message(request):
        data = await request.json()
        messages_sent.append(data)
        return web.json_response({
            "status": "sent",
            "message_id": data.get("message_id"),
        })

    async def heartbeat(request):
        agent_id = request.match_info["agent_id"]
        if agent_id in registered_agents:
            registered_agents[agent_id]["last_heartbeat"] = datetime.now().isoformat()
            return web.json_response({"status": "acknowledged"})
        return web.json_response({"error": "Not found"}, status=404)

    app = web.Application()
    app.router.add_get("/health", health_check)
    app.router.add_post("/api/v1/agents/register", register_agent)
    app.router.add_get("/api/v1/agents/{agent_id}", get_agent)
    app.router.add_get("/api/v1/agents/discover", discover_agents)
    app.router.add_post("/api/v1/messages/send", send_message)
    app.router.add_post("/api/v1/agents/{agent_id}/heartbeat", heartbeat)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "127.0.0.1", 8999)
    await site.start()

    # Store references for test access
    app["registered_agents"] = registered_agents
    app["messages_sent"] = messages_sent

    yield app

    await runner.cleanup()


# ==================== Utility Fixtures ====================

@pytest.fixture
def sample_message_data():
    """Create sample message data for testing."""
    from datetime import datetime
    import uuid

    return {
        "message_id": str(uuid.uuid4()),
        "type": "request",
        "sender_id": "sender-001",
        "receiver_id": "receiver-001",
        "content": {"action": "test", "data": "sample"},
        "timestamp": datetime.now().isoformat(),
        "priority": 1,
        "ttl": 60,
        "metadata": {},
    }


@pytest.fixture
def sample_agent_data():
    """Create sample agent data for testing."""
    return {
        "agent_id": "test-agent-001",
        "name": "TestAgent",
        "description": "A test agent",
        "version": "1.0.0",
        "skills": [
            {"name": "test_skill", "description": "Test skill"},
        ],
        "capabilities": [
            {"name": "testing", "description": "Testing capability"},
        ],
        "protocols": ["http", "websocket"],
        "tags": ["test"],
        "is_online": True,
    }


@pytest.fixture
def sample_storage_data():
    """Create sample data for storage testing."""
    return {
        "key": "test/data/001",
        "value": {
            "name": "test",
            "data": [1, 2, 3],
            "nested": {"a": "b"},
        },
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "type": "test_data",
        },
    }


# ==================== Skip Conditions ====================

def skip_if_no_ipfs():
    """Skip test if IPFS is not available."""
    pytest.skip("IPFS connection not available")


def skip_if_no_grpc():
    """Skip test if gRPC is not available."""
    try:
        import grpc
        return False
    except ImportError:
        pytest.skip("gRPC library not installed")
        return True


# ==================== Helper Functions ====================

async def wait_for_condition(condition, timeout=5.0, interval=0.1):
    """Wait for a condition to become true."""
    import asyncio

    start = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start < timeout:
        if await condition() if asyncio.iscoroutinefunction(condition) else condition():
            return True
        await asyncio.sleep(interval)
    return False


@pytest.fixture
def wait_helper():
    """Provide the wait_for_condition helper."""
    return wait_for_condition
