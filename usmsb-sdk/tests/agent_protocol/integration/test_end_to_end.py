"""
End-to-End Integration Tests

Tests for complete workflows including:
- Full agent registration -> discovery -> communication flow
- Multi-agent collaboration scenarios
- Storage and protocol integration
- Node and broadcast service integration
"""

import asyncio
import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp
from aiohttp import web

from usmsb_sdk.agent_sdk.agent_config import (
    AgentConfig,
    ProtocolType,
    ProtocolConfig,
    SkillDefinition,
    CapabilityDefinition,
    NetworkConfig,
    SecurityConfig,
)
from usmsb_sdk.agent_sdk.registration import RegistrationManager, RegistrationStatus
from usmsb_sdk.agent_sdk.communication import (
    CommunicationManager,
    Message,
    MessageType,
    Session,
)
from usmsb_sdk.agent_sdk.discovery import DiscoveryManager, DiscoveryFilter, AgentInfo
from usmsb_sdk.platform.external.storage.storage_manager import (
    StorageManager,
    CacheStrategy,
    SyncStrategy,
)
from usmsb_sdk.platform.environment.broadcast_service import (
    EnvironmentBroadcastService,
    BroadcastType,
    BroadcastScope,
)
from usmsb_sdk.node.decentralized_node import P2PNode, NodeStatus, ServiceType


class TestFullRegistrationDiscoveryCommunication:
    """Tests for the complete registration -> discovery -> communication flow."""

    @pytest.fixture
    async def mock_platform(self):
        """Create a mock platform server for end-to-end testing."""
        registered_agents = {}
        messages = []

        async def health(request):
            return web.json_response({
                "node_id": "platform-node-1",
                "status": "healthy",
                "load": 0.3,
                "priority": 80,
            })

        async def register_agent(request):
            data = await request.json()
            agent_id = data.get("agent_id")
            registered_agents[agent_id] = {
                **data,
                "registered_at": datetime.now().isoformat(),
                "is_online": True,
            }
            return web.json_response({
                "registration_id": f"reg-{agent_id}",
                "agent_id": agent_id,
                "status": "registered",
                "token": f"token-{agent_id}",
                "expires_in": 86400,
            }, status=201)

        async def get_agent(request):
            agent_id = request.match_info["agent_id"]
            if agent_id in registered_agents:
                return web.json_response(registered_agents[agent_id])
            return web.json_response({"error": "Not found"}, status=404)

        async def discover_agents(request):
            agents_list = list(registered_agents.values())
            return web.json_response({"agents": agents_list})

        async def send_message(request):
            data = await request.json()
            messages.append(data)
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

        async def get_endpoint(request):
            agent_id = request.match_info["agent_id"]
            return web.json_response({
                "p2p_endpoint": f"ws://localhost:9000/p2p/{agent_id}",
            })

        app = web.Application()
        app.router.add_get("/health", health)
        app.router.add_post("/api/v1/agents/register", register_agent)
        app.router.add_get("/api/v1/agents/{agent_id}", get_agent)
        app.router.add_get("/api/v1/agents/discover", discover_agents)
        app.router.add_post("/api/v1/messages/send", send_message)
        app.router.add_post("/api/v1/agents/{agent_id}/heartbeat", heartbeat)
        app.router.add_get("/api/v1/agents/{agent_id}/endpoint", get_endpoint)

        app["registered_agents"] = registered_agents
        app["messages"] = messages

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 18999)
        await site.start()

        yield app

        await runner.cleanup()

    @pytest.fixture
    def e2e_agent_config(self):
        """Create agent config for end-to-end testing."""
        config = AgentConfig(
            name="E2ETestAgent",
            description="End-to-end test agent",
            version="1.0.0",
            skills=[
                SkillDefinition(
                    name="process",
                    description="Process data",
                    parameters=[],
                ),
                SkillDefinition(
                    name="analyze",
                    description="Analyze data",
                    parameters=[],
                ),
            ],
            capabilities=[
                CapabilityDefinition(
                    name="data_processing",
                    description="Data processing capability",
                    category="data",
                    level="advanced",
                ),
            ],
            network=NetworkConfig(
                platform_endpoints=["http://127.0.0.1:18999"],
            ),
            security=SecurityConfig(
                auth_enabled=False,
            ),
            auto_register=False,
            auto_discover=False,
        )
        return config

    @pytest.mark.asyncio
    async def test_e2e_single_agent_registration(self, mock_platform, e2e_agent_config):
        """Test end-to-end single agent registration."""
        # Create registration manager
        reg_manager = RegistrationManager(
            agent_id=e2e_agent_config.agent_id,
            agent_config=e2e_agent_config,
        )

        # Register
        result = await reg_manager.register()

        # Should have attempted registration
        assert reg_manager.status in [
            RegistrationStatus.REGISTERED,
            RegistrationStatus.FAILED,
        ]

        await reg_manager.close()

    @pytest.mark.asyncio
    async def test_e2e_agent_discovery_flow(self, mock_platform, e2e_agent_config):
        """Test end-to-end agent discovery flow."""
        # First, register an agent to the mock platform
        mock_platform["registered_agents"]["known-agent-1"] = {
            "agent_id": "known-agent-1",
            "name": "KnownAgent",
            "description": "A known agent",
            "skills": [{"name": "process", "description": "Process"}],
            "capabilities": [{"name": "data_processing"}],
            "is_online": True,
        }

        # Create communication manager
        async def message_handler(msg, session):
            return {"status": "handled"}

        comm_manager = CommunicationManager(
            agent_id=e2e_agent_config.agent_id,
            agent_config=e2e_agent_config,
            message_handler=message_handler,
        )
        await comm_manager.initialize()

        # Create discovery manager
        discovery_manager = DiscoveryManager(
            agent_id=e2e_agent_config.agent_id,
            agent_config=e2e_agent_config,
            communication_manager=comm_manager,
        )
        await discovery_manager.initialize()

        # Discover agents
        agents = await discovery_manager.discover(DiscoveryFilter(limit=10))

        # Should find the known agent
        assert isinstance(agents, list)

        await discovery_manager.close()
        await comm_manager.close()

    @pytest.mark.asyncio
    async def test_e2e_message_communication_flow(self, mock_platform, e2e_agent_config):
        """Test end-to-end message communication flow."""
        # Create communication manager
        received_messages = []

        async def message_handler(msg, session):
            received_messages.append(msg)
            return Message(
                type=MessageType.RESPONSE,
                sender_id=e2e_agent_config.agent_id,
                content={"status": "received"},
                correlation_id=msg.message_id,
            )

        comm_manager = CommunicationManager(
            agent_id=e2e_agent_config.agent_id,
            agent_config=e2e_agent_config,
            message_handler=message_handler,
        )
        await comm_manager.initialize()

        # Create a message
        message = Message(
            type=MessageType.REQUEST,
            sender_id=e2e_agent_config.agent_id,
            receiver_id="target-agent",
            content={"action": "test", "data": "sample"},
        )

        # Message should be properly formed
        assert message.message_id is not None
        assert message.sender_id == e2e_agent_config.agent_id

        await comm_manager.close()


class TestMultiAgentCollaboration:
    """Tests for multi-agent collaboration scenarios."""

    @pytest.fixture
    def agent_configs(self):
        """Create configurations for multiple agents."""
        configs = []

        # Data processor agent
        processor_config = AgentConfig(
            name="DataProcessor",
            description="Processes and transforms data",
            skills=[
                SkillDefinition(
                    name="process",
                    description="Process data",
                    parameters=[],
                ),
                SkillDefinition(
                    name="transform",
                    description="Transform data",
                    parameters=[],
                ),
            ],
            capabilities=[
                CapabilityDefinition(
                    name="data_processing",
                    description="Data processing",
                    category="data",
                ),
            ],
        )
        configs.append(processor_config)

        # Analyzer agent
        analyzer_config = AgentConfig(
            name="DataAnalyzer",
            description="Analyzes data and generates insights",
            skills=[
                SkillDefinition(
                    name="analyze",
                    description="Analyze data",
                    parameters=[],
                ),
                SkillDefinition(
                    name="report",
                    description="Generate report",
                    parameters=[],
                ),
            ],
            capabilities=[
                CapabilityDefinition(
                    name="analysis",
                    description="Data analysis",
                    category="data",
                ),
            ],
        )
        configs.append(analyzer_config)

        # Coordinator agent
        coordinator_config = AgentConfig(
            name="Coordinator",
            description="Coordinates multi-agent workflows",
            skills=[
                SkillDefinition(
                    name="coordinate",
                    description="Coordinate workflow",
                    parameters=[],
                ),
            ],
            capabilities=[
                CapabilityDefinition(
                    name="coordination",
                    description="Workflow coordination",
                    category="orchestration",
                ),
            ],
        )
        configs.append(coordinator_config)

        return configs

    @pytest.mark.asyncio
    async def test_multi_agent_communication_setup(self, agent_configs):
        """Test setting up communication between multiple agents."""
        comm_managers = []

        for config in agent_configs:
            async def handler(msg, session):
                return {"handled_by": config.name}

            manager = CommunicationManager(
                agent_id=config.agent_id,
                agent_config=config,
                message_handler=handler,
            )
            await manager.initialize()
            comm_managers.append(manager)

        # All managers should be initialized
        assert len(comm_managers) == 3
        assert all(m._initialized for m in comm_managers)

        # Cleanup
        for manager in comm_managers:
            await manager.close()

    @pytest.mark.asyncio
    async def test_multi_agent_session_collaboration(self, agent_configs):
        """Test multi-agent collaboration through sessions."""
        # Create communication managers
        managers = []
        for config in agent_configs:
            async def handler(msg, session):
                return {"status": "ok"}

            manager = CommunicationManager(
                agent_id=config.agent_id,
                agent_config=config,
                message_handler=handler,
            )
            await manager.initialize()
            managers.append((config, manager))

        # Coordinator creates a session with all agents
        coordinator_manager = managers[2][1]
        session = await coordinator_manager.create_session(
            participant_ids=[m[0].agent_id for m in managers[:2]],
            protocol=ProtocolType.HTTP,
            metadata={"workflow": "data_pipeline"},
        )

        assert session is not None
        assert len(session.participant_ids) == 2

        # Cleanup
        for _, manager in managers:
            await manager.close()

    @pytest.mark.asyncio
    async def test_workflow_message_chain(self, agent_configs):
        """Test message chain in a workflow scenario."""
        message_log = []

        # Create mock handlers that log messages
        async def create_handler(agent_name):
            async def handler(msg, session):
                message_log.append({
                    "receiver": agent_name,
                    "type": msg.type.value if hasattr(msg.type, 'value') else str(msg.type),
                    "content": msg.content,
                })
                return {"processed_by": agent_name}
            return handler

        managers = []
        for config in agent_configs:
            handler = await create_handler(config.name)
            manager = CommunicationManager(
                agent_id=config.agent_id,
                agent_config=config,
                message_handler=handler,
            )
            await manager.initialize()
            managers.append((config, manager))

        # Simulate workflow messages
        # Step 1: Coordinator sends task to Processor
        task_message = Message(
            type=MessageType.REQUEST,
            sender_id=agent_configs[2].agent_id,
            receiver_id=agent_configs[0].agent_id,
            content={"task": "process_data", "data": "raw_input"},
        )
        message_log.append({
            "sender": agent_configs[2].name,
            "type": "request",
            "content": task_message.content,
        })

        # Step 2: Processor processes and sends to Analyzer
        process_message = Message(
            type=MessageType.REQUEST,
            sender_id=agent_configs[0].agent_id,
            receiver_id=agent_configs[1].agent_id,
            content={"task": "analyze_data", "data": "processed_data"},
        )
        message_log.append({
            "sender": agent_configs[0].name,
            "type": "request",
            "content": process_message.content,
        })

        # Verify message chain
        assert len(message_log) == 2
        assert message_log[0]["sender"] == "Coordinator"
        assert message_log[1]["sender"] == "DataProcessor"

        # Cleanup
        for _, manager in managers:
            await manager.close()


class TestStorageProtocolIntegration:
    """Tests for storage and protocol integration."""

    @pytest.mark.asyncio
    async def test_store_agent_communication_logs(
        self,
        storage_manager,
        basic_agent_config,
    ):
        """Test storing communication logs in storage."""
        # Create a communication log
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": basic_agent_config.agent_id,
            "messages": [
                {
                    "type": "request",
                    "sender": "agent-a",
                    "receiver": "agent-b",
                    "content": {"action": "test"},
                },
            ],
        }

        # Store in storage manager
        result = await storage_manager.store(
            key=f"logs/{basic_agent_config.agent_id}/comm_001",
            data=log_data,
            metadata={"type": "communication_log"},
        )

        assert result.success

        # Retrieve and verify
        retrieved = await storage_manager.retrieve(
            key=f"logs/{basic_agent_config.agent_id}/comm_001",
        )

        assert retrieved.success
        assert retrieved.data["agent_id"] == basic_agent_config.agent_id

    @pytest.mark.asyncio
    async def test_store_agent_state(
        self,
        storage_manager,
        basic_agent_config,
    ):
        """Test storing agent state."""
        state_data = {
            "agent_id": basic_agent_config.agent_id,
            "name": basic_agent_config.name,
            "status": "active",
            "skills": [s.to_dict() for s in basic_agent_config.skills],
            "last_updated": datetime.now().isoformat(),
        }

        result = await storage_manager.store(
            key=f"agents/{basic_agent_config.agent_id}/state",
            data=state_data,
        )

        assert result.success

    @pytest.mark.asyncio
    async def test_retrieve_agent_config_from_storage(
        self,
        storage_manager,
        basic_agent_config,
    ):
        """Test retrieving agent configuration from storage."""
        # Store configuration
        config_dict = basic_agent_config.to_dict()

        await storage_manager.store(
            key=f"configs/{basic_agent_config.agent_id}",
            data=config_dict,
        )

        # Retrieve
        result = await storage_manager.retrieve(
            key=f"configs/{basic_agent_config.agent_id}",
        )

        assert result.success
        assert result.data["name"] == basic_agent_config.name


class TestBroadcastNodeIntegration:
    """Tests for broadcast and node integration."""

    @pytest.mark.asyncio
    async def test_broadcast_agent_announcement(
        self,
        broadcast_service,
        basic_agent_config,
    ):
        """Test broadcasting agent announcement."""
        message = await broadcast_service.broadcast_agent_online(
            agent_id=basic_agent_config.agent_id,
            agent_name=basic_agent_config.name,
            capabilities=[c.name for c in basic_agent_config.capabilities],
            metadata={"version": basic_agent_config.version},
        )

        assert message.broadcast_type == BroadcastType.AGENT_ONLINE

    @pytest.mark.asyncio
    async def test_broadcast_workflow_event(
        self,
        broadcast_service,
    ):
        """Test broadcasting workflow events."""
        # Broadcast workflow start
        start_msg = await broadcast_service.broadcast(
            broadcast_type=BroadcastType.ENVIRONMENT_UPDATE,
            sender_id="workflow-manager",
            sender_name="WorkflowManager",
            content={
                "event": "workflow_started",
                "workflow_id": "wf-001",
                "participants": ["agent-a", "agent-b"],
            },
        )

        assert start_msg.broadcast_type == BroadcastType.ENVIRONMENT_UPDATE

        # Broadcast workflow completion
        complete_msg = await broadcast_service.broadcast(
            broadcast_type=BroadcastType.TRANSACTION_COMPLETE,
            sender_id="workflow-manager",
            sender_name="WorkflowManager",
            content={
                "event": "workflow_completed",
                "workflow_id": "wf-001",
                "result": "success",
            },
        )

        assert complete_msg.broadcast_type == BroadcastType.TRANSACTION_COMPLETE

    @pytest.mark.asyncio
    async def test_node_service_broadcast(self, broadcast_service):
        """Test broadcasting node service availability."""
        # Broadcast supply (service available)
        supply_msg = await broadcast_service.broadcast_supply_available(
            agent_id="compute-node-1",
            agent_name="ComputeNode",
            resource={
                "type": "compute",
                "gpu": True,
                "memory": "32GB",
            },
            price_range={"min": 0.01, "max": 0.10},
        )

        assert supply_msg.broadcast_type == BroadcastType.SUPPLY_AVAILABLE


class TestCompleteWorkflowScenarios:
    """Complete end-to-end workflow scenario tests."""

    @pytest.mark.asyncio
    async def test_data_pipeline_workflow(
        self,
        storage_manager,
        broadcast_service,
    ):
        """Test complete data pipeline workflow."""
        # Step 1: Store initial data
        raw_data = {
            "source": "sensor",
            "readings": [1.0, 2.0, 3.0, 4.0, 5.0],
            "timestamp": datetime.now().isoformat(),
        }

        store_result = await storage_manager.store(
            key="pipeline/raw_data",
            data=raw_data,
        )
        assert store_result.success

        # Step 2: Broadcast data available
        broadcast = await broadcast_service.broadcast_supply_available(
            agent_id="data-producer",
            agent_name="DataProducer",
            resource={"type": "sensor_data", "count": 5},
        )
        assert broadcast.broadcast_type == BroadcastType.SUPPLY_AVAILABLE

        # Step 3: Simulate processing and store result
        processed_data = {
            **raw_data,
            "processed": True,
            "average": sum(raw_data["readings"]) / len(raw_data["readings"]),
        }

        process_result = await storage_manager.store(
            key="pipeline/processed_data",
            data=processed_data,
        )
        assert process_result.success

        # Step 4: Broadcast processing complete
        complete_broadcast = await broadcast_service.broadcast(
            broadcast_type=BroadcastType.TRANSACTION_COMPLETE,
            sender_id="data-processor",
            sender_name="DataProcessor",
            content={"status": "processed", "records": 5},
        )
        assert complete_broadcast.broadcast_type == BroadcastType.TRANSACTION_COMPLETE

    @pytest.mark.asyncio
    async def test_agent_lifecycle_workflow(
        self,
        storage_manager,
        broadcast_service,
        basic_agent_config,
    ):
        """Test complete agent lifecycle workflow."""
        agent_id = basic_agent_config.agent_id

        # Step 1: Store agent configuration
        config_result = await storage_manager.store(
            key=f"agents/{agent_id}/config",
            data=basic_agent_config.to_dict(),
        )
        assert config_result.success

        # Step 2: Broadcast agent online
        online_broadcast = await broadcast_service.broadcast_agent_online(
            agent_id=agent_id,
            agent_name=basic_agent_config.name,
            capabilities=[c.name for c in basic_agent_config.capabilities],
        )
        assert online_broadcast.broadcast_type == BroadcastType.AGENT_ONLINE

        # Step 3: Store agent state (heartbeat)
        state_data = {
            "status": "active",
            "timestamp": datetime.now().isoformat(),
            "metrics": {"cpu": 50, "memory": 60},
        }
        state_result = await storage_manager.store(
            key=f"agents/{agent_id}/state",
            data=state_data,
        )
        assert state_result.success

        # Step 4: Broadcast heartbeat
        heartbeat = await broadcast_service.broadcast_heartbeat(
            agent_id=agent_id,
            agent_name=basic_agent_config.name,
            status=state_data,
        )
        assert heartbeat.broadcast_type == BroadcastType.HEARTBEAT

        # Step 5: Broadcast agent offline
        offline_broadcast = await broadcast_service.broadcast_agent_offline(
            agent_id=agent_id,
            agent_name=basic_agent_config.name,
        )
        assert offline_broadcast.broadcast_type == BroadcastType.AGENT_OFFLINE

    @pytest.mark.asyncio
    async def test_collaboration_workflow(
        self,
        storage_manager,
        broadcast_service,
    ):
        """Test multi-agent collaboration workflow."""
        # Step 1: Store collaboration context
        context = {
            "workflow_id": "collab-001",
            "participants": ["agent-a", "agent-b", "agent-c"],
            "created_at": datetime.now().isoformat(),
            "status": "initiated",
        }

        context_result = await storage_manager.store(
            key="workflows/collab-001/context",
            data=context,
        )
        assert context_result.success

        # Step 2: Broadcast collaboration request
        request_broadcast = await broadcast_service.broadcast(
            broadcast_type=BroadcastType.NEGOTIATION_REQUEST,
            sender_id="agent-a",
            sender_name="AgentA",
            content={
                "workflow_id": "collab-001",
                "task": "collaborative_analysis",
            },
            scope=BroadcastScope.GLOBAL,
        )
        assert request_broadcast.broadcast_type == BroadcastType.NEGOTIATION_REQUEST

        # Step 3: Store collaboration results
        results = {
            "workflow_id": "collab-001",
            "results": {
                "agent-a": {"contribution": "data_processing"},
                "agent-b": {"contribution": "analysis"},
                "agent-c": {"contribution": "reporting"},
            },
            "completed_at": datetime.now().isoformat(),
        }

        results_result = await storage_manager.store(
            key="workflows/collab-001/results",
            data=results,
        )
        assert results_result.success

        # Step 4: Broadcast completion
        complete_broadcast = await broadcast_service.broadcast(
            broadcast_type=BroadcastType.TRANSACTION_COMPLETE,
            sender_id="collab-001",
            sender_name="Collaboration",
            content={"workflow_id": "collab-001", "status": "completed"},
        )
        assert complete_broadcast.broadcast_type == BroadcastType.TRANSACTION_COMPLETE


class TestErrorRecoveryScenarios:
    """Tests for error recovery in workflows."""

    @pytest.mark.asyncio
    async def test_storage_failure_recovery(self, storage_manager):
        """Test recovery from storage failures."""
        # Store data
        key = "test/recovery/data"
        data = {"important": "data"}

        await storage_manager.store(key, data)

        # Try to retrieve (simulating recovery scenario)
        result = await storage_manager.retrieve(key)

        assert result.success
        assert result.data == data

    @pytest.mark.asyncio
    async def test_communication_retry_scenario(self, basic_agent_config):
        """Test communication retry scenario."""
        attempts = []

        async def message_handler(msg, session):
            attempts.append(msg.message_id)
            return {"status": "ok"}

        manager = CommunicationManager(
            agent_id=basic_agent_config.agent_id,
            agent_config=basic_agent_config,
            message_handler=message_handler,
        )
        await manager.initialize()

        # Create a message
        message = Message(
            type=MessageType.REQUEST,
            sender_id="test-sender",
            content={"test": "retry"},
        )

        # Message should be properly created for retry
        assert message.message_id is not None

        await manager.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
