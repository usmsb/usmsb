"""
USMSB SDK - Universal System Model of Social Behavior SDK

A comprehensive framework for building AI-powered applications based on the USMSB model.
Includes Agent SDK for creating, registering, and communicating with AI agents.
"""

__version__ = "0.9.0-alpha"
__author__ = "Felix Gu"

from importlib import import_module as _import_module

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

# Keep the original objects and import paths, but load their dependencies only
# when requested. Importing an element or a portable contract needs only stdlib.
_EXPORTS = {
    name: ("usmsb_sdk.core.elements", name)
    for name in (
        "Agent",
        "Object",
        "Goal",
        "Resource",
        "Rule",
        "Information",
        "Value",
        "Risk",
        "Environment",
    )
}
_EXPORTS.update(
    {
        name: ("usmsb_sdk.agent_sdk", name)
        for name in (
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
        )
    }
)
_EXPORTS.update(
    {
        "USMSBManager": ("usmsb_sdk.api.python.usmsb_manager", "USMSBManager"),
        "AgentBuilder": ("usmsb_sdk.api.python.agent_builder", "AgentBuilder"),
        "EnvironmentBuilder": ("usmsb_sdk.api.python.environment_builder", "EnvironmentBuilder"),
    }
)


def __getattr__(name: str):
    """Resolve a public export on first access, preserving import failures."""
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module, attribute = _EXPORTS[name]
    value = getattr(_import_module(module), attribute)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
