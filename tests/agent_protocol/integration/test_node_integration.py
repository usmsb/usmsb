"""
Node Integration Tests

Tests for P2P node management including:
- Node startup and shutdown
- Service discovery
- Broadcast service integration
- Sync service integration
- Node identity and registry
"""

import asyncio
import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from usmsb_sdk.node.decentralized_node import (
    P2PNode,
    NodeIdentity,
    NodeStatus,
    ServiceType,
    ServiceEndpoint,
    ServiceRequest,
    ServiceResponse,
    DistributedServiceRegistry,
)
from usmsb_sdk.platform.environment.broadcast_service import (
    EnvironmentBroadcastService,
    BroadcastType,
    BroadcastScope,
    BroadcastPriority,
    BroadcastMessage,
)


class TestNodeIdentity:
    """Tests for node identity."""

    def test_node_identity_creation(self):
        """Test creating node identity."""
        identity = NodeIdentity(
            node_id="node-001",
            public_key="public_key_hash",
            address="192.168.1.100",
            port=8080,
        )

        assert identity.node_id == "node-001"
        assert identity.address == "192.168.1.100"
        assert identity.port == 8080
        assert identity.reputation == 1.0

    def test_node_identity_to_dict(self):
        """Test converting node identity to dictionary."""
        identity = NodeIdentity(
            node_id="node-002",
            public_key="pk",
            address="127.0.0.1",
            port=9000,
            reputation=0.9,
            stake=100.0,
        )

        data = identity.to_dict()

        assert data["node_id"] == "node-002"
        assert data["reputation"] == 0.9
        assert data["stake"] == 100.0


class TestServiceEndpoint:
    """Tests for service endpoints."""

    def test_service_endpoint_creation(self):
        """Test creating service endpoint."""
        endpoint = ServiceEndpoint(
            service_id="service-001",
            service_type=ServiceType.LLM_INFERENCE,
            provider_node="node-001",
            endpoint="http://localhost:8080/llm",
            capabilities=["text_generation", "embeddings"],
        )

        assert endpoint.service_id == "service-001"
        assert endpoint.service_type == ServiceType.LLM_INFERENCE
        assert endpoint.is_available()

    def test_service_endpoint_availability(self):
        """Test service availability check."""
        endpoint = ServiceEndpoint(
            service_id="service-002",
            service_type=ServiceType.COMPUTE,
            provider_node="node-001",
            endpoint="http://localhost:8080/compute",
            load=50.0,
            max_capacity=100.0,
            uptime=0.95,
        )

        assert endpoint.is_available()

        # Over capacity
        endpoint.load = 150.0
        assert not endpoint.is_available()

        # Low uptime
        endpoint.load = 50.0
        endpoint.uptime = 0.8
        assert not endpoint.is_available()

    def test_service_endpoint_to_dict(self):
        """Test converting endpoint to dictionary."""
        endpoint = ServiceEndpoint(
            service_id="service-003",
            service_type=ServiceType.AGENT_HOSTING,
            provider_node="node-002",
            endpoint="http://localhost:8080/agents",
        )

        data = endpoint.to_dict()

        assert data["service_id"] == "service-003"
        assert data["service_type"] == "agent_hosting"


class TestDistributedServiceRegistry:
    """Tests for distributed service registry."""

    @pytest.fixture
    def registry(self):
        """Create a service registry for testing."""
        return DistributedServiceRegistry(node_id="test-node")

    @pytest.mark.asyncio
    async def test_registry_start_stop(self, registry):
        """Test starting and stopping the registry."""
        await registry.start()
        assert registry._running

        await registry.stop()
        assert not registry._running

    @pytest.mark.asyncio
    async def test_register_service(self, registry):
        """Test registering a service."""
        service = ServiceEndpoint(
            service_id="test-service",
            service_type=ServiceType.LLM_INFERENCE,
            provider_node="test-node",
            endpoint="http://localhost:8080/test",
        )

        await registry.register_service(service)

        assert "test-service" in registry._services
        assert ServiceType.LLM_INFERENCE in registry._service_by_type
        assert "test-service" in registry._service_by_type[ServiceType.LLM_INFERENCE]

    @pytest.mark.asyncio
    async def test_unregister_service(self, registry):
        """Test unregistering a service."""
        service = ServiceEndpoint(
            service_id="to-remove",
            service_type=ServiceType.STORAGE,
            provider_node="test-node",
            endpoint="http://localhost:8080/storage",
        )

        await registry.register_service(service)
        result = await registry.unregister_service("to-remove")

        assert result is True
        assert "to-remove" not in registry._services

    @pytest.mark.asyncio
    async def test_discover_services(self, registry):
        """Test discovering services."""
        # Register multiple services
        services = [
            ServiceEndpoint(
                service_id=f"service-{i}",
                service_type=ServiceType.COMPUTE if i % 2 == 0 else ServiceType.STORAGE,
                provider_node="test-node",
                endpoint=f"http://localhost:808{i}",
                capabilities=[f"cap-{i}"],
            )
            for i in range(5)
        ]

        for s in services:
            await registry.register_service(s)

        # Discover by type
        compute_services = await registry.discover_services(
            service_type=ServiceType.COMPUTE
        )
        assert len(compute_services) >= 2

        # Discover by capability
        cap_services = await registry.discover_services(
            capabilities=["cap-1"]
        )
        assert len(cap_services) >= 1

    @pytest.mark.asyncio
    async def test_discover_services_with_filters(self, registry):
        """Test discovering services with filters."""
        # Register services with different costs
        for i in range(3):
            service = ServiceEndpoint(
                service_id=f"cost-service-{i}",
                service_type=ServiceType.LLM_INFERENCE,
                provider_node="test-node",
                endpoint=f"http://localhost:808{i}",
                cost_per_request=float(i * 0.1),
            )
            await registry.register_service(service)

        # Filter by max cost
        cheap_services = await registry.discover_services(
            service_type=ServiceType.LLM_INFERENCE,
            max_cost=0.15,
        )

        for s in cheap_services:
            assert s.cost_per_request <= 0.15

    @pytest.mark.asyncio
    async def test_update_heartbeat(self, registry):
        """Test updating service heartbeat."""
        service = ServiceEndpoint(
            service_id="heartbeat-test",
            service_type=ServiceType.ORACLE,
            provider_node="test-node",
            endpoint="http://localhost:8080/oracle",
        )
        await registry.register_service(service)

        old_heartbeat = service.last_heartbeat
        await asyncio.sleep(0.1)

        await registry.update_heartbeat("heartbeat-test")
        new_heartbeat = registry._services["heartbeat-test"].last_heartbeat

        assert new_heartbeat > old_heartbeat

    @pytest.mark.asyncio
    async def test_cleanup_stale_services(self, registry):
        """Test cleaning up stale services."""
        # Register a service with old heartbeat
        import time

        stale_service = ServiceEndpoint(
            service_id="stale-service",
            service_type=ServiceType.SKILL_PROVIDER,
            provider_node="test-node",
            endpoint="http://localhost:8080/skills",
        )
        stale_service.last_heartbeat = time.time() - 400  # Older than TTL
        await registry.register_service(stale_service)

        # Cleanup
        cleaned = await registry.cleanup_stale_services()

        assert cleaned >= 1
        assert "stale-service" not in registry._services

    @pytest.mark.asyncio
    async def test_registry_gossip(self, registry):
        """Test registry gossip state exchange."""
        # Get state
        state = await registry.get_registry_state()

        assert "services" in state
        assert "nodes" in state
        assert "timestamp" in state

        # Merge state from another registry
        other_state = {
            "services": {
                "remote-service": {
                    "service_id": "remote-service",
                    "service_type": "gateway",
                    "provider_node": "remote-node",
                    "endpoint": "http://remote:8080/gateway",
                    "capabilities": [],
                    "load": 0,
                    "max_capacity": 100,
                    "cost_per_request": 0.001,
                    "avg_latency": 0,
                    "uptime": 1.0,
                    "last_heartbeat": time.time(),
                }
            },
            "nodes": {},
        }

        await registry.merge_registry_state(other_state)
        assert "remote-service" in registry._services


class TestP2PNode:
    """Tests for P2P Node."""

    @pytest.fixture
    def node_config(self):
        """Create node configuration."""
        return {
            "address": "127.0.0.1",
            "port": 19001,
            "bootstrap_peers": [],
            "capabilities": ["testing"],
            "metadata": {"test": True},
        }

    def test_node_creation(self, node_config):
        """Test creating a P2P node."""
        node = P2PNode(config=node_config)

        assert node.node_id is not None
        assert node.identity is not None
        assert node.status == NodeStatus.INITIALIZING

    @pytest.mark.asyncio
    async def test_node_start_stop(self, node_config):
        """Test starting and stopping a P2P node."""
        node = P2PNode(config=node_config)

        # Start
        started = await node.start()
        assert started
        assert node.status == NodeStatus.ACTIVE

        # Stop
        await node.stop()
        assert node.status == NodeStatus.OFFLINE

    @pytest.mark.asyncio
    async def test_node_info(self, node_config):
        """Test getting node info."""
        node = P2PNode(config=node_config)
        await node.start()

        info = await node.get_node_info()

        assert "node_id" in info
        assert "identity" in info
        assert "status" in info
        assert info["status"] == "active"

        await node.stop()

    @pytest.mark.asyncio
    async def test_register_service_on_node(self, node_config):
        """Test registering a service on the node."""
        node = P2PNode(config=node_config)
        await node.start()

        service = await node.register_service(
            service_type=ServiceType.LLM_INFERENCE,
            capabilities=["text_generation"],
            endpoint="http://localhost:8080/llm",
        )

        assert service.service_id is not None
        assert service.service_type == ServiceType.LLM_INFERENCE

        await node.stop()

    @pytest.mark.asyncio
    async def test_discover_services_on_node(self, node_config):
        """Test discovering services through the node."""
        node = P2PNode(config=node_config)
        await node.start()

        # Register a service
        await node.register_service(
            service_type=ServiceType.COMPUTE,
            capabilities=["cpu", "gpu"],
            endpoint="http://localhost:8080/compute",
        )

        # Discover
        services = await node.discover_services(
            service_type=ServiceType.COMPUTE,
        )

        assert len(services) >= 1

        await node.stop()


class TestBroadcastService:
    """Tests for Environment Broadcast Service."""

    @pytest.mark.asyncio
    async def test_broadcast_service_start_stop(self):
        """Test starting and stopping broadcast service."""
        service = EnvironmentBroadcastService()
        await service.start()
        assert service._running

        await service.stop()
        assert not service._running

    @pytest.mark.asyncio
    async def test_broadcast_message(self, broadcast_service):
        """Test broadcasting a message."""
        message = await broadcast_service.broadcast(
            broadcast_type=BroadcastType.AGENT_ONLINE,
            sender_id="agent-001",
            sender_name="TestAgent",
            content={"status": "online"},
        )

        assert message.message_id is not None
        assert message.broadcast_type == BroadcastType.AGENT_ONLINE
        assert not message.is_expired()

    @pytest.mark.asyncio
    async def test_subscribe_to_broadcasts(self, broadcast_service):
        """Test subscribing to broadcasts."""
        received_messages = []

        async def callback(msg):
            received_messages.append(msg)

        subscription = await broadcast_service.subscribe(
            agent_id="subscriber-001",
            topics=["test"],
            broadcast_types=[BroadcastType.ALERT],
            callback=callback,
        )

        assert subscription.subscription_id is not None

        # Broadcast matching message
        await broadcast_service.broadcast(
            broadcast_type=BroadcastType.ALERT,
            sender_id="sender",
            sender_name="Sender",
            content={"alert": "test"},
            topics=["test"],
        )

        # Allow delivery
        await asyncio.sleep(0.1)

        assert len(received_messages) >= 1

    @pytest.mark.asyncio
    async def test_broadcast_supply_available(self, broadcast_service):
        """Test broadcasting supply availability."""
        message = await broadcast_service.broadcast_supply_available(
            agent_id="supplier-001",
            agent_name="SupplierAgent",
            resource={"type": "compute", "capacity": 100},
            price_range={"min": 10, "max": 50},
        )

        assert message.broadcast_type == BroadcastType.SUPPLY_AVAILABLE
        assert "resource" in message.content

    @pytest.mark.asyncio
    async def test_broadcast_demand_seeking(self, broadcast_service):
        """Test broadcasting demand seeking."""
        message = await broadcast_service.broadcast_demand_seeking(
            agent_id="demander-001",
            agent_name="DemanderAgent",
            requirement={"type": "storage", "size": "1TB"},
            budget={"min": 5, "max": 20},
        )

        assert message.broadcast_type == BroadcastType.DEMAND_SEEKING
        assert "requirement" in message.content

    @pytest.mark.asyncio
    async def test_broadcast_direct_message(self, broadcast_service):
        """Test direct broadcast to specific agents."""
        received = []

        async def callback(msg):
            received.append(msg)

        # Subscribe
        await broadcast_service.subscribe(
            agent_id="target-agent",
            callback=callback,
        )

        # Direct broadcast
        await broadcast_service.broadcast(
            broadcast_type=BroadcastType.NEGOTIATION_REQUEST,
            sender_id="sender",
            sender_name="Sender",
            content={"negotiate": True},
            scope=BroadcastScope.DIRECT,
            target_agents=["target-agent"],
        )

        await asyncio.sleep(0.1)

        assert len(received) >= 1

    @pytest.mark.asyncio
    async def test_broadcast_market_signal(self, broadcast_service):
        """Test broadcasting market signals."""
        message = await broadcast_service.broadcast_market_signal(
            signal_type="price_change",
            data={"resource": "compute", "change": "+5%"},
        )

        assert message.broadcast_type == BroadcastType.MARKET_SIGNAL

    @pytest.mark.asyncio
    async def test_broadcast_alert(self, broadcast_service):
        """Test broadcasting alerts."""
        message = await broadcast_service.broadcast_alert(
            alert_level="high",
            message="System maintenance scheduled",
            affected_agents=["agent-1", "agent-2"],
        )

        assert message.broadcast_type == BroadcastType.ALERT
        assert message.priority == BroadcastPriority.HIGH

    @pytest.mark.asyncio
    async def test_message_history(self, broadcast_service):
        """Test message history."""
        # Broadcast several messages
        for i in range(5):
            await broadcast_service.broadcast(
                broadcast_type=BroadcastType.HEARTBEAT,
                sender_id=f"agent-{i}",
                sender_name=f"Agent {i}",
                content={"beat": i},
            )

        history = broadcast_service.get_message_history(
            broadcast_type=BroadcastType.HEARTBEAT,
        )

        assert len(history) >= 5

    @pytest.mark.asyncio
    async def test_unsubscribe(self, broadcast_service):
        """Test unsubscribing from broadcasts."""
        subscription = await broadcast_service.subscribe(
            agent_id="unsub-agent",
            topics=["test"],
        )

        result = await broadcast_service.unsubscribe(subscription.subscription_id)

        assert result is True
        assert subscription.subscription_id not in broadcast_service._subscriptions

    @pytest.mark.asyncio
    async def test_broadcast_statistics(self, broadcast_service):
        """Test broadcast service statistics."""
        # Broadcast some messages
        await broadcast_service.broadcast(
            broadcast_type=BroadcastType.AGENT_ONLINE,
            sender_id="agent",
            sender_name="Agent",
            content={},
        )

        stats = broadcast_service.get_statistics()

        assert stats["total_messages"] >= 1
        assert "messages_by_type" in stats


class TestNodeDiscovery:
    """Tests for node discovery mechanisms."""

    @pytest.mark.asyncio
    async def test_service_discovery_by_type(self, node_config):
        """Test discovering services by type."""
        node = P2PNode(config=node_config)
        await node.start()

        # Register services
        await node.register_service(
            service_type=ServiceType.BLOCKCHAIN,
            capabilities=["consensus"],
            endpoint="http://localhost:8080/blockchain",
        )

        services = await node.discover_services(
            service_type=ServiceType.BLOCKCHAIN,
        )

        assert any(s.service_type == ServiceType.BLOCKCHAIN for s in services)

        await node.stop()

    @pytest.mark.asyncio
    async def test_service_discovery_by_capability(self, node_config):
        """Test discovering services by capability."""
        node = P2PNode(config=node_config)
        await node.start()

        await node.register_service(
            service_type=ServiceType.COMPUTE,
            capabilities=["gpu", "cuda"],
            endpoint="http://localhost:8080/compute",
        )

        services = await node.discover_services(
            capabilities=["gpu"],
        )

        assert len(services) >= 1
        assert "gpu" in services[0].capabilities

        await node.stop()


class TestNodeHealthAndHeartbeat:
    """Tests for node health and heartbeat."""

    @pytest.mark.asyncio
    async def test_node_heartbeat(self, node_config):
        """Test node heartbeat mechanism."""
        node = P2PNode(config=node_config)
        await node.start()

        # Register a service
        service = await node.register_service(
            service_type=ServiceType.COORDINATION,
            capabilities=["orchestration"],
            endpoint="http://localhost:8080/coord",
        )

        # Check that heartbeat updates
        await asyncio.sleep(0.2)

        # Service should still be active
        services = await node.discover_services(
            service_type=ServiceType.COORDINATION,
        )

        assert len(services) >= 1

        await node.stop()

    @pytest.mark.asyncio
    async def test_broadcast_heartbeat(self, broadcast_service):
        """Test broadcasting heartbeat."""
        message = await broadcast_service.broadcast_heartbeat(
            agent_id="heartbeat-agent",
            agent_name="HeartbeatAgent",
            status={"cpu": 50, "memory": 60},
        )

        assert message.broadcast_type == BroadcastType.HEARTBEAT
        assert message.ttl == 60.0  # Short TTL for heartbeats


class TestMultiNodeInteraction:
    """Tests for interaction between multiple nodes."""

    @pytest.mark.asyncio
    async def test_two_node_communication(self):
        """Test communication between two nodes."""
        config1 = {
            "address": "127.0.0.1",
            "port": 19002,
            "bootstrap_peers": [],
            "capabilities": ["test1"],
        }
        config2 = {
            "address": "127.0.0.1",
            "port": 19003,
            "bootstrap_peers": ["127.0.0.1:19002"],
            "capabilities": ["test2"],
        }

        node1 = P2PNode(config=config1)
        node2 = P2PNode(config=config2)

        try:
            await node1.start()
            await node2.start()

            # Both nodes should be active
            assert node1.status == NodeStatus.ACTIVE
            assert node2.status == NodeStatus.ACTIVE

        finally:
            await node1.stop()
            await node2.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
