"""
USMSB SDK - Universal System Model of Social Behavior SDK

A comprehensive framework for building AI-powered applications based on the USMSB model.
Includes Agent SDK for creating, registering, and communicating with AI agents.
"""

__version__ = "0.9.0-alpha"
__author__ = "Felix Gu"

# Agent SDK
from usmsb_sdk.agent_sdk import (
    AgentCapability,
    AgentConfig,
    BaseAgent,
    CapabilityDefinition,
    CommunicationManager,
    DiscoveryManager,
    ProtocolConfig,
    ProtocolType,
    RegistrationManager,
    SkillDefinition,
    create_agent,
)
from usmsb_sdk.api.python.agent_builder import AgentBuilder
from usmsb_sdk.api.python.environment_builder import EnvironmentBuilder
from usmsb_sdk.api.python.usmsb_manager import USMSBManager
from usmsb_sdk.core.elements import (
    Agent,
    Environment,
    Goal,
    Information,
    Object,
    Resource,
    Risk,
    Rule,
    Value,
)

__all__ = [
    # Core Elements
    "Agent",
    "Object",
    "Goal",
    "Resource",
    "Rule",
    "Information",
    "Value",
    "Risk",
    "Environment",
    # SDK Manager
    "USMSBManager",
    # Builders
    "AgentBuilder",
    "EnvironmentBuilder",
    # Agent SDK
    "BaseAgent",
    "AgentConfig",
    "AgentCapability",
    "CapabilityDefinition",
    "SkillDefinition",
    "ProtocolConfig",
    "ProtocolType",
    "RegistrationManager",
    "CommunicationManager",
    "DiscoveryManager",
    "create_agent",
]
