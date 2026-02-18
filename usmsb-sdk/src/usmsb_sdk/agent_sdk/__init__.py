"""
Agent SDK - Unified Agent Development Framework

This SDK provides a comprehensive framework for building intelligent agents
that support multiple communication protocols (A2A, MCP, P2P, HTTP/WebSocket/gRPC).

Key Features:
- BaseAgent abstract class for agent development
- Multi-protocol registration support
- Unified communication interface
- P2P direct connection capability
- Automatic agent discovery
- Skill definition and publishing

Example Usage:
    from usmsb_sdk.agent_sdk import BaseAgent, AgentConfig

    class MyAgent(BaseAgent):
        async def initialize(self):
            # Custom initialization
            pass

        async def handle_message(self, message):
            # Handle incoming messages
            return {"status": "processed"}

        async def execute_skill(self, skill_name, params):
            # Execute skills
            pass

    config = AgentConfig(
        name="my_agent",
        description="My intelligent agent",
        capabilities=["text_processing", "data_analysis"]
    )

    agent = MyAgent(config)
    await agent.start()
"""

from usmsb_sdk.agent_sdk.base_agent import BaseAgent
from usmsb_sdk.agent_sdk.agent_config import (
    AgentConfig,
    ProtocolConfig,
    SkillDefinition,
    CapabilityDefinition,
)
from usmsb_sdk.agent_sdk.registration import (
    RegistrationManager,
    RegistrationStatus,
    PlatformNode,
)
from usmsb_sdk.agent_sdk.communication import (
    CommunicationManager,
    Message,
    MessageType,
    Session,
    P2PConnection,
)
from usmsb_sdk.agent_sdk.discovery import (
    DiscoveryManager,
    DiscoveryFilter,
    AgentInfo,
    RecommendationResult,
)

__all__ = [
    # Base Agent
    "BaseAgent",
    # Configuration
    "AgentConfig",
    "ProtocolConfig",
    "SkillDefinition",
    "CapabilityDefinition",
    # Registration
    "RegistrationManager",
    "RegistrationStatus",
    "PlatformNode",
    # Communication
    "CommunicationManager",
    "Message",
    "MessageType",
    "Session",
    "P2PConnection",
    # Discovery
    "DiscoveryManager",
    "DiscoveryFilter",
    "AgentInfo",
    "RecommendationResult",
]

__version__ = "1.0.0"
__author__ = "USMSB SDK Team"
