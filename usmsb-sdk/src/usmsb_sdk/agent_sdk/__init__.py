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
- Platform integration (marketplace, wallet, negotiation, collaboration)
- Learning and optimization
- Gene Capsule system for precise experience-based matching

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

    # Platform integration
    await agent.register_to_platform()
    opportunities = await agent.find_work()
    balance = await agent.get_balance()

    # Gene Capsule - add and manage experiences
    await agent.add_experience({
        "task_type": "data_analysis",
        "techniques": ["pandas", "numpy"],
        "outcome": "success",
        ...
    })
"""

from usmsb_sdk.agent_sdk.base_agent import BaseAgent
from usmsb_sdk.agent_sdk.agent_config import (
    AgentConfig,
    ProtocolConfig,
    ProtocolType,
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
    # Enhanced Discovery
    EnhancedDiscoveryManager,
    MatchDimension,
    DimensionScore,
    MultiDimensionalMatchResult,
    SearchCriteria,
    WatchCondition,
    WatchEvent,
    AgentComparison,
)
from usmsb_sdk.agent_sdk.http_server import (
    HTTPServer,
    run_agent_with_http,
)
from usmsb_sdk.agent_sdk.p2p_server import (
    P2PServer,
    PeerInfo,
    DHT,
    run_agent_with_p2p,
)

# Platform integration modules
from usmsb_sdk.agent_sdk.platform_client import (
    PlatformClient,
    RegistrationResult,
    APIResponse,
)
from usmsb_sdk.agent_sdk.marketplace import (
    MarketplaceManager,
    ServiceDefinition,
    Service,
    DemandDefinition,
    Demand,
    Opportunity,
    MatchScore,
    PriceRange,
)
from usmsb_sdk.agent_sdk.wallet import (
    WalletManager,
    WalletBalance,
    StakeInfo,
    StakeResult,
    Transaction,
    WalletLimits,
)
from usmsb_sdk.agent_sdk.negotiation import (
    NegotiationManager,
    NegotiationSession,
    NegotiationTerms,
    NegotiationContext,
    NegotiationRound,
    ProposalResult,
)
from usmsb_sdk.agent_sdk.collaboration import (
    CollaborationManager,
    CollaborationSession,
    CollaborationRole,
    CollaborationParticipant,
    CollaborationPlan,
    Contribution,
    CollaborationResult,
)
from usmsb_sdk.agent_sdk.workflow import (
    WorkflowManager,
    Workflow,
    WorkflowStep,
    WorkflowResult,
)
from usmsb_sdk.agent_sdk.learning import (
    LearningManager,
    LearningInsight,
    PerformanceAnalysis,
    MatchingStrategy,
    MarketInsights,
    Experience,
)
from usmsb_sdk.agent_sdk.gene_capsule import (
    GeneCapsuleManager,
    GeneCapsule,
    ExperienceGene,
    SkillGene,
    PatternGene,
    ExperienceValueScore,
    DesensitizationResult,
    ChangeRecord,
    ShareLevel,
    VerificationStatus,
    ProficiencyLevel,
    PatternType,
)

# Alias for backward compatibility
AgentCapability = CapabilityDefinition


def create_agent(
    agent_id: str = None,
    name: str = "DefaultAgent",
    description: str = "",
    **kwargs
) -> BaseAgent:
    """
    Factory function to create a simple agent instance.

    Args:
        agent_id: Unique agent identifier (auto-generated if not provided)
        name: Agent name
        description: Agent description
        **kwargs: Additional configuration options

    Returns:
        A SimpleAgent instance
    """
    from uuid import uuid4

    class SimpleAgent(BaseAgent):
        """A simple agent implementation for quick prototyping"""

        async def initialize(self):
            self.logger.info(f"SimpleAgent {self.name} initialized")

        async def handle_message(self, message, session=None):
            self.logger.info(f"Received message: {message}")
            return {"status": "received", "message_id": getattr(message, 'message_id', None)}

        async def execute_skill(self, skill_name, params):
            self.logger.info(f"Executing skill: {skill_name} with params: {params}")
            return {"skill": skill_name, "result": "executed", "params": params}

        async def shutdown(self):
            self.logger.info(f"SimpleAgent {self.name} shutting down")

    config = AgentConfig(
        agent_id=agent_id or str(uuid4()),
        name=name,
        description=description,
        **kwargs
    )
    return SimpleAgent(config)


__all__ = [
    # Base Agent
    "BaseAgent",
    # Configuration
    "AgentConfig",
    "ProtocolConfig",
    "ProtocolType",
    "SkillDefinition",
    "CapabilityDefinition",
    "AgentCapability",  # Alias
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
    "EnhancedDiscoveryManager",
    "SearchCriteria",
    "MultiDimensionalMatchResult",
    "DimensionScore",
    "MatchDimension",
    "WatchCondition",
    "WatchEvent",
    "AgentComparison",
    # HTTP Server
    "HTTPServer",
    "run_agent_with_http",
    # P2P Server
    "P2PServer",
    "PeerInfo",
    "DHT",
    "run_agent_with_p2p",
    # Platform Client
    "PlatformClient",
    "RegistrationResult",
    "APIResponse",
    # Marketplace
    "MarketplaceManager",
    "ServiceDefinition",
    "Service",
    "DemandDefinition",
    "Demand",
    "Opportunity",
    "MatchScore",
    "PriceRange",
    # Wallet
    "WalletManager",
    "WalletBalance",
    "StakeInfo",
    "StakeResult",
    "Transaction",
    "WalletLimits",
    # Negotiation
    "NegotiationManager",
    "NegotiationSession",
    "NegotiationTerms",
    "NegotiationContext",
    "NegotiationRound",
    "ProposalResult",
    # Collaboration
    "CollaborationManager",
    "CollaborationSession",
    "CollaborationRole",
    "CollaborationParticipant",
    "CollaborationPlan",
    "Contribution",
    "CollaborationResult",
    # Workflow
    "WorkflowManager",
    "Workflow",
    "WorkflowStep",
    "WorkflowResult",
    # Learning
    "LearningManager",
    "LearningInsight",
    "PerformanceAnalysis",
    "MatchingStrategy",
    "MarketInsights",
    "Experience",
    # Gene Capsule
    "GeneCapsuleManager",
    "GeneCapsule",
    "ExperienceGene",
    "SkillGene",
    "PatternGene",
    "ExperienceValueScore",
    "DesensitizationResult",
    "ChangeRecord",
    "ShareLevel",
    "VerificationStatus",
    "ProficiencyLevel",
    "PatternType",
    # Factory
    "create_agent",
]

__version__ = "1.4.0"
__author__ = "USMSB SDK Team"
